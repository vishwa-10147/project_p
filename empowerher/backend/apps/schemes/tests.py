from django.test import TestCase
from rest_framework.test import APIClient

from config.testing import make_client
from apps.schemes.recommender import recommend


class SchemeApiTests(TestCase):
    def test_catalogue_is_public_and_filters_by_state(self):
        response = APIClient().get("/api/schemes/", {"state": "Karnataka"})
        self.assertEqual(response.status_code, 200)
        ids = {s["id"] for s in response.data["schemes"]}
        self.assertIn("karnataka-udyogini", ids)
        self.assertNotIn("we-hub-telangana", ids)

    def test_recommend_requires_login(self):
        self.assertEqual(
            APIClient().get("/api/schemes/recommend/").status_code, 401
        )

    def test_recommend_uses_profile_state(self):
        _, client = make_client()
        response = client.get("/api/schemes/recommend/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["inputs"]["state"], "Telangana")
        states = {
            s for r in response.data["recommendations"]
            for s in r["scheme"]["states"]
        }
        self.assertTrue(states <= {"ALL", "Telangana"})

    def test_unknown_scheme_returns_404(self):
        self.assertEqual(
            APIClient().get("/api/schemes/no-such-scheme/").status_code, 404
        )


class RecommenderTests(TestCase):
    def test_food_processing_idea_ranks_pmfme_first(self):
        results = recommend(
            state="Telangana", category="food", stage="idea",
            social_groups=["shg"], amount_needed=300000,
            description="homemade pickles and millet snacks",
        )
        self.assertEqual(results[0]["scheme"]["id"], "pmfme")

    def test_community_schemes_require_membership(self):
        ids = {r["scheme"]["id"] for r in recommend(state="Telangana",
                                                     limit=50)}
        self.assertNotIn("nsfdc-mahila-samriddhi", ids)
        with_group = {
            r["scheme"]["id"]
            for r in recommend(state="Telangana", social_groups=["sc_st"],
                               limit=50)
        }
        self.assertIn("nsfdc-mahila-samriddhi", with_group)

    def test_stage_is_a_hard_filter(self):
        ids = {r["scheme"]["id"] for r in recommend(stage="existing",
                                                     limit=50)}
        self.assertNotIn("stand-up-india", ids)
