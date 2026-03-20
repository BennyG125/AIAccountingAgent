# tests/test_agent.py
"""Tests for agent.py — all mock Gemini, no real API calls."""

import json
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

_mock_genai_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    import agent as agent_module


class TestToolDefinitions:
    def test_has_four_tools(self):
        names = [fd.name for fd in agent_module.FUNCTION_DECLARATIONS]
        assert sorted(names) == ["tripletex_delete", "tripletex_get", "tripletex_post", "tripletex_put"]

    def test_post_requires_path_and_body(self):
        post = next(fd for fd in agent_module.FUNCTION_DECLARATIONS if fd.name == "tripletex_post")
        params = post.parameters
        required = params.required if hasattr(params, "required") else params.get("required", [])
        assert "path" in required
        assert "body" in required

    def test_put_has_params(self):
        put = next(fd for fd in agent_module.FUNCTION_DECLARATIONS if fd.name == "tripletex_put")
        params = put.parameters
        properties = params.properties if hasattr(params, "properties") else params.get("properties", {})
        assert "params" in properties


class TestSystemPrompt:
    def test_includes_cheat_sheet(self):
        prompt = agent_module.build_system_prompt()
        assert "POST /employee" in prompt

    def test_includes_payment_gotcha(self):
        prompt = agent_module.build_system_prompt()
        assert "params, NOT body" in prompt

    def test_includes_known_constants(self):
        prompt = agent_module.build_system_prompt()
        assert "vatType id=3" in prompt
        assert "id=162" in prompt


class TestBuildUserContent:
    def test_includes_prompt(self):
        parts = agent_module.build_user_content("Create employee", [])
        texts = [p.text for p in parts if hasattr(p, "text") and p.text]
        assert any("Create employee" in t for t in texts)

    def test_includes_file_text(self):
        files = [{"filename": "data.csv", "text_content": "col1;col2\n1;2", "images": []}]
        parts = agent_module.build_user_content("Process", files)
        texts = [p.text for p in parts if hasattr(p, "text") and p.text]
        assert any("col1;col2" in t for t in texts)

    def test_includes_images(self):
        files = [{"filename": "receipt.png", "text_content": "", "images": [
            {"data": b"PNG_DATA", "mime_type": "image/png"}
        ]}]
        parts = agent_module.build_user_content("Process", files)
        # Should have 2 parts: image + prompt text
        assert len(parts) == 2

    def test_pdf_with_text_and_images(self):
        """PDF produces both text part and image parts."""
        files = [{"filename": "invoice.pdf", "text_content": "Invoice #123",
                  "images": [{"data": b"PAGE1_PNG", "mime_type": "image/png"}]}]
        parts = agent_module.build_user_content("Process invoice", files)
        # Should have 3 parts: text attachment + image + prompt
        assert len(parts) == 3


class TestExecuteTool:
    def test_get(self):
        mock_client = MagicMock()
        mock_client.get.return_value = {"success": True, "status_code": 200, "body": {}}
        result = agent_module.execute_tool("tripletex_get", {"path": "/employee"}, mock_client)
        mock_client.get.assert_called_once_with("/employee", params=None)
        assert result["success"]

    def test_put_with_params(self):
        mock_client = MagicMock()
        mock_client.put.return_value = {"success": True, "status_code": 200, "body": {}}
        agent_module.execute_tool("tripletex_put", {
            "path": "/invoice/1/:payment",
            "params": {"paymentDate": "2026-03-20", "paidAmount": 1000},
        }, mock_client)
        mock_client.put.assert_called_once_with(
            "/invoice/1/:payment", body=None,
            params={"paymentDate": "2026-03-20", "paidAmount": 1000}
        )

    def test_unknown_tool(self):
        result = agent_module.execute_tool("tripletex_patch", {}, MagicMock())
        assert not result["success"]


class TestRouting:
    """Test the run_agent router logic."""

    @patch("agent.run_tool_loop")
    @patch("agent.execute_plan", return_value={"success": True, "ref_map": {}, "api_calls": 1})
    @patch("agent.is_known_pattern", return_value=True)
    @patch("agent.parse_prompt", return_value={"actions": [{"action": "create", "entity": "department", "fields": {"name": "IT"}, "ref": "d1", "depends_on": {}}]})
    def test_deterministic_path(self, mock_parse, mock_match, mock_exec, mock_fallback):
        result = agent_module.run_agent("Create dept", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_exec.assert_called_once()
        mock_fallback.assert_not_called()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.is_known_pattern", return_value=False)
    @patch("agent.parse_prompt", return_value={"actions": [{"action": "update", "entity": "employee", "fields": {}, "ref": "e1", "depends_on": {}}]})
    def test_fallback_on_unknown_pattern(self, mock_parse, mock_match, mock_fallback):
        result = agent_module.run_agent("Update employee", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_fallback.assert_called_once()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.parse_prompt", return_value=None)
    def test_fallback_on_parse_failure(self, mock_parse, mock_fallback):
        result = agent_module.run_agent("???", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_fallback.assert_called_once()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.execute_plan")
    @patch("agent.is_known_pattern", return_value=True)
    @patch("agent.parse_prompt", return_value={"actions": []})
    def test_fallback_on_execution_failure(self, mock_parse, mock_match, mock_exec, mock_fallback):
        from planner import FallbackContext
        mock_exec.return_value = {
            "success": False,
            "fallback_context": FallbackContext(error="422 failed"),
        }
        result = agent_module.run_agent("Create employee", [], "http://x/v2", "tok")
        mock_fallback.assert_called_once()
