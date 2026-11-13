from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.datasets import load_json

from .calculator import (
    affordability,
    loan_summary,
    matching_products,
    pmegp_split,
)


class InputError(ValueError):
    pass


def number(data, field, minimum=0.0, maximum=1e10, required=True,
           default=None):
    raw = data.get(field)
    if raw in (None, ""):
        if required:
            raise InputError(f"{field.replace('_', ' ')} is required.")
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise InputError(f"{field.replace('_', ' ')} must be a number.") from None
    if value != value or not minimum <= value <= maximum:
        raise InputError(
            f"{field.replace('_', ' ')} must be between "
            f"{minimum:g} and {maximum:g}."
        )
    return value


def bad_request(error):
    return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class EmiView(APIView):
    """Calculators are public: no personal data is stored."""

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            principal = number(request.data, "principal", 1, 1e9)
            rate = number(request.data, "annual_rate", 0, 40)
            months = int(number(request.data, "tenure_months", 1, 360))
        except InputError as error:
            return bad_request(error)

        summary = loan_summary(principal, rate, months)
        summary["matching_products"] = matching_products(principal)
        return Response(summary)


class AffordabilityView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            income = number(request.data, "monthly_income", 0, 1e9)
            expenses = number(request.data, "monthly_expenses", 0, 1e9)
            existing = number(request.data, "existing_emis", 0, 1e9,
                              required=False, default=0.0)
            rate = number(request.data, "annual_rate", 0, 40,
                          required=False, default=11.0)
            months = int(number(request.data, "tenure_months", 1, 360,
                                required=False, default=60))
            foir = number(request.data, "foir", 0.1, 0.7,
                          required=False, default=0.5)
        except InputError as error:
            return bad_request(error)

        result = affordability(income, expenses, existing, rate, months, foir)
        result["matching_products"] = matching_products(
            result["max_loan_amount"]
        )
        return Response(result)


class PmegpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            cost = number(request.data, "project_cost", 1, 5_000_000)
        except InputError as error:
            return bad_request(error)
        area = request.data.get("area", "rural")
        if area not in ("rural", "urban"):
            return bad_request("area must be 'rural' or 'urban'.")
        return Response(pmegp_split(cost, area))


class LoanProductsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = load_json("loan_products")
        amount = request.query_params.get("amount")
        try:
            amount = float(amount) if amount else None
        except ValueError:
            return bad_request("amount must be a number.")
        return Response({
            "meta": data["meta"],
            "products": matching_products(amount),
        })
