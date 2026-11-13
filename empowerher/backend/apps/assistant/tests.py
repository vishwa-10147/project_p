import os
from unittest import mock

from django.test import TestCase

from apps.assistant.engine import answer, detect_intent, parse_emi_request
from config.testing import make_client, throttle_rates


class AssistantTests(TestCase):
    def test_intents_in_three_languages(self):
        self.assertEqual(detect_intent("Which government schemes suit me?"),
                         "schemes")
        self.assertEqual(detect_intent("ప్రభుత్వ పథకాలు చెప్పండి"), "schemes")
        self.assertEqual(detect_intent("मेरे साथ ऑनलाइन धोखा हुआ"), "safety")
        self.assertEqual(detect_intent("I am in danger"), "emergency")

    def test_emi_parsing(self):
        self.assertEqual(
            parse_emi_request("EMI for 5 lakh at 10% for 3 years"),
            (500000, 10.0, 36))
        self.assertEqual(
            parse_emi_request("emi 250000 at 12.5% for 18 months"),
            (250000, 12.5, 18))
        self.assertIsNone(parse_emi_request("what is emi"))

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_knowledge_base_answers(self):
        result = answer("EMI for 5 lakh at 10% for 3 years")
        self.assertIn("16,134", result["reply"])
        self.assertEqual(result["mode"], "knowledge-base")

    @mock.patch("apps.assistant.engine.ai_answer")
    def test_emergency_never_waits_for_ai(self, ai_answer):
        result = answer("help me, I am unsafe", language="te")
        ai_answer.assert_not_called()
        self.assertIn("112", result["reply"])

    def test_chat_endpoint(self):
        _, client = make_client()
        response = client.post("/api/assistant/chat/",
                               {"message": "hello", "language": "hi"},
                               format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["language"], "hi")

    def test_chat_needs_login(self):
        from rest_framework.test import APIClient
        response = APIClient().post("/api/assistant/chat/",
                                    {"message": "hello"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_chat_rejects_empty_and_long_messages(self):
        _, client = make_client()
        for message in ("", "   ", None, 42):
            with self.subTest(message=message):
                response = client.post("/api/assistant/chat/",
                                       {"message": message}, format="json")
                self.assertEqual(response.status_code, 400)
        too_long = client.post("/api/assistant/chat/",
                               {"message": "a" * 1001}, format="json")
        self.assertEqual(too_long.status_code, 400)

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(answer("hello", language="xx")["language"], "en")

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_chat_uses_profile_language_by_default(self):
        user, client = make_client()
        user.entrepreneur_profile.preferred_language = "te"
        user.entrepreneur_profile.save()
        response = client.post("/api/assistant/chat/",
                               {"message": "hello"}, format="json")
        self.assertEqual(response.data["language"], "te")

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_chat_is_rate_limited(self):
        _, client = make_client()
        with throttle_rates(ai="2/minute"):
            codes = [client.post("/api/assistant/chat/", {"message": "hi"},
                                 format="json").status_code
                     for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])
