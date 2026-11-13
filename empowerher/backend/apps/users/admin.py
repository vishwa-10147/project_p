from django.contrib import admin

from .models import EntrepreneurProfile


@admin.register(EntrepreneurProfile)
class EntrepreneurProfileAdmin(admin.ModelAdmin):

    # Phone number and city are encrypted, so they are not listed or
    # searchable here.
    list_display = (
        "user",
        "state",
        "business_stage",
        "preferred_language",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "state",
    )

    list_filter = (
        "business_stage",
        "preferred_language",
        "state",
    )
