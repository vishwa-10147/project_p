from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.business.models import BusinessIdea

from .analysis import analyse, list_districts, list_states


class StateListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"states": list_states()})


class DistrictListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        state = request.query_params.get("state", "")
        return Response({"state": state, "districts": list_districts(state)})


class MarketAnalysisView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        category = params.get("category", "")
        if category not in dict(BusinessIdea.CATEGORY_CHOICES):
            return Response(
                {"error": "Select a valid business category."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = analyse(
            state=params.get("state", ""),
            category=category,
            district=params.get("district"),
            location=params.get("location"),
        )
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
