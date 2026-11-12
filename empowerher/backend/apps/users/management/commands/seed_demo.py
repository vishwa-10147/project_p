"""
Create a demo entrepreneur with sample data for presentations and testing.

    python manage.py seed_demo

The data is created through the real API endpoints, so it is encrypted,
validated and reported exactly as it would be for a real user. Running the
command again replaces the previous demo account.
"""

import io
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont
from rest_framework.test import APIClient

DEMO_USERNAME = "demo_entrepreneur"
DEFAULT_DEMO_PASSWORD = "EmpowerHer@Demo2026"


def synthetic_pan_card():
    """A fake PAN-style image (not a real person's document)."""
    image = Image.new("RGB", (1000, 560), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("Arial.ttf", 40)
    except OSError:
        try:
            font = ImageFont.truetype(
                "/System/Library/Fonts/Supplemental/Arial.ttf", 40)
        except OSError:
            font = ImageFont.load_default(size=40)
    lines = ["INCOME TAX DEPARTMENT", "GOVT. OF INDIA",
             "Permanent Account Number Card", "ABCPD1234K",
             "Name", "PRIYA DEMO", "Date of Birth", "15/08/1992"]
    for i, line in enumerate(lines):
        draw.text((60, 30 + i * 62), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)
    buffer.name = "demo_pan_card.png"
    return buffer


class Command(BaseCommand):
    help = "Create (or recreate) a demo entrepreneur account with sample data."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)
        User.objects.filter(username=DEMO_USERNAME).delete()

        client = APIClient(SERVER_NAME="localhost")
        response = client.post("/api/users/register/", {
            "username": DEMO_USERNAME,
            "email": "demo@empowerher.local",
            "password": password,
            "password_confirm": password,
            "first_name": "Priya",
            "last_name": "Demo",
            "state": "Telangana",
            "city": "Warangal",
            "business_stage": "idea",
            "preferred_language": "en",
        }, format="json")
        if response.status_code != 201:
            self.stderr.write(f"Could not create demo user: {response.data}")
            return
        client.credentials(HTTP_AUTHORIZATION="Token " + response.data["token"])

        idea = {
            "business_name": "Millet Bites",
            "category": "food",
            "description": (
                "Healthy millet snacks and laddus made at home with "
                "traditional recipes, packed in eco-friendly pouches and "
                "sold to offices, gyms and schools through WhatsApp orders."
            ),
            "state": "Telangana",
            "location": "Warangal",
            "target_customers": "Office workers and parents looking for "
                                "healthy snacks",
            "investment": "150000",
            "selling_price": "120",
            "expected_monthly_sales": "600",
            "estimated_monthly_expenses": "45000",
        }
        client.post("/api/business/validate/", idea, format="json")
        client.post("/api/business/validate/", dict(
            idea,
            business_name="Ragi Energy Bars",
            description=(
                "Sprouted ragi bars sweetened with jaggery, using a "
                "slow-drying process that keeps them crisp for 60 days."
            ),
            is_confidential=True,
        ), format="json")

        vault = client.post("/api/ideas/", {
            "title": "Millet snack subscription boxes",
            "idea": "Weekly subscription boxes of millet snacks for IT "
                    "offices in Hanamkonda, with a reusable steel tiffin "
                    "deposit scheme.",
        }, format="json").data

        client.post("/api/documents/", {
            "file": synthetic_pan_card(), "doc_type": "auto",
        }, format="multipart")

        self.stdout.write(self.style.SUCCESS("Demo account ready."))
        self.stdout.write(f"  Username: {DEMO_USERNAME}")
        self.stdout.write(
            "  Password: the DEMO_PASSWORD environment variable, or the "
            "default listed in SETUP.md"
        )
        self.stdout.write(
            f"  Idea Vault witness secret (for proof demos): "
            f"{vault.get('witness_secret')}"
        )
