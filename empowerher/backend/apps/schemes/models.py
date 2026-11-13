"""
Scheme data comes from datasets/curated/schemes.json (no table). The only
tables here hold each user's scheme alerts.
"""

from django.conf import settings
from django.db import models


class SchemeAlertState(models.Model):
    """Per-user alert settings and the schemes she has already been told about."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheme_alert_state",
    )
    enabled = models.BooleanField(default=True)
    # Matching scheme ids at the last check. The first check only records
    # them (they are already on the Schemes page); later checks alert about
    # schemes that are new to this list.
    known_scheme_ids = models.JSONField(default=list, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Scheme alerts - User {self.user_id}"


class SchemeNotification(models.Model):
    KIND_CHOICES = [
        ("new_match", "New matching scheme"),
        ("deadline", "Deadline approaching"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheme_notifications",
    )
    scheme_id = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    # Makes each alert unique, e.g. the deadline date it is about.
    key = models.CharField(max_length=50, blank=True, default="")
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "scheme_id", "kind", "key"],
                name="unique_scheme_notification",
            ),
        ]

    def __str__(self):
        return f"{self.kind}: {self.scheme_id} - User {self.user_id}"
