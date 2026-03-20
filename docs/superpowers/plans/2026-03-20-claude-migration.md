# Claude Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Gemini with Claude Opus 4.6 (Vertex AI) for parsing and tool-use. Keep Gemini for OCR only. Fixes the empty `fields`/`depends_on` parse bug.

**Architecture:** Claude (via AnthropicVertex SDK) handles prompt parsing and tool-use fallback. Gemini (google-genai) handles OCR for image attachments. Shared Claude client in `claude_client.py`. Executor, registry, and pattern matcher are unchanged.

**Tech Stack:** anthropic[vertex] SDK, google-genai (OCR), FastAPI, Python 3.11

**Spec:** `docs/superpowers/specs/2026-03-20-claude-migration-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `claude_client.py` | **Create** | Cached AnthropicVertex client + model constant |
| `planner.py` | **Modify** | Replace Gemini parse → Claude JSON extraction |
| `agent.py` | **Modify** | Replace Gemini tool loop → Claude tool-use, add gemini_ocr() |
| `requirements.txt` | **Modify** | Add `anthropic[vertex]>=0.86.0` |
| `tests/test_planner.py` | **Modify** | Mock Claude instead of Gemini, add JSON parsing tests |
| `tests/test_agent.py` | **Modify** | Rewrite tool defs tests, remove build_user_content tests, add OCR tests |
| `tests/test_executor.py` | **Modify** | Update import mocks |
| `tests/test_main.py` | **Modify** | Update import mocks (add claude_client patch) |

---

### Task 1: Create claude_client.py + update requirements.txt

**Files:**
- Create: `claude_client.py`
- Modify: `requirements.txt`

- [x] **Step 1: Create claude_client.py**

```python
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
```

- [x] **Step 2: Update requirements.txt**

Add `anthropic[vertex]>=0.86.0` after `google-genai`:

```
fastapi
uvicorn[standard]
requests
google-genai>=1.51.0
anthropic[vertex]>=0.86.0
pymupdf
python-dotenv
```

- [x] **Step 3: Install and verify import**

Run: `pip install anthropic[vertex]>=0.86.0 && python -c "from claude_client import get_claude_client, CLAUDE_MODEL; print(CLAUDE_MODEL)"`
Expected: `claude-opus-4-6`

- [x] **Step 4: Commit**

```bash
git add claude_client.py requirements.txt
git commit -m "feat: add Claude client for Vertex AI + anthropic SDK dependency"
```

---

### Task 2: Migrate planner.py — Claude parse replaces Gemini structured output

**Files:**
- Modify: `planner.py`
- Modify: `tests/test_planner.py`

- [x] **Step 1: Write updated planner tests**

Replace `TestParsePrompt` class and add code fence test. Keep all `TestIsKnownPattern` and `TestFallbackContext` tests unchanged. Replace the entire file:

```python
# tests/test_planner.py
"""Tests for planner.py — Claude-based parsing and pattern matching."""

import json
from unittest.mock import MagicMock, patch

# Mock the Claude client before importing planner
_mock_claude_client = MagicMock()

with patch("claude_client.get_claude_client", return_value=_mock_claude_client):
    # agent.py still imports google.genai for OCR — mock that too
    _mock_genai_client = MagicMock()
    with patch("google.genai.Client", return_value=_mock_genai_client):
        from planner import parse_prompt, is_known_pattern, PARSE_SYSTEM_PROMPT, FallbackContext


class TestParsePrompt:
    def _mock_response(self, text: str) -> MagicMock:
        """Create a mock Claude response with given text content."""
        response = MagicMock()
        content_block = MagicMock()
        content_block.text = text
        response.content = [content_block]
        return response

    def test_returns_task_plan_dict(self):
        """parse_prompt returns a dict with 'actions' key."""
        plan_json = json.dumps({
            "actions": [
                {"action": "create", "entity": "department",
                 "fields": {"name": "IT", "departmentNumber": "100"},
                 "search_fields": {}, "ref": "dep1", "depends_on": {}}
            ]
        })
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        result = parse_prompt("Opprett avdeling IT", [])
        assert result is not None
        assert "actions" in result
        assert result["actions"][0]["entity"] == "department"
        assert result["actions"][0]["fields"]["name"] == "IT"

    def test_extracts_fields_and_depends_on(self):
        """Verify fields and depends_on are populated (the bug we're fixing)."""
        plan_json = json.dumps({
            "actions": [
                {"action": "create", "entity": "department",
                 "fields": {"name": "Salg", "departmentNumber": "200"},
                 "search_fields": {}, "ref": "dep1", "depends_on": {}},
                {"action": "create", "entity": "employee",
                 "fields": {"firstName": "Kari", "lastName": "Nordmann"},
                 "search_fields": {}, "ref": "emp1",
                 "depends_on": {"department": "dep1"}},
            ]
        })
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        result = parse_prompt("Opprett avdeling Salg og ansatt Kari Nordmann", [])
        assert result["actions"][0]["fields"]["name"] == "Salg"
        assert result["actions"][1]["depends_on"]["department"] == "dep1"

    def test_strips_markdown_code_fences(self):
        """Claude sometimes wraps JSON in ```json ... ``` fences."""
        plan_json = '```json\n{"actions": [{"action": "create", "entity": "department", "fields": {"name": "IT"}, "search_fields": {}, "ref": "dep1", "depends_on": {}}]}\n```'
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        result = parse_prompt("Opprett avdeling IT", [])
        assert result is not None
        assert result["actions"][0]["fields"]["name"] == "IT"

    def test_strips_code_fence_without_language(self):
        """Code fence without language tag."""
        plan_json = '```\n{"actions": [{"action": "create", "entity": "customer", "fields": {"name": "Acme"}, "search_fields": {}, "ref": "c1", "depends_on": {}}]}\n```'
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        result = parse_prompt("Opprett kunde Acme", [])
        assert result is not None
        assert result["actions"][0]["fields"]["name"] == "Acme"

    def test_returns_none_on_exception(self):
        """parse_prompt returns None if Claude call fails."""
        _mock_claude_client.messages.create.side_effect = Exception("timeout")
        result = parse_prompt("test", [])
        assert result is None
        _mock_claude_client.messages.create.side_effect = None

    def test_returns_none_on_invalid_json(self):
        """parse_prompt returns None if response is not valid JSON."""
        _mock_claude_client.messages.create.return_value = self._mock_response("not json at all")
        result = parse_prompt("test", [])
        assert result is None

    def test_returns_none_on_missing_actions(self):
        """parse_prompt returns None if JSON has no 'actions' key."""
        _mock_claude_client.messages.create.return_value = self._mock_response('{"result": "ok"}')
        result = parse_prompt("test", [])
        assert result is None

    def test_includes_file_contents_in_message(self):
        """File text is included in the user message sent to Claude."""
        plan_json = json.dumps({"actions": [{"action": "create", "entity": "department", "fields": {"name": "IT"}, "search_fields": {}, "ref": "dep1", "depends_on": {}}]})
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        files = [{"filename": "data.csv", "text_content": "col1;col2\n1;2", "images": []}]
        parse_prompt("Process file", files)

        call_args = _mock_claude_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        assert "col1;col2" in user_msg
        assert "data.csv" in user_msg

    def test_parse_system_prompt_includes_field_names(self):
        assert "firstName" in PARSE_SYSTEM_PROMPT
        assert "departmentNumber" in PARSE_SYSTEM_PROMPT
        assert "priceExcludingVatCurrency" in PARSE_SYSTEM_PROMPT

    def test_parse_system_prompt_requires_json_only(self):
        assert "Output ONLY the JSON" in PARSE_SYSTEM_PROMPT


class TestIsKnownPattern:
    def test_simple_create_department(self):
        plan = {"actions": [
            {"action": "create", "entity": "department",
             "fields": {"name": "IT", "departmentNumber": "100"},
             "ref": "dep1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_create_employee_with_department_dep(self):
        plan = {"actions": [
            {"action": "create", "entity": "department",
             "fields": {"name": "IT", "departmentNumber": "100"},
             "ref": "dep1", "depends_on": {}},
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "Kari", "lastName": "Nordmann"},
             "ref": "emp1", "depends_on": {"department": "dep1"}},
        ]}
        assert is_known_pattern(plan) is True

    def test_rejects_update_without_search_fields(self):
        plan = {"actions": [
            {"action": "update", "entity": "employee",
             "fields": {"email": "new@test.no"}, "search_fields": {},
             "ref": "emp1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_rejects_delete_without_search_fields(self):
        plan = {"actions": [
            {"action": "delete", "entity": "customer",
             "fields": {}, "search_fields": {},
             "ref": "c1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_rejects_unknown_entity(self):
        plan = {"actions": [
            {"action": "create", "entity": "spaceship",
             "fields": {"name": "X"}, "ref": "s1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_rejects_unresolved_ref(self):
        plan = {"actions": [
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "Kari", "lastName": "N"},
             "ref": "emp1", "depends_on": {"department": "nonexistent_ref"}},
        ]}
        assert is_known_pattern(plan) is False

    def test_accepts_employee_without_department_action(self):
        plan = {"actions": [
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "Kari", "lastName": "N"},
             "ref": "emp1", "depends_on": {}},
        ]}
        assert is_known_pattern(plan) is True

    def test_accepts_invoice_with_array_dep(self):
        plan = {"actions": [
            {"action": "create", "entity": "customer",
             "fields": {"name": "Acme"}, "ref": "c1", "depends_on": {}},
            {"action": "create", "entity": "product",
             "fields": {"name": "Thing"}, "ref": "p1", "depends_on": {}},
            {"action": "create", "entity": "order",
             "fields": {}, "ref": "o1",
             "depends_on": {"customer": "c1", "product": "p1"}},
            {"action": "create", "entity": "invoice",
             "fields": {}, "ref": "inv1",
             "depends_on": {"orders": ["o1"]}},
        ]}
        assert is_known_pattern(plan) is True

    def test_rejects_none_plan(self):
        assert is_known_pattern(None) is False

    def test_rejects_empty_actions(self):
        assert is_known_pattern({"actions": []}) is False

    def test_accepts_update_with_search_fields(self):
        plan = {"actions": [
            {"action": "update", "entity": "customer",
             "fields": {"email": "new@test.no"},
             "search_fields": {"name": "Acme AS"},
             "ref": "c1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_accepts_delete_with_search_fields(self):
        plan = {"actions": [
            {"action": "delete", "entity": "department",
             "fields": {}, "search_fields": {"name": "Old Dept"},
             "ref": "d1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_accepts_named_action(self):
        plan = {"actions": [
            {"action": "send_invoice", "entity": "invoice",
             "fields": {"sendType": "EMAIL"},
             "search_fields": {"customerId": "123"},
             "ref": "si1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_rejects_named_action_wrong_entity(self):
        plan = {"actions": [
            {"action": "send_invoice", "entity": "department",
             "fields": {}, "search_fields": {"name": "X"},
             "ref": "si1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_accepts_new_entity_types(self):
        plan = {"actions": [
            {"action": "create", "entity": "supplier",
             "fields": {"name": "Test Supplier"},
             "ref": "s1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_parse_system_prompt_includes_action_instructions(self):
        assert "update" in PARSE_SYSTEM_PROMPT
        assert "search_fields" in PARSE_SYSTEM_PROMPT
        assert "send_invoice" in PARSE_SYSTEM_PROMPT

    def test_parse_system_prompt_includes_examples(self):
        assert "Opprett en avdeling med navn Salg" in PARSE_SYSTEM_PROMPT
        assert "Erstellen Sie einen Mitarbeiter" in PARSE_SYSTEM_PROMPT

    def test_accepts_singleton_update_without_search_fields(self):
        plan = {"actions": [
            {"action": "update", "entity": "company",
             "fields": {"name": "New Name"},
             "search_fields": {},
             "ref": "co1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True


class TestFallbackContext:
    def test_default_values(self):
        ctx = FallbackContext()
        assert ctx.task_plan is None
        assert ctx.completed_refs == {}
        assert ctx.failed_action is None
        assert ctx.error is None

    def test_with_values(self):
        ctx = FallbackContext(
            task_plan={"actions": []},
            completed_refs={"dep1": 123},
            failed_action={"entity": "employee"},
            error="422 Validation failed",
        )
        assert ctx.completed_refs["dep1"] == 123
```

- [x] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_planner.py -v`
Expected: FAIL with ImportError — planner.py still imports `google.genai` and doesn't use `claude_client` yet. This is expected and will be resolved in Step 3.

- [x] **Step 3: Update planner.py**

Replace the imports, remove `genai_client`, `TASK_PLAN_SCHEMA`, and rewrite `parse_prompt()`. Keep `PARSE_SYSTEM_PROMPT`, `is_known_pattern()`, `DETERMINISTIC_ACTIONS`, and `FallbackContext` unchanged.

Key changes:
1. Replace imports at top of file:
```python
# REMOVE these:
# from google import genai
# from google.genai import types

# ADD these:
import json
import re
from claude_client import get_claude_client, CLAUDE_MODEL
```

2. Remove the Gemini client block (lines 25-29 of current file):
```python
# REMOVE:
# genai_client = genai.Client(...)
# MODEL = "gemini-3.1-pro-preview"
# PARSE_TIMEOUT = 20
```

3. Add to end of `PARSE_SYSTEM_PROMPT` (before the closing `"""`):
```
Output ONLY the JSON object. No explanation, no markdown code fences, no other text.
```

4. Remove `TASK_PLAN_SCHEMA` dict entirely (lines 144-170)

5. Replace `parse_prompt()` with the Claude version from the spec (Section 3). The complete function is in the spec.

6. Update module docstring:
```python
"""Structured output parsing and pattern matching for deterministic execution.

parse_prompt() — Claude extracts a TaskPlan from the prompt (1 LLM call).
is_known_pattern() — Checks if the plan can be executed deterministically.
FallbackContext — Shared context for tool-use fallback handoff.
"""
```

- [x] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_planner.py -v`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add planner.py tests/test_planner.py
git commit -m "feat: migrate planner to Claude Opus 4.6 — fixes empty fields parse bug

Replaces Gemini structured output with Claude JSON extraction via
AnthropicVertex SDK. Removes TASK_PLAN_SCHEMA (no schema constraint
needed). Claude returns populated fields/depends_on from instructions
and few-shot examples alone."
```

---

### Task 3: Migrate agent.py — Claude tool-use + Gemini OCR

**Files:**
- Modify: `agent.py`
- Modify: `tests/test_agent.py`
- Modify: `tests/test_executor.py`

- [x] **Step 1: Write updated agent tests**

Replace the entire test file. Keep `TestSystemPrompt`, `TestExecuteTool`, and `TestRouting` with minor mock updates. Replace `TestToolDefinitions` and `TestBuildUserContent`. Add `TestGeminiOcr`.

```python
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
```

- [x] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_agent.py -v`
Expected: FAIL (agent.py still has Gemini code, missing `TOOLS`, `gemini_ocr`)

- [x] **Step 3: Update agent.py**

Complete rewrite. Key changes from spec Section 4:

1. **Update imports** — keep Gemini imports for OCR, add Claude client:
```python
# KEEP these (needed for gemini_ocr):
from google import genai
from google.genai import types

# KEEP: genai_client = genai.Client(...) block (needed for OCR)

# ADD:
from claude_client import get_claude_client, CLAUDE_MODEL
```
**Important:** `from google.genai import types` and the `genai_client` must stay — `gemini_ocr()` uses `types.Part`, `types.Content`, `types.GenerateContentConfig`, and `genai_client.models.generate_content()`.

2. **Rename** `MODEL` → `GEMINI_MODEL` (keep for OCR)

3. **Replace** `FUNCTION_DECLARATIONS` and `TOOLS` with Anthropic format tool dicts (from spec Section 4)

4. **Remove** `build_user_content()` entirely

5. **Add** `gemini_ocr()` function (from spec Section 4)

6. **Rewrite** `run_tool_loop()` for Claude message format (from spec Section 4)

7. **Update** `run_agent()` to add OCR step 0 (from spec Section 4)

8. **Update** module docstring:
```python
"""Claude tool-use agentic loop for Tripletex accounting tasks.

Uses Claude Opus 4.6 via Vertex AI for tool-use fallback.
Gemini retained for OCR (image text extraction) only.
"""
```

All replacement code is in spec Sections 4. Copy `TOOLS`, `gemini_ocr()`, `run_tool_loop()`, and `run_agent()` exactly from the spec.

- [x] **Step 4: Update tests/test_executor.py mock**

The executor tests mock `google.genai.Client` because `planner.py` used to instantiate it at import time. Since `planner.py` no longer does this, but `agent.py` still does (for OCR), update the mock patch:

Replace lines 6-8:
```python
# OLD:
_mock_genai_client = MagicMock()
with patch("google.genai.Client", return_value=_mock_genai_client):
    from executor import (...)

# NEW:
_mock_genai_client = MagicMock()
_mock_claude_client = MagicMock()
with patch("google.genai.Client", return_value=_mock_genai_client):
    with patch("claude_client.get_claude_client", return_value=_mock_claude_client):
        from executor import (
            execute_plan, _topological_sort, _build_payload,
            _resolve_pre_lookups, _resolve_by_search, _auto_batch,
        )
        from task_registry import BULK_ENDPOINTS
```

- [x] **Step 5: Update tests/test_main.py mock**

`test_main.py` imports `main.py` which imports `agent.py` which now imports `claude_client`. Add the claude_client mock:

Replace lines 6-8:
```python
# OLD:
_mock_genai = MagicMock()
with patch("google.genai.Client", return_value=_mock_genai):
    from main import app, _preconfigure_bank_account

# NEW:
_mock_genai = MagicMock()
_mock_claude = MagicMock()
with patch("google.genai.Client", return_value=_mock_genai):
    with patch("claude_client.get_claude_client", return_value=_mock_claude):
        from main import app, _preconfigure_bank_account
```

- [x] **Step 6: Run all tests — expect PASS**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [x] **Step 7: Commit**

```bash
git add agent.py tests/test_agent.py tests/test_executor.py tests/test_main.py
git commit -m "feat: migrate agent to Claude tool-use + Gemini OCR

Replaces Gemini tool-use loop with Claude Opus 4.6 via AnthropicVertex.
Tool definitions ported to Anthropic format (same 4 HTTP tools).
Gemini retained for image OCR only (gemini_ocr function).
Removes build_user_content — Claude receives text only."
```

---

### Task 4: Deploy + smoke test — verify deterministic path works

**Files:**
- No code changes (unless smoke test reveals issues)

- [x] **Step 1: Run full unit test suite**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [x] **Step 2: Deploy to Cloud Run**

```bash
gcloud run deploy ai-accounting-agent-det --source . \
  --region europe-north1 --project ai-nm26osl-1799 \
  --no-allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global" \
  --quiet
```

- [x] **Step 3: Run Tier 1 smoke tests**

```bash
source .env && export TRIPLETEX_SESSION_TOKEN
python smoke_test.py --tier 1
```

Expected: All Tier 1 tasks PASS.
**Critical check:** Look at Cloud Run logs for `path=deterministic` — this confirms the parse bug is fixed:
```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="ai-accounting-agent-det" AND textPayload=~"result:"' \
  --project ai-nm26osl-1799 --limit 10 --format="value(textPayload)" --freshness=15m
```

Before: all `path=deterministic+fallback` or `path=fallback`
After: should see `path=deterministic`

- [x] **Step 4: Run Tier 2 smoke tests**

```bash
python smoke_test.py --tier 2
```

Expected: Most Tier 2 tasks PASS. Update/delete tasks should work via deterministic path.

- [x] **Step 5: Commit any fixes**

```bash
git status  # review changes first
git add smoke_test.py  # add only relevant files
git commit -m "test: smoke test verified — Claude parse enables deterministic path"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Claude client + dependency | `claude_client.py`, `requirements.txt` |
| 2 | Planner: Gemini → Claude parse | `planner.py`, `tests/test_planner.py` |
| 3 | Agent: Gemini → Claude tool-use + OCR | `agent.py`, `tests/test_agent.py`, `tests/test_executor.py`, `tests/test_main.py` |
| 4 | Deploy + smoke test | (no code changes expected) |
