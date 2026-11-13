import io

from django.test import TestCase
from PIL import Image, ImageDraw, ImageFont

from config.testing import make_client, throttle_rates
from apps.documents.models import Document
from apps.documents.validators import (
    aadhaar_valid,
    detect_type,
    extract_fields,
    gstin_check_char,
    gstin_valid,
    verhoeff_valid,
)


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
