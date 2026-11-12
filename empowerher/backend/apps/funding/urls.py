from django.urls import path

from .views import AffordabilityView, EmiView, LoanProductsView, PmegpView

urlpatterns = [
    path("emi/", EmiView.as_view(), name="funding-emi"),
    path("affordability/", AffordabilityView.as_view(),
         name="funding-affordability"),
    path("pmegp/", PmegpView.as_view(), name="funding-pmegp"),
    path("products/", LoanProductsView.as_view(), name="funding-products"),
]
