
import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


COMMITMENT_PREFIX = b"EmpowerHer-Idea-Commitment-v1:"


def get_fernet():
    """
    Load the encryption key from the environment.
    Never generate a new key automatically when the server starts:
    doing so would make previously stored ideas unreadable.
    """
    key = __import__("os").environ.get("IDEA_VAULT_ENCRYPTION_KEY")

    if not key:
        raise ImproperlyConfigured(
            "Set the IDEA_VAULT_ENCRYPTION_KEY environment variable."
        )

    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ImproperlyConfigured(
            "IDEA_VAULT_ENCRYPTION_KEY is not a valid Fernet key."
        ) from exc


def encrypt_idea(idea):
    """Encrypt an idea before it is stored in the database."""
    return get_fernet().encrypt(idea.encode("utf-8")).decode("ascii")


def decrypt_idea(ciphertext):
    """Decrypt an idea for an authorized owner."""
    try:
        return get_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeEncodeError) as exc:
        raise ValueError(
            "The idea could not be decrypted. Check the configured key."
        ) from exc


def create_commitment(idea):
    """
    Return a public commitment and a random private witness.

    The witness is not stored in the database. It must be preserved by
    the owner for the later proof-generation workflow.
    """
    witness = secrets.token_bytes(32)

    digest = hashlib.sha256(
        COMMITMENT_PREFIX + witness + idea.encode("utf-8")
    ).hexdigest()

    return digest, witness.hex()


def verify_commitment(idea, witness_hex, expected_commitment):
    """
    Recompute a commitment from an idea and witness.

    This is a commitment check, NOT a zero-knowledge proof.
    """
    try:
        witness = bytes.fromhex(witness_hex)
    except (TypeError, ValueError):
        return False

    if len(witness) != 32:
        return False

    actual = hashlib.sha256(
        COMMITMENT_PREFIX + witness + idea.encode("utf-8")
    ).hexdigest()

    return secrets.compare_digest(actual, expected_commitment)
