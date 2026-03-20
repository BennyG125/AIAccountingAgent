# Tripletex Tool-Use Agent — Implementation Plan v2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Gemini tool-use agent that solves accounting tasks via the Tripletex API, handling text/PDF/image attachments, with a local test harness for rapid iteration.

**Architecture:** Gemini 3.1 Pro Preview with native function calling. 4 REST tools (GET/POST/PUT/DELETE). The model sees each API response and decides the next action. File attachments are pre-processed: PDFs → text + page images, CSVs → parsed text, images → multimodal parts. A local test harness sends real payloads to `/solve` using sandbox credentials.

**Tech Stack:** google-genai SDK (Vertex AI), FastAPI, requests, pymupdf

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `main.py` | **Rewrite** | FastAPI endpoint, payload parsing, bank account pre-config |
| `agent.py` | **Create** | Gemini tool-use loop, system prompt, tool definitions |
| `file_handler.py` | **Rewrite** | PDF→text+images, CSV with Norwegian format, image passthrough |
| `tripletex_api.py` | **Modify** | Add `params` to `put()` for payment registration |
| `api_knowledge/cheat_sheet.py` | **Modify** | Fix payment docs (query params, not body) |
| `test_harness.py` | **Create** | Local testing script using sandbox credentials |
| `tests/test_file_handler.py` | **Rewrite** | Tests for new file processing |
| `tests/test_agent.py` | **Create** | Tests for agent loop (mocked Gemini) |
| `tests/test_main.py` | **Rewrite** | Tests for payload parsing + bank pre-config |
| `planner.py` | **Delete** | Replaced by agent.py |
| `executor.py` | **Delete** | Replaced by agent.py |
| `recovery.py` | **Delete** | Replaced by agent.py |
| `tests/test_planner.py` | **Delete** | No longer relevant |
| `tests/test_executor.py` | **Delete** | No longer relevant |
| `tests/test_recovery.py` | **Delete** | No longer relevant |

---

### Task 1: Fix tripletex_api.py and cheat sheet

**Files:**
- Modify: `tripletex_api.py:29-33`
- Modify: `api_knowledge/cheat_sheet.py:274-277`

- [ ] **Step 1: Add `params` to `TripletexClient.put()`**

In `tripletex_api.py`, replace the `put` method:

```python
def put(self, endpoint: str, body: dict | None = None, params: dict | None = None) -> dict:
    url = f"{self.base_url}{endpoint}"
    logger.info(f"PUT {url} params={params}")
    resp = requests.put(url, auth=self.auth, json=body, params=params)
    return self._parse_response(resp)
```

- [ ] **Step 2: Fix cheat sheet payment section**

In `api_knowledge/cheat_sheet.py`, replace lines 274-277:

```
### PUT /invoice/{id}/:payment
Register payment. Use QUERY PARAMETERS (not JSON body):
?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1
Do NOT put these fields in the request body — they MUST be query parameters.
```

- [ ] **Step 3: Run existing tests**

Run: `python -m pytest tests/test_tripletex_api.py -v`
Expected: PASS (new `params` kwarg defaults to None)

- [ ] **Step 4: Commit**

```bash
git add tripletex_api.py api_knowledge/cheat_sheet.py
git commit -m "fix: PUT params support + payment registration docs

TripletexClient.put() now forwards params to requests.put().
Cheat sheet corrected: payment uses query params, not body."
```

---

### Task 2: Rewrite file_handler.py with PDF→image fallback

**Files:**
- Rewrite: `file_handler.py`
- Rewrite: `tests/test_file_handler.py`

The competition sends PDFs and images as base64-encoded attachments. Scanned PDFs (receipts) have no extractable text — we need to convert their pages to images for Gemini's vision.

- [ ] **Step 1: Write tests for file processing**

```python
# tests/test_file_handler.py
"""Tests for file_handler.py — PDF, image, CSV, and text processing."""

import base64
import pytest
from file_handler import process_files


class TestProcessFiles:
    def test_empty_files(self):
        assert process_files([]) == []

    def test_text_file_utf8(self):
        content = "Hello, world"
        result = process_files([{
            "filename": "data.txt",
            "content_base64": base64.b64encode(content.encode()).decode(),
            "mime_type": "text/plain",
        }])
        assert len(result) == 1
        assert result[0]["text_content"] == content
        assert result[0]["images"] == []

    def test_csv_with_semicolons(self):
        """Norwegian CSV with semicolons and comma decimals."""
        csv = "Dato;Beskrivelse;Beløp\n15.03.2026;Faktura;1.500,00"
        result = process_files([{
            "filename": "bank.csv",
            "content_base64": base64.b64encode(csv.encode()).decode(),
            "mime_type": "text/csv",
        }])
        assert "Dato" in result[0]["text_content"]
        assert "1.500,00" in result[0]["text_content"]

    def test_image_passthrough(self):
        """Images are kept as raw bytes for multimodal input."""
        raw = b"FAKE_PNG_DATA"
        result = process_files([{
            "filename": "receipt.png",
            "content_base64": base64.b64encode(raw).decode(),
            "mime_type": "image/png",
        }])
        assert len(result) == 1
        assert result[0]["text_content"] == ""
        assert len(result[0]["images"]) == 1
        assert result[0]["images"][0]["data"] == raw
        assert result[0]["images"][0]["mime_type"] == "image/png"

    def test_pdf_text_extraction(self):
        """PDF with extractable text returns text_content."""
        # Create a minimal valid PDF with text
        try:
            import pymupdf
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((50, 50), "Invoice #123\nAmount: 5000 NOK")
            pdf_bytes = doc.tobytes()
            doc.close()
        except ImportError:
            pytest.skip("pymupdf not installed")

        result = process_files([{
            "filename": "invoice.pdf",
            "content_base64": base64.b64encode(pdf_bytes).decode(),
            "mime_type": "application/pdf",
        }])
        assert "Invoice #123" in result[0]["text_content"]

    def test_pdf_always_includes_page_images(self):
        """PDF pages are always converted to images (for vision fallback)."""
        try:
            import pymupdf
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((50, 50), "Some text")
            pdf_bytes = doc.tobytes()
            doc.close()
        except ImportError:
            pytest.skip("pymupdf not installed")

        result = process_files([{
            "filename": "doc.pdf",
            "content_base64": base64.b64encode(pdf_bytes).decode(),
            "mime_type": "application/pdf",
        }])
        assert len(result[0]["images"]) >= 1
        assert result[0]["images"][0]["mime_type"] == "image/png"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_file_handler.py -v`
Expected: FAIL (old file_handler doesn't return `images` key)

- [ ] **Step 3: Rewrite file_handler.py**

```python
# file_handler.py
"""Process file attachments from /solve requests.

Output format per file:
  {
    "filename": str,
    "mime_type": str,
    "text_content": str,        # extracted text (may be empty)
    "images": [                  # images for multimodal input
      {"data": bytes, "mime_type": str}
    ]
  }

PDFs: extract text + render pages as PNG images (for scanned docs).
Images: passthrough as multimodal parts.
CSV/Text: decode to string.
"""

import base64
import logging

logger = logging.getLogger(__name__)

PDF_DPI = 150  # resolution for PDF→image conversion


def process_files(files: list[dict]) -> list[dict]:
    if not files:
        return []

    processed = []
    for f in files:
        filename = f.get("filename", "unknown")
        raw_bytes = base64.b64decode(f["content_base64"])
        mime_type = f.get("mime_type", "")

        logger.info(f"Processing: {filename} ({mime_type}, {len(raw_bytes)} bytes)")

        entry = {
            "filename": filename,
            "mime_type": mime_type,
            "text_content": "",
            "images": [],
        }

        if mime_type == "application/pdf":
            entry["text_content"] = _extract_pdf_text(raw_bytes)
            entry["images"] = _pdf_to_images(raw_bytes)
        elif mime_type.startswith("image/"):
            entry["images"] = [{"data": raw_bytes, "mime_type": mime_type}]
        else:
            # Text/CSV/other — decode to string
            entry["text_content"] = _decode_text(raw_bytes)

        processed.append(entry)

    return processed


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        parts = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(parts).strip()
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return ""


def _pdf_to_images(pdf_bytes: bytes) -> list[dict]:
    """Convert each PDF page to a PNG image for Gemini vision."""
    images = []
    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(dpi=PDF_DPI)
            images.append({
                "data": pix.tobytes("png"),
                "mime_type": "image/png",
            })
        doc.close()
    except Exception as e:
        logger.error(f"PDF→image conversion failed: {e}")
    return images


def _decode_text(raw_bytes: bytes) -> str:
    """Decode text bytes, trying UTF-8 first then Latin-1."""
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_file_handler.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add file_handler.py tests/test_file_handler.py
git commit -m "feat: rewrite file_handler with PDF→image fallback

PDFs now produce both text (for text-based PDFs) and page images
(for scanned receipts/invoices). Gemini vision handles the images.
CSV/text decoded with UTF-8/Latin-1 fallback."
```

---

### Task 3: Create agent.py with Gemini tool-use loop

**Files:**
- Create: `agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write agent.py**

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
        description="POST request to create entities. ALWAYS include body with the JSON payload.",
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
                    "For payment registration, use params for query parameters, NOT body.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/invoice/123/:payment'"},
                "body": {"type": "object", "description": "JSON body (optional for action endpoints)"},
                "params": {"type": "object", "description": "Query params — use for payment registration"},
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
7. For payment registration: PUT /invoice/{{id}}/:payment with QUERY PARAMS (paymentDate, paymentTypeId, paidAmount, paidAmountCurrency), NOT a JSON body.
8. Dates are always YYYY-MM-DD for the API.
9. Object references are always {{"id": <int>}}, never bare ints.
10. departmentNumber is a STRING, not an int.
11. On error: read the error message, fix the issue, retry ONCE. Never retry more than once.
12. When done, stop calling tools. Do not add verification GETs after successful creates.
13. If file attachments are provided, analyze them to extract relevant data (amounts, dates, names, line items) for use in API calls.

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
    """Build the user message parts from prompt and processed file attachments.

    Each file in file_contents has: filename, mime_type, text_content, images[].
    - text_content is included as text (PDF extracted text, CSV, plain text)
    - images are included as multimodal parts (PDF page images, photo attachments)
    """
    parts: list[types.Part] = []

    for f in file_contents:
        # Add text content
        text = f.get("text_content", "").strip()
        if text:
            parts.append(types.Part.from_text(
                text=f"[Attached file: {f['filename']}]\n{text}"
            ))

        # Add images (PDF pages, photo attachments)
        for img in f.get("images", []):
            parts.append(types.Part.from_bytes(
                data=img["data"], mime_type=img["mime_type"]
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

    contents: list[types.Content] = [
        types.Content(role="user", parts=user_parts),
    ]

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=TOOLS,
        temperature=0.0,
        max_output_tokens=4096,
    )

    iteration = 0
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
            logger.info(f"  Tool: {fc.name}({json.dumps(fc.args, ensure_ascii=False)[:200]})")

            try:
                result = execute_tool(fc.name, fc.args, client)
            except Exception as e:
                logger.error(f"  Tool error: {e}")
                result = {"success": False, "error": str(e)}

            logger.info(f"  → {result.get('status_code')} success={result.get('success')}")

            response_parts.append(types.Part.from_function_response(
                name=fc.name,
                response=result,
            ))

        contents.append(types.Content(role="tool", parts=response_parts))

    return {"status": "completed", "iterations": iteration + 1}
```

- [ ] **Step 2: Write tests for agent.py**

```python
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
        assert "path" in post.parameters.get("required", [])
        assert "body" in post.parameters.get("required", [])

    def test_put_has_params(self):
        put = next(fd for fd in agent_module.FUNCTION_DECLARATIONS if fd.name == "tripletex_put")
        assert "params" in put.parameters.get("properties", {})


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
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_agent.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: Gemini tool-use agent with 4 REST tools + file handling

Native function calling loop. Model sees each API response and decides
next action. Handles text, image, and PDF attachments (text + page images).

Refs #2"
```

---

### Task 4: Rewrite main.py

**Files:**
- Rewrite: `main.py`
- Rewrite: `tests/test_main.py`

- [ ] **Step 1: Write new main.py**

```python
# main.py
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
    """Ensure ledger account 1920 has a bank account configured."""
    client = TripletexClient(base_url, session_token)
    try:
        result = client.get("/ledger/account", params={"number": "1920", "fields": "id,number,bankAccountNumber"})
        if not result["success"]:
            return

        accounts = result["body"].get("values", [])
        if not accounts:
            return

        account = accounts[0]
        if not account.get("bankAccountNumber"):
            client.put(f"/ledger/account/{account['id']}", body={
                "id": account["id"],
                "number": 1920,
                "bankAccountNumber": "86010517941",
            })
            logger.info("Pre-configured bank account on ledger 1920")
    except Exception as e:
        logger.warning(f"Bank pre-config failed (non-fatal): {e}")


@app.post("/solve")
async def solve(request: Request):
    if API_KEY:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()

    # Handle both payload formats (official + competitor-observed)
    prompt = body.get("prompt") or body.get("task_prompt", "")
    files = body.get("files") or body.get("attached_files", [])
    creds = body.get("tripletex_credentials", {})
    base_url = creds.get("base_url") or body.get("tripletex_base_url", "")
    session_token = creds.get("session_token") or body.get("session_token", "")

    logger.info(f"Task received. Prompt: {len(prompt)} chars, Files: {len(files)}")

    try:
        file_contents = process_files(files)
        _preconfigure_bank_account(base_url, session_token)
        result = run_agent(prompt, file_contents, base_url, session_token)
        logger.info(f"Agent: {result}")
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

    return JSONResponse({"status": "completed"})
```

- [ ] **Step 2: Write tests**

```python
# tests/test_main.py
"""Tests for /solve payload parsing and bank account pre-config."""

from unittest.mock import patch, MagicMock

_mock_genai = MagicMock()
with patch("google.genai.Client", return_value=_mock_genai):
    from main import app, _preconfigure_bank_account

from fastapi.testclient import TestClient

client = TestClient(app)

PAYLOAD_A = {
    "prompt": "Opprett ansatt Ola Nordmann",
    "files": [],
    "tripletex_credentials": {"base_url": "https://t.dev/v2", "session_token": "tok-a"},
}

PAYLOAD_B = {
    "task_prompt": "Create employee Ola Nordmann",
    "attached_files": [],
    "tripletex_base_url": "https://t.dev/v2",
    "session_token": "tok-b",
}


class TestPayloadParsing:
    @patch("main.run_agent", return_value={"status": "completed"})
    @patch("main.process_files", return_value=[])
    @patch("main._preconfigure_bank_account")
    def test_format_a(self, *_):
        assert client.post("/solve", json=PAYLOAD_A).status_code == 200

    @patch("main.run_agent", return_value={"status": "completed"})
    @patch("main.process_files", return_value=[])
    @patch("main._preconfigure_bank_account")
    def test_format_b(self, *_):
        assert client.post("/solve", json=PAYLOAD_B).status_code == 200


class TestBankPreconfig:
    def test_configures_when_empty(self):
        mock_cls = MagicMock()
        mock_cls.return_value.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 99, "number": 1920, "bankAccountNumber": None}]},
        }
        mock_cls.return_value.put.return_value = {"success": True, "status_code": 200, "body": {}}
        with patch("main.TripletexClient", mock_cls):
            _preconfigure_bank_account("https://t.dev/v2", "tok")
        mock_cls.return_value.put.assert_called_once()

    def test_skips_when_set(self):
        mock_cls = MagicMock()
        mock_cls.return_value.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 99, "number": 1920, "bankAccountNumber": "86010517941"}]},
        }
        with patch("main.TripletexClient", mock_cls):
            _preconfigure_bank_account("https://t.dev/v2", "tok")
        mock_cls.return_value.put.assert_not_called()
```

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/test_main.py tests/test_agent.py tests/test_file_handler.py tests/test_tripletex_api.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: rewrite main.py with agent, dual payload, bank pre-config

Closes #1, closes #2, closes #3"
```

---

### Task 5: Delete old plan-execute-recover code

**Files:**
- Delete: `planner.py`, `executor.py`, `recovery.py`
- Delete: `tests/test_planner.py`, `tests/test_executor.py`, `tests/test_recovery.py`

- [ ] **Step 1: Verify no imports remain**

Run: `grep -rn "from planner\|from executor\|from recovery" --include="*.py" .`
Expected: No matches

- [ ] **Step 2: Delete files**

```bash
git rm planner.py executor.py recovery.py
git rm tests/test_planner.py tests/test_executor.py tests/test_recovery.py
```

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove plan-execute-recover architecture

Replaced by Gemini tool-use agent loop in agent.py."
```

---

### Task 6: Create local test harness

**Files:**
- Create: `test_harness.py`

This script sends real task payloads to your local `/solve` endpoint using your sandbox credentials. It mimics what the competition platform does.

- [ ] **Step 1: Create test_harness.py**

```python
#!/usr/bin/env python3
"""Local test harness — sends task payloads to /solve using sandbox credentials.

Usage:
  # Start server first: uvicorn main:app --port 8000
  python test_harness.py "Opprett en ansatt med navn Ola Nordmann"
  python test_harness.py --file receipt.pdf "Registrer denne fakturaen"
  python test_harness.py --list  # show sample tasks
"""

import argparse
import base64
import json
import mimetypes
import sys
import time
from pathlib import Path

import requests

# --- Configuration (edit these or set via environment) ---
SOLVE_URL = "http://localhost:8000/solve"
SANDBOX_BASE_URL = "https://kkpqfuj-amager.tripletex.dev/v2"
SANDBOX_TOKEN = ""  # Set via TRIPLETEX_SESSION_TOKEN env var or --token flag

SAMPLE_TASKS = {
    "employee-simple": "Opprett en ansatt med navn Ola Nordmann i IT-avdelingen",
    "employee-en": "Create an employee named Jane Smith in the Sales department with email jane@example.com",
    "customer": "Opprett en kunde med navn Acme AS, epost post@acme.no",
    "product": "Lag et produkt med navn 'Konsulenttime' til 1500 kr eks mva",
    "invoice": "Lag en faktura til kunden Nordmann AS for 3 timer konsulentarbeid à 1500 kr",
    "department": "Opprett en avdeling med navn 'Utvikling' og avdelingsnummer '300'",
    "employee-de": "Erstellen Sie einen Mitarbeiter namens Hans Müller in der Buchhaltungsabteilung",
    "employee-es": "Crea un empleado llamado Carlos García en el departamento de Ventas",
}


def build_payload(prompt: str, file_paths: list[str], token: str) -> dict:
    """Build the competition-format payload."""
    files = []
    for path_str in file_paths:
        path = Path(path_str)
        if not path.exists():
            print(f"WARNING: File not found: {path}")
            continue
        mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        files.append({
            "filename": path.name,
            "content_base64": base64.b64encode(path.read_bytes()).decode(),
            "mime_type": mime_type,
        })

    return {
        "prompt": prompt,
        "files": files,
        "tripletex_credentials": {
            "base_url": SANDBOX_BASE_URL,
            "session_token": token,
        },
    }


def main():
    import os
    parser = argparse.ArgumentParser(description="Test harness for Tripletex agent")
    parser.add_argument("prompt", nargs="?", help="Task prompt to send")
    parser.add_argument("--file", action="append", default=[], help="Attach file(s)")
    parser.add_argument("--token", default=os.getenv("TRIPLETEX_SESSION_TOKEN", SANDBOX_TOKEN))
    parser.add_argument("--url", default=SOLVE_URL, help="Solve endpoint URL")
    parser.add_argument("--list", action="store_true", help="List sample tasks")
    parser.add_argument("--sample", help="Run a sample task by name")
    args = parser.parse_args()

    if args.list:
        print("Sample tasks:")
        for name, prompt in SAMPLE_TASKS.items():
            print(f"  {name:20s} → {prompt}")
        return

    if args.sample:
        if args.sample not in SAMPLE_TASKS:
            print(f"Unknown sample: {args.sample}. Use --list to see options.")
            return
        prompt = SAMPLE_TASKS[args.sample]
    elif args.prompt:
        prompt = args.prompt
    else:
        parser.print_help()
        return

    if not args.token:
        print("ERROR: No session token. Set TRIPLETEX_SESSION_TOKEN or use --token")
        sys.exit(1)

    payload = build_payload(prompt, args.file, args.token)

    print(f"Sending to {args.url}")
    print(f"  Prompt: {prompt}")
    print(f"  Files: {len(payload['files'])}")
    print()

    start = time.time()
    try:
        resp = requests.post(args.url, json=payload, timeout=310)
        elapsed = time.time() - start
        print(f"Response: {resp.status_code} in {elapsed:.1f}s")
        print(f"  Body: {resp.json()}")
    except requests.Timeout:
        print(f"TIMEOUT after {time.time() - start:.1f}s")
    except requests.ConnectionError:
        print("ERROR: Cannot connect. Is the server running? (uvicorn main:app --port 8000)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add test_harness.py
git commit -m "feat: add local test harness for sandbox testing

Sends real task payloads to /solve using sandbox credentials.
Supports file attachments and sample tasks in multiple languages."
```

---

### Task 7: Smoke test against real sandbox

- [ ] **Step 1: Start server**

```bash
cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent
export GCP_PROJECT_ID=ai-nm26osl-1799
export TRIPLETEX_SESSION_TOKEN=<your-token>
uvicorn main:app --port 8000
```

- [ ] **Step 2: Test simple employee creation**

```bash
python test_harness.py --sample employee-simple --token $TRIPLETEX_SESSION_TOKEN
```

Expected: `{"status":"completed"}`, server logs show agent iterations and successful POST to /employee

- [ ] **Step 3: Test multilingual task**

```bash
python test_harness.py --sample employee-de --token $TRIPLETEX_SESSION_TOKEN
```

Expected: Agent handles German prompt correctly

- [ ] **Step 4: Test customer creation**

```bash
python test_harness.py --sample customer --token $TRIPLETEX_SESSION_TOKEN
```

- [ ] **Step 5: Verify in Tripletex UI**

Open `https://kkpqfuj-amager.tripletex.dev` and check that the created entities exist.

- [ ] **Step 6: Commit any fixes**

```bash
git add -A
git commit -m "test: smoke test against sandbox verified"
```

---

## Summary

| Task | GitHub Issue | Est. Time | What it does |
|------|-------------|-----------|-------------|
| 1 | #2 | 10 min | Fix PUT params + cheat sheet payment docs |
| 2 | #2 | 20 min | Rewrite file_handler: PDF→text+images, CSV, image passthrough |
| 3 | #2 | 45 min | Create agent.py: Gemini tool-use loop + 4 REST tools |
| 4 | #1, #2, #3 | 20 min | Rewrite main.py: dual payload + bank pre-config + agent |
| 5 | #2 | 5 min | Delete old planner/executor/recovery |
| 6 | — | 15 min | Local test harness with sandbox credentials |
| 7 | — | 20 min | Smoke test against real Tripletex sandbox |
| **Total** | | **~2.5 hours** | |
