import asyncio
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import HTTPException

from app import alerts, config, db, flags, incidents, models
from app.main import app, feedback, fallback_rollback, rolled_back, status, telegram


PACK = "pack_broad_test"


class IncidentTests(unittest.TestCase):
    def setUp(self):
        root = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(db, "DB_PATH", Path(root) / "db.sqlite3"))
        self.enterContext(patch.multiple(
            config, HOOK_SECRET="secret", TELEGRAM_SECRET="telegram-secret", FLAGSMITH_ENV_KEY="",
            APP_BASE_URL="https://cards.example", NUDGEBEE_WEBHOOK_URL="https://workflow.example/hook",
            FLAGSMITH_FEATURE_IDS={PACK: 123}, FLAGSMITH_ADMIN_ENV_KEY="environment",
            FLAGSMITH_ADMIN_API_KEY="admin-key", FLAGSMITH_SEGMENT_IDS={"canary_20": 987},
        ))
        db.initialize()
        self.user, code = db.create_user(models.Identify(name="Asha", role="parent", lang="hi"))
        db.pair_child(code, 25, "Riya")
        self.requests = []
        self.code = 200
        self.delete_code = None
        def service(request):
            self.requests.append(request)
            code = self.delete_code if request.method == "DELETE" and self.delete_code else self.code
            return httpx.Response(code, json={})
        self.enterContext(patch.object(incidents, "Client", side_effect=lambda **kw:
            httpx.Client(transport=httpx.MockTransport(service), **kw)))
        self.bot = self.enterContext(patch.object(alerts, "bot_call", return_value=True))
        flags.clear_cache()
        self.clear = self.enterContext(patch.object(flags, "clear_cache", wraps=flags.clear_cache))

    def scan(self):
        return db.save_scan(self.user["id"], "DANGEROUS", [PACK], None, "invite.pdf")

    def report(self, scan_id):
        return feedback(models.Feedback(scan_id=scan_id, real_invite=True))

    def open_incident(self):
        for _ in range(3):
            self.report(self.scan())
        return status()["incidents"][0]["id"]

    def test_telegram_and_frontend_share_threshold_and_rollback(self):
        old = self.scan()
        self.report(old)
        with db.connection() as conn:
            conn.execute("UPDATE false_alarms SET created_at=datetime('now','-6 minutes')")
        first = self.scan()
        self.assertEqual(self.report(first), self.report(first))
        self.report(self.scan())
        self.assertFalse(self.requests)
        query = {"id": "button", "from": {"id": 25}, "data": "fa:" + self.scan()}
        telegram({"callback_query": query}, "telegram-secret")
        snapshot = status()
        incident, = snapshot["incidents"]
        self.assertEqual(next(p for p in snapshot["packs"] if p["name"] == PACK)["false_alarms_5m"], 3)
        self.assertEqual((incident["status"], incident["count"]), ("open", 3))
        req, = self.requests
        self.assertEqual(json.loads(req.content), {
            "type": "false_alarm_spike", "pack": PACK, "false_alarms": 3, "window_minutes": 5,
            "flagsmith_feature_id": 123, "incident_id": incident["id"],
            "flagsmith_segment_id": 987, "rollout": "canary_20",
            "app_callback": "https://cards.example/hooks/rolled-back",
            "summary": f"Pack {PACK} flagged 3 real invites as scams in 5 minutes",
        })
        body = models.Rollback(incident_id=incident["id"], pack=PACK, approver="ops")
        for secret, pack, expected in [("bad", PACK, 403), ("secret", "pack_core", 409)]:
            with self.assertRaises(HTTPException) as err:
                rolled_back(body.model_copy(update={"pack": pack}), secret)
            self.assertEqual(err.exception.status_code, expected)
        self.bot.reset_mock()
        self.assertEqual(rolled_back(body, "secret"), {"ok": True})
        rolled_back(body, "secret")
        self.assertEqual(status()["incidents"][0]["status"], "rolled_back")
        self.bot.assert_called_once_with("sendMessage", chat_id=25,
            text=f"Card Kholo: the {PACK} rule pack was causing false alarms and has been rolled back.")
        self.assertTrue(self.clear.called)
        self.report(first)
        self.assertEqual(len(status()["incidents"]), 1)

    def test_fallback_checks_admin_response_before_closing(self):
        incident_id = self.open_incident()
        self.requests.clear()
        with self.assertRaises(HTTPException) as denied:
            fallback_rollback(incident_id, "wrong")
        self.assertEqual(denied.exception.status_code, 403)
        self.assertFalse(self.requests)
        self.code = 503
        with self.assertRaises(HTTPException) as upstream:
            fallback_rollback(incident_id, "secret")
        self.assertEqual(upstream.exception.status_code, 502)
        self.assertEqual(status()["incidents"][0]["status"], "open")
        self.assertEqual([r.method for r in self.requests], ["DELETE", "PATCH"])
        self.delete_code = 404
        with self.assertRaises(HTTPException):
            fallback_rollback(incident_id, "secret")
        self.assertEqual(status()["incidents"][0]["status"], "open")
        self.code = 200
        fallback_rollback(incident_id, "secret")
        fallback_rollback(incident_id, "secret")
        self.assertEqual([r.method for r in self.requests], ["DELETE", "PATCH", "DELETE", "PATCH", "DELETE", "PATCH"])
        self.assertEqual(self.requests[-2].url.path, "/api/__future__/environments/environment/features/123/segment-overrides/987/")
        req = self.requests[-1]
        self.assertEqual(req.method, "PATCH")
        self.assertEqual(str(req.url), "https://api.flagsmith.com/api/__future__/environments/environment/features/123/")
        self.assertEqual(req.headers["Authorization"], "Api-Key admin-key")
        self.assertEqual(json.loads(req.content), {"environment_default": {"enabled": False}})
        self.assertEqual(status()["incidents"][0]["status"], "rolled_back")

    def test_simultaneous_reports_open_once(self):
        scan_ids = [self.scan() for _ in range(5)]
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(self.report, scan_ids))
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(status()["incidents"]), 1)

    def test_status_reads_environment_flags(self):
        with patch.object(config, "FLAGSMITH_ENV_KEY", "env"), patch.object(flags, "Flagsmith") as sdk:
            remote = sdk.return_value.get_environment_flags.return_value
            remote.all_flags.return_value = [SimpleNamespace(feature_name=PACK, enabled=True),
                                             SimpleNamespace(feature_name="pack_extra", enabled=True)]
            states = {p["name"]: p["enabled"] for p in status()["packs"]}
            self.assertTrue(states[PACK])
            self.assertTrue(states["pack_extra"])
            sdk.return_value.get_identity_flags.assert_not_called()

    def test_delivery_failures_survive_restart_and_retry_only_pending_recipients(self):
        self.code = 503
        with self.assertLogs("app.incidents"):
            incident_id = self.open_incident()
        self.assertEqual(len(self.requests), 1)
        db.initialize()
        self.code = 200
        def retry_now():
            with db.connection() as conn:
                conn.execute("UPDATE incident_notifications SET next_attempt_at=CURRENT_TIMESTAMP")
            incidents.deliver_pending()
        retry_now()
        incidents.deliver_pending()
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.requests[0].content, self.requests[1].content)
        for chat in (25, 30):
            _, code = db.create_user(models.Identify(name="Parent", role="parent", lang="en"))
            db.pair_child(code, chat, "Child")
        self.bot.side_effect = lambda method, chat_id, text: chat_id == 25
        rolled_back(models.Rollback(incident_id=incident_id, pack=PACK, approver="ops"), "secret")
        self.assertCountEqual([call.kwargs["chat_id"] for call in self.bot.call_args_list], [25, 30])
        self.bot.reset_mock()
        self.bot.side_effect = None
        retry_now()
        incidents.deliver_pending()
        self.assertEqual([call.kwargs["chat_id"] for call in self.bot.call_args_list], [30])

    def test_public_http_flow_from_scanned_card_to_approved_rollback(self):
        async def run():
            sample = (Path(__file__).resolve().parents[1] / "demo" / "sample-invite.pdf").read_bytes()
            remote = self.enterContext(patch.object(flags, "Flagsmith")).return_value
            state = {PACK: True, "strict_mode": False, "spoken_summary": False}
            flags_for_user = remote.get_identity_flags.return_value
            flags_for_user.get_feature_value.return_value = json.dumps(flags.DEFAULT_RULES)
            flags_for_user.is_feature_enabled.side_effect = lambda key: state.get(key, False)
            remote.get_environment_flags.return_value.all_flags.side_effect = lambda: [
                SimpleNamespace(feature_name=PACK, enabled=state[PACK])]
            self.enterContext(patch.object(config, "FLAGSMITH_ENV_KEY", "mock-environment"))
            self.enterContext(patch("app.sarvam_client.read_card", return_value=None))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
                identity = await api.post("/api/identify", json={"name":"Demo", "role":"child", "lang":"en"})
                user = identity.json()["user_id"]
                async def scan_card():
                    r = await api.post("/api/scan", files={"file": ("invite.pdf", sample, "application/pdf")},
                                       data={"user_id": user})
                    r.raise_for_status()
                    return r.json()
                for n in range(1, 4):
                    scan = await scan_card()
                    self.assertEqual(scan["pack_hits"], [PACK])
                    r = await api.post("/api/feedback", json={"scan_id":scan["scan_id"], "real_invite":True})
                    self.assertEqual(r.json()["pack_false_alarms"], {PACK:n})
                opened, = (await api.get("/api/status")).json()["incidents"]
                body = {"incident_id":opened["id"], "pack":PACK, "approver":"Demo operator"}
                self.assertEqual((await api.post("/hooks/rolled-back", json=body)).status_code, 403)
                state[PACK] = False  # NudgeBee has applied the approved external change.
                response = await api.post("/hooks/rolled-back", json=body, headers={"X-Hook-Secret":"secret"})
                self.assertEqual(response.json(), {"ok":True})
                self.assertEqual((await scan_card())["verdict"], "OK")
                snapshot = (await api.get("/api/status")).json()
                self.assertEqual(snapshot["incidents"][0]["status"], "rolled_back")
                self.assertFalse(next(pack["enabled"] for pack in snapshot["packs"] if pack["name"] == PACK))
        asyncio.run(run())
