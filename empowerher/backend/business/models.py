
from django.conf import settings
from django.db import models


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
    description = models.TextField(max_length=3000)
    state = models.CharField(max_length=100)
    location = models.CharField(max_length=150)
    target_customers = models.CharField(max_length=500)

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

    report = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business_name} - {self.user.username}"
