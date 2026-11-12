"""Fernet (AES-128-CBC + HMAC-SHA256) helpers keyed from environment variables."""

import os

from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured


def get_fernet(env_var):
    key = os.environ.get(env_var)
    if not key:
        raise ImproperlyConfigured(f"Set the {env_var} environment variable.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ImproperlyConfigured(
            f"{env_var} is not a valid Fernet key."
        ) from exc


def encrypt_bytes(env_var, data):
    return get_fernet(env_var).encrypt(data)


def decrypt_bytes(env_var, token):
    try:
        return get_fernet(env_var).decrypt(bytes(token))
    except InvalidToken as exc:
        raise ValueError("Decryption failed; check the configured key.") from exc
