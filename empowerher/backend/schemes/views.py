from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.models import BusinessIdea
from config.datasets import load_json

from .recommender import (
    SOCIAL_GROUP_LABELS,
    filter_schemes,
    get_scheme,
    recommend,
)


def parse_amount(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount > 0 else None


class SchemeListView(APIView):
    """Browse and filter the scheme catalogue (public)."""

    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        schemes = filter_schemes(
            state=params.get("state"),
            category=params.get("category"),
            stage=params.get("stage"),
            benefit_type=params.get("benefit_type"),
            query=params.get("q"),
        )
        meta = load_json("schemes")["meta"]
        return Response({
            "count": len(schemes),
            "last_reviewed": meta["last_reviewed"],
            "disclaimer": meta["disclaimer"],
            "social_groups": SOCIAL_GROUP_LABELS,
            "schemes": schemes,
        })


class SchemeDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, scheme_id):
        scheme = get_scheme(scheme_id)
        if scheme is None:
            return Response(
                {"error": "Scheme not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(scheme)


class SchemeRecommendView(APIView):
    """
    Personalised recommendations.

    Defaults come from the user's profile (state, business stage) and,
    when idea_id is given, from a saved business idea (category,
    description, investment). Query parameters override both.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = request.query_params
        profile = getattr(request.user, "entrepreneur_profile", None)

        state = profile.state if profile else ""
        stage = profile.business_stage if profile else None
        category = None
        description = ""
        amount = None

        idea_id = params.get("idea_id")
        if idea_id:
            idea = BusinessIdea.objects.filter(
                pk=idea_id, user=request.user
            ).first()
            if idea is None:
                return Response(
                    {"error": "Business idea not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            state = idea.state
            category = idea.category
            description = f"{idea.description} {idea.target_customers}"
            amount = float(idea.investment) or None

        state = params.get("state") or state
        stage = params.get("stage") or stage
        category = params.get("category") or category
        description = params.get("description") or description
        amount = parse_amount(params.get("amount")) or amount
        groups = [
            g for g in params.getlist("group")
            if g in SOCIAL_GROUP_LABELS
        ]

        results = recommend(
            state=state,
            category=category,
            stage=stage,
            social_groups=groups,
            amount_needed=amount,
            description=description,
        )

        return Response({
            "inputs": {
                "state": state,
                "stage": stage,
                "category": category,
                "amount_needed": amount,
                "social_groups": groups,
                "used_description": bool(description),
            },
            "disclaimer": load_json("schemes")["meta"]["disclaimer"],
            "recommendations": results,
        })
