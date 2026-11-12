from django.urls import path

from .views import EncryptedFinancialCheckView

urlpatterns = [
    path("financial-check/", EncryptedFinancialCheckView.as_view(),
         name="privacy-financial-check"),
]
