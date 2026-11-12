import os
from unittest import mock

from django.test import TestCase

from apps.assistant.engine import answer, detect_intent, parse_emi_request
from config.testing import make_client


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
