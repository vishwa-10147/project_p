from django.contrib.auth.models import User
from django.db import models

from config.fields import EncryptedCharField


class EntrepreneurProfile(models.Model):
    """
    Additional profile information for an EmpowerHer entrepreneur.
    """

    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("te", "Telugu"),
        ("hi", "Hindi"),
        ("ta", "Tamil"),
        ("kn", "Kannada"),
        ("mr", "Marathi"),
        ("bn", "Bengali"),
    ]

    BUSINESS_STAGE_CHOICES = [
        ("idea", "Business Idea"),
        ("startup", "Startup"),
        ("existing", "Existing Business"),
        ("expansion", "Business Expansion"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="entrepreneur_profile"
    )

    # Encrypted at rest (Fernet): a copy of the database doesn't reveal
    # where an entrepreneur lives or how to call her.
    phone_number = EncryptedCharField(max_length=15)

    city = EncryptedCharField(max_length=100)

    state = models.CharField(
        max_length=100,
        blank=True
    )

    business_stage = models.CharField(
        max_length=20,
        choices=BUSINESS_STAGE_CHOICES,
        default="idea"
    )

    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default="en"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.username} - Entrepreneur Profile"
