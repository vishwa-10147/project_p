from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.settings import api_settings
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from business.models import BusinessIdea
from config.testing import make_client
from documents.models import Document
from idea_vault.models import ConfidentialIdea

PASSWORD = "Str0ng-Pass-9876"


class ProfileTests(TestCase):
    def test_update_profile(self):
        _, client = make_client()
        response = client.patch("/api/users/profile/", {
            "first_name": "Sita", "state": "Kerala",
            "preferred_language": "hi",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["first_name"], "Sita")
        self.assertEqual(response.data["profile"]["state"], "Kerala")

    def test_rejects_invalid_language(self):
        _, client = make_client()
        response = client.patch("/api/users/profile/",
                                {"preferred_language": "xx"}, format="json")
        self.assertEqual(response.status_code, 400)


class SessionTests(TestCase):
    def setUp(self):
        cache.clear()

    def login(self, password=PASSWORD):
        return APIClient().post("/api/users/login/", {
            "username": "tester", "password": password,
        }, format="json")

    def test_login_rotates_token(self):
        make_client()
        first = self.login().data["token"]
        second = self.login().data["token"]
        self.assertNotEqual(first, second)
        old = APIClient()
        old.credentials(HTTP_AUTHORIZATION="Token " + first)
        self.assertEqual(old.get("/api/users/profile/").status_code, 401)

    def test_expired_token_is_rejected_and_deleted(self):
        user, client = make_client()
        Token.objects.filter(user=user).update(
            created=Token.objects.get(user=user).created - timedelta(days=8)
        )
        response = client.get("/api/users/profile/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", str(response.data))
        self.assertFalse(Token.objects.filter(user=user).exists())

    @override_settings(REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {"auth": "3/minute", "public": "60/minute"},
    })
    def test_login_is_rate_limited(self):
        # DRF reads throttle rates once at import; reload them for the test.
        api_settings.reload()
        SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
        try:
            codes = [self.login("wrong").status_code for _ in range(5)]
        finally:
            api_settings.reload()
            SimpleRateThrottle.THROTTLE_RATES = (
                api_settings.DEFAULT_THROTTLE_RATES)
        self.assertEqual(codes[:3], [401, 401, 401])
        self.assertEqual(codes[3:], [429, 429])

    def test_change_password(self):
        _, client = make_client()
        wrong = client.post("/api/users/change-password/", {
            "current_password": "nope", "new_password": "An0ther-Pass-1234",
        }, format="json")
        self.assertEqual(wrong.status_code, 400)
        weak = client.post("/api/users/change-password/", {
            "current_password": PASSWORD, "new_password": "123",
        }, format="json")
        self.assertEqual(weak.status_code, 400)
        ok = client.post("/api/users/change-password/", {
            "current_password": PASSWORD, "new_password": "An0ther-Pass-1234",
        }, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.login("An0ther-Pass-1234").status_code, 200)


class DataControlTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.client = make_client()
        self.client.post("/api/business/validate/", {
            "business_name": "Bites", "category": "food",
            "description": "Secret ragi recipe for crunchy energy bars",
            "state": "Telangana", "location": "Warangal",
            "target_customers": "Gym members", "investment": "1000",
            "selling_price": "10", "expected_monthly_sales": "10",
            "estimated_monthly_expenses": "50", "is_confidential": True,
        }, format="json")
        self.client.post("/api/ideas/", {"title": "T", "idea": "Vault idea"},
                         format="json")

    def test_export_decrypts_for_owner(self):
        response = self.client.get("/api/users/export/")
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertIn("Secret ragi", data["business_ideas"][0]["description"])
        self.assertEqual(data["idea_vault"][0]["idea"], "Vault idea")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_owner_can_view_and_delete_business_idea(self):
        idea = BusinessIdea.objects.get()
        _, other = make_client(username="other")
        self.assertEqual(other.get(f"/api/business/{idea.id}/").status_code,
                         404)
        detail = self.client.get(f"/api/business/{idea.id}/")
        self.assertEqual(detail.data["target_customers"], "Gym members")
        self.assertEqual(
            self.client.delete(f"/api/business/{idea.id}/").status_code, 204)
        self.assertFalse(BusinessIdea.objects.exists())

    def test_delete_account_requires_password_and_removes_everything(self):
        Document.objects.create(
            owner=self.user, doc_type="pan", original_name="x.png",
            content_type="image/png", size_bytes=1, encrypted_file=b"x",
            status="failed",
        )
        bad = self.client.post("/api/users/delete-account/",
                               {"password": "wrong"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

        ok = self.client.post("/api/users/delete-account/",
                              {"password": PASSWORD}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(BusinessIdea.objects.exists())
        self.assertFalse(ConfidentialIdea.objects.exists())
        self.assertFalse(Document.objects.exists())
