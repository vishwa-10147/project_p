
from django.urls import path

from .views import (
    BusinessIdeaValidationView,
    BusinessIdeaHistoryView,
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
]
