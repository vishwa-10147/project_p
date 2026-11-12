from django.test import TestCase

from config.testing import make_client


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
