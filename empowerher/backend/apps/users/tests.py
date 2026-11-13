from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.business.models import BusinessIdea
from apps.documents.models import Document
from apps.idea_vault.models import ConfidentialIdea
from config.testing import make_client, throttle_rates

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

    def test_login_is_rate_limited(self):
        with throttle_rates(auth="3/minute"):
            codes = [self.login("wrong").status_code for _ in range(5)]
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


class CookieSessionTests(TestCase):
    """The website keeps the login token in an HttpOnly cookie."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="cookie", password=PASSWORD)
        self.client = APIClient(enforce_csrf_checks=True)

    def login(self):
        return self.client.post("/api/users/login/", {
            "username": "cookie", "password": PASSWORD, "session": "cookie",
        }, format="json")

    def csrf(self):
        return {"HTTP_X_CSRFTOKEN": self.client.cookies["csrftoken"].value}

    def test_login_sets_httponly_cookie_and_hides_token(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("token", response.data)
        auth = response.cookies["empowerher_auth"]
        self.assertTrue(auth["httponly"])
        self.assertEqual(auth["samesite"], "Lax")
        self.assertEqual(auth.value, Token.objects.get(user=self.user).key)
        self.assertFalse(response.cookies["empowerher_signed_in"]["httponly"])
        self.assertIn("csrftoken", response.cookies)

    def test_api_clients_still_get_the_token(self):
        response = APIClient().post("/api/users/login/", {
            "username": "cookie", "password": PASSWORD,
        }, format="json")
        self.assertIn("token", response.data)
        self.assertNotIn("empowerher_auth", response.cookies)

    def test_cookie_authenticates_reads(self):
        self.login()
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "cookie")

    def test_cookie_writes_need_csrf_token(self):
        self.login()
        body = {"first_name": "Asha"}
        blocked = self.client.patch("/api/users/profile/", body, format="json")
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("CSRF", str(blocked.data))
        allowed = self.client.patch("/api/users/profile/", body, format="json",
                                    **self.csrf())
        self.assertEqual(allowed.status_code, 200)

    def test_header_token_needs_no_csrf(self):
        token = Token.objects.create(user=self.user)
        client = APIClient(enforce_csrf_checks=True)
        client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = client.patch("/api/users/profile/", {"first_name": "Asha"},
                                format="json")
        self.assertEqual(response.status_code, 200)

    def test_stale_cookie_never_blocks_login_or_public_pages(self):
        self.client.cookies["empowerher_auth"] = "not-a-real-token"
        self.assertEqual(self.client.get("/api/safety/resources/").status_code, 200)
        self.assertEqual(self.client.get("/api/users/profile/").status_code, 401)
        self.assertEqual(self.login().status_code, 200)

    def test_logout_clears_cookies_and_token(self):
        self.login()
        response = self.client.post("/api/users/logout/", **self.csrf())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["empowerher_auth"].value, "")
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.get("/api/users/profile/").status_code, 401)

    def test_logout_works_after_session_expired(self):
        self.client.cookies["empowerher_auth"] = "expired-or-unknown"
        response = self.client.post("/api/users/logout/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["empowerher_auth"].value, "")

    def test_password_change_renews_the_cookie(self):
        self.login()
        old = self.client.cookies["empowerher_auth"].value
        response = self.client.post("/api/users/change-password/", {
            "current_password": PASSWORD, "new_password": "An0ther-Pass-1234",
            "session": "cookie",
        }, format="json", **self.csrf())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("token", response.data)
        self.assertNotEqual(response.cookies["empowerher_auth"].value, old)
        self.assertEqual(self.client.get("/api/users/profile/").status_code, 200)


class ProfileEncryptionTests(TestCase):
    def test_phone_and_city_are_encrypted_in_the_database(self):
        from django.db import connection

        user, client = make_client()
        client.patch("/api/users/profile/", {
            "phone_number": "9876543210", "city": "Hanamkonda",
        }, format="json")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT phone_number, city FROM users_entrepreneurprofile "
                "WHERE user_id = %s", [user.id])
            phone, city = cursor.fetchone()
        for stored in (phone, city):
            self.assertTrue(stored.startswith("gAAAAA"))
        self.assertNotIn("9876543210", phone)
        self.assertNotIn("Hanamkonda", city)
        # The owner still sees plain text.
        profile = client.get("/api/users/profile/").data["profile"]
        self.assertEqual(profile["phone_number"], "9876543210")
        self.assertEqual(profile["city"], "Hanamkonda")

    def test_plain_text_lengths_are_still_limited(self):
        _, client = make_client()
        response = client.patch("/api/users/profile/", {
            "phone_number": "1" * 16}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_old_plain_text_rows_are_still_readable(self):
        from django.db import connection

        user, _ = make_client()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users_entrepreneurprofile SET city = %s WHERE user_id = %s",
                ["Warangal", user.id])
        user.entrepreneur_profile.refresh_from_db()
        self.assertEqual(user.entrepreneur_profile.city, "Warangal")
