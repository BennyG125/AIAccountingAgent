# AI Accounting Agent — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an AI agent that receives Norwegian accounting task prompts, uses Gemini 3.1 Pro to plan Tripletex API calls, executes them, and scores maximum points in the NM i AI competition.

**Architecture:** Hybrid Planner with Targeted Recovery. Gemini 3.1 Pro reads the prompt and outputs a structured JSON execution plan. A Python executor runs the plan step by step, threading entity IDs between steps. On failure, Gemini re-plans from the error context (max 2 recovery attempts). Always returns `{"status": "completed"}`.

**Tech Stack:** Python 3.11, FastAPI, Google Gen AI SDK (`google-genai`), Vertex AI (Gemini 3.1 Pro), Docker, Cloud Run (europe-north1)

---

## Task 1: Project Scaffold

**Files:**
- Create: `main.py`
- Create: `requirements.txt`
- Create: `Dockerfile`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `.dockerignore`

**Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
venv/
.venv/
*.egg-info/
dist/
build/
```

**Step 2: Create `.dockerignore`**

```dockerignore
__pycache__/
*.pyc
.env
venv/
.venv/
.git/
docs/
tests/
```

**Step 3: Create `requirements.txt`**

```
fastapi
uvicorn[standard]
requests
google-genai>=1.51.0
pymupdf
python-dotenv
```

**Step 4: Create `.env.example`**

```env
# GCP credentials (from gcplab.me account)
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=global

# Optional: protect your /solve endpoint
API_KEY=your-optional-api-key
```

**Step 5: Create `main.py`** (minimal `/solve` endpoint)

```python
import base64
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from planner import plan_task
from executor import execute_plan
from recovery import recover_and_execute
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


@app.post("/solve")
async def solve(request: Request):
    # Optional: API key protection
    if API_KEY:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()
    prompt = body["prompt"]
    files = body.get("files", [])
    creds = body["tripletex_credentials"]

    base_url = creds["base_url"]
    session_token = creds["session_token"]

    logger.info(f"Received task. Prompt length: {len(prompt)}, Files: {len(files)}")

    try:
        # Step 1: Process any attached files
        file_contents = process_files(files)

        # Step 2: Plan — Gemini analyzes prompt and returns execution plan
        client = TripletexClient(base_url, session_token)
        plan = plan_task(prompt, file_contents)

        logger.info(f"Plan generated with {len(plan['steps'])} steps")

        # Step 3: Execute the plan
        result = execute_plan(client, plan)

        if not result["success"]:
            # Step 4: Recovery — send error context back to Gemini
            logger.warning(f"Step {result['failed_step']} failed: {result['error']}")
            recover_and_execute(client, prompt, file_contents, plan, result)

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

    # Always return completed — partial work may earn partial credit
    return JSONResponse({"status": "completed"})
```

**Step 6: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 7: Run locally to verify scaffold**

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

Expected: Server starts (will fail on import since modules don't exist yet — that's fine, we create them next)

**Step 8: Commit**

```bash
git add .gitignore .dockerignore requirements.txt .env.example main.py Dockerfile
git commit -m "feat: project scaffold with FastAPI endpoint and Docker setup"
```

---

## Task 2: Tripletex API Client

**Files:**
- Create: `tripletex_api.py`
- Create: `tests/test_tripletex_api.py`

**Step 1: Write the failing test**

```python
# tests/test_tripletex_api.py
import json
from unittest.mock import patch, MagicMock
from tripletex_api import TripletexClient


def test_client_uses_basic_auth():
    """Client authenticates with username '0' and session token as password."""
    client = TripletexClient("https://example.com/v2", "test-token-123")
    assert client.auth == ("0", "test-token-123")


def test_client_get():
    """GET request includes auth and params."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"values": [{"id": 1}]}
        mock_get.return_value = mock_response

        result = client.get("/employee", params={"fields": "id,firstName"})

        mock_get.assert_called_once_with(
            "https://example.com/v2/employee",
            auth=("0", "token"),
            params={"fields": "id,firstName"},
        )
        assert result["status_code"] == 200
        assert result["body"]["values"] == [{"id": 1}]


def test_client_post():
    """POST request includes auth and JSON body."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"value": {"id": 42}}
        mock_post.return_value = mock_response

        result = client.post("/employee", body={"firstName": "Ola"})

        mock_post.assert_called_once_with(
            "https://example.com/v2/employee",
            auth=("0", "token"),
            json={"firstName": "Ola"},
        )
        assert result["status_code"] == 201
        assert result["body"]["value"]["id"] == 42


def test_client_put():
    """PUT request includes auth and JSON body."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.put") as mock_put:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": {"id": 42}}
        mock_put.return_value = mock_response

        result = client.put("/employee/42", body={"firstName": "Kari"})

        mock_put.assert_called_once_with(
            "https://example.com/v2/employee/42",
            auth=("0", "token"),
            json={"firstName": "Kari"},
        )
        assert result["status_code"] == 200


def test_client_delete():
    """DELETE request uses ID in URL path."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.delete") as mock_delete:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}
        mock_delete.return_value = mock_response

        result = client.delete("/travelExpense/99")

        mock_delete.assert_called_once_with(
            "https://example.com/v2/travelExpense/99",
            auth=("0", "token"),
        )
        assert result["status_code"] == 204


def test_client_handles_error_response():
    """Client returns error details without raising."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "status": 422,
            "message": "email is required",
        }
        mock_post.return_value = mock_response

        result = client.post("/employee", body={"firstName": "Ola"})

        assert result["status_code"] == 422
        assert result["success"] is False
        assert "email is required" in result["error"]
```

**Step 2: Run test to verify it fails**

```bash
cd "E:/Coding Projects/Personal/AIAccountingAgent"
python -m pytest tests/test_tripletex_api.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tripletex_api'`

**Step 3: Write implementation**

```python
# tripletex_api.py
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TripletexClient:
    """Thin wrapper around the Tripletex v2 REST API."""

    def __init__(self, base_url: str, session_token: str):
        self.base_url = base_url.rstrip("/")
        self.session_token = session_token
        self.auth = ("0", session_token)

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"GET {url} params={params}")
        resp = requests.get(url, auth=self.auth, params=params)
        return self._parse_response(resp)

    def post(self, endpoint: str, body: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"POST {url}")
        resp = requests.post(url, auth=self.auth, json=body)
        return self._parse_response(resp)

    def put(self, endpoint: str, body: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"PUT {url}")
        resp = requests.put(url, auth=self.auth, json=body)
        return self._parse_response(resp)

    def delete(self, endpoint: str) -> dict:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"DELETE {url}")
        resp = requests.delete(url, auth=self.auth)
        return self._parse_response(resp)

    def _parse_response(self, resp: requests.Response) -> dict:
        try:
            body = resp.json()
        except Exception:
            body = {}

        success = 200 <= resp.status_code < 300
        result = {
            "status_code": resp.status_code,
            "success": success,
            "body": body,
        }

        if not success:
            error_msg = body.get("message", str(body))
            result["error"] = error_msg
            logger.warning(f"API error {resp.status_code}: {error_msg}")

        return result
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_tripletex_api.py -v
```

Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add tripletex_api.py tests/test_tripletex_api.py
git commit -m "feat: Tripletex API client with Basic Auth and error handling"
```

---

## Task 3: File Handler

**Files:**
- Create: `file_handler.py`
- Create: `tests/test_file_handler.py`

**Step 1: Write the failing test**

```python
# tests/test_file_handler.py
import base64
from file_handler import process_files


def test_process_empty_files():
    """No files returns empty list."""
    result = process_files([])
    assert result == []


def test_process_text_file():
    """Base64-encoded text file is decoded."""
    content = base64.b64encode(b"Hello world").decode()
    files = [
        {
            "filename": "test.txt",
            "content_base64": content,
            "mime_type": "text/plain",
        }
    ]
    result = process_files(files)
    assert len(result) == 1
    assert result[0]["filename"] == "test.txt"
    assert result[0]["text_content"] == "Hello world"


def test_process_image_file():
    """Image files are returned as raw bytes for multimodal input."""
    content = base64.b64encode(b"\x89PNG fake image data").decode()
    files = [
        {
            "filename": "receipt.png",
            "content_base64": content,
            "mime_type": "image/png",
        }
    ]
    result = process_files(files)
    assert len(result) == 1
    assert result[0]["filename"] == "receipt.png"
    assert result[0]["mime_type"] == "image/png"
    assert result[0]["raw_bytes"] == b"\x89PNG fake image data"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_file_handler.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# file_handler.py
import base64
import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_files(files: list[dict]) -> list[dict]:
    """Process attached files from the /solve request.

    PDFs are extracted to text via pymupdf.
    Images are kept as raw bytes for multimodal Gemini input.
    Text files are decoded to strings.
    """
    if not files:
        return []

    processed = []
    for f in files:
        filename = f["filename"]
        raw_bytes = base64.b64decode(f["content_base64"])
        mime_type = f.get("mime_type", "")

        logger.info(f"Processing file: {filename} ({mime_type}, {len(raw_bytes)} bytes)")

        entry = {
            "filename": filename,
            "mime_type": mime_type,
            "raw_bytes": raw_bytes,
        }

        if mime_type == "application/pdf":
            entry["text_content"] = _extract_pdf_text(raw_bytes)
        elif mime_type.startswith("image/"):
            # Keep raw bytes — Gemini handles images as multimodal input
            pass
        else:
            # Assume text-like content
            try:
                entry["text_content"] = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                entry["text_content"] = raw_bytes.decode("latin-1")

        processed.append(entry)

    return processed


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pymupdf."""
    try:
        import pymupdf

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_file_handler.py -v
```

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add file_handler.py tests/test_file_handler.py
git commit -m "feat: file handler for PDF, image, and text attachments"
```

---

## Task 4: API Knowledge Cheat Sheet

**Files:**
- Create: `api_knowledge/cheat_sheet.py`
- Create: `api_knowledge/__init__.py`

**Step 1: Create `api_knowledge/__init__.py`**

```python
# empty
```

**Step 2: Create `api_knowledge/cheat_sheet.py`**

This is the curated reference that Gemini sees in its system prompt. We will expand this as we explore the sandbox and discover exact field requirements.

```python
# api_knowledge/cheat_sheet.py

TRIPLETEX_API_CHEAT_SHEET = """
## Tripletex v2 API — Endpoint Reference

### Authentication
- Basic Auth: username = "0", password = session_token
- All requests go through the provided base_url (proxy)

### Important: Fresh Account
The Tripletex account starts EMPTY. If the task requires modifying or deleting an entity,
check if the prompt asks you to create it first. If not, query for any pre-seeded data.

### Response Format
- Single entity responses: {"value": {<entity>}}
- List responses: {"fullResultSize": N, "values": [{...}, ...]}
- POST returns the created entity with its assigned ID

### Endpoints

#### POST /employee
Create an employee.
Required: firstName (string), lastName (string)
Optional: email (string), phoneNumberMobile (string), isAdministrator (boolean),
          department (object: {id: int}), employments (array)
Returns: {value: {id, firstName, lastName, email, ...}}

#### PUT /employee/{id}
Update an employee. Send full object with changes.
Required: id (int), firstName, lastName

#### GET /employee
Search employees.
Params: firstName, lastName, email, fields, from, count
Returns: {values: [...]}

#### POST /customer
Create a customer.
Required: name (string)
Optional: email (string), phoneNumber (string), isCustomer (boolean, default true),
          isSupplier (boolean), organizationNumber (string), accountManager (object: {id: int})
Returns: {value: {id, name, email, ...}}

#### PUT /customer/{id}
Update a customer.

#### GET /customer
Search customers.
Params: name, email, isCustomer, fields, from, count

#### POST /product
Create a product.
Required: name (string)
Optional: number (string), priceExcludingVat (number), priceIncludingVat (number),
          vatType (object: {id: int}), productUnit (object: {id: int}),
          account (object: {id: int}), department (object: {id: int})
Returns: {value: {id, name, ...}}

#### GET /product
Search products.
Params: name, number, fields, from, count

#### POST /order
Create an order (required before creating an invoice).
Required: customer (object: {id: int}), deliveryDate (string: YYYY-MM-DD),
          orderDate (string: YYYY-MM-DD)
Optional: orderLines (array of {product: {id: int}, count: number, unitPriceExcludingVat: number}),
          receiver (string)
Returns: {value: {id, ...}}

#### GET /order
Search orders.

#### POST /invoice
Create an invoice from an order.
Required: invoiceDate (string: YYYY-MM-DD), invoiceDueDate (string: YYYY-MM-DD),
          orders (array of {id: int})
Optional: comment (string), customer (object: {id: int})
Returns: {value: {id, invoiceNumber, ...}}

#### GET /invoice
Search invoices.

#### POST /travelExpense
Create a travel expense report.
Required: employeeId (int), title (string), date (string: YYYY-MM-DD)
Optional: description (string), costs (array), project (object: {id: int})
Returns: {value: {id, ...}}

#### DELETE /travelExpense/{id}
Delete a travel expense report.

#### POST /project
Create a project.
Required: name (string), projectManager (object: {id: int})
Optional: customer (object: {id: int}), number (string), description (string),
          startDate (string: YYYY-MM-DD), endDate (string: YYYY-MM-DD)
Returns: {value: {id, name, ...}}

#### POST /department
Create a department.
Required: name (string), departmentNumber (int)
Optional: departmentManager (object: {id: int})
Returns: {value: {id, name, ...}}

#### GET /ledger/account
Query chart of accounts.
Params: number, from, count, fields

#### GET /ledger/posting
Query ledger postings.

#### GET /ledger/voucher
Query vouchers.

#### POST /ledger/voucher
Create a voucher (for journal entries, corrections).
Required: date (string: YYYY-MM-DD), description (string),
          postings (array of {account: {id: int}, amount: number, ...})

#### DELETE /ledger/voucher/{id}
Delete a voucher.

### API Tips
- Use ?fields=* to discover all available fields on any entity
- Use ?fields=id,name,email to select specific fields (faster)
- Pagination: ?from=0&count=100
- Norwegian characters (æ, ø, å) work fine — send as UTF-8
- Dates are always YYYY-MM-DD format
- All IDs are integers
"""
```

**Step 3: Commit**

```bash
git add api_knowledge/__init__.py api_knowledge/cheat_sheet.py
git commit -m "feat: curated Tripletex API cheat sheet for Gemini planning prompt"
```

---

## Task 5: Gemini Planner

**Files:**
- Create: `planner.py`
- Create: `tests/test_planner.py`

**Step 1: Write the failing test**

```python
# tests/test_planner.py
import json
from unittest.mock import patch, MagicMock
from planner import plan_task, build_planning_prompt


def test_build_planning_prompt_includes_cheat_sheet():
    """Planning prompt includes the API cheat sheet."""
    prompt = build_planning_prompt("Create employee Ola Nordmann", [])
    assert "Tripletex v2 API" in prompt
    assert "POST /employee" in prompt


def test_build_planning_prompt_includes_task():
    """Planning prompt includes the user's task."""
    prompt = build_planning_prompt("Opprett en ansatt med navn Ola", [])
    assert "Opprett en ansatt med navn Ola" in prompt


def test_build_planning_prompt_includes_file_content():
    """Planning prompt includes extracted file content."""
    files = [{"filename": "invoice.pdf", "text_content": "Invoice #123 for Acme AS"}]
    prompt = build_planning_prompt("Process this invoice", files)
    assert "Invoice #123 for Acme AS" in prompt


def test_plan_task_returns_structured_plan():
    """plan_task returns a dict with 'steps' array."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "reasoning": "Create an employee with the given details",
        "steps": [
            {
                "method": "POST",
                "endpoint": "/employee",
                "body": {"firstName": "Ola", "lastName": "Nordmann"},
                "capture": {"id": "employee_id"},
            }
        ],
    })

    with patch("planner.genai_client") as mock_client:
        mock_client.models.generate_content.return_value = mock_response
        result = plan_task("Create employee Ola Nordmann", [])

    assert "steps" in result
    assert len(result["steps"]) == 1
    assert result["steps"][0]["method"] == "POST"
    assert result["steps"][0]["endpoint"] == "/employee"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_planner.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# planner.py
import json
import logging
import os
from typing import Any

from google import genai
from google.genai import types

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET

logger = logging.getLogger(__name__)

# Initialize Gemini client for Vertex AI
genai_client = genai.Client(
    vertexai=True,
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "global"),
)

MODEL = "gemini-3.1-pro-preview"

SYSTEM_PROMPT = f"""You are an expert accounting agent. You receive a task prompt describing an accounting operation
in the Tripletex system. Your job is to produce a precise JSON execution plan.

{TRIPLETEX_API_CHEAT_SHEET}

## Rules
1. Output ONLY valid JSON — no markdown, no explanation, no code fences.
2. Each step is one API call with method, endpoint, and body.
3. Use "capture" to save IDs from responses for use in later steps.
4. Reference captured variables with {{variable_name}} in endpoints and body values.
5. The account starts EMPTY. Create prerequisite entities (customer, product, order) before
   entities that depend on them (invoice, payment).
6. Use the MINIMUM number of API calls needed. Do NOT add verification GETs.
7. Get it right on the first try — every error costs points.
8. Dates should use today's date (YYYY-MM-DD) unless the prompt specifies otherwise.

## Output Schema
{{
  "reasoning": "Brief explanation of what the task requires",
  "steps": [
    {{
      "method": "POST|PUT|GET|DELETE",
      "endpoint": "/endpoint/path",
      "body": {{}},
      "params": {{}},
      "capture": {{"variable_name": "json.path.to.value"}}
    }}
  ]
}}

The "body" field is only needed for POST/PUT. The "params" field is only needed for GET.
The "capture" field is optional — use it when a later step needs an ID from this step's response.
For capture, use "id" as the path to capture the entity ID from the standard response format.
"""


def build_planning_prompt(task_prompt: str, file_contents: list[dict]) -> str:
    """Build the full prompt sent to Gemini for planning."""
    parts = [SYSTEM_PROMPT, f"\n## Task\n{task_prompt}"]

    if file_contents:
        parts.append("\n## Attached Files")
        for f in file_contents:
            parts.append(f"\n### {f['filename']}")
            if "text_content" in f:
                parts.append(f["text_content"])

    return "\n".join(parts)


def plan_task(task_prompt: str, file_contents: list[dict]) -> dict:
    """Use Gemini to generate an execution plan for the accounting task."""
    text_prompt = build_planning_prompt(task_prompt, file_contents)

    # Build content parts — include images as multimodal input
    content_parts = [text_prompt]
    for f in file_contents:
        if f.get("mime_type", "").startswith("image/") and "raw_bytes" in f:
            content_parts.append(
                types.Part.from_bytes(data=f["raw_bytes"], mime_type=f["mime_type"])
            )

    logger.info(f"Sending planning request to {MODEL}")

    response = genai_client.models.generate_content(
        model=MODEL,
        contents=content_parts,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=4096,
        ),
    )

    raw_text = response.text.strip()
    logger.info(f"Gemini response: {raw_text[:200]}...")

    # Parse JSON — handle potential markdown code fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    plan = json.loads(raw_text)

    if "steps" not in plan:
        raise ValueError(f"Gemini returned plan without 'steps': {raw_text[:200]}")

    return plan
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_planner.py -v
```

Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add planner.py tests/test_planner.py
git commit -m "feat: Gemini 3.1 Pro planner with structured JSON output"
```

---

## Task 6: Plan Executor

**Files:**
- Create: `executor.py`
- Create: `tests/test_executor.py`

**Step 1: Write the failing test**

```python
# tests/test_executor.py
import json
from unittest.mock import MagicMock
from executor import execute_plan
from tripletex_api import TripletexClient


def _mock_client():
    return MagicMock(spec=TripletexClient)


def test_execute_single_post_step():
    """Executor runs a single POST step and captures ID."""
    client = _mock_client()
    client.post.return_value = {
        "status_code": 201,
        "success": True,
        "body": {"value": {"id": 42, "firstName": "Ola"}},
    }

    plan = {
        "steps": [
            {
                "method": "POST",
                "endpoint": "/employee",
                "body": {"firstName": "Ola", "lastName": "Nordmann"},
                "capture": {"employee_id": "id"},
            }
        ]
    }

    result = execute_plan(client, plan)
    assert result["success"] is True
    assert result["variables"]["employee_id"] == 42
    client.post.assert_called_once_with("/employee", body={"firstName": "Ola", "lastName": "Nordmann"})


def test_execute_variable_substitution():
    """Executor substitutes captured variables in later steps."""
    client = _mock_client()
    client.post.side_effect = [
        {"status_code": 201, "success": True, "body": {"value": {"id": 10}}},
        {"status_code": 201, "success": True, "body": {"value": {"id": 20}}},
    ]

    plan = {
        "steps": [
            {
                "method": "POST",
                "endpoint": "/customer",
                "body": {"name": "Acme AS"},
                "capture": {"customer_id": "id"},
            },
            {
                "method": "POST",
                "endpoint": "/order",
                "body": {"customer": {"id": "{customer_id}"}, "deliveryDate": "2026-03-19"},
            },
        ]
    }

    result = execute_plan(client, plan)
    assert result["success"] is True

    # Second call should have substituted {customer_id} with 10
    second_call_body = client.post.call_args_list[1][1]["body"]
    assert second_call_body["customer"]["id"] == 10


def test_execute_handles_failure():
    """Executor stops on first failure and reports error context."""
    client = _mock_client()
    client.post.return_value = {
        "status_code": 422,
        "success": False,
        "body": {"message": "email is required"},
        "error": "email is required",
    }

    plan = {
        "steps": [
            {
                "method": "POST",
                "endpoint": "/employee",
                "body": {"firstName": "Ola"},
            }
        ]
    }

    result = execute_plan(client, plan)
    assert result["success"] is False
    assert result["failed_step"] == 0
    assert "email is required" in result["error"]


def test_execute_get_step():
    """Executor handles GET steps with params."""
    client = _mock_client()
    client.get.return_value = {
        "status_code": 200,
        "success": True,
        "body": {"values": [{"id": 5, "name": "Test"}]},
    }

    plan = {
        "steps": [
            {
                "method": "GET",
                "endpoint": "/customer",
                "params": {"name": "Test", "fields": "id,name"},
                "capture": {"customer_id": "id"},
            }
        ]
    }

    result = execute_plan(client, plan)
    assert result["success"] is True
    assert result["variables"]["customer_id"] == 5


def test_execute_delete_step():
    """Executor handles DELETE steps."""
    client = _mock_client()
    client.delete.return_value = {
        "status_code": 204,
        "success": True,
        "body": {},
    }

    plan = {
        "steps": [
            {
                "method": "DELETE",
                "endpoint": "/travelExpense/99",
            }
        ]
    }

    result = execute_plan(client, plan)
    assert result["success"] is True
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_executor.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# executor.py
import copy
import logging
import re
from typing import Any

from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)


def execute_plan(client: TripletexClient, plan: dict) -> dict:
    """Execute a structured plan step by step.

    Returns:
        {
            "success": bool,
            "variables": dict of captured variables,
            "completed_steps": list of completed step indices,
            "results": list of API responses per step,
            "failed_step": int (if failed),
            "error": str (if failed),
        }
    """
    variables: dict[str, Any] = {}
    results: list[dict] = []
    completed_steps: list[int] = []

    for i, step in enumerate(plan["steps"]):
        method = step["method"].upper()
        endpoint = _substitute_vars(step["endpoint"], variables)
        body = _substitute_vars_deep(step.get("body"), variables)
        params = _substitute_vars_deep(step.get("params"), variables)

        logger.info(f"Step {i}: {method} {endpoint}")

        # Execute the API call
        if method == "GET":
            response = client.get(endpoint, params=params)
        elif method == "POST":
            response = client.post(endpoint, body=body)
        elif method == "PUT":
            response = client.put(endpoint, body=body)
        elif method == "DELETE":
            response = client.delete(endpoint)
        else:
            response = {"success": False, "error": f"Unknown method: {method}", "status_code": 0, "body": {}}

        results.append(response)

        if not response["success"]:
            logger.warning(f"Step {i} failed: {response.get('error')}")
            return {
                "success": False,
                "variables": variables,
                "completed_steps": completed_steps,
                "results": results,
                "failed_step": i,
                "error": response.get("error", f"HTTP {response['status_code']}"),
                "remaining_steps": plan["steps"][i:],
            }

        # Capture variables from response
        capture = step.get("capture", {})
        if capture:
            _capture_variables(capture, response["body"], variables)

        completed_steps.append(i)

    return {
        "success": True,
        "variables": variables,
        "completed_steps": completed_steps,
        "results": results,
    }


def _substitute_vars(text: str, variables: dict) -> str:
    """Replace {variable_name} placeholders in a string."""
    if not isinstance(text, str):
        return text

    def replacer(match):
        var_name = match.group(1)
        if var_name in variables:
            return str(variables[var_name])
        return match.group(0)

    return re.sub(r"\{(\w+)\}", replacer, text)


def _substitute_vars_deep(obj: Any, variables: dict) -> Any:
    """Recursively substitute variables in a nested structure."""
    if obj is None:
        return None
    if isinstance(obj, str):
        result = _substitute_vars(obj, variables)
        # If the entire string was a variable reference, return the actual value (not stringified)
        if isinstance(result, str) and result.isdigit():
            return int(result)
        return result
    if isinstance(obj, dict):
        return {k: _substitute_vars_deep(v, variables) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_vars_deep(item, variables) for item in obj]
    return obj


def _capture_variables(capture: dict, body: dict, variables: dict) -> None:
    """Extract values from API response body and store in variables."""
    for var_name, json_path in capture.items():
        try:
            # Handle standard Tripletex response formats
            if "value" in body:
                # Single entity: {"value": {"id": 42, ...}}
                value = body["value"].get(json_path)
            elif "values" in body and body["values"]:
                # List response: {"values": [{"id": 5, ...}, ...]}
                value = body["values"][0].get(json_path)
            else:
                value = body.get(json_path)

            if value is not None:
                variables[var_name] = value
                logger.info(f"Captured {var_name} = {value}")
            else:
                logger.warning(f"Could not capture {var_name} from path '{json_path}'")
        except Exception as e:
            logger.warning(f"Capture error for {var_name}: {e}")
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_executor.py -v
```

Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add executor.py tests/test_executor.py
git commit -m "feat: plan executor with variable substitution and capture"
```

---

## Task 7: Recovery Flow

**Files:**
- Create: `recovery.py`
- Create: `tests/test_recovery.py`

**Step 1: Write the failing test**

```python
# tests/test_recovery.py
import json
from unittest.mock import patch, MagicMock
from recovery import build_recovery_prompt, recover_and_execute


def test_build_recovery_prompt_includes_error():
    """Recovery prompt includes the error message and failed step."""
    prompt = build_recovery_prompt(
        task_prompt="Create employee",
        file_contents=[],
        original_plan={"steps": [{"method": "POST", "endpoint": "/employee", "body": {"firstName": "Ola"}}]},
        execution_result={
            "failed_step": 0,
            "error": "email is required",
            "completed_steps": [],
            "results": [{"status_code": 422, "body": {"message": "email is required"}}],
            "remaining_steps": [{"method": "POST", "endpoint": "/employee", "body": {"firstName": "Ola"}}],
            "variables": {},
        },
    )
    assert "email is required" in prompt
    assert "Create employee" in prompt


def test_build_recovery_prompt_includes_completed_context():
    """Recovery prompt includes what was already completed."""
    prompt = build_recovery_prompt(
        task_prompt="Create invoice",
        file_contents=[],
        original_plan={"steps": [
            {"method": "POST", "endpoint": "/customer", "body": {"name": "Acme"}, "capture": {"customer_id": "id"}},
            {"method": "POST", "endpoint": "/order", "body": {}},
        ]},
        execution_result={
            "failed_step": 1,
            "error": "deliveryDate is required",
            "completed_steps": [0],
            "results": [
                {"status_code": 201, "body": {"value": {"id": 10}}, "success": True},
                {"status_code": 422, "body": {"message": "deliveryDate is required"}, "success": False},
            ],
            "remaining_steps": [{"method": "POST", "endpoint": "/order", "body": {}}],
            "variables": {"customer_id": 10},
        },
    )
    assert "customer_id" in prompt
    assert "deliveryDate is required" in prompt
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_recovery.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# recovery.py
import json
import logging
from typing import Any

from google import genai
from google.genai import types

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET

logger = logging.getLogger(__name__)

MAX_RECOVERY_ATTEMPTS = 2


def build_recovery_prompt(
    task_prompt: str,
    file_contents: list[dict],
    original_plan: dict,
    execution_result: dict,
) -> str:
    """Build a prompt for Gemini to produce a corrected plan."""
    completed_info = ""
    if execution_result["completed_steps"]:
        completed_info = f"""
## Already Completed
The following steps succeeded (do NOT repeat these):
{json.dumps([original_plan["steps"][i] for i in execution_result["completed_steps"]], indent=2)}

Captured variables from completed steps: {json.dumps(execution_result["variables"])}
"""

    return f"""You are an expert accounting agent fixing a failed execution plan.

{TRIPLETEX_API_CHEAT_SHEET}

## Original Task
{task_prompt}

{completed_info}

## Failed Step
Step {execution_result["failed_step"]} failed with error: {execution_result["error"]}

The failed step was:
{json.dumps(execution_result["remaining_steps"][0], indent=2)}

Full error response: {json.dumps(execution_result["results"][-1].get("body", {}), indent=2)}

## Instructions
1. Produce a CORRECTED plan for the remaining work only.
2. Do NOT repeat already-completed steps.
3. Use the captured variables (e.g., customer_id = {execution_result["variables"]}) in your corrected steps.
4. Fix the specific error — do not change the overall approach unless necessary.
5. Output ONLY valid JSON with the same schema as before.
"""


def recover_and_execute(
    client: Any,
    task_prompt: str,
    file_contents: list[dict],
    original_plan: dict,
    execution_result: dict,
) -> dict:
    """Attempt to recover from a failed plan execution."""
    from planner import genai_client, MODEL
    from executor import execute_plan

    for attempt in range(1, MAX_RECOVERY_ATTEMPTS + 1):
        logger.info(f"Recovery attempt {attempt}/{MAX_RECOVERY_ATTEMPTS}")

        recovery_prompt = build_recovery_prompt(
            task_prompt, file_contents, original_plan, execution_result
        )

        response = genai_client.models.generate_content(
            model=MODEL,
            contents=[recovery_prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=4096,
            ),
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            corrected_plan = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Recovery returned invalid JSON: {e}")
            continue

        if "steps" not in corrected_plan:
            logger.error("Recovery plan missing 'steps'")
            continue

        logger.info(f"Recovery plan has {len(corrected_plan['steps'])} steps")

        # Execute the corrected plan, carrying over existing variables
        result = execute_plan(client, corrected_plan)

        if result["success"]:
            logger.info(f"Recovery succeeded on attempt {attempt}")
            return result

        # Update context for next recovery attempt
        execution_result = result
        original_plan = corrected_plan

    logger.warning("All recovery attempts exhausted")
    return execution_result
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_recovery.py -v
```

Expected: All 2 tests PASS

**Step 5: Commit**

```bash
git add recovery.py tests/test_recovery.py
git commit -m "feat: targeted recovery flow with max 2 re-planning attempts"
```

---

## Task 8: Create tests/__init__.py and Run Full Test Suite

**Files:**
- Create: `tests/__init__.py`

**Step 1: Create `tests/__init__.py`**

```python
# empty
```

**Step 2: Run full test suite**

```bash
cd "E:/Coding Projects/Personal/AIAccountingAgent"
python -m pytest tests/ -v
```

Expected: All tests PASS (16+ tests across 4 test files)

**Step 3: Commit**

```bash
git add tests/__init__.py
git commit -m "chore: add tests init and verify full test suite passes"
```

---

## Task 9: Local Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test that simulates a full /solve request**

```python
# tests/test_integration.py
"""
Integration test that simulates the full /solve flow with mocked Gemini.
Run with: python -m pytest tests/test_integration.py -v
"""
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_full_solve_flow():
    """Simulate a complete /solve request with mocked Gemini and Tripletex."""
    # Mock Gemini response
    gemini_plan = json.dumps({
        "reasoning": "Create employee with admin role",
        "steps": [
            {
                "method": "POST",
                "endpoint": "/employee",
                "body": {
                    "firstName": "Ola",
                    "lastName": "Nordmann",
                    "email": "ola@example.org",
                    "isAdministrator": True,
                },
                "capture": {"employee_id": "id"},
            }
        ],
    })

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = gemini_plan

    # Mock Tripletex API response
    mock_tripletex_response = MagicMock()
    mock_tripletex_response.status_code = 201
    mock_tripletex_response.json.return_value = {
        "value": {
            "id": 42,
            "firstName": "Ola",
            "lastName": "Nordmann",
            "email": "ola@example.org",
            "isAdministrator": True,
        }
    }

    with patch("planner.genai_client") as mock_genai, \
         patch("tripletex_api.requests") as mock_requests:

        mock_genai.models.generate_content.return_value = mock_gemini_response
        mock_requests.post.return_value = mock_tripletex_response

        from main import app
        client = TestClient(app)

        response = client.post("/solve", json={
            "prompt": "Opprett en ansatt med navn Ola Nordmann, ola@example.org. Han skal være kontoadministrator.",
            "files": [],
            "tripletex_credentials": {
                "base_url": "https://tx-proxy.ainm.no/v2",
                "session_token": "test-token",
            },
        })

        assert response.status_code == 200
        assert response.json() == {"status": "completed"}

        # Verify Gemini was called
        mock_genai.models.generate_content.assert_called_once()

        # Verify Tripletex API was called
        mock_requests.post.assert_called_once()


def test_solve_returns_completed_even_on_error():
    """Agent returns completed even when things fail — partial credit."""
    with patch("planner.genai_client") as mock_genai:
        mock_genai.models.generate_content.side_effect = Exception("Gemini timeout")

        from main import app
        client = TestClient(app)

        response = client.post("/solve", json={
            "prompt": "Some task",
            "files": [],
            "tripletex_credentials": {
                "base_url": "https://example.com/v2",
                "session_token": "token",
            },
        })

        # Must still return completed
        assert response.status_code == 200
        assert response.json() == {"status": "completed"}
```

**Step 2: Run integration test**

```bash
python -m pytest tests/test_integration.py -v
```

Expected: All 2 tests PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration test simulating full /solve flow"
```

---

## Task 10: Deploy to Cloud Run

**Step 1: Set up .env with real GCP credentials**

Copy `.env.example` to `.env` and fill in:
- `GCP_PROJECT_ID` from the GCP console (the assigned project)
- `GCP_LOCATION=global` (required for Gemini 3.1 Pro)

**Step 2: Authenticate with GCP**

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

**Step 3: Deploy to Cloud Run**

```bash
cd "E:/Coding Projects/Personal/AIAccountingAgent"
gcloud run deploy ai-accounting-agent \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --min-instances 1
```

Expected: Produces URL like `https://ai-accounting-agent-xxxxx-lz.a.run.app`

**Step 4: Test the deployed endpoint**

```bash
curl -X POST https://YOUR-URL/solve \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "files": [], "tripletex_credentials": {"base_url": "https://example.com/v2", "session_token": "test"}}'
```

Expected: `{"status": "completed"}`

**Step 5: Test health endpoint**

```bash
curl https://YOUR-URL/health
```

Expected: `{"status": "ok"}`

**Step 6: Submit endpoint URL**

Go to `https://app.ainm.no/submit/tripletex` and submit your Cloud Run URL.

---

## Task 11: Sandbox API Exploration (Manual)

This is a manual exploration task to refine the API cheat sheet.

**Step 1: Use the sandbox to test each endpoint**

Using the sandbox credentials from the competition platform, manually test:

```bash
# Test employee creation
curl -u "0:YOUR_SANDBOX_TOKEN" \
  -X POST "https://kkpqfuj-amager.tripletex.dev/v2/employee" \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Test", "lastName": "User", "email": "test@example.com"}'
```

**Step 2: Discover required fields with `?fields=*`**

```bash
curl -u "0:YOUR_SANDBOX_TOKEN" \
  "https://kkpqfuj-amager.tripletex.dev/v2/employee?fields=*&count=1"
```

**Step 3: Update `api_knowledge/cheat_sheet.py`**

Based on findings, update the cheat sheet with exact required/optional fields, valid values, and any gotchas discovered.

**Step 4: Commit updates**

```bash
git add api_knowledge/cheat_sheet.py
git commit -m "refine: update API cheat sheet with sandbox-verified field requirements"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | Scaffold | FastAPI + Docker + project structure |
| 2 | API Client | `TripletexClient` with Basic Auth |
| 3 | File Handler | PDF/image/text processing |
| 4 | Cheat Sheet | Curated API reference for Gemini |
| 5 | Planner | Gemini 3.1 Pro structured planning |
| 6 | Executor | Step-by-step plan execution with variable capture |
| 7 | Recovery | Targeted re-planning on failure (max 2 attempts) |
| 8 | Test Suite | Full unit test verification |
| 9 | Integration | End-to-end /solve simulation |
| 10 | Deploy | Cloud Run deployment + submission |
| 11 | Exploration | Sandbox API discovery → cheat sheet refinement |

**After Phase 1:** The agent handles Tier 1 tasks (simple CRUD). Future phases expand the cheat sheet and add handling for Tier 2/3 multi-step workflows.
