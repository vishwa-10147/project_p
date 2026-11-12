
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .encryption import (
    create_commitment,
    decrypt_idea,
    encrypt_idea,
)
from .models import ConfidentialIdea


class ConfidentialIdeaListCreateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List only the current owner's ideas.
        Never include the encrypted payload in the list response.
        """
        ideas = ConfidentialIdea.objects.filter(
            owner=request.user
        ).order_by("-created_at")

        results = [
            {
                "id": item.id,
                "title": item.title,
                "commitment": item.commitment,
                "created_at": item.created_at.isoformat(),
            }
            for item in ideas
        ]

        return Response({"ideas": results})

    def post(self, request):
        title = request.data.get("title")
        idea = request.data.get("idea")

        if not isinstance(title, str) or not title.strip():
            return Response(
                {"error": "A title is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(title.strip()) > 150:
            return Response(
                {"error": "The title must be 150 characters or fewer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(idea, str) or not idea.strip():
            return Response(
                {"error": "A business idea is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(idea) > 10000:
            return Response(
                {"error": "The idea must be 10,000 characters or fewer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idea = idea.strip()
        title = title.strip()

        # Encrypt before database storage.
        encrypted = encrypt_idea(idea)

        # Generate a commitment and a private witness.
        commitment, witness_secret = create_commitment(idea)

        saved_idea = ConfidentialIdea.objects.create(
            owner=request.user,
            title=title,
            encrypted_idea=encrypted,
            commitment=commitment,
        )

        # The witness is returned only once and is not stored in the DB.
        # Save it securely: it will be needed for later proof generation.
        return Response(
            {
                "message": "Confidential idea registered successfully.",
                "id": saved_idea.id,
                "title": saved_idea.title,
                "commitment": saved_idea.commitment,
                "witness_secret": witness_secret,
                "created_at": saved_idea.created_at.isoformat(),
                "security_note": (
                    "Save the witness secret securely. It cannot be "
                    "recovered from the database if lost. Do not share it."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class ConfidentialIdeaDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_owned_idea(self, request, pk):
        return get_object_or_404(
            ConfidentialIdea,
            pk=pk,
            owner=request.user,
        )

    def get(self, request, pk):
        item = self.get_owned_idea(request, pk)

        try:
            original_idea = decrypt_idea(item.encrypted_idea)
        except ValueError:
            return Response(
                {
                    "error": (
                        "Unable to decrypt this idea. "
                        "Check the configured encryption key."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "id": item.id,
                "title": item.title,
                "idea": original_idea,
                "commitment": item.commitment,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
        )

    def delete(self, request, pk):
        item = self.get_owned_idea(request, pk)
        item.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
