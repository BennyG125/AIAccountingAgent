# tests/test_file_handler.py
"""Tests for file_handler.py — PDF, image, CSV, and text processing."""

import base64
import pytest
from file_handler import process_files


class TestProcessFiles:
    def test_empty_files(self):
        assert process_files([]) == []

    def test_text_file_utf8(self):
        content = "Hello, world"
        result = process_files([{
            "filename": "data.txt",
            "content_base64": base64.b64encode(content.encode()).decode(),
            "mime_type": "text/plain",
        }])
        assert len(result) == 1
        assert result[0]["text_content"] == content
        assert result[0]["images"] == []

    def test_csv_with_semicolons(self):
        """Norwegian CSV with semicolons and comma decimals."""
        csv = "Dato;Beskrivelse;Beløp\n15.03.2026;Faktura;1.500,00"
        result = process_files([{
            "filename": "bank.csv",
            "content_base64": base64.b64encode(csv.encode()).decode(),
            "mime_type": "text/csv",
        }])
        assert "Dato" in result[0]["text_content"]
        assert "1.500,00" in result[0]["text_content"]

    def test_image_passthrough(self):
        """Images are kept as raw bytes for multimodal input."""
        raw = b"FAKE_PNG_DATA"
        result = process_files([{
            "filename": "receipt.png",
            "content_base64": base64.b64encode(raw).decode(),
            "mime_type": "image/png",
        }])
        assert len(result) == 1
        assert result[0]["text_content"] == ""
        assert len(result[0]["images"]) == 1
        assert result[0]["images"][0]["data"] == raw
        assert result[0]["images"][0]["mime_type"] == "image/png"

    def test_pdf_text_extraction(self):
        """PDF with extractable text returns text_content."""
        try:
            import pymupdf
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((50, 50), "Invoice #123\nAmount: 5000 NOK")
            pdf_bytes = doc.tobytes()
            doc.close()
        except ImportError:
            pytest.skip("pymupdf not installed")

        result = process_files([{
            "filename": "invoice.pdf",
            "content_base64": base64.b64encode(pdf_bytes).decode(),
            "mime_type": "application/pdf",
        }])
        assert "Invoice #123" in result[0]["text_content"]

    def test_pdf_always_includes_page_images(self):
        """PDF pages are always converted to images (for vision fallback)."""
        try:
            import pymupdf
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((50, 50), "Some text")
            pdf_bytes = doc.tobytes()
            doc.close()
        except ImportError:
            pytest.skip("pymupdf not installed")

        result = process_files([{
            "filename": "doc.pdf",
            "content_base64": base64.b64encode(pdf_bytes).decode(),
            "mime_type": "application/pdf",
        }])
        assert len(result[0]["images"]) >= 1
        assert result[0]["images"][0]["mime_type"] == "image/png"
