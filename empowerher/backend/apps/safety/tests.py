from django.test import SimpleTestCase
from rest_framework.test import APIClient

from config.datasets import load_json


class SafetyTests(SimpleTestCase):
    def get(self, **params):
        response = APIClient().get("/api/safety/resources/", params)
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_state_specific_helplines(self):
        all_india = self.get()
        telangana = self.get(state="Telangana")
        self.assertIn("112", {h["number"] for h in all_india["helplines"]})
        self.assertGreater(len(telangana["helplines"]),
                           len(all_india["helplines"]))

    def test_public_without_login(self):
        # Safety help must never sit behind a login screen.
        response = APIClient().get("/api/safety/resources/")
        self.assertEqual(response.status_code, 200)

    def test_without_state_only_all_india_numbers(self):
        data = self.get()
        self.assertIsNone(data["state"])
        self.assertTrue(data["helplines"])
        self.assertEqual({h["scope"] for h in data["helplines"]},
                         {"All India"})

    def test_state_name_is_matched_loosely(self):
        # Lower case and extra spaces still find the state.
        self.assertEqual(self.get(state="  telangana ")["state"], "Telangana")

    def test_unknown_state_falls_back_to_all_india(self):
        data = self.get(state="Atlantis")
        self.assertIsNone(data["state"])
        self.assertEqual(len(data["helplines"]),
                         len(self.get()["helplines"]))

    def test_response_includes_portals_guides_and_disclaimer(self):
        data = self.get()
        source = load_json("safety_resources")
        self.assertEqual(data["reporting_portals"],
                         source["reporting_portals"])
        self.assertEqual(data["guides"], source["guides"])
        self.assertIn("112", data["meta"]["disclaimer"])

    def test_every_helpline_is_complete(self):
        for helpline in load_json("safety_resources")["helplines"]:
            with self.subTest(helpline=helpline.get("name")):
                for field in ("name", "number", "scope", "use_for"):
                    self.assertTrue(helpline.get(field), field)
