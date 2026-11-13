import json

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.authentication import (
    clear_auth_cookies,
    set_auth_cookies,
    wants_cookie_session,
)

from .models import EntrepreneurProfile
from .serializers import (
    EntrepreneurProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)


def new_token(user):
    """Replace the user's token (logs out other sessions)."""
    Token.objects.filter(user=user).delete()
    return Token.objects.create(user=user)


def signed_in_response(request, token, data, status_code=status.HTTP_200_OK):
    """
    The website (session="cookie") gets the token only as an HttpOnly
    cookie; other API clients get it in the response body.
    """
    if wants_cookie_session(request):
        response = Response(data, status=status_code)
        return set_auth_cookies(request, response, token)
    return Response({**data, "token": token.key}, status=status_code)


class RegisterView(APIView):
    """
    Register a new EmpowerHer entrepreneur.
    """

    # No authentication: a stale login cookie must never block login.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):

        serializer = RegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():

            user = serializer.save()

            token, created = Token.objects.get_or_create(
                user=user
            )

            return signed_in_response(request, token, {
                "message": "Registration successful.",
                "user": UserSerializer(user).data,
            }, status.HTTP_201_CREATED)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class LoginView(APIView):
    """
    Authenticate an EmpowerHer entrepreneur.
    """

    # No authentication: a stale login cookie must never block login.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):

        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:

            return Response(
                {
                    "error": "Username and password are required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(
            username=username,
            password=password
        )

        if user is None:

            return Response(
                {
                    "error": "Invalid username or password."
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Issue a fresh token on every login so the expiry period restarts.
        token = new_token(user)

        return signed_in_response(request, token, {
            "message": "Login successful.",
            "user": UserSerializer(user).data,
        })


class ProfileView(APIView):
    """
    Get the currently authenticated entrepreneur.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):

        serializer = UserSerializer(
            request.user
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def patch(self, request):
        """Update name, email and entrepreneur profile fields."""

        user = request.user
        profile, _ = EntrepreneurProfile.objects.get_or_create(user=user)

        profile_serializer = EntrepreneurProfileSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        if not profile_serializer.is_valid():
            return Response(
                profile_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        for field, limit in (("first_name", 150), ("last_name", 150)):
            if field in request.data:
                value = str(request.data[field]).strip()
                if len(value) > limit:
                    return Response(
                        {field: f"Must be {limit} characters or fewer."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                setattr(user, field, value)

        user.save()
        profile_serializer.save()

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_200_OK
        )


class LogoutView(APIView):
    """
    Logout: delete the token and clear the login cookies. Works even when
    the session has already expired, so the browser is always signed out.
    """

    permission_classes = [AllowAny]

    def perform_authentication(self, request):
        try:
            request.user  # noqa: B018 - triggers authentication
        except (AuthenticationFailed, PermissionDenied):
            request._not_authenticated()

    def post(self, request):

        if request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()

        return clear_auth_cookies(Response(
            {
                "message": "Logout successful."
            },
            status=status.HTTP_200_OK
        ))


class ChangePasswordView(APIView):
    """Change the password; other sessions are logged out."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        user = request.user
        current = request.data.get("current_password") or ""
        new = request.data.get("new_password") or ""

        if not user.check_password(current):
            return Response(
                {"error": "Your current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            validate_password(new, user)
        except ValidationError as error:
            return Response(
                {"error": " ".join(error.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new)
        user.save()
        token = new_token(user)

        return signed_in_response(request, token, {
            "message": "Password changed. Other sessions were logged out.",
        })


class DataExportView(APIView):
    """
    Download everything EmpowerHer stores about the user, with encrypted
    items decrypted for their owner (documents: details only; each file
    can be downloaded from the Documents page).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.documents.views import serialise as serialise_document
        from apps.idea_vault.encryption import decrypt_idea

        user = request.user

        ideas = []
        for idea in user.business_ideas.all():
            details = idea.confidential_details()
            ideas.append({
                "business_name": idea.business_name,
                "category": idea.get_category_display(),
                "state": idea.state,
                "location": idea.location,
                "description": details["description"],
                "target_customers": details["target_customers"],
                "investment": str(idea.investment),
                "selling_price": str(idea.selling_price),
                "expected_monthly_sales": idea.expected_monthly_sales,
                "estimated_monthly_expenses": str(
                    idea.estimated_monthly_expenses
                ),
                "is_confidential": idea.is_confidential,
                "report": idea.report,
                "created_at": idea.created_at.isoformat(),
            })

        vault = []
        for item in user.confidential_ideas.all():
            entry = {"title": item.title, "encryption": item.encryption}
            if item.encryption == "browser":
                # End-to-end: the server cannot decrypt it. The ciphertext
                # opens with the owner's vault passphrase.
                entry["encrypted_payload"] = json.loads(item.encrypted_idea)
                text = None
            else:
                try:
                    text = decrypt_idea(item.encrypted_idea)
                except ValueError:
                    text = None
            vault.append({
                **entry,
                "idea": text,
                "commitment": item.commitment,
                "pedersen_commitment": item.pedersen_commitment,
                "created_at": item.created_at.isoformat(),
            })

        data = {
            "exported_at": timezone.now().isoformat(),
            "account": UserSerializer(user).data,
            "business_ideas": ideas,
            "idea_vault": vault,
            "documents": [
                serialise_document(d) for d in user.documents.all()
            ],
            "note": (
                "Idea Vault witness secrets are never stored in readable "
                "form, so they are not included. End-to-end encrypted ideas "
                "are included as ciphertext that only your vault passphrase "
                "can open. Download document files from the Documents page."
            ),
        }
        response = Response(data)
        response["Content-Disposition"] = (
            'attachment; filename="empowerher-my-data.json"'
        )
        response["Cache-Control"] = "no-store"
        return response


class DeleteAccountView(APIView):
    """Permanently delete the account and all its data."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not request.user.check_password(
            request.data.get("password") or ""
        ):
            return Response(
                {"error": "Password is incorrect. Nothing was deleted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Cascades to profile, ideas, vault entries, documents and token.
        request.user.delete()
        return clear_auth_cookies(Response({
            "message": "Your account and all its data were deleted."
        }))
