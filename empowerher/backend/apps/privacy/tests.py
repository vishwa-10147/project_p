from django.test import TestCase

from config.testing import make_client
from apps.privacy.paillier import generate_keypair


class PaillierTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.public, cls.private = generate_keypair(1024)

    def test_homomorphic_operations(self):
        a, b = self.public.encrypt(1200), self.public.encrypt(-450)
        self.assertEqual(self.private.decrypt(self.public.add(a, b)), 750)
        self.assertEqual(
            self.private.decrypt(self.public.mul_plain(a, -3)), -3600)
        self.assertEqual(
            self.private.decrypt(self.public.add_plain(a, 5)), 1205)

    def test_encryption_is_randomised(self):
        self.assertNotEqual(self.public.encrypt(7), self.public.encrypt(7))

    def test_financial_check_endpoint(self):
        _, client = make_client()
        enc = lambda v: format(self.public.encrypt(v), "x")
        response = client.post("/api/privacy/financial-check/", {
            "public_key": {"n": format(self.public.n, "x")},
            "monthly_income": enc(60000),
            "monthly_expenses": enc(35000),
            "existing_emis": enc(2000),
            "proposed_emi": 9000,
            "foir_percent": 50,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        results = {
            k: self.private.decrypt(int(v, 16))
            for k, v in response.data["encrypted_results"].items()
        }
        self.assertEqual(results["monthly_surplus"], 25000)
        self.assertEqual(results["annual_surplus"], 300000)
        self.assertEqual(results["emi_headroom_x100"], 150000)
        self.assertEqual(results["total_emi"], 11000)

    def test_rejects_small_keys_and_bad_ciphertexts(self):
        _, client = make_client()
        response = client.post("/api/privacy/financial-check/", {
            "public_key": {"n": format(3233, "x")},
            "monthly_income": "1", "monthly_expenses": "1",
            "existing_emis": "1",
        }, format="json")
        self.assertEqual(response.status_code, 400)
