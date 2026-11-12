from django.test import SimpleTestCase
from rest_framework.test import APIClient

from market.analysis import analyse, find_district, list_districts


class MarketTests(SimpleTestCase):
    def test_telangana_districts_split_from_2011_andhra(self):
        self.assertEqual(len(list_districts("Telangana")), 10)
        self.assertIn("Hyderabad", list_districts("telangana"))
        self.assertNotIn("Hyderabad", list_districts("Andhra Pradesh"))

    def test_fuzzy_district_match(self):
        self.assertEqual(find_district("Telangana", "warangal, TS"),
                         "Warangal")
        self.assertEqual(find_district("Telangana", "Ranga Reddy"),
                         "Rangareddy")
        self.assertIsNone(find_district("Telangana", "Mumbai"))

    def test_analysis_scores_are_bounded(self):
        result = analyse("Telangana", "technology", district="Hyderabad")
        self.assertEqual(result["matched_district"], "Hyderabad")
        self.assertTrue(0 <= result["demand_index"] <= 100)
        self.assertEqual(result["rank_in_state"], 1)
        self.assertGreater(result["ecosystem"]["women_owned_msmes"], 500000)

    def test_unknown_state_and_category(self):
        self.assertIn("error", analyse("Atlantis", "food"))
        response = APIClient().get("/api/market/analysis/",
                                   {"state": "Kerala", "category": "x"})
        self.assertEqual(response.status_code, 400)
