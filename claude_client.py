# claude_client.py
"""Shared Claude client for Vertex AI."""

import os
from anthropic import AnthropicVertex

CLAUDE_MODEL = "claude-opus-4-6"
CLAUDE_REGION = "us-east5"

_client: AnthropicVertex | None = None


def get_claude_client() -> AnthropicVertex:
    """Get cached AnthropicVertex client.

    On Cloud Run: uses Application Default Credentials (service account).
    Locally: uses gcloud ADC or falls back to gcloud auth.
    """
    global _client
    if _client is None:
        _client = AnthropicVertex(
            region=CLAUDE_REGION,
            project_id=os.getenv("GCP_PROJECT_ID"),
        )
    return _client
