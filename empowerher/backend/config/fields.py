"""Model fields that are encrypted at rest."""

from django.core.exceptions import ValidationError
from django.db import models

from .crypto import decrypt_bytes, encrypt_bytes

# Personal details share the key that protects identity documents.
PERSONAL_DATA_KEY_ENV = "DOCUMENT_ENCRYPTION_KEY"
# Every Fernet token starts with this (version byte 0x80, base64-encoded).
FERNET_PREFIX = "gAAAAA"


class EncryptedCharField(models.TextField):
    """
    A short text value stored as a Fernet token, so a copy of the database
    reveals nothing. Python code reads and writes plain text as usual.

    Encrypted values can't be searched or filtered in SQL; use it only for
    fields the server never queries by (phone number, city).
    """

    def __init__(self, *args, max_length=None, **kwargs):
        self.plain_max_length = max_length
        kwargs.setdefault("blank", True)
        kwargs.setdefault("default", "")
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.plain_max_length is not None:
            kwargs["max_length"] = self.plain_max_length
        return name, path, args, kwargs

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if self.plain_max_length and value and len(value) > self.plain_max_length:
            raise ValidationError(
                f"Ensure this value has at most {self.plain_max_length} characters."
            )

    def from_db_value(self, value, expression, connection):
        if not value:
            return ""
        if not value.startswith(FERNET_PREFIX):
            # Written before encryption was added; re-encrypted on next save.
            return value
        return decrypt_bytes(PERSONAL_DATA_KEY_ENV, value.encode("ascii")).decode("utf-8")

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return ""
        return encrypt_bytes(PERSONAL_DATA_KEY_ENV, value.encode("utf-8")).decode("ascii")

    def formfield(self, **kwargs):
        kwargs.setdefault("max_length", self.plain_max_length)
        return super().formfield(**kwargs)
