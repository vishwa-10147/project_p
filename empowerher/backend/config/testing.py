"""Shared helpers for EmpowerHer tests."""

import os

from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from users.models import EntrepreneurProfile

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
