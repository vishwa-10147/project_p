from django.test import SimpleTestCase
from rest_framework.test import APIClient

from apps.funding.calculator import affordability, emi, max_principal, pmegp_split


class CalculatorTests(SimpleTestCase):
    def test_emi_matches_standard_formula(self):
        self.assertAlmostEqual(emi(500000, 10, 36), 16133.59, places=2)

    def test_zero_interest(self):
        self.assertEqual(emi(120000, 0, 12), 10000)

    def test_max_principal_inverts_emi(self):
        payment = emi(750000, 11, 60)
        self.assertAlmostEqual(max_principal(payment, 11, 60), 750000, 2)

    def test_affordability_uses_half_of_surplus(self):
        result = affordability(60000, 30000, 2000, 11, 60)
        self.assertEqual(result["affordable_emi"], 13000)

    def test_affordability_never_negative(self):
        self.assertEqual(affordability(10000, 20000, 0, 11, 60)
                         ["max_loan_amount"], 0)

    def test_pmegp_rural_subsidy(self):
        split = pmegp_split(1000000, "rural")
        self.assertEqual(split["own_contribution"], 50000)
        self.assertEqual(split["margin_money_subsidy"], 350000)


class FundingApiTests(SimpleTestCase):
    def test_emi_endpoint(self):
        response = APIClient().post("/api/funding/emi/", {
            "principal": 500000, "annual_rate": 10, "tenure_months": 36,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["yearly_schedule"]), 3)
        self.assertAlmostEqual(
            response.data["yearly_schedule"][-1]["closing_balance"], 0, 2
        )

    def test_rejects_bad_input(self):
        response = APIClient().post("/api/funding/emi/", {
            "principal": "abc", "annual_rate": 10, "tenure_months": 36,
        }, format="json")
        self.assertEqual(response.status_code, 400)
