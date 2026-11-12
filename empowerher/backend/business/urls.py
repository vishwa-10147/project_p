
from django.urls import path

from .views import (
    BusinessIdeaValidationView,
    BusinessIdeaHistoryView,
    BusinessIdeaDetailView,
)

urlpatterns = [
    path(
        "validate/",
        BusinessIdeaValidationView.as_view(),
        name="business-validate",
    ),
    path(
        "history/",
        BusinessIdeaHistoryView.as_view(),
        name="business-history",
    ),
    path(
        "<int:pk>/",
        BusinessIdeaDetailView.as_view(),
        name="business-detail",
    ),
]
