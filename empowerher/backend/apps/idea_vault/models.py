
from django.conf import settings
from django.db import models


class ConfidentialIdea(models.Model):
    # Where the idea was encrypted:
    #   browser: end-to-end. The owner's browser encrypted it with a key
    #            derived from her vault passphrase; the server cannot read it.
    #   server:  older ideas (and API clients) encrypted by the server.
    ENCRYPTION_CHOICES = [
        ("browser", "End-to-end (browser)"),
        ("server", "Server-side (Fernet)"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="confidential_ideas",
    )

    title = models.CharField(max_length=150)

    # Stores ciphertext, not the original business idea. For "browser"
    # ideas this is a JSON envelope {"v", "alg", "iv", "ct"} (AES-256-GCM).
    encrypted_idea = models.TextField()
    encryption = models.CharField(
        max_length=10, choices=ENCRYPTION_CHOICES, default="server",
    )

    # Public, salted cryptographic commitment to the original idea.
    commitment = models.CharField(max_length=64, unique=True)

    # Pedersen commitment (hex) used for zero-knowledge ownership proofs.
    pedersen_commitment = models.TextField(blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Idea #{self.pk} - Owner {self.owner_id}"


class VaultKey(models.Model):
    """
    Public settings of an owner's end-to-end vault key. The key itself is
    derived in the browser from a passphrase that never reaches the server
    (PBKDF2-SHA256 -> AES-256-GCM). The server keeps only the salt, the
    iteration count and a small encrypted check value that lets the browser
    tell a wrong passphrase from a right one.
    """

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vault_key",
    )
    salt = models.CharField(max_length=64)
    iterations = models.PositiveIntegerField()
    key_check = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vault key settings - Owner {self.owner_id}"
