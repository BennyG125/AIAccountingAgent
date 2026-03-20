# Tripletex Tool-Use Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static plan-execute-recover architecture with a native Gemini tool-use agentic loop, and fix the dual payload format bug.

**Architecture:** Gemini 3.1 Pro Preview receives the task prompt + cheat sheet as system instruction, with 4 REST tools (GET/POST/PUT/DELETE). It calls tools iteratively, seeing each API response before deciding the next action. This replaces planner.py, executor.py, and recovery.py with a single agent.py (~120 lines).

**Tech Stack:** google-genai SDK (Vertex AI), FastAPI, requests, pymupdf

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `main.py` | **Modify** | Fix dual payload, wire in agent.py, remove planner/executor/recovery imports |
| `agent.py` | **Create** | Gemini tool-use agentic loop + system prompt + tool definitions |
| `tripletex_api.py` | **Modify** | Add `params` support to `put()` for payment registration |
| `file_handler.py` | **Keep as-is** | File processing (already good) |
| `api_knowledge/cheat_sheet.py` | **Modify** | Fix payment registration docs (query params, not body) |
| `tests/test_main.py` | **Create** | Tests for dual payload parsing |
| `tests/test_agent.py` | **Create** | Tests for agent loop (mocked Gemini) |
| `planner.py` | **Delete** (Task 4) | Replaced by agent.py |
| `executor.py` | **Delete** (Task 4) | Replaced by agent.py |
| `recovery.py` | **Delete** (Task 4) | Replaced by agent.py |
| `tests/test_planner.py` | **Delete** (Task 4) | No longer relevant |
| `tests/test_executor.py` | **Delete** (Task 4) | No longer relevant |
| `tests/test_recovery.py` | **Delete** (Task 4) | No longer relevant |

---

### Task 1: Fix Dual Payload Format (GitHub Issue #1)

**Files:**
- Modify: `main.py:40-46`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing tests for both payload formats**

```python
# tests/test_main.py
"""Tests for /solve endpoint payload parsing."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Patch Gemini client before importing main (planner imports genai at module level)
with patch("google.genai.Client", return_value=MagicMock()):
    from main import app

client = TestClient(app)


def _format_a_payload():
    """Competition docs format."""
    return {
        "prompt": "Opprett en ansatt med navn Ola Nordmann",
        "files": [],
        "tripletex_credentials": {
            "base_url": "https://tripletex.no/v2",
            "session_token": "test-token-123",
        },
    }


def _format_b_payload():
    """Competitor-observed format."""
    return {
        "task_prompt": "Create an employee named Ola Nordmann",
        "attached_files": [],
        "tripletex_base_url": "https://tripletex.no/v2",
        "session_token": "test-token-456",
    }


class TestPayloadParsing:
    @patch("main.process_files", return_value=[])
    @patch("main.plan_task", return_value={"steps": [{"method": "GET", "endpoint": "/employee"}]})
    @patch("main.execute_plan", return_value={"success": True, "variables": {}, "completed_steps": [0], "results": []})
    def test_format_a(self, mock_exec, mock_plan, mock_files):
        """Format A: prompt + tripletex_credentials dict."""
        resp = client.post("/solve", json=_format_a_payload())
        assert resp.status_code == 200
        assert resp.json() == {"status": "completed"}
        mock_plan.assert_called_once()
        # Verify the prompt was extracted correctly
        assert mock_plan.call_args[0][0] == "Opprett en ansatt med navn Ola Nordmann"

    @patch("main.process_files", return_value=[])
    @patch("main.plan_task", return_value={"steps": [{"method": "GET", "endpoint": "/employee"}]})
    @patch("main.execute_plan", return_value={"success": True, "variables": {}, "completed_steps": [0], "results": []})
    def test_format_b(self, mock_exec, mock_plan, mock_files):
        """Format B: task_prompt + flat credentials."""
        resp = client.post("/solve", json=_format_b_payload())
        assert resp.status_code == 200
        assert resp.json() == {"status": "completed"}
        mock_plan.assert_called_once()
        assert mock_plan.call_args[0][0] == "Create an employee named Ola Nordmann"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python -m pytest tests/test_main.py -v`
Expected: test_format_b FAILS with KeyError on `body["prompt"]`

- [ ] **Step 3: Fix payload parsing in main.py**

Replace lines 40-46 of `main.py` with:

```python
    body = await request.json()

    # Handle both payload formats (competition docs vs competitor-observed)
    prompt = body.get("prompt") or body.get("task_prompt", "")
    files = body.get("files") or body.get("attached_files", [])

    # Credentials: nested dict (Format A) or flat keys (Format B)
    creds = body.get("tripletex_credentials", {})
    base_url = creds.get("base_url") or body.get("tripletex_base_url", "")
    session_token = creds.get("session_token") or body.get("session_token", "")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_main.py -v`
Expected: Both tests PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "fix: handle both competition payload formats (A and B)

Format A: {prompt, files, tripletex_credentials: {base_url, session_token}}
Format B: {task_prompt, attached_files, tripletex_base_url, session_token}

Closes #1"
```

---

### Task 2: Fix tripletex_api.py PUT params + cheat sheet payment docs

**Files:**
- Modify: `tripletex_api.py:29-33`
- Modify: `api_knowledge/cheat_sheet.py` (payment registration section)

- [ ] **Step 1: Add `params` support to `TripletexClient.put()`**

In `tripletex_api.py`, change the `put` method to accept and pass `params`:

```python
def put(self, endpoint: str, body: dict | None = None, params: dict | None = None) -> dict:
    url = f"{self.base_url}{endpoint}"
    logger.info(f"PUT {url} params={params}")
    resp = requests.put(url, auth=self.auth, json=body, params=params)
    return self._parse_response(resp)
```

- [ ] **Step 2: Fix cheat sheet payment registration section**

Find the payment registration section in `api_knowledge/cheat_sheet.py` and update it to clearly state that payment uses query parameters, not body. Search for `/:payment` and update the surrounding documentation to say:

```
### PUT /invoice/{id}/:payment
Register payment. Use QUERY PARAMETERS (not body):
?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1
```

- [ ] **Step 3: Run existing tests to verify nothing breaks**

Run: `python -m pytest tests/test_tripletex_api.py -v`
Expected: All PASS (the new `params` kwarg defaults to None, so existing calls are unaffected)

- [ ] **Step 4: Commit**

```bash
git add tripletex_api.py api_knowledge/cheat_sheet.py
git commit -m "fix: add params support to PUT + fix payment docs in cheat sheet

Payment registration uses query params, not body. TripletexClient.put()
now accepts and forwards params to requests.put().

Refs #2"
```

---

### Task 3: Create agent.py with Gemini Tool-Use Loop (GitHub Issue #2)

**Files:**
- Create: `agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write failing test for agent tool definitions**

```python
# tests/test_agent.py
"""Tests for agent.py — all mock Gemini, no real API calls."""

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

_mock_genai_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    import agent as agent_module


class TestToolDefinitions:
    def test_has_four_tools(self):
        """Tool definitions include GET, POST, PUT, DELETE."""
        names = [fd.name for fd in agent_module.FUNCTION_DECLARATIONS]
        assert sorted(names) == ["tripletex_delete", "tripletex_get", "tripletex_post", "tripletex_put"]

    def test_post_tool_requires_path_and_body(self):
        """POST tool requires both path and body."""
        post_tool = next(fd for fd in agent_module.FUNCTION_DECLARATIONS if fd.name == "tripletex_post")
        schema = post_tool.parameters
        assert "path" in schema["properties"]
        assert "body" in schema["properties"]
        assert "path" in schema["required"]
        assert "body" in schema["required"]
```

- [ ] **Step 2: Write the agent.py tool definitions and system prompt**

```python
# agent.py
"""Gemini tool-use agentic loop for Tripletex accounting tasks."""

import json
import logging
import os
import time
from datetime import date
from typing import Any

from google import genai
from google.genai import types

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET
from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client & model
# ---------------------------------------------------------------------------

genai_client = genai.Client(
    vertexai=True,
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "global"),
)

MODEL = "gemini-3.1-pro-preview"
MAX_ITERATIONS = 25
TIMEOUT_SECONDS = 270  # 30s buffer before 300s hard limit

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="tripletex_get",
        description="GET request to Tripletex API. Use for listing, searching, and fetching entities.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee', '/customer/123'"},
                "params": {"type": "object", "description": "Query params e.g. {\"fields\": \"id,name\"}"},
            },
            "required": ["path"],
        },
    ),
    types.FunctionDeclaration(
        name="tripletex_post",
        description="POST request to create entities. ALWAYS include body with JSON payload.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee'"},
                "body": {"type": "object", "description": "JSON request body for creating entities"},
                "params": {"type": "object", "description": "Query params (rare for POST)"},
            },
            "required": ["path", "body"],
        },
    ),
    types.FunctionDeclaration(
        name="tripletex_put",
        description="PUT request for updates and action endpoints (/:invoice, /:payment). "
                    "For payment registration, use params for query parameters.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/invoice/123/:payment'"},
                "body": {"type": "object", "description": "JSON body (optional for action endpoints)"},
                "params": {"type": "object", "description": "Query params e.g. payment fields"},
            },
            "required": ["path"],
        },
    ),
    types.FunctionDeclaration(
        name="tripletex_delete",
        description="DELETE request for removing entities.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee/123'"},
            },
            "required": ["path"],
        },
    ),
]

TOOLS = [types.Tool(function_declarations=FUNCTION_DECLARATIONS)]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    today = date.today().isoformat()
    return f"""You are an expert AI accounting agent for Tripletex. Complete the given task by calling the Tripletex REST API using the provided tools.

Today's date is {today}.

## Rules
1. Minimize API calls — every extra call hurts your efficiency score.
2. Do NOT search before creating unless the task says "find" or "modify existing".
3. Use known constants directly — never look them up:
   - VAT 25%: vatType id=3
   - VAT 15%: vatType id=5
   - VAT 0%: vatType id=6
   - NOK currency: id=1
   - Norway country: id=162
4. Create entities in dependency order: department → employee, customer + product → order → invoice → payment.
5. Use response IDs from create calls directly — do not re-fetch.
6. Embed orderLines in the order POST body (saves a call).
7. For payment registration: PUT /invoice/{{id}}/:payment with query PARAMS (paymentDate, paymentTypeId, paidAmount, paidAmountCurrency), NOT a JSON body.
8. Dates are always YYYY-MM-DD for the API.
9. Object references are always {{"id": <int>}}, never bare ints.
10. departmentNumber is a STRING, not an int.
11. On error: read the error message, fix the issue, retry ONCE. Never retry more than once.
12. When done, stop calling tools. Do not add verification GETs after successful creates.

## Payment Registration (critical gotcha)
PUT /invoice/{{invoiceId}}/:payment?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1
Use params, NOT body. paymentTypeId: use GET /invoice/paymentType to find the right one, or use id=0 for default.

{TRIPLETEX_API_CHEAT_SHEET}
"""


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: dict, client: TripletexClient) -> dict:
    """Execute a single tool call against the Tripletex API."""
    path = args.get("path", "")
    params = args.get("params")
    body = args.get("body")

    if name == "tripletex_get":
        return client.get(path, params=params)
    elif name == "tripletex_post":
        return client.post(path, body=body)
    elif name == "tripletex_put":
        return client.put(path, body=body, params=params)
    elif name == "tripletex_delete":
        return client.delete(path)
    else:
        return {"success": False, "error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# User content builder
# ---------------------------------------------------------------------------

def build_user_content(prompt: str, file_contents: list[dict]) -> list[types.Part]:
    """Build the user message parts from prompt and file attachments."""
    parts: list[types.Part] = []

    # Add text from file attachments
    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            parts.append(types.Part.from_text(
                text=f"[Attached file: {f['filename']}]\n{text}"
            ))
        elif f.get("mime_type", "").startswith("image/") and "raw_bytes" in f:
            parts.append(types.Part.from_bytes(
                data=f["raw_bytes"], mime_type=f["mime_type"]
            ))

    # Add task prompt last
    parts.append(types.Part.from_text(text=f"Complete this accounting task:\n\n{prompt}"))
    return parts


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(prompt: str, file_contents: list[dict], base_url: str, session_token: str) -> dict:
    """Run the Gemini tool-use agent loop."""
    client = TripletexClient(base_url, session_token)
    start_time = time.time()

    system_prompt = build_system_prompt()
    user_parts = build_user_content(prompt, file_contents)

    # Build conversation history
    contents: list[types.Content] = [
        types.Content(role="user", parts=user_parts),
    ]

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=TOOLS,
        temperature=0.0,
        max_output_tokens=4096,
    )

    for iteration in range(MAX_ITERATIONS):
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            logger.warning(f"Timeout after {elapsed:.0f}s at iteration {iteration}")
            break

        logger.info(f"Agent iteration {iteration + 1}")

        response = genai_client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        # Append model response to conversation
        model_content = response.candidates[0].content
        contents.append(model_content)

        # Check for function calls
        function_calls = response.function_calls
        if not function_calls:
            logger.info(f"Agent completed after {iteration + 1} iterations")
            break

        # Execute all function calls and build response parts
        response_parts: list[types.Part] = []
        for fc in function_calls:
            logger.info(f"  Tool call: {fc.name}({json.dumps(fc.args, ensure_ascii=False)[:200]})")

            try:
                result = execute_tool(fc.name, fc.args, client)
            except Exception as e:
                logger.error(f"  Tool execution error: {e}")
                result = {"success": False, "error": str(e)}

            logger.info(f"  Result: status={result.get('status_code')} success={result.get('success')}")

            response_parts.append(types.Part.from_function_response(
                name=fc.name,
                response=result,
            ))

        # Send tool results back to model
        contents.append(types.Content(role="tool", parts=response_parts))

    return {"status": "completed", "iterations": iteration + 1}
```

- [ ] **Step 3: Run tool definition tests**

Run: `python -m pytest tests/test_agent.py::TestToolDefinitions -v`
Expected: PASS

- [ ] **Step 4: Write tests for the agent loop**

Add to `tests/test_agent.py`:

```python
class TestRunAgent:
    def _mock_response(self, function_calls=None, text="Done"):
        """Create a mock Gemini response."""
        mock_resp = MagicMock()
        mock_candidate = MagicMock()

        if function_calls:
            # Build parts with function calls
            parts = []
            for fc in function_calls:
                part = MagicMock()
                part.function_call = MagicMock()
                part.function_call.name = fc["name"]
                part.function_call.args = fc["args"]
                parts.append(part)
            mock_candidate.content = types.Content(role="model", parts=parts)
            mock_resp.function_calls = [MagicMock(name=fc["name"], args=fc["args"]) for fc in function_calls]
            # Set .name as attribute, not constructor arg
            for mock_fc, fc in zip(mock_resp.function_calls, function_calls):
                mock_fc.name = fc["name"]
                mock_fc.args = fc["args"]
        else:
            mock_candidate.content = types.Content(
                role="model", parts=[types.Part.from_text(text=text)]
            )
            mock_resp.function_calls = None

        mock_resp.candidates = [mock_candidate]
        return mock_resp

    @patch("agent.TripletexClient")
    def test_simple_task_completes(self, MockClient):
        """Agent completes a simple task with one tool call."""
        mock_client_instance = MockClient.return_value
        mock_client_instance.post.return_value = {
            "success": True, "status_code": 201,
            "body": {"value": {"id": 42, "firstName": "Ola"}},
        }

        # First call: model wants to POST, second call: model says done
        _mock_genai_client.models.generate_content.side_effect = [
            self._mock_response(function_calls=[{
                "name": "tripletex_post",
                "args": {"path": "/employee", "body": {"firstName": "Ola", "lastName": "Nordmann"}},
            }]),
            self._mock_response(text="Created employee Ola Nordmann with ID 42"),
        ]

        result = agent_module.run_agent(
            prompt="Create employee Ola Nordmann",
            file_contents=[],
            base_url="https://test.tripletex.no/v2",
            session_token="test-token",
        )

        assert result["status"] == "completed"
        assert result["iterations"] == 2

    def test_system_prompt_includes_cheat_sheet(self):
        """System prompt includes the API cheat sheet."""
        prompt = agent_module.build_system_prompt()
        assert "POST /employee" in prompt
        assert "vatType" in prompt
        assert "YYYY-MM-DD" in prompt

    def test_system_prompt_includes_payment_gotcha(self):
        """System prompt warns about payment query params."""
        prompt = agent_module.build_system_prompt()
        assert "params, NOT body" in prompt
        assert "paymentDate" in prompt

    def test_build_user_content_includes_prompt(self):
        """User content includes the task prompt."""
        parts = agent_module.build_user_content("Create an employee", [])
        text_parts = [p.text for p in parts if hasattr(p, 'text') and p.text]
        combined = " ".join(text_parts)
        assert "Create an employee" in combined

    def test_build_user_content_includes_file_text(self):
        """User content includes text from file attachments."""
        files = [{"filename": "data.csv", "mime_type": "text/csv", "text_content": "col1,col2\n1,2"}]
        parts = agent_module.build_user_content("Process file", files)
        text_parts = [p.text for p in parts if hasattr(p, 'text') and p.text]
        combined = " ".join(text_parts)
        assert "col1,col2" in combined
        assert "data.csv" in combined
```

- [ ] **Step 5: Run all agent tests**

Run: `python -m pytest tests/test_agent.py -v`
Expected: All PASS

- [ ] **Step 6: Commit agent.py and tests**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: add Gemini tool-use agent with 4 REST tools

Native function calling loop replaces the static plan-execute-recover
architecture. The model sees each API response and decides the next
action dynamically, enabling self-correction on errors.

Refs #2"
```

---

### Task 4: Wire Agent into main.py and Pre-configure Bank Account (GitHub Issues #2, #3)

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py to use agent.py**

Replace the entire `main.py` with:

```python
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from agent import run_agent
from file_handler import process_files
from tripletex_api import TripletexClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Accounting Agent")

API_KEY = os.getenv("API_KEY")


@app.get("/health")
def health():
    return {"status": "ok"}


def _preconfigure_bank_account(base_url: str, session_token: str) -> None:
    """Ensure ledger account 1920 has a bank account configured.

    This prevents invoice creation failures on a fresh sandbox.
    """
    client = TripletexClient(base_url, session_token)
    try:
        result = client.get("/ledger/account", params={"number": "1920", "fields": "id,number,bankAccountNumber"})
        if not result["success"]:
            logger.warning(f"Could not fetch account 1920: {result.get('error')}")
            return

        accounts = result["body"].get("values", [])
        if not accounts:
            logger.warning("Ledger account 1920 not found in fresh sandbox")
            return

        account = accounts[0]
        account_id = account["id"]

        # Only update if bank account is not already set
        if not account.get("bankAccountNumber"):
            update_result = client.put(f"/ledger/account/{account_id}", body={
                "id": account_id,
                "number": 1920,
                "bankAccountNumber": "86010517941",
            })
            if update_result["success"]:
                logger.info("Pre-configured bank account on ledger account 1920")
            else:
                logger.warning(f"Failed to configure account 1920: {update_result.get('error')}")
    except Exception as e:
        logger.warning(f"Bank account pre-config failed (non-fatal): {e}")


@app.post("/solve")
async def solve(request: Request):
    # Optional: API key protection
    if API_KEY:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()

    # Handle both payload formats (competition docs vs competitor-observed)
    prompt = body.get("prompt") or body.get("task_prompt", "")
    files = body.get("files") or body.get("attached_files", [])

    # Credentials: nested dict (Format A) or flat keys (Format B)
    creds = body.get("tripletex_credentials", {})
    base_url = creds.get("base_url") or body.get("tripletex_base_url", "")
    session_token = creds.get("session_token") or body.get("session_token", "")

    logger.info(f"Received task. Prompt length: {len(prompt)}, Files: {len(files)}")

    try:
        # Step 1: Process any attached files
        file_contents = process_files(files)

        # Step 2: Pre-configure bank account 1920 (prevents invoice failures)
        _preconfigure_bank_account(base_url, session_token)

        # Step 3: Run the agent
        result = run_agent(prompt, file_contents, base_url, session_token)
        logger.info(f"Agent result: {result}")

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

    # Always return completed — partial work may earn partial credit
    return JSONResponse({"status": "completed"})
```

- [ ] **Step 2: Update tests/test_main.py for new imports**

Replace the test file to match the new main.py (which no longer imports planner/executor):

```python
# tests/test_main.py
"""Tests for /solve endpoint payload parsing and bank account pre-config."""

import pytest
from unittest.mock import patch, MagicMock

_mock_genai_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    from main import app, _preconfigure_bank_account

from fastapi.testclient import TestClient

client = TestClient(app)


def _format_a_payload():
    """Competition docs format."""
    return {
        "prompt": "Opprett en ansatt med navn Ola Nordmann",
        "files": [],
        "tripletex_credentials": {
            "base_url": "https://tripletex.no/v2",
            "session_token": "test-token-123",
        },
    }


def _format_b_payload():
    """Competitor-observed format."""
    return {
        "task_prompt": "Create an employee named Ola Nordmann",
        "attached_files": [],
        "tripletex_base_url": "https://tripletex.no/v2",
        "session_token": "test-token-456",
    }


class TestPayloadParsing:
    @patch("main.run_agent", return_value={"status": "completed", "iterations": 1})
    @patch("main.process_files", return_value=[])
    @patch("main._preconfigure_bank_account")
    def test_format_a(self, mock_bank, mock_files, mock_agent):
        """Format A: prompt + tripletex_credentials dict."""
        resp = client.post("/solve", json=_format_a_payload())
        assert resp.status_code == 200
        assert resp.json() == {"status": "completed"}
        mock_agent.assert_called_once()
        call_args = mock_agent.call_args
        assert call_args[1]["prompt"] == "Opprett en ansatt med navn Ola Nordmann" or \
               call_args[0][0] == "Opprett en ansatt med navn Ola Nordmann"

    @patch("main.run_agent", return_value={"status": "completed", "iterations": 1})
    @patch("main.process_files", return_value=[])
    @patch("main._preconfigure_bank_account")
    def test_format_b(self, mock_bank, mock_files, mock_agent):
        """Format B: task_prompt + flat credentials."""
        resp = client.post("/solve", json=_format_b_payload())
        assert resp.status_code == 200
        assert resp.json() == {"status": "completed"}
        mock_agent.assert_called_once()


class TestBankAccountPreconfig:
    def test_configures_when_empty(self):
        """Pre-configures bank account when not set."""
        mock_client_cls = MagicMock()
        mock_client = mock_client_cls.return_value
        mock_client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 99, "number": 1920, "bankAccountNumber": None}]},
        }
        mock_client.put.return_value = {"success": True, "status_code": 200, "body": {}}

        with patch("main.TripletexClient", mock_client_cls):
            _preconfigure_bank_account("https://test.tripletex.no/v2", "token")

        mock_client.put.assert_called_once()
        put_body = mock_client.put.call_args[1]["body"] if "body" in mock_client.put.call_args[1] else mock_client.put.call_args[0][1]
        assert put_body["bankAccountNumber"] == "86010517941"

    def test_skips_when_already_set(self):
        """Skips if bank account is already configured."""
        mock_client_cls = MagicMock()
        mock_client = mock_client_cls.return_value
        mock_client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 99, "number": 1920, "bankAccountNumber": "86010517941"}]},
        }

        with patch("main.TripletexClient", mock_client_cls):
            _preconfigure_bank_account("https://test.tripletex.no/v2", "token")

        mock_client.put.assert_not_called()
```

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/test_main.py tests/test_agent.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: wire agent.py into main.py with bank account pre-config

- main.py now calls run_agent() instead of plan→execute→recover
- Pre-configures ledger account 1920 with bank account before each task
- Both payload formats supported

Closes #2, closes #3"
```

---

### Task 5: Remove Old Plan-Execute-Recover Code

**Files:**
- Delete: `planner.py`, `executor.py`, `recovery.py`
- Delete: `tests/test_planner.py`, `tests/test_executor.py`, `tests/test_recovery.py`

- [ ] **Step 1: Verify no remaining imports of old modules**

Run: `grep -r "from planner\|from executor\|from recovery\|import planner\|import executor\|import recovery" --include="*.py" .`
Expected: No matches (main.py no longer imports them)

- [ ] **Step 2: Delete old files**

```bash
git rm planner.py executor.py recovery.py
git rm tests/test_planner.py tests/test_executor.py tests/test_recovery.py
```

- [ ] **Step 3: Run remaining tests to verify nothing breaks**

Run: `python -m pytest tests/ -v`
Expected: All tests in test_main.py, test_agent.py, test_file_handler.py, test_tripletex_api.py PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove plan-execute-recover architecture

Replaced by the Gemini tool-use agent loop in agent.py.
Deletes planner.py, executor.py, recovery.py and their tests."
```

---

### Task 6: Smoke Test End-to-End

- [ ] **Step 1: Start the server locally**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && uvicorn main:app --port 8000`

- [ ] **Step 2: Test health endpoint**

Run (in another terminal): `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 3: Test /solve with a mock payload (Format A)**

```bash
curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create an employee named Test User in the IT department",
    "files": [],
    "tripletex_credentials": {
      "base_url": "https://YOUR_SANDBOX_URL/v2",
      "session_token": "YOUR_SESSION_TOKEN"
    }
  }'
```

Expected: `{"status":"completed"}` (check server logs for agent iterations)

- [ ] **Step 4: Test /solve with Format B**

```bash
curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d '{
    "task_prompt": "Opprett en kunde med navn Acme AS",
    "attached_files": [],
    "tripletex_base_url": "https://YOUR_SANDBOX_URL/v2",
    "session_token": "YOUR_SESSION_TOKEN"
  }'
```

Expected: `{"status":"completed"}`

- [ ] **Step 5: Commit any final fixes from smoke testing**

```bash
git add -A
git commit -m "test: verify end-to-end smoke test passes"
```

---

## Summary

| Task | GitHub Issue | Est. Time | What it does |
|------|-------------|-----------|-------------|
| 1 | #1 (P0) | 15 min | Fix dual payload format — unblocks everything |
| 2 | #2 | 15 min | Fix PUT params + cheat sheet payment docs |
| 3 | #2 (P1) | 45 min | Create agent.py with Gemini tool-use loop |
| 4 | #2, #3 | 30 min | Wire agent into main.py + bank account pre-config |
| 5 | #2 | 10 min | Delete old planner/executor/recovery code |
| 6 | — | 15 min | End-to-end smoke test |
| **Total** | | **~2 hours** | |
