import io
import unittest
from zipfile import ZipFile

from app import scan_rules
from app.flags import DEFAULT_RULES, UserFlags


def evaluate(*, strict=False, rules=DEFAULT_RULES, **input_fields):
    settings = UserFlags({"strict_mode": strict, "pack_core": True, "pack_wedding_2026": True}, rules)
    return scan_rules.evaluate(settings, **input_fields)


class ScanRuleTests(unittest.TestCase):
    def test_zip_needs_both_root_members(self):
        for members, verdict in [
            (["AndroidManifest.xml", "classes.dex"], "DANGEROUS"),
            (["word/document.xml", "AndroidManifest.xml"], "OK"),
            (["nested/AndroidManifest.xml", "nested/classes.dex"], "OK"),
        ]:
            with self.subTest(members=members):
                stream = io.BytesIO()
                with ZipFile(stream, "w") as archive:
                    for name in members:
                        archive.writestr(name, b"")
                self.assertEqual(evaluate(data=stream.getvalue(), filename="invite.docx").verdict, verdict)

    def test_extensions_headers_and_severity(self):
        for filename, mime, data, verdict in [
            ("memento.APKM", "", b"", "DANGEROUS"), ("invite.pdf.Js", "", b"", "DANGEROUS"),
            ("card.JPG", "image/jpeg", b"%PDF", "SUSPICIOUS"),
            ("card", "image/png", b"?", "SUSPICIOUS"), ("card.pdf", "", b"%PDF-1.7", "OK"),
            ("card.jpeg", "", b"\xff\xd8\xff", "OK"), ("card.PNG", "", b"\x89PNG", "OK"),
            ("card.pDf.ApK", "application/pdf", b"", "DANGEROUS"),
        ]:
            with self.subTest(filename=filename):
                self.assertEqual(evaluate(filename=filename, content_type=mime, data=data).verdict, verdict)

    def test_shorteners_ips_http_and_punycode(self):
        for link in ("[https://bit.ly]", "https://bit.ly/a", "tinyurl.com/invite", "https://192.0.2.1/",
                     "https://[2001:db8::1]/", "http://example.org", "https://xn--test.example"):
            with self.subTest(link=link):
                self.assertEqual(evaluate(text=link).verdict, "SUSPICIOUS")
                self.assertEqual(evaluate(text=link, strict=True).verdict, "DANGEROUS")
        self.assertEqual(evaluate(text="Meet at https://bit.ly.example.org/bit.ly").verdict, "OK")

    def test_domain_boundaries_pack_filtering_and_unique_pack_hits(self):
        domain = {"id": "dom", "pack": "pack_core", "type": "domain", "pattern": "example.org",
                  "severity": "SUSPICIOUS", "label": "Listed domain"}
        for host, verdict in [("EXAMPLE.ORG", "SUSPICIOUS"), ("sub.example.org", "SUSPICIOUS"),
                              ("notexample.org", "OK"), ("example.org.test", "OK")]:
            with self.subTest(host=host):
                self.assertEqual(evaluate(text="https://" + host, rules=[domain]).verdict, verdict)
        result = evaluate(text="card.apk https://sub.example.org", rules=[*DEFAULT_RULES, domain])
        self.assertEqual(result.verdict, "DANGEROUS")
        self.assertEqual(result.pack_hits, ["pack_core"])
        self.assertIn("Listed domain", result.reasons)
        self.assertEqual(evaluate(filename="invite", data=b"").pack_hits, [])
