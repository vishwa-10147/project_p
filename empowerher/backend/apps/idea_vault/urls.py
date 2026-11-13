
from django.urls import path

from .views import (
    ConfidentialIdeaDetailView,
    ConfidentialIdeaListCreateView,
    OwnershipProofView,
    VaultKeyView,
    VerifyProofView,
)

urlpatterns = [
    path(
        "",
        ConfidentialIdeaListCreateView.as_view(),
        name="idea-list-create",
    ),
    path(
        "key/",
        VaultKeyView.as_view(),
        name="idea-vault-key",
    ),
    path(
        "<int:pk>/",
        ConfidentialIdeaDetailView.as_view(),
        name="idea-detail",
    ),
    path(
        "<int:pk>/proof/",
        OwnershipProofView.as_view(),
        name="idea-proof",
    ),
    path(
        "verify-proof/",
        VerifyProofView.as_view(),
        name="idea-verify-proof",
    ),
]
