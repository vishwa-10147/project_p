"""
Check scheme alerts for every user with alerts switched on.

    python manage.py send_scheme_alerts

Run it daily (cron, or a scheduled job on your host). Alerts appear on the
user's Schemes page and dashboard.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.schemes.alerts import check_alerts


class Command(BaseCommand):
    help = "Create scheme alerts (new matching schemes, closing deadlines)."

    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True).exclude(
            scheme_alert_state__enabled=False
        )
        total = 0
        for user in users.iterator():
            total += len(check_alerts(user, force=True))
        self.stdout.write(self.style.SUCCESS(
            f"Checked {users.count()} users; created {total} alerts."
        ))
