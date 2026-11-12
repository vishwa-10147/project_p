from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.datasets import load_json, match_state


class SafetyResourcesView(APIView):
    """Helplines, reporting portals and safety guides (public)."""

    permission_classes = [AllowAny]

    def get(self, request):
        data = load_json("safety_resources")
        state = match_state(request.query_params.get("state"))
        helplines = [
            h for h in data["helplines"]
            if h["scope"] == "All India" or (state and state in h["scope"])
        ]
        return Response({
            "meta": data["meta"],
            "state": state,
            "helplines": helplines,
            "reporting_portals": data["reporting_portals"],
            "guides": data["guides"],
        })
