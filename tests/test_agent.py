# tests/test_agent.py
"""Tests for the pure Claude agentic loop."""
import json
from unittest.mock import MagicMock, patch

# Mock external dependencies before importing agent
_mock_genai_client = MagicMock()
_mock_claude_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    with patch("claude_client.get_claude_client", return_value=_mock_claude_client):
        import agent as agent_module

# Ensure lazy genai client returns our mock
agent_module._get_genai_client = lambda: _mock_genai_client


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
        from prompts import build_system_prompt
        prompt = build_system_prompt()
        assert "POST /employee" in prompt

    def test_includes_payment_gotcha(self):
        from prompts import build_system_prompt
        prompt = build_system_prompt()
        assert "QUERY" in prompt

    def test_includes_known_constants(self):
        from prompts import build_system_prompt
        prompt = build_system_prompt()
        assert "162" in prompt
        assert "vatType" in prompt


class TestGeminiOcr:
    def setup_method(self):
        agent_module._get_genai_client = lambda: _mock_genai_client

    def test_returns_empty_when_no_images(self):
        files = [{"filename": "data.csv", "text_content": "col1;col2", "images": []}]
        result = agent_module.gemini_ocr(files)
        assert result == ""

    def test_calls_gemini_with_images(self):
        _mock_genai_client.models.generate_content.reset_mock()
        mock_response = MagicMock()
        mock_response.text = "Invoice #123, Amount: 500 NOK"
        _mock_genai_client.models.generate_content.return_value = mock_response

        files = [{"filename": "receipt.png", "text_content": "",
                  "images": [{"data": b"PNG_DATA", "mime_type": "image/png"}]}]
        result = agent_module.gemini_ocr(files)
        assert "Invoice #123" in result

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

    def test_post(self):
        mock_client = MagicMock()
        mock_client.post.return_value = {"success": True, "status_code": 201, "body": {"value": {"id": 1}}}
        result = agent_module.execute_tool("tripletex_post", {"path": "/employee", "body": {"firstName": "Ola"}}, mock_client)
        mock_client.post.assert_called_once_with("/employee", body={"firstName": "Ola"})

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

    def test_delete(self):
        mock_client = MagicMock()
        mock_client.delete.return_value = {"success": True, "status_code": 204, "body": {}}
        agent_module.execute_tool("tripletex_delete", {"path": "/employee/1"}, mock_client)
        mock_client.delete.assert_called_once_with("/employee/1", params=None)

    def test_unknown_tool(self):
        result = agent_module.execute_tool("tripletex_patch", {}, MagicMock())
        assert not result["success"]

    def test_exception_returns_error(self):
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("connection timeout")
        result = agent_module.execute_tool("tripletex_post", {"path": "/x", "body": {}}, mock_client)
        assert not result["success"]
        assert "connection timeout" in result["error"]


class TestBuildUserMessage:
    def test_prompt_only(self):
        msg = agent_module.build_user_message("Create employee Ola", [])
        assert "Create employee Ola" in msg

    def test_with_file_text(self):
        files = [{"filename": "data.csv", "text_content": "Name,Amount\nOla,1000", "images": []}]
        msg = agent_module.build_user_message("Process this", files)
        assert "data.csv" in msg
        assert "Name,Amount" in msg

    def test_with_ocr_text(self):
        files = [{"filename": "_ocr_extracted.txt", "text_content": "Invoice #123", "images": []}]
        msg = agent_module.build_user_message("Process invoice", files)
        assert "Invoice #123" in msg


class TestRunAgentOcr:
    """Test that OCR text is appended to file_contents."""

    @patch("agent.gemini_ocr", return_value="Extracted: Invoice 500 NOK")
    def test_ocr_text_appended(self, mock_ocr):
        # Mock the Claude streaming response to just end immediately
        mock_stream = MagicMock()
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = []
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.get_final_message.return_value = mock_response
        _mock_claude_client.messages.stream.return_value = mock_stream

        file_contents = [{"filename": "receipt.png", "text_content": "", "images": [{"data": b"PNG", "mime_type": "image/png"}]}]
        agent_module.run_agent("Process receipt", file_contents, "http://x/v2", "tok")
        assert any(f["filename"] == "_ocr_extracted.txt" for f in file_contents)


class TestConstants:
    def test_max_iterations(self):
        assert agent_module.MAX_ITERATIONS == 20

    def test_timeout(self):
        assert agent_module.TIMEOUT_SECONDS == 270
