"""
Scheme alerts: tell an entrepreneur when

1. a scheme that matches her profile is added to EmpowerHer, or
2. a matching scheme's application deadline is less than 30 days away
   (for schemes whose dataset entry has a "deadline").

Checks run when she opens her alerts and, for everyone, from the
`send_scheme_alerts` management command (e.g. daily via cron).
"""

from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import SchemeAlertState, SchemeNotification
from .recommender import all_schemes, recommend

DEADLINE_WARNING_DAYS = 30
# How many top recommendations count as "matching" her profile.
MATCH_LIMIT = 10
# Checking more often than this (when the page is opened) is pointless.
RECHECK_AFTER = timedelta(hours=1)


def matching_scheme_ids(user):
    profile = getattr(user, "entrepreneur_profile", None)
    latest_idea = user.business_ideas.order_by("-created_at").first()
    matches = recommend(
        state=getattr(profile, "state", None) or getattr(latest_idea, "state", None),
        stage=getattr(profile, "business_stage", None),
        category=getattr(latest_idea, "category", None),
        limit=MATCH_LIMIT,
    )
    return [m["scheme"]["id"] for m in matches]


def _notify(user, scheme, kind, key, title, message):
    try:
        with transaction.atomic():
            return SchemeNotification.objects.create(
                user=user, scheme_id=scheme["id"], kind=kind, key=key,
                title=title, message=message, link=f"/schemes/#{scheme['id']}",
            )
    except IntegrityError:
        return None      # already told her about this


def parse_deadline(scheme):
    value = scheme.get("deadline")
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def check_alerts(user, today=None, force=False):
    """Create any new notifications for `user`; return the new ones."""
    state, _ = SchemeAlertState.objects.get_or_create(user=user)
    if not state.enabled:
        return []
    now = timezone.now()
    if (not force and state.last_checked_at
            and now - state.last_checked_at < RECHECK_AFTER):
        return []

    today = today or timezone.localdate()
    schemes = {s["id"]: s for s in all_schemes()}
    matching = matching_scheme_ids(user)
    created = []

    # 1. New matching schemes (not on the first check: that sets a baseline).
    first_check = state.last_checked_at is None
    known = set(state.known_scheme_ids)
    if not first_check:
        for scheme_id in matching:
            if scheme_id not in known:
                scheme = schemes[scheme_id]
                created.append(_notify(
                    user, scheme, "new_match", "",
                    f"New scheme for you: {scheme['name']}",
                    scheme["summary"],
                ))

    # 2. Deadlines within the warning window.
    for scheme_id in matching:
        scheme = schemes[scheme_id]
        deadline = parse_deadline(scheme)
        if deadline and today <= deadline <= today + timedelta(days=DEADLINE_WARNING_DAYS):
            days = (deadline - today).days
            when = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
            note = scheme.get("deadline_note") or "Applications close"
            created.append(_notify(
                user, scheme, "deadline", deadline.isoformat(),
                f"{scheme['name']}: deadline {when}",
                f"{note} on {deadline.strftime('%d %b %Y')}. "
                f"Check the official site before applying: {scheme['source_url']}",
            ))

    state.known_scheme_ids = sorted(known | set(matching))
    state.last_checked_at = now
    state.save(update_fields=["known_scheme_ids", "last_checked_at"])
    return [n for n in created if n is not None]


def serialise(notification):
    return {
        "id": notification.id,
        "scheme_id": notification.scheme_id,
        "kind": notification.kind,
        "title": notification.title,
        "message": notification.message,
        "link": notification.link,
        "created_at": notification.created_at.isoformat(),
        "read": notification.read_at is not None,
    }
