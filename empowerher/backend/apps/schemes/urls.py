from django.urls import path

from .views import SchemeDetailView, SchemeListView, SchemeRecommendView

urlpatterns = [
    path("", SchemeListView.as_view(), name="scheme-list"),
    path("recommend/", SchemeRecommendView.as_view(), name="scheme-recommend"),
    path("<slug:scheme_id>/", SchemeDetailView.as_view(), name="scheme-detail"),
]
