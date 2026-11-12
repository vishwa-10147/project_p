from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EntrepreneurProfile
from .serializers import (
    EntrepreneurProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    """
    Register a new EmpowerHer entrepreneur.
    """

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = RegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():

            user = serializer.save()

            token, created = Token.objects.get_or_create(
                user=user
            )

            return Response(
                {
                    "message": "Registration successful.",
                    "token": token.key,
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class LoginView(APIView):
    """
    Authenticate an EmpowerHer entrepreneur.
    """

    permission_classes = [AllowAny]

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

        token, created = Token.objects.get_or_create(
            user=user
        )

        return Response(
            {
                "message": "Login successful.",
                "token": token.key,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )


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
    Logout the currently authenticated entrepreneur.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            request.user.auth_token.delete()
        except Token.DoesNotExist:
            pass

        return Response(
            {
                "message": "Logout successful."
            },
            status=status.HTTP_200_OK
        )