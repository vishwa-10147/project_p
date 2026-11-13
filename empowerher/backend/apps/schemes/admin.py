from django.contrib import admin

from .models import SchemeAlertState, SchemeNotification


@admin.register(SchemeNotification)
class SchemeNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "scheme_id", "created_at", "read_at")
    list_filter = ("kind",)


@admin.register(SchemeAlertState)
class SchemeAlertStateAdmin(admin.ModelAdmin):
    list_display = ("user", "enabled", "last_checked_at")
