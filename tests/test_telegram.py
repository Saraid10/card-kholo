import json
import tempfile
import unittest
from collections import deque
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import HTTPException

from app import alerts, config, db, models
from app.main import _classify, feedback, identify, status, telegram


class TelegramTests(unittest.TestCase):
    def setUp(self):
        stack = self.enterContext(ExitStack())
        tmp = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(patch.object(db, "DB_PATH", Path(tmp) / "test.sqlite3"))
        stack.enter_context(patch.multiple(
            config, FLAGSMITH_ENV_KEY="", TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_SECRET="test-secret",
            TELEGRAM_BOT_USERNAME="testbot", APP_BASE_URL="https://test.example",
        ))
        stack.enter_context(patch.object(alerts, "_recent", deque(maxlen=20)))
        self.calls = []
        self.fail = False
        self.accept = True

        def service(request):
            self.calls.append((request.url.path.rsplit("/", 1)[1], json.loads(request.content)))
            if self.fail:
                raise httpx.ReadTimeout("Test timeout")
            return httpx.Response(200, json={"ok": self.accept, "result": self.accept})

        stack.enter_context(patch.object(alerts, "Client", side_effect=lambda **kwargs:
            httpx.Client(transport=httpx.MockTransport(service), **kwargs)))
        db.initialize()
        identity = identify(models.Identify(role="parent", lang="hi", name="Asha"))
        self.user = identity["user_id"]
        self.code = parse_qs(urlsplit(identity["pair_link"]).query)["start"][0]

    def start(self, chat_id=25, chat_type="private"):
        return {"message": {"text": "/start " + self.code, "chat": {"type": chat_type, "id": chat_id},
                            "from": {"id": chat_id, "first_name": "Riya"}}}

    def scan(self, text="card.apk"):
        return _classify(self.user, None, "", "", text)[2]

    def test_webhook_registration_and_authentication(self):
        alerts.register_webhook()
        method, payload = self.calls.pop()
        self.assertEqual((method, payload["url"], payload["secret_token"]),
                         ("setWebhook", "https://test.example/hooks/telegram", "test-secret"))
        with self.assertRaises(HTTPException) as ctx:
            telegram(self.start(), "wrong")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIsNone(db.paired_chat(self.user))
        with patch.object(config, "TELEGRAM_BOT_TOKEN", ""):
            alerts.register_webhook()
        self.assertFalse(self.calls)

    def test_pairing_alerts_and_shared_feedback(self):
        self.assertFalse(self.scan()["alert_sent"])
        telegram(self.start(), "test-secret")
        self.assertIn("Linked!", self.calls[-1][1]["text"])
        telegram(self.start(31), "test-secret")
        with db.connection() as conn:
            pair = conn.execute("SELECT child_chat_id, child_name FROM pairings").fetchone()
            self.assertEqual(tuple(pair), (25, "Riya"))
        self.assertFalse(self.scan("Dinner tomorrow")["alert_sent"])
        item = self.scan()
        self.assertTrue(item["alert_sent"])
        method, message = self.calls[-1]
        self.assertEqual((method, message["chat_id"]), ("sendMessage", 25))
        button = message["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(button, {"text": "This was a real invite", "callback_data": "fa:" + item["scan_id"]})
        query = {"id": "button-1", "from": {"id": 31}, "data": button["callback_data"]}
        telegram({"callback_query": query}, "test-secret")
        with db.connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM false_alarms").fetchone()[0], 0)
        query["from"]["id"] = 25
        for _ in range(2):
            self.assertEqual(telegram({"callback_query": query}, "test-secret"), {"ok": True})
            self.assertEqual(self.calls[-1][0], "answerCallbackQuery")
        report = feedback(models.Feedback(scan_id=item["scan_id"], real_invite=True))
        self.assertEqual(report["pack_false_alarms"], {"pack_core": 1})
        self.assertEqual(len(status()["last_alerts"]), 1)

    def test_api_failure_and_private_pairing(self):
        telegram(self.start(chat_type="group"), "test-secret")
        self.assertFalse(self.scan()["alert_sent"])
        telegram(self.start(), "test-secret")
        self.fail = True
        with self.assertLogs("app.alerts"):
            item = self.scan()
        self.assertEqual(item["verdict"], "DANGEROUS")
        self.assertFalse(item["alert_sent"])
        self.assertEqual(status()["last_alerts"], [])

    def test_file_alert_requires_bot_acceptance(self):
        telegram(self.start(), "test-secret")
        apk = Path(__file__).resolve().parents[1] / "demo" / "Shaadi_Card_Priya.pdf.apk"
        def upload():
            return _classify(self.user, apk.read_bytes(), apk.name, "application/octet-stream", None)[2]
        self.accept = False
        with self.assertLogs("app.alerts"):
            self.assertFalse(upload()["alert_sent"])
        self.accept = True
        scan = upload()
        self.assertTrue(scan["alert_sent"])
        self.assertIn(apk.name, self.calls[-1][1]["text"])
        self.assertIn("SMS", self.calls[-1][1]["text"])
        self.assertEqual(scan["pack_hits"], ["pack_wedding_2026"])
