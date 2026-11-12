
from django.conf import settings
from django.db import models


class ConfidentialIdea(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="confidential_ideas",
    )

    title = models.CharField(max_length=150)

    # Stores ciphertext, not the original business idea.
    encrypted_idea = models.TextField()

    # Public, salted cryptographic commitment to the original idea.
    commitment = models.CharField(max_length=64, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Idea #{self.pk} - Owner {self.owner_id}"
