import base64
import hashlib
import io
import os
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.test import TestCase
from PIL import Image, ImageDraw, ImageFont

from apps.documents.models import DigiLockerLink, Document
from apps.documents.validators import (
    aadhaar_valid,
    detect_type,
    extract_fields,
    gstin_check_char,
    gstin_valid,
    verhoeff_valid,
)
from config.testing import make_client, throttle_rates


def verhoeff_complete(prefix):
    """Append the Verhoeff check digit to an 11-digit prefix."""
    for digit in "0123456789":
        if verhoeff_valid(prefix + digit):
            return prefix + digit
    raise AssertionError("no check digit")


class ValidatorTests(TestCase):
    def test_aadhaar_checksum_and_masking(self):
        number = verhoeff_complete("23456789012")
        self.assertTrue(aadhaar_valid(number))
        wrong = number[:-1] + str((int(number[-1]) + 1) % 10)
        self.assertFalse(aadhaar_valid(wrong))
        fields, checks = extract_fields(
            f"Aadhaar {number[:4]} {number[4:8]} {number[8:]}", "aadhaar"
        )
        self.assertEqual(fields["aadhaar_masked"], "XXXX XXXX " + number[-4:])
        self.assertNotIn(number, str(fields))
        self.assertTrue(checks[0]["passed"])

    def test_gstin_checksum(self):
        base = "27AAPFU0939F1Z"
        valid = base + gstin_check_char(base)
        self.assertTrue(gstin_valid(valid))
        other = next(c for c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                     if c != valid[-1])
        self.assertFalse(gstin_valid(base + other))

    def test_pan_is_masked(self):
        fields, _ = extract_fields("INCOME TAX DEPARTMENT ABCPE1234F", "pan")
        self.assertEqual(fields["pan"], "ABXXX1234F")
        self.assertEqual(fields["pan_holder_type"], "Individual")

    def test_detects_document_type(self):
        self.assertEqual(detect_type("Income Tax Department ABCPE1234F"),
                         "pan")
        self.assertEqual(detect_type("UDYAM-TS-02-0001234"), "udyam")
        self.assertEqual(detect_type("hello world"), "other")


class UploadTests(TestCase):
    def setUp(self):
        self.user, self.client = make_client()

    def pan_image(self):
        image = Image.new("RGB", (1000, 420), "white")
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype(
                "/System/Library/Fonts/Supplemental/Arial.ttf", 40)
        except OSError:
            font = ImageFont.load_default(size=40)
        for i, line in enumerate(["INCOME TAX DEPARTMENT", "ABCPE1234F",
                                  "LAKSHMI DEVI"]):
            draw.text((60, 40 + i * 90), line, fill="black", font=font)
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        buffer.seek(0)
        buffer.name = "pan.png"
        return buffer

    def test_upload_ocr_encrypts_and_masks(self):
        response = self.client.post(
            "/api/documents/", {"file": self.pan_image(), "doc_type": "auto"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["doc_type"], "pan")
        self.assertEqual(response.data["extracted_fields"]["pan"],
                         "ABXXX1234F")

        document = Document.objects.get()
        self.assertNotIn(b"PNG", bytes(document.encrypted_file)[:16])

        download = self.client.get(
            f"/api/documents/{document.id}/download/")
        self.assertEqual(download.status_code, 200)
        self.assertTrue(download.content.startswith(b"\x89PNG"))

    def test_rejects_mismatched_file_signature(self):
        fake = io.BytesIO(b"not really a pdf")
        fake.name = "fake.pdf"
        response = self.client.post("/api/documents/", {"file": fake},
                                    format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_other_users_cannot_access_documents(self):
        document = Document.objects.create(
            owner=self.user, doc_type="pan", original_name="x.png",
            content_type="image/png", size_bytes=1, encrypted_file=b"x",
            status="failed",
        )
        _, other = make_client(username="other")
        self.assertEqual(
            other.get(f"/api/documents/{document.id}/").status_code, 404)

    def test_uploads_are_rate_limited_but_listing_is_not(self):
        def upload():
            fake = io.BytesIO(b"not really a pdf")
            fake.name = "fake.pdf"
            return self.client.post("/api/documents/", {"file": fake},
                                    format="multipart").status_code

        with throttle_rates(uploads="2/minute"):
            codes = [upload() for _ in range(3)]
            listing = self.client.get("/api/documents/").status_code
        self.assertEqual(codes, [400, 400, 429])
        self.assertEqual(listing, 200)


DIGILOCKER_ENV = {
    "DIGILOCKER_CLIENT_ID": "test-client",
    "DIGILOCKER_CLIENT_SECRET": "test-secret",
    "DIGILOCKER_REDIRECT_URI": "http://localhost:8000/api/documents/digilocker/callback/",
}


class FakeDigiLocker:
    """Stands in for api.digitallocker.gov.in and checks what we send it."""

    ACCESS_TOKEN = "fake-access-token-never-stored"

    def __init__(self, test, challenge, items):
        self.test, self.challenge, self.items = test, challenge, items
        self.calls = []

    def __call__(self, method, url, data=None, headers=None):
        self.calls.append(url)
        if url.endswith("/1/token"):
            self.test.assertEqual(method, "POST")
            self.test.assertEqual(data["grant_type"], "authorization_code")
            self.test.assertEqual(data["client_secret"], "test-secret")
            # PKCE: the verifier must hash to the challenge sent earlier.
            digest = hashlib.sha256(data["code_verifier"].encode()).digest()
            expected = base64.urlsafe_b64encode(digest).decode().rstrip("=")
            self.test.assertEqual(expected, self.challenge)
            return {"access_token": self.ACCESS_TOKEN, "token_type": "Bearer"}
        if url.endswith("/2/files/issued"):
            self.test.assertEqual(headers["Authorization"], f"Bearer {self.ACCESS_TOKEN}")
            return {"items": self.items}
        raise AssertionError(url)


class DigiLockerTests(TestCase):
    ITEMS = [
        {"name": "My Documents", "type": "dir", "uri": ""},
        {"name": "PAN Verification Record", "type": "file", "doctype": "PANCR",
         "issuer": "Income Tax Department", "date": "2024-01-02",
         "uri": "in.gov.pan-PANCR-ABCPE1234F"},
        {"name": "Aadhaar Card", "type": "file", "doctype": "ADHAR",
         "issuer": "UIDAI", "uri": "in.gov.uidai-ADHAR-9f8e7d6c5b4a"},
    ]

    def setUp(self):
        self.user, self.client = make_client()
        self.pan = Document.objects.create(
            owner=self.user, doc_type="pan", original_name="pan.png",
            content_type="image/png", size_bytes=1, encrypted_file=b"x",
            status="verified", extracted_fields={"pan": "ABXXX1234F"},
        )

    def start(self):
        response = self.client.post("/api/documents/digilocker/start/")
        self.assertEqual(response.status_code, 200, response.data)
        query = parse_qs(urlparse(response.data["authorize_url"]).query)
        return query["state"][0], query["code_challenge"][0], query

    def test_switched_off_without_credentials(self):
        with mock.patch.dict(os.environ, {"DIGILOCKER_CLIENT_ID": ""}):
            self.assertFalse(self.client.get("/api/documents/digilocker/").data["configured"])
            self.assertEqual(
                self.client.post("/api/documents/digilocker/start/").status_code, 400)

    @mock.patch.dict(os.environ, DIGILOCKER_ENV)
    def test_consent_url_uses_pkce(self):
        _, _, query = self.start()
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["client_id"], ["test-client"])

    @mock.patch.dict(os.environ, DIGILOCKER_ENV)
    def test_full_flow_verifies_matching_pan_and_forgets_token(self):
        state, challenge, _ = self.start()
        fake = FakeDigiLocker(self, challenge, self.ITEMS)
        with mock.patch("apps.documents.digilocker._http", fake):
            response = self.client.get("/api/documents/digilocker/callback/",
                                       {"code": "abc", "state": state})
        self.assertRedirects(response, "/documents/?digilocker=connected",
                             fetch_redirect_response=False)
        self.assertEqual(len(fake.calls), 2)

        status = self.client.get("/api/documents/digilocker/").data
        self.assertTrue(status["connected"])
        pan = next(d for d in status["issued_documents"] if d["doctype"] == "PANCR")
        self.assertEqual(pan["masked_number"], "ABXXX1234F")
        self.assertEqual(len(status["issued_documents"]), 2)      # folder skipped

        self.pan.refresh_from_db()
        self.assertIsNotNone(self.pan.digilocker_verified_at)
        stored = str(DigiLockerLink.objects.get(owner=self.user).issued_documents)
        self.assertNotIn(FakeDigiLocker.ACCESS_TOKEN, stored)
        self.assertNotIn("ABCPE1234F", stored)                    # full PAN never kept

    @mock.patch.dict(os.environ, DIGILOCKER_ENV)
    def test_different_pan_is_not_marked(self):
        state, challenge, _ = self.start()
        items = [dict(self.ITEMS[1], uri="in.gov.pan-PANCR-ZZZPE9999Z")]
        with mock.patch("apps.documents.digilocker._http",
                        FakeDigiLocker(self, challenge, items)):
            self.client.get("/api/documents/digilocker/callback/",
                            {"code": "abc", "state": state})
        self.pan.refresh_from_db()
        self.assertIsNone(self.pan.digilocker_verified_at)

    @mock.patch.dict(os.environ, DIGILOCKER_ENV)
    def test_state_must_be_this_users_and_single_use(self):
        state, challenge, _ = self.start()
        _, other = make_client(username="other")
        fake = FakeDigiLocker(self, challenge, self.ITEMS)
        with mock.patch("apps.documents.digilocker._http", fake):
            stolen = other.get("/api/documents/digilocker/callback/",
                               {"code": "abc", "state": state})
            self.assertRedirects(stolen, "/documents/?digilocker=error",
                                 fetch_redirect_response=False)
            # The state was consumed, so even the owner can't reuse it.
            reused = self.client.get("/api/documents/digilocker/callback/",
                                     {"code": "abc", "state": state})
            self.assertRedirects(reused, "/documents/?digilocker=error",
                                 fetch_redirect_response=False)
            forged = self.client.get("/api/documents/digilocker/callback/",
                                     {"code": "abc", "state": "made-up"})
            self.assertRedirects(forged, "/documents/?digilocker=error",
                                 fetch_redirect_response=False)
        self.assertEqual(fake.calls, [])

    @mock.patch.dict(os.environ, DIGILOCKER_ENV)
    def test_user_cancelled(self):
        response = self.client.get("/api/documents/digilocker/callback/",
                                   {"error": "access_denied"})
        self.assertRedirects(response, "/documents/?digilocker=cancelled",
                             fetch_redirect_response=False)

    @mock.patch.dict(os.environ, {**DIGILOCKER_ENV,
                                  "DIGILOCKER_BASE_URL": "http://insecure.example"})
    def test_refuses_plain_http(self):
        from apps.documents.digilocker import DigiLockerError, _http
        with self.assertRaises(DigiLockerError):
            _http("GET", "http://insecure.example/2/files/issued")

    @mock.patch.dict(os.environ, DIGILOCKER_ENV)
    def test_disconnect_forgets_everything(self):
        state, challenge, _ = self.start()
        with mock.patch("apps.documents.digilocker._http",
                        FakeDigiLocker(self, challenge, self.ITEMS)):
            self.client.get("/api/documents/digilocker/callback/",
                            {"code": "abc", "state": state})
        self.assertEqual(self.client.delete("/api/documents/digilocker/").status_code, 204)
        self.assertFalse(DigiLockerLink.objects.exists())
        self.pan.refresh_from_db()
        self.assertIsNone(self.pan.digilocker_verified_at)
