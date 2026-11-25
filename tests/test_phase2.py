import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

from app import db, flags, models
from app.main import identify


class IdentityTests(unittest.TestCase):
    def test_parent_pairing_survives_restart_and_other_roles_have_no_link(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            db, "DB_PATH", Path(directory) / "test.sqlite3"
        ), patch("app.config.FLAGSMITH_ENV_KEY", ""):
            db.initialize()
            users = [identify(models.Identify(name="Priya", lang="hi", role=role))
                     for role in ("parent", "child", "host", "parent")]
            db.initialize()
            self.assertEqual(len({item["user_id"] for item in users}), 4)
            self.assertTrue(all(UUID(item["user_id"]).version == 4 for item in users))
            self.assertIsNone(users[1]["pair_link"])
            self.assertIsNone(users[2]["pair_link"])
            with db.connection() as conn:
                pairs = dict(conn.execute("SELECT parent_id, pair_code FROM pairings"))
            self.assertEqual(len(pairs), 2)
            for parent in (users[0], users[3]):
                self.assertTrue(parent["pair_link"].endswith("?start=" + pairs[parent["user_id"]]))
            self.assertEqual(db.get_user(users[2]["user_id"])["role"], "host")


class FlagTests(unittest.TestCase):
    user = {"id": "demo", "lang": "hi", "role": "parent"}

    def setUp(self):
        flags.clear_cache()
        self.addCleanup(flags.clear_cache)

    @patch("app.config.FLAGSMITH_ENV_KEY", "test-key")
    def test_remote_traits_pack_filter_and_five_second_expiry(self):
        remote = MagicMock()
        remote.is_feature_enabled.side_effect = lambda name: name == "pack_broad_test"
        remote.get_feature_value.return_value = json.dumps(flags.DEFAULT_RULES)
        with patch.object(flags, "Flagsmith") as sdk, patch.object(flags, "monotonic") as clock:
            fetch = sdk.return_value.get_identity_flags
            fetch.return_value = remote
            clock.return_value = 100
            self.assertEqual([r["id"] for r in flags.signatures(self.user)], ["broad-01"])
            clock.return_value = 104.9
            flags.signatures(self.user)
            fetch.assert_called_once_with(identifier="demo", traits={"lang": "hi", "role": "parent", "beta": "false"})
            clock.return_value = 105
            flags.signatures(self.user)
            self.assertEqual(fetch.call_count, 2)
            flags.clear_cache()
            flags.signatures(self.user)
            self.assertEqual(fetch.call_count, 3)

    @patch("app.config.FLAGSMITH_ENV_KEY", "test-key")
    def test_outage_uses_role_defaults_and_only_enabled_rules(self):
        with patch.object(flags, "Flagsmith", side_effect=TimeoutError), self.assertLogs("app.flags"):
            for role in ("parent", "child", "host"):
                user = dict(self.user, role=role)
                values = flags.for_user(user)
                self.assertEqual(values.enabled["strict_mode"], role == "parent")
                self.assertEqual(values.enabled["host_invites"], role == "host")
                self.assertEqual([r["id"] for r in flags.signatures(user)], ["core-01", "wed-01", "wed-02"])
