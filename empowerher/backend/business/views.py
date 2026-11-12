
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from config.authentication import (
    ExpiringTokenAuthentication as TokenAuthentication,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from market.analysis import analyse
from schemes.recommender import recommend

from .models import BusinessIdea
from .ai_recommendations import generate_ai_recommendations


def money(value):
    return round(float(value), 2)


def generate_report(idea):
    """Calculate finances and create transparent rule-based feedback."""

    revenue = idea.selling_price * idea.expected_monthly_sales
    expenses = idea.estimated_monthly_expenses
    profit = revenue - expenses

    margin = (
        profit / revenue * Decimal("100")
        if revenue > 0
        else Decimal("0")
    )

    strengths = []
    risks = []
    suggestions = []

    if len(idea.description.strip()) >= 100:
        strengths.append(
            "The business description gives a useful starting point."
        )
    else:
        risks.append("The business description needs more detail.")
        suggestions.append(
            "Describe the product or service, what makes it different, "
            "and how customers will buy it."
        )

    if idea.target_customers.strip():
        strengths.append("A target customer group has been identified.")
    else:
        risks.append("The target customer group is not defined.")
        suggestions.append(
            "Identify the customers' needs and how you will reach them."
        )

    if idea.investment > 0:
        strengths.append("An initial investment estimate is available.")
    else:
        risks.append("The initial investment is zero.")

    if idea.expected_monthly_sales > 0:
        strengths.append("An expected monthly sales estimate is available.")
    else:
        risks.append("Expected monthly sales are zero.")
        suggestions.append(
            "Estimate sales through customer interviews or a small pilot."
        )

    if profit < 0:
        risks.append("Estimated monthly expenses exceed estimated revenue.")
        suggestions.append(
            "Review your selling price, expected sales and expenses."
        )
    elif profit == 0:
        risks.append("The current estimate is at break-even.")
    else:
        strengths.append(
            "The entered figures show a positive estimated operating surplus."
        )
        suggestions.append(
            "Check whether the surplus covers taxes, loan repayments, "
            "your salary and other costs not entered."
        )

    suggestions.extend([
        "Speak to potential customers before making a large investment.",
        "Compare competing products and prices in your area.",
        "Test the idea on a small scale and update the estimates "
        "using actual results.",
    ])

    checks = [
        len(idea.description.strip()) >= 100,
        bool(idea.target_customers.strip()),
        idea.investment > 0,
        idea.expected_monthly_sales > 0,
        bool(idea.location.strip()),
        bool(idea.state.strip()),
    ]

    completeness_score = round(
        sum(checks) / len(checks) * 100
    )

    return {
        "assessment": (
            "Promising assumptions to investigate"
            if profit > 0 and completeness_score >= 60
            else "Further validation recommended"
        ),
        "completeness_score": completeness_score,
        "score_note": (
            "This score measures how completely the form is filled in. "
            "It is not the probability of business success."
        ),
        "business_summary": {
            "name": idea.business_name,
            "category": idea.get_category_display(),
            "location": f"{idea.location}, {idea.state}",
            "target_customers": idea.target_customers,
        },
        "financial_estimate": {
            "initial_investment": money(idea.investment),
            "expected_monthly_revenue": money(revenue),
            "estimated_monthly_expenses": money(expenses),
            "estimated_monthly_profit": money(profit),
            "estimated_profit_margin_percent": round(
                float(margin), 2
            ),
            "expected_monthly_sales": idea.expected_monthly_sales,
            "selling_price_per_unit": money(idea.selling_price),
            "note": (
                "These calculations use your assumptions. "
                "They are not guaranteed results and exclude any costs "
                "you have not entered."
            ),
        },
        "strengths": strengths,
        "risks": risks,
        "suggestions": list(dict.fromkeys(suggestions)),
        "market_research": market_summary(idea),
        "recommended_schemes": scheme_summary(idea),
    }


def market_summary(idea):
    """Census-based local demand indicators for the idea's location."""
    try:
        result = analyse(
            state=idea.state,
            category=idea.category,
            location=idea.location,
        )
    except Exception:  # Keep validation working if data is unavailable.
        result = {"error": "Market data unavailable."}

    if "error" in result:
        return {
            "status": "Not available",
            "note": result["error"],
        }

    keys = [
        "state", "matched_district", "demand_index", "demand_band",
        "rank_in_state", "districts_in_state", "state_average_score",
        "insights", "note", "method", "data_year_note", "sources",
    ]
    summary = {key: result[key] for key in keys if key in result}
    summary["status"] = "Census 2011 and Ministry of MSME indicators"
    ecosystem = result.get("ecosystem") or {}
    summary["ecosystem_interpretation"] = ecosystem.get("interpretation")
    return summary


def scheme_summary(idea, limit=3):
    profile = getattr(idea.user, "entrepreneur_profile", None)
    try:
        matches = recommend(
            state=idea.state,
            category=idea.category,
            stage=profile.business_stage if profile else None,
            amount_needed=float(idea.investment) or None,
            description=f"{idea.description} {idea.target_customers}",
            limit=limit,
        )
    except Exception:
        return []
    return [
        {
            "id": item["scheme"]["id"],
            "name": item["scheme"]["name"],
            "summary": item["scheme"]["summary"],
            "source_url": item["scheme"]["source_url"],
            "reasons": item["reasons"],
        }
        for item in matches
    ]


def validate_business_data(data):
    """Validate incoming form values before saving."""

    required = [
        "business_name",
        "category",
        "description",
        "state",
        "location",
        "target_customers",
        "investment",
        "selling_price",
        "expected_monthly_sales",
        "estimated_monthly_expenses",
    ]

    missing = [
        field for field in required
        if data.get(field) is None or str(data.get(field)).strip() == ""
    ]

    if missing:
        return None, {
            "error": "Please complete all required fields.",
            "fields": missing,
        }

    text_limits = {
        "business_name": 150,
        "description": 3000,
        "state": 100,
        "location": 150,
        "target_customers": 500,
    }

    cleaned = {}

    for field, max_length in text_limits.items():
        value = str(data.get(field, "")).strip()

        if not value:
            return None, {
                "error": f"{field.replace('_', ' ').title()} cannot be blank."
            }

        if len(value) > max_length:
            return None, {
                "error": (
                    f"{field.replace('_', ' ').title()} must contain "
                    f"no more than {max_length} characters."
                )
            }

        cleaned[field] = value

    category_values = dict(BusinessIdea.CATEGORY_CHOICES)

    if data.get("category") not in category_values:
        return None, {"error": "Select a valid business category."}

    try:
        investment = Decimal(str(data["investment"]))
        selling_price = Decimal(str(data["selling_price"]))
        expenses = Decimal(str(data["estimated_monthly_expenses"]))
        raw_sales = str(data["expected_monthly_sales"]).strip()

        # Reject fractional and non-integer sales quantities.
        sales_decimal = Decimal(raw_sales)

        if not sales_decimal.is_finite():
            raise InvalidOperation

        if sales_decimal != sales_decimal.to_integral_value():
            raise InvalidOperation

        sales = int(sales_decimal)

    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return None, {
            "error": (
                "Enter valid numbers. Monthly sales must be a whole number."
            )
        }

    values = [investment, selling_price, expenses]

    if not all(value.is_finite() for value in values):
        return None, {"error": "Financial values must be finite numbers."}

    if any(value < 0 for value in values):
        return None, {"error": "Financial values cannot be negative."}

    if any(value > Decimal("9999999999.99") for value in values):
        return None, {"error": "A financial value exceeds the allowed limit."}

    if sales < 0 or sales > 100000000:
        return None, {
            "error": "Monthly sales must be between 0 and 100000000."
        }

    cleaned.update({
        "is_confidential": str(
            data.get("is_confidential", "")
        ).strip().lower() in ("true", "1", "on", "yes"),
        "category": data["category"],
        "investment": investment,
        "selling_price": selling_price,
        "estimated_monthly_expenses": expenses,
        "expected_monthly_sales": sales,
    })

    return cleaned, None


class BusinessIdeaValidationView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cleaned, error = validate_business_data(request.data)

        if error:
            return Response(
                error,
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Build the report while the text is still in memory.
            idea = BusinessIdea(user=request.user, **cleaned)
            report = generate_report(idea)

            if idea.is_confidential:
                report["business_summary"]["target_customers"] = (
                    "Confidential (encrypted)"
                )
                report["confidentiality"] = {
                    "is_confidential": True,
                    "note": (
                        "Your description and target customers are stored "
                        "encrypted and were not sent to the AI service. "
                        "Category, location and figures are stored readable "
                        "so the report, schemes and market data work."
                    ),
                }
                idea.seal_confidential_fields()

            # Save the baseline report before calling the external AI API.
            idea.report = report
            idea.save()

        # AI failures are handled by the recommendation service.
        ai_result = generate_ai_recommendations(idea, report)
        report["ai_recommendations"] = ai_result

        idea.report = report
        idea.save(update_fields=["report"])

        return Response(
            {
                "message": "Business idea assessment generated.",
                "idea_id": idea.id,
                "report": report,
            },
            status=status.HTTP_201_CREATED,
        )


class BusinessIdeaHistoryView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ideas = BusinessIdea.objects.filter(user=request.user)

        return Response({
            "ideas": [
                {
                    "id": idea.id,
                    "business_name": idea.business_name,
                    "category": idea.get_category_display(),
                    "location": idea.location,
                    "state": idea.state,
                    "is_confidential": idea.is_confidential,
                    "created_at": idea.created_at.isoformat(),
                    "report": idea.report,
                }
                for idea in ideas
            ]
        })


class BusinessIdeaDetailView(APIView):
    """Owner-only view (decrypts confidential details) and deletion."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        idea = get_object_or_404(BusinessIdea, pk=pk, user=request.user)
        try:
            details = idea.confidential_details()
        except ValueError:
            return Response(
                {"error": "Unable to decrypt this idea. "
                          "Check the configured encryption key."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({
            "id": idea.id,
            "business_name": idea.business_name,
            "category": idea.get_category_display(),
            "state": idea.state,
            "location": idea.location,
            "is_confidential": idea.is_confidential,
            "description": details["description"],
            "target_customers": details["target_customers"],
            "created_at": idea.created_at.isoformat(),
            "report": idea.report,
        })

    def delete(self, request, pk):
        idea = get_object_or_404(BusinessIdea, pk=pk, user=request.user)
        idea.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
