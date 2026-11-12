from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .engine import answer

MAX_MESSAGE_LENGTH = 1000


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get("message")
        if not isinstance(message, str) or not message.strip():
            return Response({"error": "Type or say a question."},
                            status=status.HTTP_400_BAD_REQUEST)
        if len(message) > MAX_MESSAGE_LENGTH:
            return Response(
                {"error": "Please keep questions under 1000 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = getattr(request.user, "entrepreneur_profile", None)
        language = request.data.get("language") or (
            profile.preferred_language if profile else "en"
        )
        history = request.data.get("history")
        if not isinstance(history, list):
            history = []

        return Response(answer(
            message.strip(),
            language=language,
            history=[h for h in history if isinstance(h, dict)],
            profile=profile,
        ))
