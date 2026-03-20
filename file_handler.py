import base64
import csv
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_files(files: list[dict]) -> list[dict]:
    """Process attached files from the /solve request.

    PDFs are extracted to text via pymupdf.
    Images are kept as raw bytes for multimodal Gemini input.
    CSV files are parsed into structured rows.
    Text files are decoded to strings.
    """
    if not files:
        return []

    processed = []
    for f in files:
        filename = f["filename"]
        raw_bytes = base64.b64decode(f["content_base64"])
        mime_type = f.get("mime_type", "")

        logger.info(f"Processing file: {filename} ({mime_type}, {len(raw_bytes)} bytes)")

        entry = {
            "filename": filename,
            "mime_type": mime_type,
            "raw_bytes": raw_bytes,
        }

        if mime_type == "application/pdf":
            entry["text_content"] = _extract_pdf_text(raw_bytes)
        elif mime_type.startswith("image/"):
            # Keep raw bytes — Gemini handles images as multimodal input
            pass
        elif mime_type == "text/csv" or filename.endswith(".csv"):
            text = _decode_text(raw_bytes)
            entry["text_content"] = text
            entry["structured_data"] = _parse_csv(text)
        else:
            # Assume text-like content
            entry["text_content"] = _decode_text(raw_bytes)

        processed.append(entry)

    return processed


def _decode_text(raw_bytes: bytes) -> str:
    """Decode bytes to string, trying UTF-8 first then Latin-1."""
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pymupdf."""
    try:
        import pymupdf

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


def _parse_csv(text: str) -> list[dict]:
    """Parse CSV text into a list of row dicts."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception as e:
        logger.error(f"CSV parsing failed: {e}")
        return []
