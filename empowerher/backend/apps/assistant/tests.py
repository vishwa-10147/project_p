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


class MoreLanguagesTests(TestCase):
    """Tamil, Kannada, Marathi and Bengali (the page's suggested questions)."""

    SUGGESTIONS = {
        "ta": ["எனக்குப் பொருந்தும் அரசு திட்டங்கள் எவை?",
               "என் யோசனையை ரகசியமாக வைப்பது எப்படி?",
               "ஆன்லைனில் என்னை ஏமாற்றிவிட்டார்கள்"],
        "kn": ["ನನಗೆ ಸೂಕ್ತವಾದ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಯಾವುವು?",
               "ನನ್ನ ಆಲೋಚನೆಯನ್ನು ಗೌಪ್ಯವಾಗಿ ಇಡುವುದು ಹೇಗೆ?",
               "ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ನನಗೆ ವಂಚನೆ ಆಗಿದೆ"],
        "mr": ["माझ्यासाठी कोणत्या सरकारी योजना आहेत?",
               "माझी कल्पना गुप्त कशी ठेवू?",
               "माझी ऑनलाइन फसवणूक झाली"],
        "bn": ["আমার জন্য কোন সরকারি প্রকল্প আছে?",
               "আমার ভাবনা গোপন রাখব কীভাবে?",
               "অনলাইনে আমাকে ঠকিয়েছে"],
    }

    def test_suggested_questions_find_the_right_topic(self):
        for language, (schemes, privacy, safety) in self.SUGGESTIONS.items():
            with self.subTest(language=language):
                self.assertEqual(detect_intent(schemes), "schemes")
                self.assertEqual(detect_intent(privacy), "privacy")
                self.assertEqual(detect_intent(safety), "safety")

    def test_emergency_words(self):
        for message in ("நான் ஆபத்தில் இருக்கிறேன்", "ನಾನು ಅಪಾಯದಲ್ಲಿದ್ದೇನೆ",
                        "मला वाचवा", "আমি বিপদে আছি"):
            with self.subTest(message=message):
                self.assertEqual(detect_intent(message), "emergency")

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_every_language_has_every_answer(self):
        from apps.assistant.engine import LANGUAGES, TEXT
        keys = set(TEXT["en"])
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertEqual(set(TEXT[language]), keys)
                result = answer("EMI for 5 lakh at 10% for 3 years", language=language)
                self.assertEqual(result["language"], language)
                self.assertIn("16,134", result["reply"])

    def test_short_english_words_still_match_whole_words(self):
        self.assertEqual(detect_intent("hi there"), "greeting")
        self.assertNotEqual(detect_intent("this is about something"), "greeting")

    def test_profile_accepts_new_languages(self):
        _, client = make_client()
        response = client.patch("/api/users/profile/", {"preferred_language": "bn"},
                                format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["preferred_language"], "bn")
