from django.urls import path

from .views import DocumentDetailView, DocumentDownloadView, DocumentListCreateView

urlpatterns = [
    path("", DocumentListCreateView.as_view(), name="document-list"),
    path("<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<uuid:pk>/download/", DocumentDownloadView.as_view(),
         name="document-download"),
]
