import base64
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from sarvamai import SarvamAI

from app import config, db, models, sarvam_client as sarvam, voice
from app.main import _classify, opened


def sample_audio():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as clip:
        clip.setparams((1, 2, 8000, 0, "NONE", ""))
        clip.writeframes(bytes(20))
    return base64.b64encode(buffer.getvalue()).decode()


class VoiceTests(unittest.TestCase):
    def test_sdk_audio_and_malformed_response(self):
        audio = sample_audio()
        def respond(request):
            body = json.loads(request.content)
            self.assertEqual(body["model"], "bulbul:v3")
            self.assertEqual(body["language_code"], "hi-IN")
            self.assertEqual(body["speaker"], "shubh")
            return httpx.Response(200, json={"audios": [audio], "request_id": "demo"})
        with httpx.Client(transport=httpx.MockTransport(respond)) as http:
            client = SarvamAI(api_subscription_key="test", httpx_client=http)
            self.assertEqual(sarvam.bulbul(client, "Ruko!", "hi", "shubh"), audio)
            audio = base64.b64encode(b"invalid").decode()
            with self.assertRaises(ValueError):
                sarvam.bulbul(client, "Ruko!", "hi", "shubh")

    def test_scan_and_opened_use_cached_language_and_flag(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db, "DB_PATH", Path(tmp) / "db"), patch.object(
            config, "FLAGSMITH_ENV_KEY", ""
        ), patch.dict(voice.CLIPS, {("hi", "warning"): "warn", ("hi", "first_hour"): "help"}):
            db.initialize()
            user, _ = db.create_user(models.Identify(name="Asha", lang="hi", role="parent"))
            _, _, scan = _classify(user["id"], b"file", "demo.apk", "", None)
            self.assertEqual(scan["audio_b64"], "warn")
            ref = models.ScanRef(scan_id=scan["scan_id"])
            response = opened(ref)
            self.assertEqual(response["audio_b64"], "help")
            self.assertIn("demo.apk", response["steps"][2])
            self.assertIn("1930", response["steps"][1])
            self.assertEqual(len(response["steps"]), 5)
            from app.flags import UserFlags
            with patch("app.flags.for_user", return_value=UserFlags({"strict_mode": False, "spoken_summary": False}, [])):
                self.assertIsNone(opened(ref)["audio_b64"])
                self.assertIsNone(_classify(user["id"], b"file", "demo.apk", "", None)[2]["audio_b64"])
            with self.assertRaises(HTTPException) as ctx:
                opened(models.ScanRef(scan_id="missing"))
            self.assertEqual(ctx.exception.status_code, 404)


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_pairing_poll_before_and_after_link(self):
        from app.main import app
        with tempfile.TemporaryDirectory() as tmp, patch.object(db, "DB_PATH", Path(tmp) / "db"):
            db.initialize()
            parent, code = db.create_user(models.Identify(name="Asha", lang="hi", role="parent"))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                route = "/api/pairing/" + parent["id"]
                for url in ("/api/pairing/unknown", route):
                    response = await client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), {"linked": False, "child_name": None})
                db.pair_child(code, 42, "Riya")
                self.assertEqual((await client.get(route)).json(), {"linked": True, "child_name": "Riya"})

    async def test_missing_audio_recovers_without_regenerating_good_clips(self):
        good = sample_audio()
        def synthesize(text, lang):
            if lang == "kn":
                raise TimeoutError()
            return good
        with patch.dict(voice.CLIPS, clear=True), patch.object(config, "SARVAM_API_KEY", "test"), patch.object(
            sarvam, "synthesize", side_effect=synthesize
        ) as generate:
            with self.assertLogs("app.voice"):
                await voice.warm_clips()
            self.assertEqual(len(voice.CLIPS), 4)
            generate.side_effect = lambda text, lang: good
            with patch("app.voice.asyncio.sleep"):
                await voice.retry_missing()
            self.assertEqual(len(voice.CLIPS), 6)
            self.assertEqual(generate.call_count, 8)

    async def test_http_voice_scan_calendar_and_limits(self):
        from app.main import app, lifespan
        pdf = Path(__file__).resolve().parents[1] / "demo" / "sample-invite.pdf"
        audio = sample_audio()
        with tempfile.TemporaryDirectory() as tmp, patch.object(db, "DB_PATH", Path(tmp) / "test.sqlite3"), patch.object(
            config, "DEMO_CACHE", True
        ), patch.object(config, "TELEGRAM_BOT_TOKEN", ""), patch.object(
            config, "SARVAM_API_KEY", "test"
        ), patch.object(config, "FLAGSMITH_ENV_KEY", ""), patch.object(config, "check_startup", lambda log: None), patch.object(
            sarvam, "synthesize", return_value=audio
        ) as synthesize:
            async with lifespan(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                user = (await client.post("/api/identify", json=dict(role="child", name="Demo", lang="kn"))).json()["user_id"]
                async def upload(name, data, mime):
                    return await client.post("/api/scan", files={"file": (name, data, mime)}, data={"user_id": user})
                card = (await upload(pdf.name, pdf.read_bytes(), "application/pdf")).json()
                self.assertIsNone(card["audio_b64"])
                response = await client.get(card["ics_url"])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.text.count("BEGIN:VEVENT"), 2)
                self.assertEqual(response.content.count(b"TRIGGER:-PT60M\r\n"), 2)
                self.assertIn("maps/dir/?api=1&destination=", card["functions"][0]["maps_url"])
                invite_page = await client.get("/i/demo")
                self.assertIn("maps/dir/?api=1&amp;destination=", invite_page.text)
                with patch.object(sarvam, "read_card", side_effect=AssertionError):
                    warning = (await upload("demo.apk", b"file", "application/octet-stream")).json()
                self.assertEqual(warning["audio_b64"], audio)
                reply = (await client.post("/api/opened", json={"scan_id": warning["scan_id"]})).json()
                self.assertEqual(reply["audio_b64"], audio)
                self.assertIn("demo.apk", reply["steps"][2])
                self.assertIn("ಫೋನ್", reply["steps"][0])
                self.assertEqual(synthesize.call_count, 6)
                self.assertEqual((await upload("empty.txt", b"", "text/plain")).status_code, 422)
                self.assertEqual((await client.post("/api/scan", json={"user_id": user, "text": " "})).status_code, 422)
                with patch.object(config, "MAX_FORM_BYTES", 32):
                    self.assertEqual((await upload("sample.txt", b"hi", "text/plain")).status_code, 413)
                raw = json.dumps({"user_id": user, "text": "hello"}).encode()
                async def chunks():
                    yield raw[:-1]
                    yield raw[-1:]
                with patch.object(config, "MAX_TEXT_BYTES", len(raw)):
                    self.assertEqual((await client.post("/api/scan", content=chunks(), headers={"content-type":"application/json"})).status_code, 200)
                with patch.object(config, "MAX_TEXT_BYTES", len(raw)-1):
                    self.assertEqual((await client.post("/api/scan", content=chunks(), headers={"content-type":"application/json"})).status_code, 413)
