from django.urls import path

from .views import SafetyResourcesView

urlpatterns = [
    path("resources/", SafetyResourcesView.as_view(), name="safety-resources"),
]
