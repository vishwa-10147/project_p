
from django.contrib import admin

from .models import BusinessIdea


@admin.register(BusinessIdea)
class BusinessIdeaAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "category",
        "location",
        "state",
        "user",
        "is_confidential",
        "created_at",
    )

    search_fields = (
        "business_name",
        "description",
        "location",
        "state",
        "user__username",
    )

    list_filter = (
        "category",
        "state",
        "created_at",
    )

    readonly_fields = ("created_at", "is_confidential")

    # Never show ciphertext in the admin.
    exclude = ("encrypted_details",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")
