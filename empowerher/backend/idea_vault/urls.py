
from django.urls import path

from .views import (
    ConfidentialIdeaListCreateView,
    ConfidentialIdeaDetailView,
)

urlpatterns = [
    path(
        "",
        ConfidentialIdeaListCreateView.as_view(),
        name="idea-list-create",
    ),
    path(
        "<int:pk>/",
        ConfidentialIdeaDetailView.as_view(),
        name="idea-detail",
    ),
]
