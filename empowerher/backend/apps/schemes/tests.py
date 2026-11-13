import io
from datetime import date, timedelta
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.schemes.alerts import check_alerts, matching_scheme_ids
from apps.schemes.models import SchemeAlertState, SchemeNotification
from apps.schemes.recommender import all_schemes, recommend
from config.testing import make_client


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


class SchemeAlertTests(TestCase):
    TODAY = date(2026, 11, 13)

    def setUp(self):
        self.user, self.client = make_client()
        self.schemes = {s["id"]: dict(s) for s in all_schemes()}
        self.matching = ["stand-up-india", "pmegp"]

    def patched(self):
        """Pretend the dataset and the user's matches are what the test says."""
        return mock.patch.multiple(
            "apps.schemes.alerts",
            all_schemes=lambda: list(self.schemes.values()),
            matching_scheme_ids=lambda user: list(self.matching),
        )

    def check(self, today=None):
        with self.patched():
            return check_alerts(self.user, today=today or self.TODAY, force=True)

    def test_first_check_only_sets_a_baseline(self):
        self.assertEqual(self.check(), [])
        self.assertEqual(SchemeNotification.objects.count(), 0)

    def test_new_matching_scheme_is_announced_once(self):
        self.check()
        self.matching.append("pmmy-mudra")
        created = self.check()
        self.assertEqual([n.scheme_id for n in created], ["pmmy-mudra"])
        self.assertEqual(created[0].kind, "new_match")
        self.assertEqual(self.check(), [])

    def test_deadline_alerts_only_inside_the_window(self):
        self.check()
        for days, expected in ((10, 1), (0, 1), (31, 0), (-1, 0)):
            SchemeNotification.objects.all().delete()
            deadline = self.TODAY + timedelta(days=days)
            self.schemes["pmegp"]["deadline"] = deadline.isoformat()
            with self.subTest(days=days):
                created = self.check()
                self.assertEqual(len(created), expected)
                if expected:
                    self.assertEqual(created[0].kind, "deadline")
                    self.assertIn("PMEGP", created[0].title.upper())

    def test_deadline_alert_is_not_repeated(self):
        self.schemes["pmegp"]["deadline"] = (self.TODAY + timedelta(days=5)).isoformat()
        self.assertEqual(len(self.check()), 1)
        self.assertEqual(self.check(), [])

    def test_no_alerts_when_switched_off(self):
        self.check()
        self.assertEqual(self.client.patch("/api/schemes/alerts/", {"enabled": False},
                                           format="json").status_code, 200)
        self.matching.append("pmmy-mudra")
        self.assertEqual(self.check(), [])

    def test_api_lists_and_marks_alerts_read(self):
        self.check()
        self.matching.append("pmmy-mudra")
        self.check()
        with self.patched():
            data = self.client.get("/api/schemes/alerts/").data
        self.assertTrue(data["enabled"])
        self.assertEqual(data["unread"], 1)
        self.assertEqual(data["notifications"][0]["scheme_id"], "pmmy-mudra")
        self.client.post("/api/schemes/alerts/read/")
        with self.patched():
            self.assertEqual(self.client.get("/api/schemes/alerts/").data["unread"], 0)

    def test_alerts_are_private(self):
        self.check()
        self.matching.append("pmmy-mudra")
        self.check()
        _, other = make_client(username="other")
        with self.patched():
            self.assertEqual(other.get("/api/schemes/alerts/").data["notifications"], [])
        self.assertEqual(APIClient().get("/api/schemes/alerts/").status_code, 401)

    def test_bad_toggle_rejected(self):
        response = self.client.patch("/api/schemes/alerts/", {"enabled": "yes"},
                                     format="json")
        self.assertEqual(response.status_code, 400)

    def test_real_matching_and_command(self):
        # Real recommender: a Telangana idea-stage profile matches schemes.
        self.assertTrue(matching_scheme_ids(self.user))
        out = io.StringIO()
        call_command("send_scheme_alerts", stdout=out)
        self.assertIn("Checked", out.getvalue())
        self.assertTrue(SchemeAlertState.objects.get(user=self.user).known_scheme_ids)


class SchemeStatusTests(TestCase):
    def test_flagged_schemes_have_a_note_and_sources(self):
        flagged = [s for s in all_schemes() if s.get("status") == "check_status"]
        self.assertGreaterEqual(len(flagged), 4)
        for scheme in flagged:
            with self.subTest(scheme=scheme["id"]):
                self.assertTrue(scheme["status_note"])
                self.assertTrue(all(u.startswith("https://") for u in scheme["status_sources"]))
        for scheme in all_schemes():
            self.assertIn(scheme["status"], ("active", "check_status"))

    def test_recommendations_warn_about_uncertain_schemes(self):
        results = recommend(state="Telangana", stage="idea", limit=25)
        pmegp = next(r for r in results if r["scheme"]["id"] == "pmegp")
        self.assertTrue(any("Check this scheme's current status" in c for c in pmegp["cautions"]))

    def test_deadlines_in_dataset_are_valid_dates(self):
        for scheme in all_schemes():
            if scheme.get("deadline"):
                date.fromisoformat(scheme["deadline"])
