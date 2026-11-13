"""Shared helpers for EmpowerHer tests."""

import os
from contextlib import contextmanager

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.settings import api_settings
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.users.models import EntrepreneurProfile

for _var in ("IDEA_VAULT_ENCRYPTION_KEY", "DOCUMENT_ENCRYPTION_KEY"):
    os.environ.setdefault(_var, Fernet.generate_key().decode())


def make_client(username="tester", state="Telangana", stage="idea",
                first_name="Lakshmi", last_name="Devi"):
    user = User.objects.create_user(
        username=username, password="Str0ng-Pass-9876",
        first_name=first_name, last_name=last_name,
    )
    EntrepreneurProfile.objects.create(
        user=user, state=state, business_stage=stage, city="Warangal",
    )
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user).key
    )
    return user, client


@contextmanager
def throttle_rates(**overrides):
    """
    Temporarily change some rate limits, e.g. throttle_rates(ai="2/minute").

    DRF copies the rates onto SimpleRateThrottle once at import, so they
    are swapped there too and restored afterwards. The cache is cleared on
    both sides so request counts from other tests never leak in.
    """
    rates = {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], **overrides}
    cache.clear()
    with override_settings(REST_FRAMEWORK={
        **settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates,
    }):
        SimpleRateThrottle.THROTTLE_RATES = rates
        try:
            yield
        finally:
            cache.clear()
    api_settings.reload()
    SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
