from django.urls import path

from .views import DistrictListView, MarketAnalysisView, StateListView

urlpatterns = [
    path("states/", StateListView.as_view(), name="market-states"),
    path("districts/", DistrictListView.as_view(), name="market-districts"),
    path("analysis/", MarketAnalysisView.as_view(), name="market-analysis"),
]
