
import json

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.authentication import (
    ExpiringTokenAuthentication as TokenAuthentication,
)

from . import zkp
from .e2e import (
    E2EError,
    clean_envelope,
    clean_key_settings,
    clean_pedersen_commitment,
    public_commitment,
)
from .encryption import (
    create_commitment,
    decrypt_idea,
    encrypt_idea,
    verify_commitment,
)
from .models import ConfidentialIdea, VaultKey

MAX_CONTEXT_LENGTH = 300


def bad_request(message):
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def key_settings(vault_key):
    return {
        "configured": True,
        "salt": vault_key.salt,
        "iterations": vault_key.iterations,
        "key_check": json.loads(vault_key.key_check),
        "created_at": vault_key.created_at.isoformat(),
    }


class VaultKeyView(APIView):
    """
    The public settings of the owner's end-to-end vault key (salt,
    iteration count, encrypted check value). The passphrase and the key
    never reach the server.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vault_key = VaultKey.objects.filter(owner=request.user).first()
        if vault_key is None:
            return Response({"configured": False})
        return Response(key_settings(vault_key))

    def post(self, request):
        try:
            settings = clean_key_settings(request.data)
        except E2EError as error:
            return bad_request(str(error))

        existing = VaultKey.objects.filter(owner=request.user).first()
        if existing is not None:
            # Replacing the key would make existing ideas unreadable, so
            # it's only allowed while no end-to-end idea uses it.
            if request.user.confidential_ideas.filter(encryption="browser").exists():
                return Response(
                    {"error": "Your vault passphrase is already set. Delete "
                              "your end-to-end ideas before choosing a new one."},
                    status=status.HTTP_409_CONFLICT,
                )
            existing.delete()

        vault_key = VaultKey.objects.create(owner=request.user, **settings)
        return Response(key_settings(vault_key), status=status.HTTP_201_CREATED)


def idea_summary(item):
    return {
        "id": item.id,
        "title": item.title,
        "encryption": item.encryption,
        "commitment": item.commitment,
        "pedersen_commitment": item.pedersen_commitment,
        "created_at": item.created_at.isoformat(),
    }


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

        results = [idea_summary(item) for item in ideas]

        return Response({"ideas": results})

    def post(self, request):
        if "encrypted_payload" in request.data:
            return self.create_end_to_end(request)
        return self.create_server_encrypted(request)

    @staticmethod
    def clean_title(title):
        if not isinstance(title, str) or not title.strip():
            raise E2EError("A title is required.")
        if len(title.strip()) > 150:
            raise E2EError("The title must be 150 characters or fewer.")
        return title.strip()

    def create_end_to_end(self, request):
        """
        End-to-end: the browser already encrypted the idea (and its witness)
        and computed the Pedersen commitment. The server stores ciphertext
        it cannot read.
        """
        if not VaultKey.objects.filter(owner=request.user).exists():
            return bad_request("Set your vault passphrase first.")
        try:
            title = self.clean_title(request.data.get("title"))
            envelope = clean_envelope(request.data.get("encrypted_payload"))
            pedersen = clean_pedersen_commitment(
                request.data.get("pedersen_commitment")
            )
        except E2EError as error:
            return bad_request(str(error))

        try:
            with transaction.atomic():
                saved_idea = ConfidentialIdea.objects.create(
                    owner=request.user,
                    title=title,
                    encrypted_idea=envelope,
                    encryption="browser",
                    commitment=public_commitment(pedersen),
                    pedersen_commitment=pedersen,
                )
        except IntegrityError:
            return bad_request("This commitment is already registered.")

        return Response(
            {
                "message": "Idea encrypted in your browser and registered.",
                **idea_summary(saved_idea),
            },
            status=status.HTTP_201_CREATED,
        )

    def create_server_encrypted(self, request):
        """Older flow, kept for API clients: the server encrypts the idea."""
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

        if item.encryption == "browser":
            # Only the owner's browser can decrypt this.
            return Response({
                **idea_summary(item),
                "encrypted_payload": json.loads(item.encrypted_idea),
                "updated_at": item.updated_at.isoformat(),
            })

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
                **idea_summary(item),
                "idea": original_idea,
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
        if item.encryption == "browser":
            return bad_request(
                "This idea is end-to-end encrypted: create its proof in your "
                "browser on the Idea Vault page."
            )
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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

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
