import base64
import json
import unittest
from unittest.mock import patch

import httpx

from app import sarvam_client as sarvam


def completion(text):
    return {
        "id": "demo", "created": 1, "model": "sarvam-105b", "object": "chat.completion",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
    }


class InviteProviderTests(unittest.TestCase):
    def provider(self, handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        return patch.object(sarvam.httpx, "Client", return_value=client)

    def test_transcription_posts_named_audio_in_codemix(self):
        def respond(req):
            for value in (b'filename="note.webm"', b"audio/webm", b"encoded clip",
                          b"saaras:v4", b"codemix", b"kn-IN"):
                self.assertIn(value, req.content)
            self.assertGreater(req.extensions["timeout"]["read"], 0)
            return httpx.Response(200, json={"request_id": "demo", "transcript": "  invite Neha  "})

        with self.provider(respond):
            self.assertEqual(sarvam.transcribe_invite("note.webm", b"encoded clip", "audio/webm", "kn"), "invite Neha")

    def test_parser_recovers_an_object_in_fenced_model_text(self):
        parsed = {"guest_name": "Neha", "guest_lang": "en", "function_names": ["Mehendi"], "phone": "", "tone": "warm"}
        def respond(req):
            body = json.loads(req.content)
            self.assertEqual(body["model"], "sarvam-105b")
            self.assertIn("Invite Neha", body["messages"][-1]["content"])
            self.assertIn("Mehendi", body["messages"][-1]["content"])
            return httpx.Response(200, json=completion("Result\n```json\n" + json.dumps(parsed) + "\n```"))

        with self.provider(respond):
            self.assertEqual(sarvam.parse_invite("Invite Neha", ["Mehendi"]), parsed)

    def test_writer_limits_input_to_invitation_details(self):
        link = "https://cards.test/i/test"
        draft = "Neha, join A & B for Mehendi on 2026-12-01 at Taj! " + link
        def respond(req):
            body = json.loads(req.content)
            self.assertEqual(body["model"], "sarvam-105b")
            message = body["messages"][-1]["content"]
            for value in ("Neha", "Mehendi", "A & B", "2026-12-01", "Taj", link):
                self.assertIn(value, message)
            self.assertNotIn("1234567890", message)
            return httpx.Response(200, json=completion(draft))

        functions = [{"name": "Mehendi", "date": "2026-12-01", "venue_name": "Taj", "phone": "1234567890"}]
        with self.provider(respond):
            self.assertEqual(sarvam.write_invite("Neha", "en", "warm", "A & B", functions, link), draft)

    def test_writer_rejects_replies_that_break_message_contract(self):
        link = "https://cards.test/i/test"
        for draft in ("", "Welcome!", "x" * (400 - len(link)) + link, "Visit other.test then " + link):
            with self.subTest(draft=draft), self.provider(lambda req: httpx.Response(200, json=completion(draft))):
                with self.assertRaises(ValueError):
                    sarvam.write_invite("Neha", "en", "warm", "A & B", [], link)

    def test_invite_language_without_a_speaker_override_can_synthesize(self):
        audio = base64.b64encode(b"RIFF\x00\x00\x00\x00WAVE").decode()
        def respond(req):
            body = json.loads(req.content)
            self.assertEqual(body["language_code"], "ta-IN")
            self.assertEqual(body["speaker"], "shubh")
            return httpx.Response(200, json={"request_id": "demo", "audios": [audio]})

        with self.provider(respond):
            self.assertEqual(sarvam.synthesize("வணக்கம்", "ta"), audio)
