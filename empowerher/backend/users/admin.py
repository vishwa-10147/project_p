from django.contrib import admin

from .models import EntrepreneurProfile


@admin.register(EntrepreneurProfile)
class EntrepreneurProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "phone_number",
        "city",
        "state",
        "business_stage",
        "preferred_language",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "city",
        "state",
    )

    list_filter = (
        "business_stage",
        "preferred_language",
        "state",
    )