"""Rate limits for expensive endpoints (AI calls and document OCR)."""

from rest_framework.throttling import ScopedRateThrottle


class WriteScopedRateThrottle(ScopedRateThrottle):
    """
    Like ScopedRateThrottle, but only counts requests that do work
    (POST/PUT/PATCH). Listing or reading data stays unlimited, so a
    user browsing their documents never hits the upload limit.
    """

    def allow_request(self, request, view):
        if request.method not in ("POST", "PUT", "PATCH"):
            return True
        return super().allow_request(request, view)
