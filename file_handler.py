# file_handler.py
"""Process file attachments from /solve requests.

Output format per file:
  {
    "filename": str,
    "mime_type": str,
    "text_content": str,        # extracted text (may be empty)
    "images": [                  # images for multimodal input
      {"data": bytes, "mime_type": str}
    ]
  }

PDFs: extract text + render pages as PNG images (for scanned docs).
Images: passthrough as multimodal parts.
CSV/Text: decode to string.
"""

import base64
import logging

logger = logging.getLogger(__name__)

PDF_DPI = 150  # resolution for PDF→image conversion


def process_files(files: list[dict]) -> list[dict]:
    if not files:
        return []

    processed = []
    for f in files:
        filename = f.get("filename", "unknown")
        raw_bytes = base64.b64decode(f["content_base64"])
        mime_type = f.get("mime_type", "")

        logger.info(f"Processing: {filename} ({mime_type}, {len(raw_bytes)} bytes)")

        entry = {
            "filename": filename,
            "mime_type": mime_type,
            "text_content": "",
            "images": [],
        }

        if mime_type == "application/pdf":
            entry["text_content"] = _extract_pdf_text(raw_bytes)
            entry["images"] = _pdf_to_images(raw_bytes)
        elif mime_type.startswith("image/"):
            entry["images"] = [{"data": raw_bytes, "mime_type": mime_type}]
        else:
            # Text/CSV/other — decode to string
            entry["text_content"] = _decode_text(raw_bytes)

        processed.append(entry)

    return processed


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        parts = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(parts).strip()
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return ""


def _pdf_to_images(pdf_bytes: bytes) -> list[dict]:
    """Convert each PDF page to a PNG image for Gemini vision."""
    images = []
    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(dpi=PDF_DPI)
            images.append({
                "data": pix.tobytes("png"),
                "mime_type": "image/png",
            })
        doc.close()
    except Exception as e:
        logger.error(f"PDF→image conversion failed: {e}")
    return images


def _decode_text(raw_bytes: bytes) -> str:
    """Decode text bytes, trying UTF-8 first then Latin-1."""
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")
