from html.parser import HTMLParser
from unittest import TestCase

from app import calendar_links


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)

    def attrs(self, tag):
        return [attrs for name, attrs in self.elements if name == tag]


class GuestPageTests(TestCase):
    def setUp(self):
        from app.guest_page import render

        self.render = render
        self.invite = {
            "token": "a-token", "guest_name": "Guest <test-tag>",
            "couple": "Anu & Dev", "host_family": "Shah",
            "functions": [], "audio_b64": None,
        }

    def test_private_invitation_renders_names_as_text(self):
        page = Page(self.render(self.invite))
        self.assertIn("Guest <test-tag>, the Shah family invites you to", page.text)
        self.assertIn("Anu & Dev", page.text)
        self.assertFalse(page.attrs("test-tag"))
        self.assertFalse(page.attrs("audio"))
        self.assertFalse(page.attrs("a"))

    def test_event_actions_use_the_event_links_and_calendar_for_this_invite(self):
        event, = calendar_links.normalize({"functions": [{
            "name_original": "संगीत", "date": "2026-12-12",
            "time": "19:30", "venue_name": "Rose <Hall>",
        }]})["functions"]
        self.invite["functions"] = [event]
        self.invite["audio_b64"] = "UklGRg=="
        page = Page(self.render(self.invite))
        links = {attrs["href"] for attrs in page.attrs("a")}
        self.assertEqual(links, {event["maps_url"], event["gcal_url"], "/i/a-token/calendar.ics"})
        for label in ("संगीत", "Dec", "12", "Sat", "Hear the invite"):
            self.assertIn(label, page.text)
        self.assertIn("Rose <Hall>", "".join(page.text))
        audio, = page.attrs("audio")
        self.assertEqual(audio["src"], "data:audio/wav;base64,UklGRg==")

    def test_sample_marks_the_page_as_a_preview(self):
        self.invite["preview"] = True
        page = Page(self.render(self.invite))
        self.assertIn("Sample invitation", page.text)
        self.assertNotIn("Verified by Card Kholo", page.text)
