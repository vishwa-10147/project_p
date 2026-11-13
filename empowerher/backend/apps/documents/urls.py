from django.urls import path

from .views import (
    DigiLockerCallbackView,
    DigiLockerStartView,
    DigiLockerStatusView,
    DocumentDetailView,
    DocumentDownloadView,
    DocumentListCreateView,
)

urlpatterns = [
    path("", DocumentListCreateView.as_view(), name="document-list"),
    path("digilocker/", DigiLockerStatusView.as_view(), name="digilocker-status"),
    path("digilocker/start/", DigiLockerStartView.as_view(), name="digilocker-start"),
    path("digilocker/callback/", DigiLockerCallbackView.as_view(),
         name="digilocker-callback"),
    path("<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<uuid:pk>/download/", DocumentDownloadView.as_view(),
         name="document-download"),
]
