# tests/test_agent.py
"""Tests for agent.py — mock Claude + Gemini, no real API calls."""

import json
from unittest.mock import MagicMock, patch, call

import pytest

_mock_genai_client = MagicMock()
_mock_claude_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    with patch("claude_client.get_claude_client", return_value=_mock_claude_client):
        import agent as agent_module


class TestToolDefinitions:
    def test_has_four_tools(self):
        names = [t["name"] for t in agent_module.TOOLS]
        assert sorted(names) == ["tripletex_delete", "tripletex_get", "tripletex_post", "tripletex_put"]

    def test_post_requires_path_and_body(self):
        post = next(t for t in agent_module.TOOLS if t["name"] == "tripletex_post")
        assert "path" in post["input_schema"]["required"]
        assert "body" in post["input_schema"]["required"]

    def test_put_has_params(self):
        put = next(t for t in agent_module.TOOLS if t["name"] == "tripletex_put")
        assert "params" in put["input_schema"]["properties"]

    def test_all_tools_have_input_schema(self):
        for tool in agent_module.TOOLS:
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"


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


class TestGeminiOcr:
    def test_returns_empty_when_no_images(self):
        files = [{"filename": "data.csv", "text_content": "col1;col2", "images": []}]
        result = agent_module.gemini_ocr(files)
        assert result == ""
        _mock_genai_client.models.generate_content.assert_not_called()

    def test_calls_gemini_with_images(self):
        _mock_genai_client.models.generate_content.reset_mock()
        mock_response = MagicMock()
        mock_response.text = "Invoice #123, Amount: 500 NOK"
        _mock_genai_client.models.generate_content.return_value = mock_response

        files = [{"filename": "receipt.png", "text_content": "",
                  "images": [{"data": b"PNG_DATA", "mime_type": "image/png"}]}]
        result = agent_module.gemini_ocr(files)
        assert "Invoice #123" in result
        _mock_genai_client.models.generate_content.assert_called_once()

    def test_returns_empty_on_none_response(self):
        mock_response = MagicMock()
        mock_response.text = None
        _mock_genai_client.models.generate_content.return_value = mock_response

        files = [{"filename": "img.jpg", "text_content": "",
                  "images": [{"data": b"JPG", "mime_type": "image/jpeg"}]}]
        result = agent_module.gemini_ocr(files)
        assert result == ""


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
    @patch("agent.run_tool_loop")
    @patch("agent.execute_plan", return_value={"success": True, "ref_map": {}, "api_calls": 1})
    @patch("agent.is_known_pattern", return_value=True)
    @patch("agent.parse_prompt", return_value={"actions": [{"action": "create", "entity": "department", "fields": {"name": "IT"}, "ref": "d1", "depends_on": {}}]})
    @patch("agent.gemini_ocr", return_value="")
    def test_deterministic_path(self, mock_ocr, mock_parse, mock_match, mock_exec, mock_fallback):
        result = agent_module.run_agent("Create dept", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_exec.assert_called_once()
        mock_fallback.assert_not_called()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.is_known_pattern", return_value=False)
    @patch("agent.parse_prompt", return_value={"actions": [{"action": "update", "entity": "employee", "fields": {}, "ref": "e1", "depends_on": {}}]})
    @patch("agent.gemini_ocr", return_value="")
    def test_fallback_on_unknown_pattern(self, mock_ocr, mock_parse, mock_match, mock_fallback):
        result = agent_module.run_agent("Update employee", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_fallback.assert_called_once()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.parse_prompt", return_value=None)
    @patch("agent.gemini_ocr", return_value="")
    def test_fallback_on_parse_failure(self, mock_ocr, mock_parse, mock_fallback):
        result = agent_module.run_agent("???", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_fallback.assert_called_once()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.execute_plan")
    @patch("agent.is_known_pattern", return_value=True)
    @patch("agent.parse_prompt", return_value={"actions": []})
    @patch("agent.gemini_ocr", return_value="")
    def test_fallback_on_execution_failure(self, mock_ocr, mock_parse, mock_match, mock_exec, mock_fallback):
        from planner import FallbackContext
        mock_exec.return_value = {
            "success": False,
            "fallback_context": FallbackContext(error="422 failed"),
        }
        result = agent_module.run_agent("Create employee", [], "http://x/v2", "tok")
        mock_fallback.assert_called_once()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.is_known_pattern", return_value=False)
    @patch("agent.parse_prompt", return_value=None)
    @patch("agent.gemini_ocr", return_value="Extracted: Invoice 500 NOK")
    def test_ocr_text_appended_to_file_contents(self, mock_ocr, mock_parse, mock_match, mock_fallback):
        file_contents = [{"filename": "receipt.png", "text_content": "", "images": [{"data": b"PNG", "mime_type": "image/png"}]}]
        agent_module.run_agent("Process receipt", file_contents, "http://x/v2", "tok")
        # OCR text should be appended as synthetic file
        assert any(f["filename"] == "_ocr_extracted.txt" for f in file_contents)
        ocr_file = next(f for f in file_contents if f["filename"] == "_ocr_extracted.txt")
        assert "Invoice 500 NOK" in ocr_file["text_content"]


class TestRunToolLoop:
    def _make_tool_use_response(self, tool_name, tool_input, tool_id="tu_1"):
        """Create a mock Claude response with a tool_use block."""
        resp = MagicMock()
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = tool_name
        tool_block.input = tool_input
        tool_block.id = tool_id
        resp.content = [tool_block]
        return resp

    def _make_text_response(self, text="Done"):
        """Create a mock Claude response with only text (no tool use)."""
        resp = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text
        resp.content = [text_block]
        return resp

    def test_single_tool_call_then_stop(self):
        """Claude calls one tool, gets result, then responds with text."""
        mock_tripletex = MagicMock()
        mock_tripletex.get.return_value = {"success": True, "status_code": 200, "body": {"values": []}}

        _mock_claude_client.messages.create.side_effect = [
            self._make_tool_use_response("tripletex_get", {"path": "/department"}),
            self._make_text_response("Created department"),
        ]

        from planner import FallbackContext
        result = agent_module.run_tool_loop("Create dept", [], mock_tripletex, FallbackContext())
        assert result["status"] == "completed"
        assert result["iterations"] == 2
        mock_tripletex.get.assert_called_once()
        _mock_claude_client.messages.create.side_effect = None

    def test_fallback_context_injected_in_system_prompt(self):
        """Completed refs and error are included in the system prompt."""
        mock_tripletex = MagicMock()
        _mock_claude_client.messages.create.return_value = self._make_text_response("Done")

        from planner import FallbackContext
        ctx = FallbackContext(
            completed_refs={"dep1": 42},
            failed_action={"entity": "employee", "ref": "emp1"},
            error="422 Validation failed",
        )
        agent_module.run_tool_loop("Create employee", [], mock_tripletex, ctx)

        call_args = _mock_claude_client.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "dep1" in system_prompt
        assert "422 Validation failed" in system_prompt
        _mock_claude_client.messages.create.side_effect = None
