import os
from unittest import mock

from django.test import TestCase

from business.models import BusinessIdea
from config.testing import make_client

SECRET = "Secret recipe: sprouted ragi with jaggery syrup, slow-dried for 9 hours"
CUSTOMERS = "Gym members near Hanamkonda who order on WhatsApp"


def payload(**extra):
    data = {
        "business_name": "Millet Bites",
        "category": "food",
        "description": SECRET + " and packed in eco-friendly pouches for offices.",
        "state": "Telangana",
        "location": "Warangal",
        "target_customers": CUSTOMERS,
        "investment": "150000",
        "selling_price": "120",
        "expected_monthly_sales": "600",
        "estimated_monthly_expenses": "45000",
    }
    data.update(extra)
    return data


class ConfidentialIdeaTests(TestCase):
    def setUp(self):
        _, self.client = make_client()

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_plain_idea_is_stored_readable(self):
        response = self.client.post("/api/business/validate/", payload(),
                                    format="json")
        self.assertEqual(response.status_code, 201, response.data)
        idea = BusinessIdea.objects.get()
        self.assertFalse(idea.is_confidential)
        self.assertIn("Secret recipe", idea.description)
        self.assertEqual(idea.encrypted_details, "")

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_confidential_idea_is_encrypted_at_rest(self):
        response = self.client.post(
            "/api/business/validate/", payload(is_confidential=True),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        idea = BusinessIdea.objects.get()
        self.assertTrue(idea.is_confidential)
        self.assertEqual(idea.description, "")
        self.assertEqual(idea.target_customers, "")
        self.assertNotIn("ragi", idea.encrypted_details)
        self.assertNotIn("ragi", str(idea.report))
        self.assertNotIn(CUSTOMERS, str(idea.report))

        # The owner's data can still be recovered with the key.
        details = idea.confidential_details()
        self.assertIn("Secret recipe", details["description"])
        self.assertEqual(details["target_customers"], CUSTOMERS)

        # The report is still complete: figures, market data, schemes.
        report = response.data["report"]
        self.assertEqual(
            report["financial_estimate"]["estimated_monthly_profit"], 27000
        )
        self.assertEqual(report["market_research"]["matched_district"],
                         "Warangal")
        self.assertTrue(report["recommended_schemes"])
        self.assertTrue(report["confidentiality"]["is_confidential"])

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @mock.patch("business.ai_recommendations.OpenAI")
    def test_confidential_text_is_never_sent_to_ai(self, openai):
        openai.return_value.responses.create.return_value.output_text = "ok"

        self.client.post("/api/business/validate/",
                         payload(is_confidential=True), format="json")
        sent = str(openai.return_value.responses.create.call_args)
        self.assertNotIn("ragi", sent)
        self.assertNotIn(CUSTOMERS, sent)
        self.assertIn("Warangal", sent)

        self.client.post("/api/business/validate/", payload(),
                         format="json")
        sent = str(openai.return_value.responses.create.call_args)
        self.assertIn("ragi", sent)

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_history_marks_confidential_ideas(self):
        self.client.post("/api/business/validate/",
                         payload(is_confidential="on"), format="json")
        history = self.client.get("/api/business/history/").data["ideas"]
        self.assertTrue(history[0]["is_confidential"])
