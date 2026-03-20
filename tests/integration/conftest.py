"""Integration test fixtures."""

import os
import pytest
import requests
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

load_dotenv()

# Mock google.genai.Client before any module that might chain-import agent.py
# is loaded. verification.py itself only imports tripletex_api, but this guard
# prevents accidental transitive imports from initialising the real Gemini client.
_mock_genai = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai):
    from tests.verification import VerificationSuite
    from tripletex_api import TripletexClient


SOLVE_URL = os.getenv("SOLVE_URL", "http://localhost:8000/solve")
TRIPLETEX_BASE_URL = os.getenv("TRIPLETEX_BASE_URL", "")
TRIPLETEX_SESSION_TOKEN = os.getenv("TRIPLETEX_SESSION_TOKEN", "")


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests against real sandbox")


@pytest.fixture(scope="session")
def sandbox_client():
    """Real Tripletex client for verification queries."""
    if not TRIPLETEX_BASE_URL or not TRIPLETEX_SESSION_TOKEN:
        pytest.skip("Set TRIPLETEX_BASE_URL and TRIPLETEX_SESSION_TOKEN in .env")
    return TripletexClient(TRIPLETEX_BASE_URL, TRIPLETEX_SESSION_TOKEN)


@pytest.fixture(scope="session")
def verifier(sandbox_client):
    """Verification suite for checking API state."""
    return VerificationSuite(sandbox_client)


@pytest.fixture(scope="session")
def solve():
    """Send a task prompt to the /solve endpoint and return the parsed response."""
    def _solve(prompt: str, files: list = None):
        payload = {
            "prompt": prompt,
            "files": files or [],
            "tripletex_credentials": {
                "base_url": TRIPLETEX_BASE_URL,
                "session_token": TRIPLETEX_SESSION_TOKEN,
            },
        }
        resp = requests.post(SOLVE_URL, json=payload, timeout=310)
        assert resp.status_code == 200, f"Solve failed: {resp.status_code} {resp.text}"
        return resp.json()
    return _solve
