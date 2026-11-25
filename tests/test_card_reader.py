import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import httpx
from PIL import Image
from sarvamai import SarvamAI

from app import calendar_links as calendar
from app import sarvam_client as reader


CARD = {"couple": "Riya & Dev", "functions": [
    {"name": "Sangeet", "date": "12 December 2026", "time": "10:30 pm", "city": "Jaipur"},
    {"name": "Wedding", "name_original": "विवाह", "date": "13/12/2026", "venue_name": "A, B"},
    {"name": "Undated", "date": ""},
]}


class CardReaderTests(unittest.TestCase):
    def test_dotted_times_and_cmyk_conversion(self):
        for clock in ("6.30 p.m.", "18.30"):
            card = calendar.normalize({"functions": [{"name": "Dinner", "time": clock, "date": "2026-12-12"}]})
            self.assertEqual(card["functions"][0]["time"], "18:30")
        stream = io.BytesIO()
        Image.new("CMYK", (100, 100)).save(stream, format="JPEG")
        with patch.object(reader, "MAX_IMAGE_BYTES", len(stream.getvalue()) - 1):
            image, mime = reader._image_payload(stream.getvalue(), "image/jpeg")
        self.assertEqual(mime, "image/jpeg")
        self.assertEqual(Image.open(io.BytesIO(image)).mode, "RGB")

    def test_links_calendar_and_expiry(self):
        card = calendar.normalize(CARD)
        self.assertEqual(len(card["functions"]), 2)
        timed, all_day = card["functions"]
        self.assertEqual(timed["time"], "22:30")
        def query(url):
            return parse_qs(urlsplit(url).query)
        self.assertEqual(query(timed["gcal_url"])["dates"], ["20261212T223000/20261213T013000"])
        self.assertEqual(query(all_day["gcal_url"])["dates"], ["20261213/20261214"])
        self.assertEqual(urlsplit(all_day["maps_url"]).path, "/maps/dir/")
        self.assertEqual(query(all_day["maps_url"]), {"api": ["1"], "destination": ["A, B"]})
        with patch.object(calendar, "monotonic", return_value=100):
            calendar.remember("my-scan", card)
        with patch.object(calendar, "monotonic", return_value=699):
            ics = calendar.lookup("my-scan")
            self.assertEqual(ics.count("BEGIN:VEVENT\r\n"), 2)
            self.assertIn("DTSTART;TZID=Asia/Kolkata:20261212T223000\r\n", ics)
            self.assertIn("DTEND;VALUE=DATE:20261214\r\n", ics)
            self.assertIn(r"LOCATION:A\, B", ics)
            self.assertNotIn("\n", ics.replace("\r\n", ""))
            events = ics.split("BEGIN:VEVENT\r\n")[1:]
            for event, name in zip(events, ("Sangeet", "Wedding"), strict=True):
                alarm = f"BEGIN:VALARM\r\nACTION:DISPLAY\r\nDESCRIPTION:{name} in 1 hour\r\nTRIGGER:-PT60M\r\nEND:VALARM"
                self.assertIn(alarm, event.partition("END:VEVENT")[0])
        with patch.object(calendar, "monotonic", return_value=700):
            self.assertIsNone(calendar.lookup("my-scan"))

    def test_functions_sorted_by_local_date_then_time_unknown_last(self):
        events = [{"name": name, "date": date, "time": clock} for name, date, clock in [
            ("Later day", "2026-12-13", "7 am"), ("No time", "2026-12-12", ""),
            ("Dinner", "2026-12-12", "8 pm"), ("Breakfast", "2026-12-12", "9 am"),
        ]]
        ordered = calendar.normalize({"functions": events})["functions"]
        self.assertEqual([event["name"] for event in ordered], ["Breakfast", "Dinner", "No time", "Later day"])

    def test_real_sdk_sends_schema_language_and_fetches_partial_result(self):
        def service(request):
            if request.method == "POST":
                body = request.read()
                self.assertIn(b'name="language"\r\n\r\nkn-IN', body)
                self.assertIn(json.dumps(reader.SCHEMA).encode(), body)
                self.assertIn(b'filename="invite.png"', body)
                payload = {"job_id": "job", "run_id": "run", "status": "queued"}
            elif request.url.path.endswith("/status"):
                payload = {"job_id": "job", "status": "partially_completed", "usage": {},
                           "created_at": "", "updated_at": ""}
            else:
                payload = {"job_id": "job", "status": "partially_completed", "type": "extract",
                           "usage": {}, "result": CARD, "annotations": {}, "version": 1}
            return httpx.Response(200, json=payload)
        with httpx.Client(transport=httpx.MockTransport(service)) as http:
            sdk = SarvamAI(api_subscription_key="test", httpx_client=http)
            result = reader.document_extract(sdk, b"image", "invite.png", "image/png", "kn")
        self.assertEqual(result, CARD)

    def test_pdf_fallback_sends_png_and_parses_fenced_json(self):
        pdf = io.BytesIO()
        Image.new("RGB", (200, 100), "white").save(pdf, "PDF")
        sdk = MagicMock()
        reply = sdk.chat.completions_v2.return_value.choices[0].message
        reply.content = "Here is the card:\n" + chr(96)*3 + "json\n" + json.dumps(CARD) + "\n" + chr(96)*3
        self.assertEqual(reader.vision_extract(sdk, pdf.getvalue(), "application/pdf"), CARD)
        kwargs = sdk.chat.completions_v2.call_args.kwargs
        uri = kwargs["messages"][0]["content"][1]["image_url"]["url"]
        self.assertTrue(uri.startswith("data:image/png;base64,iVBOR"))
        self.assertLess(len(json.dumps(kwargs).encode()), 10 * 1024**2)

    def test_polling_stops_at_deadline_and_rejection(self):
        sdk = MagicMock()
        sdk.doc_ai.get_status.return_value.status = "processing"
        with patch.object(reader, "monotonic", side_effect=[0, 0, 0, 0, reader.DOC_SECONDS]), patch.object(reader, "sleep") as wait:
            with self.assertRaises(TimeoutError):
                reader.document_extract(sdk, b"card", "card.jpg", "image/jpeg", "hi")
            wait.assert_called_once_with(2)
        sdk.doc_ai.get_status.return_value.status = "rejected"
        with self.assertRaises(ValueError):
            reader.document_extract(sdk, b"card", "card.jpg", "image/jpeg", "hi")
        sdk.doc_ai.get_results.assert_not_called()

    def test_demo_cache_reads_seed_only(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            reader, "CACHE_PATH", Path(directory) / "cache.json"
        ), patch("app.config.DEMO_CACHE", True):
            card = calendar.normalize(CARD)
            reader.CACHE_PATH.write_text(json.dumps({"a" * 64: card}), encoding="utf-8")
            reader.load_cache()
            self.assertEqual(reader.cached_card("a" * 64), card)
            with patch("app.sarvam_client.asyncio.get_running_loop"):
                reader.cache_card("b" * 64, card)
            self.assertEqual(reader.cached_card("b" * 64), card)
            reader.load_cache()
            self.assertIsNone(reader.cached_card("b" * 64))
