import base64
from file_handler import process_files


def test_process_empty_files():
    """No files returns empty list."""
    result = process_files([])
    assert result == []


def test_process_text_file():
    """Base64-encoded text file is decoded."""
    content = base64.b64encode(b"Hello world").decode()
    files = [
        {
            "filename": "test.txt",
            "content_base64": content,
            "mime_type": "text/plain",
        }
    ]
    result = process_files(files)
    assert len(result) == 1
    assert result[0]["filename"] == "test.txt"
    assert result[0]["text_content"] == "Hello world"


def test_process_image_file():
    """Image files are returned as raw bytes for multimodal input."""
    content = base64.b64encode(b"\x89PNG fake image data").decode()
    files = [
        {
            "filename": "receipt.png",
            "content_base64": content,
            "mime_type": "image/png",
        }
    ]
    result = process_files(files)
    assert len(result) == 1
    assert result[0]["filename"] == "receipt.png"
    assert result[0]["mime_type"] == "image/png"
    assert result[0]["raw_bytes"] == b"\x89PNG fake image data"


def test_process_csv_file():
    """CSV files are parsed into structured rows and also kept as text."""
    csv_content = "date,amount,description\n2026-01-15,1500.00,Office supplies\n2026-01-16,2300.50,Software license"
    content = base64.b64encode(csv_content.encode()).decode()
    files = [
        {
            "filename": "transactions.csv",
            "content_base64": content,
            "mime_type": "text/csv",
        }
    ]
    result = process_files(files)
    assert len(result) == 1
    assert result[0]["filename"] == "transactions.csv"
    assert result[0]["text_content"] == csv_content
    assert "structured_data" in result[0]
    assert len(result[0]["structured_data"]) == 2
    assert result[0]["structured_data"][0]["amount"] == "1500.00"
    assert result[0]["structured_data"][1]["description"] == "Software license"
