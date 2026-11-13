"""
Checks for end-to-end encrypted Idea Vault data.

The server cannot decrypt anything here; it only checks that what the
browser sends has the expected shape and size, so the database never holds
junk and a broken client fails loudly instead of losing an idea.
"""

import base64
import binascii
import hashlib
import json

from . import zkp

ENVELOPE_VERSION = 1
ALGORITHM = "AES-256-GCM"
IV_BYTES = 12
# 10,000 characters of idea + witness + JSON, as UTF-8 (up to 4 bytes each),
# plus the 16-byte GCM tag.
MAX_CIPHERTEXT_BYTES = 10_000 * 4 + 512
MIN_ITERATIONS = 100_000
MAX_ITERATIONS = 5_000_000
E2E_COMMITMENT_PREFIX = b"EmpowerHer-E2E-Commitment-v2:"


class E2EError(ValueError):
    """Invalid end-to-end encrypted data (message is safe to show)."""


def _b64(value, name, min_bytes=1, max_bytes=None):
    if not isinstance(value, str):
        raise E2EError(f"{name} must be base64 text.")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise E2EError(f"{name} must be base64 text.") from None
    if len(raw) < min_bytes or (max_bytes and len(raw) > max_bytes):
        raise E2EError(f"{name} has the wrong length.")
    return raw


def clean_envelope(envelope):
    """Validate an AES-GCM envelope and return it as compact JSON text."""
    if not isinstance(envelope, dict):
        raise E2EError("encrypted_payload must be an object.")
    if envelope.get("v") != ENVELOPE_VERSION or envelope.get("alg") != ALGORITHM:
        raise E2EError("Unsupported encryption format.")
    _b64(envelope.get("iv"), "iv", IV_BYTES, IV_BYTES)
    # At least the 16-byte authentication tag.
    _b64(envelope.get("ct"), "ct", 17, MAX_CIPHERTEXT_BYTES)
    return json.dumps(
        {"v": ENVELOPE_VERSION, "alg": ALGORITHM,
         "iv": envelope["iv"], "ct": envelope["ct"]},
        separators=(",", ":"),
    )


def clean_key_settings(data):
    salt = data.get("salt")
    _b64(salt, "salt", 16, 32)
    try:
        iterations = int(data.get("iterations"))
    except (TypeError, ValueError):
        raise E2EError("iterations must be a number.") from None
    if not MIN_ITERATIONS <= iterations <= MAX_ITERATIONS:
        raise E2EError(
            f"iterations must be between {MIN_ITERATIONS} and {MAX_ITERATIONS}."
        )
    return {
        "salt": salt,
        "iterations": iterations,
        "key_check": clean_envelope(data.get("key_check")),
    }


def clean_pedersen_commitment(value):
    """A hex group element, normalised to lower case."""
    if not isinstance(value, str) or not 1 <= len(value) <= 600:
        raise E2EError("pedersen_commitment must be hexadecimal.")
    try:
        number = int(value, 16)
    except ValueError:
        raise E2EError("pedersen_commitment must be hexadecimal.") from None
    if not zkp.is_group_element(number):
        raise E2EError("pedersen_commitment is not a valid commitment.")
    return format(number, "x")


def public_commitment(pedersen_hex):
    """
    The 64-character fingerprint stored in `commitment` for browser ideas.
    (Older server-side ideas hash the idea itself; the server can't here.)
    """
    return hashlib.sha256(E2E_COMMITMENT_PREFIX + pedersen_hex.encode()).hexdigest()
