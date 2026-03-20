# tests/test_claude_client.py
"""Tests for Claude client initialization and LangSmith wrapping."""
import os
from unittest.mock import patch, MagicMock


class TestGetClaudeClient:
    def setup_method(self):
        import claude_client as mod
        mod._client = None  # reset singleton between tests

    def teardown_method(self):
        import claude_client as mod
        mod._client = None

    def test_returns_client(self):
        import claude_client as mod
        with patch.object(mod, "AnthropicVertex") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = mod.get_claude_client()
            assert client is not None
            mock_cls.assert_called_once()

    def test_caches_client(self):
        import claude_client as mod
        with patch.object(mod, "AnthropicVertex") as mock_cls:
            mock_cls.return_value = MagicMock()
            c1 = mod.get_claude_client()
            c2 = mod.get_claude_client()
            assert c1 is c2
            mock_cls.assert_called_once()

    def test_wrapping_attempted_when_tracing_enabled(self):
        import claude_client as mod
        with patch.object(mod, "AnthropicVertex") as mock_cls:
            mock_cls.return_value = MagicMock()
            with patch.object(mod, "_try_wrap_anthropic", wraps=mod._try_wrap_anthropic) as mock_wrap:
                with patch.dict(os.environ, {"LANGSMITH_TRACING": "true"}):
                    mod.get_claude_client()
                    mock_wrap.assert_called_once()

    def test_wrapping_skipped_when_tracing_disabled(self):
        import claude_client as mod
        with patch.object(mod, "AnthropicVertex") as mock_cls:
            mock_cls.return_value = MagicMock()
            with patch.object(mod, "_try_wrap_anthropic") as mock_wrap:
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("LANGSMITH_TRACING", None)
                    mod.get_claude_client()
                    mock_wrap.assert_not_called()

    def test_graceful_fallback_when_wrap_fails(self):
        """wrap_anthropic fails on AnthropicVertex — client still works."""
        import claude_client as mod
        mock_client = MagicMock()
        with patch.object(mod, "AnthropicVertex", return_value=mock_client):
            with patch.dict(os.environ, {"LANGSMITH_TRACING": "true"}):
                with patch("claude_client.wrap_anthropic", side_effect=AttributeError("no completions"), create=True):
                    client = mod.get_claude_client()
                    assert client is mock_client
                    assert mod.LANGSMITH_LLM_WRAPPED is False
