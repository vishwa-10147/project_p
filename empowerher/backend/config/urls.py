"""
Main URL routing.

- Website pages (frontend) come from frontend/urls.py.
- The JSON REST API (backend) is under /api/, one prefix per app in apps/.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django admin panel
    path("admin/", admin.site.urls),

    # ---- Frontend: HTML pages ------------------------------------------
    path("", include("frontend.urls")),

    # ---- Backend: REST API ---------------------------------------------
    path("api/users/", include("apps.users.urls")),
    path("api/business/", include("apps.business.urls")),
    path("api/schemes/", include("apps.schemes.urls")),
    path("api/funding/", include("apps.funding.urls")),
    path("api/privacy/", include("apps.privacy.urls")),
    path("api/market/", include("apps.market.urls")),
    path("api/documents/", include("apps.documents.urls")),
    path("api/ideas/", include("apps.idea_vault.urls")),
    path("api/assistant/", include("apps.assistant.urls")),
    path("api/safety/", include("apps.safety.urls")),
]
