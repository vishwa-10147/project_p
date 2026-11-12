"""
Text extraction for uploaded documents.

- Images: RapidOCR (PaddleOCR models on ONNX Runtime, no system
  install needed).
- PDFs: embedded text via pypdf; scanned pages fall back to OCR on the
  page images.
"""

import io
from functools import lru_cache

import numpy as np
from PIL import Image, ImageOps
from pypdf import PdfReader

MAX_PDF_PAGES = 5
MAX_IMAGE_SIDE = 2000


@lru_cache(maxsize=1)
def _engine():
    # Imported lazily: loading the models takes a few seconds.
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _prepare(image):
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    return np.array(image)


def ocr_image(image):
    result, _ = _engine()(_prepare(image))
    if not result:
        return "", 0.0
    lines = [item[1] for item in result]
    confidence = sum(float(item[2]) for item in result) / len(result)
    return "\n".join(lines), confidence


def extract_text(data, content_type):
    """Return (text, method, confidence) for the uploaded bytes."""
    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[:MAX_PDF_PAGES]
        text = "\n".join(page.extract_text() or "" for page in pages).strip()
        if len(text) > 30:
            return text, "pdf-text", 1.0

        texts, confidences = [], []
        for page in pages:
            for embedded in page.images:
                page_text, confidence = ocr_image(
                    Image.open(io.BytesIO(embedded.data))
                )
                if page_text:
                    texts.append(page_text)
                    confidences.append(confidence)
        if texts:
            return (
                "\n".join(texts),
                "pdf-ocr",
                sum(confidences) / len(confidences),
            )
        return "", "pdf-ocr", 0.0

    text, confidence = ocr_image(Image.open(io.BytesIO(data)))
    return text, "image-ocr", confidence
