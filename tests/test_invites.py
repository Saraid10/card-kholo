import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx

from app import config, db, examples, sarvam_client
from app.main import app


class VoiceInviteFlow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        stack = self.enterContext(ExitStack())
        tmp = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(patch.object(db, "DB_PATH", Path(tmp) / "db"))
        stack.enter_context(patch.multiple(config, APP_BASE_URL="https://invites.example", SARVAM_API_KEY="test",
                                          FLAGSMITH_ENV_KEY="", TELEGRAM_BOT_TOKEN=""))
        db.initialize()
        self.client = await self.enterAsyncContext(httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                                                     base_url="https://invites.example"))
        self.host = await self.identify("host")
        self.child = await self.identify("child")
        self.event = examples.FUNCTION.model_dump()
        self.event["maps_url"] = "javascript:wrong"
        self.wedding = {"user_id": self.host, "couple": "Priya & Arjun", "host_family": "Gupta",
                        "functions": [self.event, dict(self.event, name="Reception", name_original="")]}
        self.parsed = dict(guest_name="Riya", guest_lang="hi", tone="warm", function_names=["Sangeet"],
                           phone="202-555-0142")
        self.transcribe = stack.enter_context(patch.object(sarvam_client, "transcribe_invite",
                                                          return_value="private transcript 202-555-0142"))
        self.parse = stack.enter_context(patch.object(sarvam_client, "parse_invite", return_value=self.parsed))
        self.write = stack.enter_context(patch.object(sarvam_client, "write_invite", side_effect=TimeoutError))
        self.synthesize = stack.enter_context(patch.object(sarvam_client, "synthesize", side_effect=TimeoutError))

    async def identify(self, role):
        response = await self.client.post("/api/identify", json={"name": "Demo", "lang": "en", "role": role})
        return response.json()["user_id"]

    async def record(self, user):
        return await self.client.post("/api/invites/voice", data={"user_id": user},
                                      files={"audio": ("note.wav", b"private voice note", "audio/wav")})

    async def test_wedding_to_whatsapp_to_verified_scan(self):
        await self.client.post("/api/invites/wedding", json=dict(self.wedding, host_family="Earlier"))
        saved = await self.client.post("/api/invites/wedding", json=self.wedding)
        self.assertTrue(saved.json()["wedding_id"])
        response = await self.record(self.host)
        self.assertEqual(response.status_code, 200, response.text)
        invite = response.json()
        self.assertIsNone(invite["audio_b64"])
        self.assertTrue(invite["invite_text"].endswith(invite["invite_url"]))
        self.assertLess(len(invite["invite_text"]), 400)
        wa = urlsplit(invite["wa_url"])
        self.assertEqual(wa.path, "/912025550142")
        self.assertEqual(parse_qs(wa.query)["text"], [invite["invite_text"]])
        page = await self.client.get(invite["invite_url"])
        self.assertIn("Verified by Card Kholo", page.text)
        self.assertIn("the Gupta family", page.text)
        self.assertIn("Sangeet", page.text)
        self.assertNotIn("Reception", page.text)
        self.assertNotIn("javascript:wrong", page.text)
        cal = await self.client.get(invite["invite_url"] + "/calendar.ics")
        self.assertEqual(cal.content.count(b"BEGIN:VEVENT\r\n"), 1)
        self.assertIn(b"TRIGGER:-PT60M\r\n", cal.content)
        with db.connection() as conn:
            stored = str(tuple(conn.execute("SELECT * FROM invites").fetchone()))
        for private in ("202-555-0142", "2025550142", "private transcript", "private voice note"):
            self.assertNotIn(private, stored)
        for text in (invite["invite_text"], invite["invite_url"]):
            scan = (await self.client.post("/api/scan", json={"user_id": self.child, "text": text})).json()
            self.assertEqual((scan["verdict"], scan["verified_from"]), ("OK", "Gupta"))
        db.initialize()
        self.assertEqual((await self.client.get(invite["invite_url"])).status_code, 200)
        self.assertEqual((await self.client.get("/i/missing")).status_code, 404)

    async def test_feature_gate_host_isolation_and_failures(self):
        self.assertEqual((await self.record(self.child)).status_code, 403)
        denied = await self.client.post("/api/invites/wedding", json=dict(self.wedding, user_id=self.child))
        self.assertEqual(denied.status_code, 403)
        await self.client.post("/api/invites/wedding", json=self.wedding)
        self.assertEqual((await self.record(await self.identify("host"))).status_code, 409)
        self.transcribe.assert_not_called()
        self.parsed["function_names"] = ["Missing"]
        self.assertEqual((await self.record(self.host)).status_code, 422)
        self.transcribe.side_effect = TimeoutError
        self.assertEqual((await self.record(self.host)).status_code, 502)
        with db.connection() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM invites").fetchone()[0], 0)

    async def test_generated_invite_has_playable_audio_and_generic_share_link(self):
        await self.client.post("/api/invites/wedding", json=self.wedding)
        self.parsed.update(phone="", guest_lang="en")
        self.write.side_effect = lambda guest, lang, tone, couple, functions, url: (
            f"{guest}, join {couple} for Sangeet on 12 December at Rose Garden. {url}"
        )
        self.synthesize.side_effect = None
        self.synthesize.return_value = "UklGRg=="
        response = await self.record(self.host)
        self.assertEqual(response.status_code, 200)
        invite = response.json()
        self.assertEqual(urlsplit(invite["wa_url"]).path, "/")
        self.assertTrue(invite["invite_text"].startswith("Riya, join Priya & Arjun"))
        self.assertEqual(invite["audio_b64"], "UklGRg==")
        page = await self.client.get(invite["invite_url"])
        self.assertIn("Hear the invite", page.text)
        self.assertIn("data:audio/wav;base64,UklGRg==", page.text)
