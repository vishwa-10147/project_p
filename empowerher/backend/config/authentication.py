"""Token authentication with expiry."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


def token_lifetime():
    return timedelta(hours=getattr(settings, "TOKEN_TTL_HOURS", 168))


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    DRF tokens never expire by default. Here a token is valid for
    TOKEN_TTL_HOURS (default 7 days) after login; an expired token is
    deleted and the user must log in again.
    """

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if token.created < timezone.now() - token_lifetime():
            token.delete()
            raise AuthenticationFailed("Session expired. Please log in again.")
        return user, token
