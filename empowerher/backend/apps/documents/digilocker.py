"""
DigiLocker document verification (Requester API, OAuth 2.0 + PKCE).

Documents in DigiLocker are issued directly by the government department
(e.g. PAN by the Income Tax Department), so they are authentic. With the
user's consent EmpowerHer reads the list of her issued documents and marks a
matching uploaded document as "verified by DigiLocker".

Flow (DigiLocker Requester API Specification v1.12):
1. /1/authorize  - the user signs in to DigiLocker and gives consent
   (authorization code flow with PKCE, S256).
2. /1/token      - EmpowerHer swaps the code for a short-lived access token.
3. /2/files/issued - the list of documents issued to her.

Privacy: the access token is used once and thrown away; only document
types, issuers, dates and masked numbers are kept.

Needs EmpowerHer to be registered as a DigiLocker partner (API Setu), which
provides DIGILOCKER_CLIENT_ID / DIGILOCKER_CLIENT_SECRET. Without them the
feature is simply switched off.
"""

import base64
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

from django.core.cache import cache

DEFAULT_BASE_URL = "https://api.digitallocker.gov.in/public/oauth2"
STATE_TTL_SECONDS = 600
TIMEOUT_SECONDS = 15

# DigiLocker doctype -> EmpowerHer document type, and how to mask its number
# the same way the Documents module does.
DOCTYPES = {
    "PANCR": ("pan", lambda n: n[:2] + "XXX" + n[5:] if len(n) == 10 else None),
    "ADHAR": ("aadhaar", lambda n: None),       # the URI holds no Aadhaar number
    "DRVLC": ("other", lambda n: None),
}


class DigiLockerError(Exception):
    """A failure that is safe to show the user."""


def config():
    return {
        "client_id": os.environ.get("DIGILOCKER_CLIENT_ID", ""),
        "client_secret": os.environ.get("DIGILOCKER_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("DIGILOCKER_REDIRECT_URI", ""),
        "base_url": os.environ.get("DIGILOCKER_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
    }


def is_configured():
    c = config()
    return bool(c["client_id"] and c["client_secret"] and c["redirect_uri"])


def _pkce_pair():
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    return verifier, challenge


def start(user):
    """Return the DigiLocker consent URL; remember state + verifier briefly."""
    if not is_configured():
        raise DigiLockerError("DigiLocker is not set up on this server.")
    c = config()
    state = secrets.token_urlsafe(32)
    verifier, challenge = _pkce_pair()
    cache.set(f"digilocker:{state}", {"user_id": user.id, "verifier": verifier},
              STATE_TTL_SECONDS)
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": c["client_id"],
        "redirect_uri": c["redirect_uri"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "req_doctype": "PANCR,ADHAR,DRVLC",
    })
    return f"{c['base_url']}/1/authorize?{query}"


def _http(method, url, data=None, headers=None):
    """Small JSON-over-HTTPS helper (stdlib only)."""
    if not url.startswith("https://"):
        # Tokens and documents must never travel unencrypted (or via file:).
        raise DigiLockerError("DIGILOCKER_BASE_URL must start with https://.")
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    request = urllib.request.Request(  # noqa: S310 - scheme checked above
        url, data=body, method=method, headers=headers or {}
    )
    if body is not None:
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise DigiLockerError(f"DigiLocker refused the request ({error.code}).") from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise DigiLockerError("Could not reach DigiLocker. Please try again.") from None


def finish(user, code, state):
    """Swap the code for a token, read the issued documents, forget the token."""
    saved = cache.get(f"digilocker:{state}") if state else None
    cache.delete(f"digilocker:{state}")
    if not saved or saved["user_id"] != user.id:
        raise DigiLockerError("This DigiLocker link has expired. Please start again.")
    if not code:
        raise DigiLockerError("DigiLocker did not return a consent code.")

    c = config()
    token = _http("POST", f"{c['base_url']}/1/token", data={
        "code": code,
        "grant_type": "authorization_code",
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "redirect_uri": c["redirect_uri"],
        "code_verifier": saved["verifier"],
    })
    access_token = token.get("access_token")
    if not access_token:
        raise DigiLockerError("DigiLocker did not issue an access token.")

    listing = _http("GET", f"{c['base_url']}/2/files/issued",
                    headers={"Authorization": f"Bearer {access_token}"})
    return summarise(listing.get("items", []))


def summarise(items):
    """Keep only what EmpowerHer needs, with numbers masked."""
    documents = []
    for item in items:
        if item.get("type") == "dir":
            continue
        doctype = str(item.get("doctype", ""))
        uri = str(item.get("uri", ""))
        kind, mask = DOCTYPES.get(doctype, ("other", lambda n: None))
        number = uri.rsplit("-", 1)[-1] if uri.count("-") >= 2 else ""
        documents.append({
            "doctype": doctype,
            "doc_type": kind,
            "name": str(item.get("name") or item.get("description") or doctype)[:200],
            "issuer": str(item.get("issuer", ""))[:200],
            "date": str(item.get("date", ""))[:40],
            "masked_number": mask(number) if number else None,
        })
    return documents


def apply_to_documents(user, issued, now):
    """Mark uploaded documents whose masked number matches an issued one."""
    verified = 0
    for doc in user.documents.filter(doc_type="pan"):
        uploaded = doc.extracted_fields.get("pan")
        if uploaded and any(
            d["doc_type"] == "pan" and d["masked_number"] == uploaded for d in issued
        ):
            doc.digilocker_verified_at = now
            doc.save(update_fields=["digilocker_verified_at"])
            verified += 1
    return verified
