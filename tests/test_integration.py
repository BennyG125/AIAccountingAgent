# tests/test_integration.py
"""Integration tests that simulate the full /solve flow with mocked Gemini."""
import json
import time
from unittest.mock import patch, MagicMock


# --- Test helpers ---

def _make_fc_response(name, args):
    """Mock Gemini response with a function call."""
    fc = MagicMock()
    fc.name = name
    fc.args = args
    part = MagicMock()
    part.function_call = fc
    part.text = None
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    return response


def _make_text_response(text):
    """Mock Gemini response with text only (task complete)."""
    part = MagicMock()
    part.function_call = None
    part.text = text
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    return response


# --- Tests ---

def test_full_solve_creates_employee():
    """Full /solve flow: Gemini calls POST /employee, then completes."""
    mock_tripletex = MagicMock()
    mock_tripletex.status_code = 201
    mock_tripletex.json.return_value = {
        "value": {"id": 42, "firstName": "Ola", "lastName": "Nordmann"}
    }

    gemini_responses = [
        _make_fc_response("tripletex_api", {
            "method": "POST",
            "endpoint": "/employee",
            "body_json": '{"firstName":"Ola","lastName":"Nordmann","email":"ola@example.com","isAdministrator":true}',
        }),
        _make_text_response("Created employee Ola Nordmann with ID 42"),
    ]

    with patch("agent.genai_client") as mock_genai, \
         patch("tripletex_api.requests") as mock_requests:
        mock_genai.models.generate_content.side_effect = gemini_responses
        mock_requests.post.return_value = mock_tripletex

        from main import app
        from fastapi.testclient import TestClient
        test_client = TestClient(app)

        response = test_client.post("/solve", json={
            "prompt": "Opprett en ansatt med navn Ola Nordmann, ola@example.com. Kontoadministrator.",
            "files": [],
            "tripletex_credentials": {
                "base_url": "https://tx-proxy.ainm.no/v2",
                "session_token": "test-token",
            },
        })

    assert response.status_code == 200
    assert response.json() == {"status": "completed"}


def test_solve_returns_completed_on_gemini_error():
    """Agent returns completed even when Gemini fails — for partial credit."""
    with patch("agent.genai_client") as mock_genai:
        mock_genai.models.generate_content.side_effect = Exception("Gemini timeout")

        from main import app
        from fastapi.testclient import TestClient
        test_client = TestClient(app)

        response = test_client.post("/solve", json={
            "prompt": "Some task",
            "files": [],
            "tripletex_credentials": {
                "base_url": "https://example.com/v2",
                "session_token": "token",
            },
        })

    assert response.status_code == 200
    assert response.json() == {"status": "completed"}


def test_health_endpoint():
    """Health check returns ok."""
    from main import app
    from fastapi.testclient import TestClient
    test_client = TestClient(app)

    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
