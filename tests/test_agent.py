# tests/test_agent.py
import json
import time
from unittest.mock import patch, MagicMock
from tripletex_api import TripletexClient


# --- Test helpers ---

def _mock_client():
    """Create a mock TripletexClient with metric counters."""
    client = MagicMock(spec=TripletexClient)
    client.call_count = 0
    client.error_count = 0
    return client


def _make_fc_response(name, args):
    """Create a mock Gemini response containing a single function call."""
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
    """Create a mock Gemini response containing only text (task complete)."""
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


# --- Unit tests ---

def test_build_system_prompt_includes_date_and_cheatsheet():
    """System prompt includes today's date and the API cheat sheet."""
    from agent import build_system_prompt
    from datetime import date

    prompt = build_system_prompt()
    assert date.today().isoformat() in prompt
    assert "Tripletex v2 API" in prompt
    assert "POST /employee" in prompt


def test_execute_tool_routes_get():
    """_execute_tool routes GET requests to client.get with parsed params."""
    from agent import _execute_tool

    client = _mock_client()
    client.get.return_value = {"status_code": 200, "success": True, "body": {"values": []}}
    result = _execute_tool(client, "tripletex_api", {
        "method": "GET",
        "endpoint": "/employee",
        "query_params_json": '{"fields": "id,firstName"}',
    })
    client.get.assert_called_once_with("/employee", params={"fields": "id,firstName"})
    assert result["success"] is True


def test_execute_tool_routes_post():
    """_execute_tool routes POST requests to client.post with parsed body."""
    from agent import _execute_tool

    client = _mock_client()
    client.post.return_value = {"status_code": 201, "success": True, "body": {"value": {"id": 42}}}
    result = _execute_tool(client, "tripletex_api", {
        "method": "POST",
        "endpoint": "/employee",
        "body_json": '{"firstName": "Ola", "lastName": "Nordmann"}',
    })
    client.post.assert_called_once_with("/employee", body={"firstName": "Ola", "lastName": "Nordmann"})
    assert result["body"]["value"]["id"] == 42


def test_execute_tool_routes_put():
    """_execute_tool routes PUT requests to client.put."""
    from agent import _execute_tool

    client = _mock_client()
    client.put.return_value = {"status_code": 200, "success": True, "body": {"value": {"id": 42}}}
    _execute_tool(client, "tripletex_api", {
        "method": "PUT",
        "endpoint": "/employee/42",
        "body_json": '{"firstName": "Kari"}',
    })
    client.put.assert_called_once_with("/employee/42", body={"firstName": "Kari"})


def test_execute_tool_routes_delete():
    """_execute_tool routes DELETE requests to client.delete."""
    from agent import _execute_tool

    client = _mock_client()
    client.delete.return_value = {"status_code": 204, "success": True, "body": {}}
    _execute_tool(client, "tripletex_api", {
        "method": "DELETE",
        "endpoint": "/travelExpense/99",
    })
    client.delete.assert_called_once_with("/travelExpense/99")


def test_execute_tool_handles_dict_body():
    """_execute_tool accepts body_json as a dict (Gemini may send either str or dict)."""
    from agent import _execute_tool

    client = _mock_client()
    client.post.return_value = {"status_code": 201, "success": True, "body": {"value": {"id": 1}}}
    _execute_tool(client, "tripletex_api", {
        "method": "POST",
        "endpoint": "/customer",
        "body_json": {"name": "Acme AS"},
    })
    client.post.assert_called_once_with("/customer", body={"name": "Acme AS"})


def test_execute_tool_unknown_tool():
    """_execute_tool returns error for unknown tool names."""
    from agent import _execute_tool

    client = _mock_client()
    result = _execute_tool(client, "unknown_tool", {})
    assert "error" in result


def test_parse_json_arg_handles_types():
    """_parse_json_arg handles string, dict, None, and empty string."""
    from agent import _parse_json_arg

    assert _parse_json_arg('{"a": 1}') == {"a": 1}
    assert _parse_json_arg({"a": 1}) == {"a": 1}
    assert _parse_json_arg(None) is None
    assert _parse_json_arg("") is None
    assert _parse_json_arg("not json") is None


# --- Integration-style tests (mocked Gemini) ---

def test_run_agent_single_tool_call():
    """Agent executes one tool call then completes when Gemini returns text."""
    from agent import run_agent

    client = _mock_client()
    client.post.return_value = {
        "status_code": 201,
        "success": True,
        "body": {"value": {"id": 42, "firstName": "Ola"}},
    }

    gemini_responses = [
        _make_fc_response("tripletex_api", {
            "method": "POST",
            "endpoint": "/employee",
            "body_json": '{"firstName":"Ola","lastName":"Nordmann"}',
        }),
        _make_text_response("Created employee Ola Nordmann with ID 42"),
    ]

    with patch("agent.genai_client") as mock_genai:
        mock_genai.models.generate_content.side_effect = gemini_responses
        result = run_agent(
            client=client,
            prompt="Opprett ansatt Ola Nordmann",
            file_contents=[],
            deadline=time.time() + 300,
        )

    assert result["success"] is True
    assert "Ola" in result["summary"]
    client.post.assert_called_once()


def test_run_agent_stops_at_timeout():
    """Agent stops when deadline has passed."""
    from agent import run_agent

    client = _mock_client()

    with patch("agent.genai_client") as mock_genai:
        result = run_agent(
            client=client,
            prompt="Some task",
            file_contents=[],
            deadline=time.time() - 10,  # Already expired
        )

    assert result["success"] is False
    mock_genai.models.generate_content.assert_not_called()


def test_run_agent_handles_gemini_error():
    """Agent handles Gemini API errors gracefully."""
    from agent import run_agent

    client = _mock_client()

    with patch("agent.genai_client") as mock_genai:
        mock_genai.models.generate_content.side_effect = Exception("API error")
        result = run_agent(
            client=client,
            prompt="Some task",
            file_contents=[],
            deadline=time.time() + 300,
        )

    assert result["success"] is False
