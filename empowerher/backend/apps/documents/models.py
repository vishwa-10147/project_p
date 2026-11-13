import uuid

from django.conf import settings
from django.db import models

from .validators import DOC_TYPES


class Document(models.Model):
    """
    An uploaded identity or business document.

    The file and its full OCR text are stored encrypted. Only masked,
    non-sensitive extracted fields are stored in plain form.
    """

    STATUS_CHOICES = [
        ("verified", "Checks passed"),
        ("needs_review", "Needs review"),
        ("failed", "Could not read document"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(max_length=20, choices=list(DOC_TYPES.items()))
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=50)
    size_bytes = models.PositiveIntegerField()

    encrypted_file = models.BinaryField()
    encrypted_text = models.BinaryField(blank=True, default=b"")

    extraction_method = models.CharField(max_length=20, blank=True)
    ocr_confidence = models.FloatField(default=0)
    extracted_fields = models.JSONField(default=dict, blank=True)
    checks = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    # Set when the same document was found among those issued to the owner
    # in DigiLocker (i.e. confirmed by the issuing department).
    digilocker_verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.owner_id}"


class DigiLockerLink(models.Model):
    """
    What DigiLocker confirmed for a user: the documents issued to her, with
    numbers masked. The DigiLocker access token is never stored.
    """

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="digilocker_link",
    )
    issued_documents = models.JSONField(default=list, blank=True)
    connected_at = models.DateTimeField()

    def __str__(self):
        return f"DigiLocker - {self.owner_id}"
