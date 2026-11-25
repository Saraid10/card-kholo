import unittest
from unittest.mock import patch

from app import config, scan_rules
from app.flags import DEFAULT_RULES, UserFlags


class InviteRuleTests(unittest.TestCase):
    def setUp(self):
        self.settings = UserFlags({"strict_mode": False, "pack_core": True}, DEFAULT_RULES)
        self.invites = {"Family_k9-Q": "Mehta Family"}

    def scan(self, text, **kwargs):
        return scan_rules.evaluate(self.settings, text=text, lookup_invite=self.invites.get, **kwargs)

    def test_saved_invite_matches_configured_origin_and_base_path(self):
        for base, url in (
            ("http://127.0.0.1:8000", "http://127.0.0.1:8000/i/Family_k9-Q"),
            ("http://localhost:8000", "http://localhost:8000/i/Family_k9-Q"),
            ("https://cards.example/demo", "https://CARDS.example:443/demo/i/Family_k9-Q"),
        ):
            with self.subTest(base=base), patch.object(config, "APP_BASE_URL", base):
                result = self.scan("  " + url + "\n")
                self.assertEqual(result.verdict, "OK")
                self.assertEqual(result.verified_from, "Mehta Family")
                self.assertIn("Verified invite from the Mehta Family family", result.reasons)

    @patch.object(config, "APP_BASE_URL", "http://127.0.0.1:8000")
    def test_forwarded_invite_text_verifies_the_saved_host(self):
        result = self.scan("Please join us for the wedding!\nhttp://127.0.0.1:8000/i/Family_k9-Q")
        self.assertEqual(result.verdict, "OK")
        self.assertEqual(result.verified_from, "Mehta Family")

    @patch.object(config, "APP_BASE_URL", "https://cards.example")
    def test_only_an_actual_invite_endpoint_can_verify(self):
        for url in (
            "https://cards.example/i/Unknown",
            "https://cards.example.evil.test/i/Family_k9-Q",
            "https://cards.example@evil.test/i/Family_k9-Q",
            "https://evil.test@cards.example/i/Family_k9-Q",
            "http://cards.example/i/Family_k9-Q",
            "https://cards.example:8080/i/Family_k9-Q",
            "https://cards.example:bad/i/Family_k9-Q",
            "https://cards.example/other/i/Family_k9-Q",
            "https://cards.example/i/Family_k9-Q/extra",
            "https://cards.example/i/Family_k9-Q?redirect=elsewhere",
            "https://cards.example/i/Family_k9-Q#copy",
            "https://cards.ex\nample/i/Family_k9-Q",
            "otherhttps://cards.example/i/Family_k9-Q",
            "https://cards.example/i/Family_k9-Q!",
        ):
            with self.subTest(url=url):
                self.assertIsNone(self.scan(url).verified_from)

    @patch.object(config, "APP_BASE_URL", "https://cards.example")
    def test_invite_cannot_verify_other_content_or_clear_flags(self):
        url = "https://cards.example/i/Family_k9-Q"
        for text, fields, verdict in (
            (url + " wedding-card.apk", {}, "DANGEROUS"),
            (url + "\nhttps://bit.ly/invite", {}, "SUSPICIOUS"),
            (url + "\nhttps://other.example/rsvp", {}, "OK"),
            (url, {"data": b"", "filename": "card.apk"}, "DANGEROUS"),
            (url, {"data": b"%PDF", "filename": "card.pdf"}, "OK"),
        ):
            with self.subTest(text=text, fields=fields):
                result = self.scan(text, **fields)
                self.assertEqual(result.verdict, verdict)
                self.assertIsNone(result.verified_from)

    @patch.object(config, "APP_BASE_URL", "https://cards.example")
    def test_active_pack_can_flag_the_trusted_domain(self):
        rule = {"type": "domain", "pattern": "cards.example", "severity": "DANGEROUS",
                "label": "Flagged by domain pack", "pack": "pack_core"}
        self.settings.rules = [rule]
        result = self.scan("https://cards.example/i/Family_k9-Q")
        self.assertEqual(result.verdict, "DANGEROUS")
        self.assertIsNone(result.verified_from)

    @patch.object(config, "APP_BASE_URL", "http://localhost:8000")
    def test_unknown_local_invite_still_receives_http_warning(self):
        result = self.scan("http://localhost:8000/i/Unknown")
        self.assertEqual(result.verdict, "SUSPICIOUS")
        self.assertIsNone(result.verified_from)
