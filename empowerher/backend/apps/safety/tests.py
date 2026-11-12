from django.test import SimpleTestCase
from rest_framework.test import APIClient


class SafetyTests(SimpleTestCase):
    def test_state_specific_helplines(self):
        all_india = APIClient().get("/api/safety/resources/").data
        telangana = APIClient().get("/api/safety/resources/",
                                    {"state": "Telangana"}).data
        self.assertIn("112", {h["number"] for h in all_india["helplines"]})
        self.assertGreater(len(telangana["helplines"]),
                           len(all_india["helplines"]))
