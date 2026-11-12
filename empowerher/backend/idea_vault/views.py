
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.permissions import AllowAny

from . import zkp
from .encryption import (
    create_commitment,
    decrypt_idea,
    encrypt_idea,
    verify_commitment,
)
from .models import ConfidentialIdea

MAX_CONTEXT_LENGTH = 300


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
                "pedersen_commitment": item.pedersen_commitment,
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
            pedersen_commitment=format(
                zkp.commit(idea, witness_secret), "x"
            ),
        )

        # The witness is returned only once and is not stored in the DB.
        # Save it securely: it will be needed for later proof generation.
        return Response(
            {
                "message": "Confidential idea registered successfully.",
                "id": saved_idea.id,
                "title": saved_idea.title,
                "commitment": saved_idea.commitment,
                "pedersen_commitment": saved_idea.pedersen_commitment,
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
                "pedersen_commitment": item.pedersen_commitment,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
        )

    def delete(self, request, pk):
        item = self.get_owned_idea(request, pk)
        item.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class OwnershipProofView(APIView):
    """
    Generate a zero-knowledge proof that the owner knows the idea behind
    a registered commitment. Requires the witness secret, which only the
    owner holds. The proof reveals nothing about the idea itself.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        item = get_object_or_404(ConfidentialIdea, pk=pk, owner=request.user)
        witness = request.data.get("witness_secret")
        context = request.data.get("context")

        if not isinstance(context, str) or not context.strip():
            return Response(
                {"error": "Describe who the proof is for (context)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(context) > MAX_CONTEXT_LENGTH:
            return Response(
                {"error": "Context must be 300 characters or fewer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not item.pedersen_commitment:
            return Response(
                {"error": "This idea was registered before proofs were "
                          "supported. Register it again to enable proofs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            idea = decrypt_idea(item.encrypted_idea)
        except ValueError:
            return Response(
                {"error": "Unable to decrypt this idea."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not isinstance(witness, str) or not verify_commitment(
            idea, witness.strip(), item.commitment
        ):
            return Response(
                {"error": "The witness secret does not match this idea."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        proof = zkp.prove(idea, witness.strip(), context.strip())
        if proof["commitment"] != item.pedersen_commitment:
            return Response(
                {"error": "Commitment mismatch."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "proof": proof,
            "registered_at": item.created_at.isoformat(),
            "verify_url": request.build_absolute_uri("/vault/verify/"),
            "note": (
                "Share this proof with the person named in the context. "
                "They can verify it without seeing your idea."
            ),
        })


class VerifyProofView(APIView):
    """Public verification of an ownership proof (no login needed)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        proof = request.data.get("proof", request.data)
        if not isinstance(proof, dict):
            return Response({"error": "Paste the proof JSON."},
                            status=status.HTTP_400_BAD_REQUEST)

        valid = zkp.verify(proof)
        item = None
        if valid:
            item = ConfidentialIdea.objects.filter(
                pedersen_commitment=str(proof.get("commitment", "")).lower()
            ).first()

        return Response({
            "valid_proof": valid,
            "registered_on_empowerher": item is not None,
            "registered_at": item.created_at.isoformat() if item else None,
            "context": proof.get("context") if valid else None,
            "explanation": (
                "The prover knows the confidential idea behind a commitment "
                "registered on EmpowerHer at the time shown. The idea "
                "itself was not revealed."
                if valid and item else
                "The proof is mathematically valid, but its commitment is "
                "not registered on EmpowerHer."
                if valid else
                "The proof is invalid or was altered."
            ),
        })
