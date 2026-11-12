
from django.contrib import admin

from .models import ConfidentialIdea


@admin.register(ConfidentialIdea)
class ConfidentialIdeaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "owner",
        "commitment",
        "created_at",
    )

    search_fields = (
        "title",
        "commitment",
        "owner__username",
    )

    list_filter = ("created_at",)

    # Avoid displaying ciphertext unnecessarily in the admin form.
    exclude = ("encrypted_idea",)

    readonly_fields = (
        "owner",
        "title",
        "commitment",
        "created_at",
        "updated_at",
    )
