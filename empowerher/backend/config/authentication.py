"""
Login tokens: expiring, and kept in an HttpOnly cookie for the website.

The website never sees the token. After login the server puts it in an
HttpOnly cookie, which page scripts (including any injected script) cannot
read. Because the browser sends that cookie automatically, every
state-changing request authenticated by the cookie must also carry Django's
CSRF token, exactly like Django's own session login.

Other API clients (scripts, a future mobile app, the tests) can still send
`Authorization: Token <key>`; such requests don't need CSRF, since a
malicious site cannot make the browser add that header.
"""

from datetime import timedelta

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

AUTH_COOKIE = "empowerher_auth"
# Not secret: lets page scripts know someone is signed in (to redirect
# signed-out visitors to the login page before any API call).
SIGNED_IN_COOKIE = "empowerher_signed_in"


def token_lifetime():
    return timedelta(hours=getattr(settings, "TOKEN_TTL_HOURS", 168))


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    DRF tokens never expire by default. Here a token is valid for
    TOKEN_TTL_HOURS (default 7 days) after login; an expired token is
    deleted and the user must log in again.

    The token is read from the Authorization header, or else from the
    HttpOnly auth cookie (with a CSRF check).
    """

    def authenticate(self, request):
        if get_authorization_header(request):
            return super().authenticate(request)

        key = request.COOKIES.get(AUTH_COOKIE)
        if not key:
            return None
        try:
            user, token = self.authenticate_credentials(key)
        except AuthenticationFailed:
            # A stale cookie (expired or logged out elsewhere) makes the
            # visitor anonymous: public pages keep working, and pages that
            # need a login answer 401 as usual.
            return None
        self.enforce_csrf(request)
        return user, token

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if token.created < timezone.now() - token_lifetime():
            token.delete()
            raise AuthenticationFailed("Session expired. Please log in again.")
        return user, token

    @staticmethod
    def enforce_csrf(request):
        """Same CSRF rule as DRF's SessionAuthentication."""
        check = _CSRFCheck(lambda req: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise PermissionDenied(f"CSRF Failed: {reason}")


def _cookie_options():
    return {
        "max_age": int(token_lifetime().total_seconds()),
        "secure": getattr(settings, "AUTH_COOKIE_SECURE", not settings.DEBUG),
        "samesite": "Lax",
        "path": "/",
    }


def set_auth_cookies(request, response, token):
    """Log the browser in: HttpOnly token cookie + fresh CSRF cookie."""
    options = _cookie_options()
    response.set_cookie(AUTH_COOKIE, token.key, httponly=True, **options)
    response.set_cookie(SIGNED_IN_COOKIE, "1", httponly=False, **options)
    # Make sure the browser has a CSRF cookie for its next requests.
    get_token(request)
    return response


def clear_auth_cookies(response):
    for name in (AUTH_COOKIE, SIGNED_IN_COOKIE):
        response.delete_cookie(name, path="/", samesite="Lax")
    return response


def wants_cookie_session(request):
    """The website asks for a cookie session instead of a token in the body."""
    return request.data.get("session") == "cookie"
