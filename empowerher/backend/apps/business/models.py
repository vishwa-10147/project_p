
import json

from django.conf import settings
from django.db import models

from config.crypto import decrypt_bytes, encrypt_bytes

# Confidential business ideas share the Idea Vault key: both hold ideas.
CONFIDENTIAL_KEY_ENV = "IDEA_VAULT_ENCRYPTION_KEY"
CONFIDENTIAL_FIELDS = ("description", "target_customers")


class BusinessIdea(models.Model):
    CATEGORY_CHOICES = [
        ("food", "Food and Beverages"),
        ("clothing", "Clothing and Fashion"),
        ("beauty", "Beauty and Personal Care"),
        ("handicrafts", "Handicrafts"),
        ("agriculture", "Agriculture"),
        ("education", "Education"),
        ("technology", "Technology"),
        ("retail", "Retail"),
        ("services", "Professional or Local Services"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_ideas",
    )

    business_name = models.CharField(max_length=150)
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
    )
    # Empty when is_confidential is True: the text is in encrypted_details.
    description = models.TextField(max_length=3000, blank=True)
    state = models.CharField(max_length=100)
    location = models.CharField(max_length=150)
    target_customers = models.CharField(max_length=500, blank=True)

    investment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    expected_monthly_sales = models.PositiveIntegerField()
    estimated_monthly_expenses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    # When True, description and target_customers are stored only as
    # Fernet ciphertext and are never sent to the external AI service.
    is_confidential = models.BooleanField(default=False)
    encrypted_details = models.TextField(blank=True, default="")

    report = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business_name} - {self.user.username}"

    def seal_confidential_fields(self):
        """Encrypt the free-text fields and clear their plain copies."""
        payload = json.dumps({
            field: getattr(self, field) for field in CONFIDENTIAL_FIELDS
        }).encode("utf-8")
        self.encrypted_details = encrypt_bytes(
            CONFIDENTIAL_KEY_ENV, payload
        ).decode("ascii")
        for field in CONFIDENTIAL_FIELDS:
            setattr(self, field, "")

    def confidential_details(self):
        """Decrypt the free-text fields (owner access only)."""
        if not self.encrypted_details:
            return {field: getattr(self, field) for field in CONFIDENTIAL_FIELDS}
        return json.loads(decrypt_bytes(
            CONFIDENTIAL_KEY_ENV, self.encrypted_details.encode("ascii")
        ))
