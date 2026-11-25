import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app import config, db, flags
from app.main import app


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        root = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(db, "DB_PATH", Path(root) / "exp.sqlite3"))
        self.enterContext(patch.multiple(config, FLAGSMITH_ENV_KEY="", TELEGRAM_BOT_TOKEN=""))
        flags.clear_cache()
        db.initialize()

    def test_events_are_tagged_validated_and_counted(self):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                user = (await client.post("/api/identify", json={"name": "A", "lang": "en", "role": "parent"})).json()
                scan = (await client.post("/api/scan", data={"user_id": user["user_id"]},
                                          files={"file": ("Shaadi.pdf.apk", b"x", "application/octet-stream")})).json()
                self.assertEqual(scan["verdict"], "DANGEROUS")
                style = scan["warning_style"]
                self.assertIn(style, ("calm", "urgent"))
                ok = (await client.post("/api/scan", json={"user_id": user["user_id"], "text": "hello"})).json()
                self.assertIsNone(ok["warning_style"])
                for event in ("warning_shown", "warning_shown", "warning_played", "warning_completed"):
                    response = await client.post("/api/events", json={"scan_id": scan["scan_id"], "event": event})
                    self.assertEqual(response.json(), {"ok": True})
                bad = await client.post("/api/events", json={"scan_id": scan["scan_id"], "event": "nope"})
                self.assertEqual(bad.status_code, 400)
                missing = await client.post("/api/events", json={"scan_id": "x", "event": "warning_shown"})
                self.assertEqual(missing.status_code, 404)
                status = (await client.get("/api/status")).json()
                variants = {v["name"]: v for v in status["experiment"]["variants"]}
                self.assertEqual(variants[style]["shown"], 1)
                self.assertEqual(variants[style]["completion_rate"], 1)
                other = "urgent" if style == "calm" else "calm"
                self.assertEqual(variants[other]["completion_rate"], 0)
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
