import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app import config, db, flag_changes, flags, models
from app.main import app


class CanaryTests(unittest.TestCase):
    def setUp(self):
        root = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(db, "DB_PATH", Path(root) / "flags.sqlite3"))
        self.enterContext(patch.multiple(config, HOOK_SECRET="test-secret", FLAGSMITH_ENV_KEY=""))
        flags.clear_cache()

    def test_existing_database_migration_and_scan_context(self):
        with db.connection() as conn:
            conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, name TEXT, lang TEXT, role TEXT, created_at TEXT)")
            conn.execute("INSERT INTO users VALUES ('old', 'Asha', 'hi', 'parent', CURRENT_TIMESTAMP)")
        db.initialize()
        db.initialize()
        self.assertFalse(db.get_user("old")["beta"])
        user, _ = db.create_user(models.Identify(name="Demo", lang="hi", role="child", beta=True))
        self.assertTrue(db.get_user(user["id"])["beta"])
        scan = db.save_scan(user["id"], "OK", [], None, None)
        self.assertTrue(db.scan_context(scan)["beta"])

    def test_feed_survives_restart_with_bounds_and_unknown_payloads(self):
        db.initialize()
        flag_changes.initialize()
        for i in range(32):
            flag_changes.record(json.dumps({"data": {"feature_name": f"pack_{i}"}}).encode())
        for raw in (b"not JSON", b"[]", b'{"data":{"new_state":123,"previous_state":false}}'):
            flag_changes.record(raw)
        with db.connection() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM flag_changes").fetchone()[0], 35)
        flag_changes.initialize()
        self.assertEqual(len(flag_changes._recent), 30)
        feed = flag_changes.latest()
        self.assertEqual(len(feed), 15)
        self.assertEqual(feed[0]["summary"], "Flag changed")
        self.assertEqual(feed[0]["feature"], "unknown")
        self.assertEqual(feed[3]["feature"], "pack_31")
        self.assertEqual(set(feed[0]), {"time", "feature", "summary", "source"})

    def test_source_is_feature_specific_and_expires(self):
        db.initialize()
        flag_changes.initialize()
        with db.connection() as conn:
            conn.execute("INSERT INTO incidents (id,pack,count,status,closed_at) "
                         "VALUES ('incident','pack_test',3,'rolled_back',CURRENT_TIMESTAMP)")
        payload = {"event_type":"FLAG_UPDATED", "data":{
            "previous_state":{"feature":{"name":"pack_test"},"enabled":True},
            "new_state":{"enabled":False,"feature_segment":{"segment":{"name":"canary_20"}}},
            "changed_by":"Operator"}}
        flag_changes.record(json.dumps(payload).encode())
        change = flag_changes.latest()[0]
        self.assertEqual(change["source"], "NudgeBee rollback")
        self.assertEqual(change["summary"], "pack_test turned OFF (segment canary_20)")
        with db.connection() as conn:
            row = conn.execute("SELECT enabled_before, enabled_after FROM flag_changes").fetchone()
            self.assertEqual(tuple(row), (1, 0))
            conn.execute("UPDATE incidents SET closed_at=datetime('now','-121 seconds')")
        flag_changes.record(json.dumps(payload).encode())
        self.assertEqual(flag_changes.latest()[0]["source"], "Dashboard or API")

    def test_http_beta_traits_webhook_and_next_scan(self):
        db.initialize()
        flag_changes.initialize()
        self.enterContext(patch.object(config, "FLAGSMITH_ENV_KEY", "test"))
        sdk = self.enterContext(patch.object(flags, "Flagsmith"))
        remote = sdk.return_value.get_identity_flags
        rollout = True

        def identity_flags(identifier, traits):
            from unittest.mock import Mock
            result = Mock()
            enabled = traits["beta"] == "true" and rollout
            result.is_feature_enabled.side_effect = lambda name: name == "pack_broad_test" and enabled
            result.get_feature_value.return_value = json.dumps(flags.DEFAULT_RULES)
            return result
        remote.side_effect = identity_flags

        async def run():
            nonlocal rollout
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                body = {"name":"Demo","role":"child","lang":"kn"}
                await client.post("/api/identify", json=body)
                self.assertEqual(remote.call_args.kwargs["traits"]["beta"], "false")
                user = (await client.post("/api/identify", json={**body, "beta":True})).json()["user_id"]
                self.assertEqual(remote.call_args.kwargs["traits"], {"lang":"kn","role":"child","beta":"true"})
                async def scan():
                    response = await client.post("/api/scan", data={"user_id": user},
                                                 files={"file": ("invite.txt", b"Wedding invitation", "text/plain")})
                    return response.json()["verdict"]
                self.assertEqual(await scan(), "DANGEROUS")
                rollout = False
                event = {"event_type":"FLAG_UPDATED", "data":{
                    "new_state":{"feature":{"name":"scam_signatures"}, "enabled":True, "feature_state_value":"new"},
                    "previous_state":{"enabled":True, "feature_state_value":"old"}}}
                denied = await client.post("/hooks/flagsmith?token=bad", json=event)
                self.assertEqual(denied.status_code, 403)
                self.assertFalse(flag_changes.latest())
                with self.assertLogs(flag_changes.log, level="INFO") as logged:
                    accepted = await client.post("/hooks/flagsmith?token=test-secret", json=event)
                self.assertEqual(len(logged.records), 1)
                self.assertEqual(accepted.json(), {"ok": True})
                self.assertEqual(await scan(), "OK")
                feed = (await client.get("/api/status")).json()["flag_changes"]
                self.assertEqual(feed[0]["summary"], "scam_signatures value updated")
        asyncio.run(run())
