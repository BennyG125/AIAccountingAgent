# claude_client.py
"""Shared Claude client for Vertex AI with optional LangSmith tracing."""

import logging
import os

from anthropic import AnthropicVertex

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-opus-4-6"
CLAUDE_REGION = "us-east5"

_client: AnthropicVertex | None = None
LANGSMITH_LLM_WRAPPED = False

# Imported at module level so tests can patch claude_client.wrap_anthropic.
# This will be None if langsmith is not installed.
try:
    from langsmith.wrappers import wrap_anthropic
except ImportError:
    wrap_anthropic = None  # type: ignore[assignment]


class _CompletionsStub:
    """Stub for AnthropicVertex which lacks a completions attribute.

    wrap_anthropic patches client.completions.create, but AnthropicVertex
    only has messages + beta. This stub lets wrap_anthropic succeed so it
    can patch messages.create, messages.stream, and beta.messages.create
    with full automatic tracing (token usage, outputs, streaming).
    """

    @staticmethod
    def create(*args, **kwargs):
        raise NotImplementedError("completions not available on AnthropicVertex")


def _try_wrap_anthropic(client: AnthropicVertex) -> AnthropicVertex:
    """Wrap the client with LangSmith tracing.

    AnthropicVertex lacks 'completions' — we add a stub so wrap_anthropic
    can patch messages.create and messages.stream (the ones we actually use).
    """
    global LANGSMITH_LLM_WRAPPED
    try:
        if wrap_anthropic is None:
            raise ImportError("langsmith not installed")
        # AnthropicVertex has messages + beta but not completions.
        # Add a stub so wrap_anthropic doesn't crash.
        if not hasattr(client, "completions"):
            client.completions = _CompletionsStub()  # type: ignore[attr-defined]
        wrapped = wrap_anthropic(client)
        LANGSMITH_LLM_WRAPPED = True
        logger.info("LangSmith: Claude client wrapped for automatic LLM tracing")
        return wrapped
    except Exception as e:
        LANGSMITH_LLM_WRAPPED = False
        logger.info(f"LangSmith: auto-wrapping skipped ({e}), agent.py will trace LLM calls manually")
        return client


def get_claude_client() -> AnthropicVertex:
    """Get cached AnthropicVertex client, optionally wrapped with LangSmith.

    On Cloud Run: uses Application Default Credentials (service account).
    Locally: uses gcloud ADC or falls back to gcloud auth.
    """
    global _client
    if _client is None:
        _client = AnthropicVertex(
            region=CLAUDE_REGION,
            project_id=os.getenv("GCP_PROJECT_ID"),
        )
        if os.getenv("LANGSMITH_TRACING", "").lower() == "true":
            _client = _try_wrap_anthropic(_client)
    return _client
