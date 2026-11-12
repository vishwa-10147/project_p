from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "doc_type", "status", "created_at")
    list_filter = ("doc_type", "status")
    search_fields = ("owner__username", "original_name")
    # Never show encrypted payloads in the admin.
    exclude = ("encrypted_file", "encrypted_text")
    readonly_fields = (
        "owner", "doc_type", "original_name", "content_type", "size_bytes",
        "extraction_method", "ocr_confidence", "extracted_fields",
        "checks", "status", "created_at",
    )
