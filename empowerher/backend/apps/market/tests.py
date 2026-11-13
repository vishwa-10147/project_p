from django.test import SimpleTestCase
from rest_framework.test import APIClient

from apps.market.analysis import analyse, find_district, list_districts


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


class MarketApiTests(SimpleTestCase):
    def test_states_endpoint_lists_all_states(self):
        response = APIClient().get("/api/market/states/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["states"]), 36)
        self.assertIn("Telangana", response.data["states"])

    def test_districts_endpoint(self):
        response = APIClient().get("/api/market/districts/",
                                   {"state": "TS"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Warangal", response.data["districts"])
        unknown = APIClient().get("/api/market/districts/",
                                  {"state": "Atlantis"})
        self.assertEqual(unknown.data["districts"], [])

    def test_analysis_endpoint_is_public(self):
        response = APIClient().get("/api/market/analysis/", {
            "state": "Telangana", "category": "food", "district": "Warangal",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], "Telangana")
        self.assertEqual(response.data["matched_district"], "Warangal")
        for key in ("demand_index", "demand_band", "insights", "sources"):
            self.assertIn(key, response.data)

    def test_unknown_state_is_a_bad_request(self):
        response = APIClient().get("/api/market/analysis/",
                                   {"state": "Atlantis", "category": "food"})
        self.assertEqual(response.status_code, 400)

    def test_unmatched_district_still_gives_state_analysis(self):
        result = analyse("Telangana", "food", district="Mumbai")
        self.assertNotIn("error", result)
        self.assertIsNone(result["matched_district"])
        self.assertTrue(0 <= result["state_average_score"] <= 100)

    def test_every_category_gives_a_bounded_score(self):
        from apps.business.models import BusinessIdea
        for category, _ in BusinessIdea.CATEGORY_CHOICES:
            with self.subTest(category=category):
                result = analyse("Kerala", category)
                self.assertNotIn("error", result)
                self.assertTrue(0 <= result["demand_index"] <= 100)
