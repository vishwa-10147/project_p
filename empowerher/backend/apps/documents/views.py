from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from config.crypto import decrypt_bytes, encrypt_bytes
from config.throttles import WriteScopedRateThrottle

from .models import Document
from .ocr import extract_text
from .validators import DOC_TYPES, detect_type, extract_fields, name_matches

KEY_ENV = "DOCUMENT_ENCRYPTION_KEY"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# Check the file signature as well as the declared type.
SIGNATURES = {
    "application/pdf": [b"%PDF"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],
}


def serialise(document):
    return {
        "id": str(document.id),
        "doc_type": document.doc_type,
        "doc_type_label": document.get_doc_type_display(),
        "original_name": document.original_name,
        "size_bytes": document.size_bytes,
        "status": document.status,
        "status_label": document.get_status_display(),
        "extraction_method": document.extraction_method,
        "ocr_confidence": round(document.ocr_confidence, 3),
        "extracted_fields": document.extracted_fields,
        "checks": document.checks,
        "created_at": document.created_at.isoformat(),
    }


def decide_status(text, checks, confidence):
    if not text.strip():
        return "failed"
    if checks and all(c["passed"] for c in checks) and confidence >= 0.8:
        return "verified"
    return "needs_review"


class DocumentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    # OCR is CPU-heavy: limit uploads, but never listing.
    throttle_classes = [UserRateThrottle, WriteScopedRateThrottle]
    throttle_scope = "uploads"

    def get(self, request):
        documents = Document.objects.filter(owner=request.user)
        return Response({
            "document_types": DOC_TYPES,
            "documents": [serialise(d) for d in documents],
        })

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"error": "Choose a file to upload."},
                            status=status.HTTP_400_BAD_REQUEST)
        if upload.size > MAX_UPLOAD_BYTES:
            return Response({"error": "Files must be 8 MB or smaller."},
                            status=status.HTTP_400_BAD_REQUEST)

        content_type = upload.content_type
        data = upload.read()
        if content_type not in SIGNATURES or not any(
            data.startswith(sig) for sig in SIGNATURES[content_type]
        ):
            return Response(
                {"error": "Upload a PDF, JPEG, PNG or WebP file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requested_type = request.data.get("doc_type") or "auto"
        if requested_type != "auto" and requested_type not in DOC_TYPES:
            return Response({"error": "Unknown document type."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            text, method, confidence = extract_text(data, content_type)
        except Exception:
            text, method, confidence = "", "error", 0.0

        doc_type = (
            detect_type(text) if requested_type == "auto" else requested_type
        )
        fields, checks = extract_fields(text, doc_type)

        user = request.user
        name_check = name_matches(text, user.first_name, user.last_name)
        if name_check is not None and doc_type in ("pan", "aadhaar",
                                                   "bank_statement"):
            checks.append({
                "check": "Name matches your profile",
                "passed": name_check,
                "detail": "Your profile name appears on the document."
                if name_check else
                "Your profile name was not found; check spelling or "
                "image quality.",
            })

        document = Document.objects.create(
            owner=user,
            doc_type=doc_type,
            original_name=upload.name[:255],
            content_type=content_type,
            size_bytes=upload.size,
            encrypted_file=encrypt_bytes(KEY_ENV, data),
            encrypted_text=encrypt_bytes(KEY_ENV, text.encode("utf-8")),
            extraction_method=method,
            ocr_confidence=confidence,
            extracted_fields=fields,
            checks=checks,
            status=decide_status(text, checks, confidence),
        )
        result = serialise(document)
        result["note"] = (
            "Checks confirm the format and checksums of numbers found on "
            "the document. They do not confirm the document with the "
            "issuing authority."
        )
        return Response(result, status=status.HTTP_201_CREATED)


class DocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk, owner=request.user)
        return Response(serialise(document))

    def delete(self, request, pk):
        document = get_object_or_404(Document, pk=pk, owner=request.user)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentDownloadView(APIView):
    """Decrypt and return the original file to its owner only."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk, owner=request.user)
        data = decrypt_bytes(KEY_ENV, document.encrypted_file)
        response = HttpResponse(data, content_type=document.content_type)
        safe_name = document.original_name.replace('"', "")
        response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
        response["Cache-Control"] = "no-store"
        return response
