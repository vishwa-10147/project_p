"""
Loan maths for EmpowerHer: EMI, amortisation, affordability and the
PMEGP subsidy split. All money values are in rupees.
"""

from config.datasets import load_json

# Lenders typically cap total EMIs at 40-50% of monthly surplus income.
DEFAULT_FOIR = 0.5


def monthly_rate(annual_rate_percent):
    return annual_rate_percent / 12 / 100


def emi(principal, annual_rate_percent, tenure_months):
    """Equated monthly instalment (reducing-balance method)."""
    r = monthly_rate(annual_rate_percent)
    if r == 0:
        return principal / tenure_months
    factor = (1 + r) ** tenure_months
    return principal * r * factor / (factor - 1)


def max_principal(affordable_emi, annual_rate_percent, tenure_months):
    """Largest loan whose EMI fits within affordable_emi."""
    if affordable_emi <= 0:
        return 0.0
    r = monthly_rate(annual_rate_percent)
    if r == 0:
        return affordable_emi * tenure_months
    return affordable_emi * (1 - (1 + r) ** -tenure_months) / r


def amortisation(principal, annual_rate_percent, tenure_months):
    """Year-by-year summary of the repayment schedule."""
    r = monthly_rate(annual_rate_percent)
    payment = emi(principal, annual_rate_percent, tenure_months)
    balance = principal
    years = []
    year = {"year": 1, "principal_paid": 0.0, "interest_paid": 0.0}

    for month in range(1, tenure_months + 1):
        interest = balance * r
        principal_part = min(payment - interest, balance)
        balance -= principal_part
        year["principal_paid"] += principal_part
        year["interest_paid"] += interest

        if month % 12 == 0 or month == tenure_months:
            year["closing_balance"] = max(balance, 0.0)
            years.append({k: round(v, 2) if isinstance(v, float) else v
                          for k, v in year.items()})
            year = {"year": year["year"] + 1,
                    "principal_paid": 0.0, "interest_paid": 0.0}

    return years


def loan_summary(principal, annual_rate_percent, tenure_months):
    payment = emi(principal, annual_rate_percent, tenure_months)
    total = payment * tenure_months
    return {
        "principal": round(principal, 2),
        "annual_rate_percent": annual_rate_percent,
        "tenure_months": tenure_months,
        "emi": round(payment, 2),
        "total_payment": round(total, 2),
        "total_interest": round(total - principal, 2),
        "yearly_schedule": amortisation(
            principal, annual_rate_percent, tenure_months
        ),
    }


def affordability(monthly_income, monthly_expenses, existing_emis,
                  annual_rate_percent, tenure_months, foir=DEFAULT_FOIR):
    surplus = monthly_income - monthly_expenses
    affordable = max(surplus * foir - existing_emis, 0.0)
    principal = max_principal(affordable, annual_rate_percent, tenure_months)
    return {
        "monthly_surplus": round(surplus, 2),
        "foir_used": foir,
        "affordable_emi": round(affordable, 2),
        "max_loan_amount": round(principal, 2),
        "note": (
            f"Assumes lenders allow EMIs of up to {int(foir * 100)}% of "
            "your monthly surplus (income minus expenses), less existing "
            "EMIs. Lenders also look at credit history and documents."
        ),
    }


def matching_products(amount):
    products = load_json("loan_products")["products"]
    if not amount:
        return products
    return [
        p for p in products
        if p["min_amount_inr"] <= amount <= p["max_amount_inr"]
    ]


def pmegp_split(project_cost, area="rural"):
    """
    Funding split for a woman applicant under PMEGP (special category):
    5% own contribution, 25% (urban) / 35% (rural) margin-money subsidy,
    the rest as a bank loan.
    """
    subsidy_rate = 0.35 if area == "rural" else 0.25
    own = project_cost * 0.05
    loan = project_cost - own
    subsidy = project_cost * subsidy_rate
    return {
        "project_cost": round(project_cost, 2),
        "area": area,
        "own_contribution": round(own, 2),
        "bank_loan": round(loan, 2),
        "subsidy_rate_percent": int(subsidy_rate * 100),
        "margin_money_subsidy": round(subsidy, 2),
        "effective_loan_after_subsidy": round(loan - subsidy, 2),
        "note": (
            "The subsidy is held as a term deposit for 3 years and then "
            "adjusted against the loan, subject to the unit working "
            "successfully. Ceiling: Rs 50 lakh (manufacturing), "
            "Rs 20 lakh (service)."
        ),
    }
