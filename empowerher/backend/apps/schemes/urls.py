from django.urls import path

from .views import (
    SchemeAlertsReadView,
    SchemeAlertsView,
    SchemeDetailView,
    SchemeListView,
    SchemeRecommendView,
)

urlpatterns = [
    path("", SchemeListView.as_view(), name="scheme-list"),
    path("recommend/", SchemeRecommendView.as_view(), name="scheme-recommend"),
    path("alerts/", SchemeAlertsView.as_view(), name="scheme-alerts"),
    path("alerts/read/", SchemeAlertsReadView.as_view(), name="scheme-alerts-read"),
    path("<slug:scheme_id>/", SchemeDetailView.as_view(), name="scheme-detail"),
]
