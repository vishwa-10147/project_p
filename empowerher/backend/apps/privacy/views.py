from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .paillier import PublicKey

MAX_RUPEES = 10 ** 10


def parse_hex(value, name):
    if not isinstance(value, str) or len(value) > 2100:
        raise ValueError(f"{name} must be a hexadecimal string.")
    try:
        return int(value, 16)
    except ValueError:
        raise ValueError(f"{name} must be a hexadecimal string.") from None


def parse_int(value, name, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a whole number.") from None
    if not low <= number <= high:
        raise ValueError(f"{name} must be between {low} and {high}.")
    return number


class EncryptedFinancialCheckView(APIView):
    """
    Loan-affordability check computed on Paillier-encrypted figures.

    Input (all ciphertexts hex-encoded, encrypted with the user's own
    public key in the browser):
        public_key.n          Paillier modulus
        monthly_income        Enc(income)
        monthly_expenses      Enc(expenses)
        existing_emis         Enc(existing EMIs)
        proposed_emi          plaintext EMI of the loan being considered
        foir_percent          share of surplus lenders allow for EMIs

    Output (ciphertexts the browser decrypts):
        monthly_surplus       Enc(income - expenses)
        annual_surplus        Enc(12 * (income - expenses))
        emi_headroom_x100     Enc(foir% * surplus - 100 * (existing + proposed))
        total_emi             Enc(existing + proposed)

    The server never receives the private key, so it cannot read the
    inputs or the results. Nothing is stored.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        try:
            key = data.get("public_key") or {}
            public = PublicKey(parse_hex(key.get("n"), "public_key.n"))
            income = public.check_ciphertext(
                parse_hex(data.get("monthly_income"), "monthly_income"))
            expenses = public.check_ciphertext(
                parse_hex(data.get("monthly_expenses"), "monthly_expenses"))
            existing = public.check_ciphertext(
                parse_hex(data.get("existing_emis"), "existing_emis"))
            proposed = parse_int(data.get("proposed_emi", 0),
                                 "proposed_emi", 0, MAX_RUPEES)
            foir = parse_int(data.get("foir_percent", 50),
                             "foir_percent", 10, 70)
        except ValueError as error:
            return Response({"error": str(error)},
                            status=status.HTTP_400_BAD_REQUEST)

        surplus = public.linear([(income, 1), (expenses, -1)])
        results = {
            "monthly_surplus": surplus,
            "annual_surplus": public.mul_plain(surplus, 12),
            "emi_headroom_x100": public.linear(
                [(income, foir), (expenses, -foir), (existing, -100)],
                constant=-100 * proposed,
            ),
            "total_emi": public.add_plain(existing, proposed),
        }

        return Response({
            "encrypted_results": {k: format(v, "x") for k, v in results.items()},
            "computed_on_ciphertext": True,
            "proposed_emi": proposed,
            "foir_percent": foir,
            "how_to_read": (
                "Decrypt emi_headroom_x100 and divide by 100. A value of "
                "zero or more means the proposed EMI fits within "
                f"{foir}% of your monthly surplus after existing EMIs."
            ),
        })
