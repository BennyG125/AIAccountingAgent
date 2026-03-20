# AI Accounting Agent V2 — Competition-Winning Implementation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a competition-winning AI agent that uses Gemini function calling in an agentic loop to autonomously complete all 30 Tripletex accounting task types, maximizing correctness, efficiency, and score across the NM i AI competition.

**Architecture:** Agentic Tool-Use Loop. Instead of generating a static JSON plan and executing it linearly (V1 approach), the agent gives Gemini a single `tripletex_api` tool and lets it call the API iteratively — observing each result before deciding the next action. This naturally handles errors (Gemini sees the 422 message and fixes its next call), multi-step workflows (create customer → use ID in order → use order in invoice), and conditional logic (check if entity exists before creating). Timeout management ensures we never exceed the 5-minute limit.

**Tech Stack:** Python 3.11, FastAPI, Google Gen AI SDK (`google-genai`), Vertex AI (Gemini), Docker, Cloud Run (europe-north1)

**Why V2 over V1 (plan-then-execute)?**
- V1 generates a full JSON plan upfront, then executes linearly. If step 3 of 5 fails, it needs expensive re-planning.
- V2 lets Gemini observe each API response before deciding the next action. Errors are handled in-line, not via separate recovery flow.
- V2 eliminates brittle JSON plan parsing, variable substitution bugs, and the entire recovery module.
- V2 naturally supports Tier 2/3 tasks that require runtime decisions based on API responses.

---

## Task 1: Enhance TripletexClient with Metrics and Timeouts

The competition scores efficiency (fewer API calls = higher bonus) and penalizes errors (4xx responses). We need to track both. We also need request timeouts to avoid hanging on slow API calls.

**Files:**
- Modify: `tripletex_api.py`
- Modify: `tests/test_tripletex_api.py`

**Step 1: Write the failing tests**

Add these three tests to the end of `tests/test_tripletex_api.py`:

```python
def test_client_tracks_call_count():
    """Client counts total API calls made."""
    client = TripletexClient("https://example.com/v2", "token")
    assert client.call_count == 0
    with patch("tripletex_api.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"values": []}
        mock_get.return_value = mock_response
        client.get("/employee")
        client.get("/customer")
    assert client.call_count == 2


def test_client_tracks_error_count():
    """Client counts 4xx/5xx errors separately."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"message": "validation error"}
        mock_post.return_value = mock_response
        client.post("/employee", body={})
    assert client.error_count == 1
    assert client.call_count == 1


def test_client_uses_timeout():
    """Client passes timeout to every request."""
    client = TripletexClient("https://example.com/v2", "token", timeout=15)
    with patch("tripletex_api.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"values": []}
        mock_get.return_value = mock_response
        client.get("/employee")
        mock_get.assert_called_once_with(
            "https://example.com/v2/employee",
            auth=("0", "token"),
            params=None,
            timeout=15,
        )
```

**Step 2: Run tests to verify the new ones fail**

```bash
cd "E:/Coding Projects/Personal/AIAccountingAgent"
python -m pytest tests/test_tripletex_api.py -v
```

Expected: 3 new tests FAIL (call_count, error_count, timeout attributes don't exist). 6 existing tests may also fail because `timeout` is now passed to requests but not expected in assertions.

**Step 3: Replace `tripletex_api.py` with updated implementation**

```python
# tripletex_api.py
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TripletexClient:
    """Thin wrapper around the Tripletex v2 REST API with metrics tracking."""

    def __init__(self, base_url: str, session_token: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.session_token = session_token
        self.auth = ("0", session_token)
        self.timeout = timeout
        self.call_count = 0
        self.error_count = 0

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        self.call_count += 1
        logger.info(f"GET {url} params={params}")
        resp = requests.get(url, auth=self.auth, params=params, timeout=self.timeout)
        return self._parse_response(resp)

    def post(self, endpoint: str, body: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        self.call_count += 1
        logger.info(f"POST {url}")
        resp = requests.post(url, auth=self.auth, json=body, timeout=self.timeout)
        return self._parse_response(resp)

    def put(self, endpoint: str, body: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        self.call_count += 1
        logger.info(f"PUT {url}")
        resp = requests.put(url, auth=self.auth, json=body, timeout=self.timeout)
        return self._parse_response(resp)

    def delete(self, endpoint: str) -> dict:
        url = f"{self.base_url}{endpoint}"
        self.call_count += 1
        logger.info(f"DELETE {url}")
        resp = requests.delete(url, auth=self.auth, timeout=self.timeout)
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
            self.error_count += 1
            error_msg = body.get("message", str(body))
            result["error"] = error_msg
            logger.warning(f"API error {resp.status_code}: {error_msg}")

        return result
```

**Step 4: Update existing test assertions to include `timeout=30`**

The existing tests assert exact call args which now include `timeout`. Update each `assert_called_once_with` in the existing tests to add `timeout=30`:

- `test_client_get`: add `timeout=30` to `mock_get.assert_called_once_with(...)`
- `test_client_post`: add `timeout=30` to `mock_post.assert_called_once_with(...)`
- `test_client_put`: add `timeout=30` to `mock_put.assert_called_once_with(...)`
- `test_client_delete`: add `timeout=30` to `mock_delete.assert_called_once_with(...)`

Full updated `tests/test_tripletex_api.py`:

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
    """GET request includes auth, params, and timeout."""
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
            timeout=30,
        )
        assert result["status_code"] == 200
        assert result["body"]["values"] == [{"id": 1}]


def test_client_post():
    """POST request includes auth, JSON body, and timeout."""
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
            timeout=30,
        )
        assert result["status_code"] == 201
        assert result["body"]["value"]["id"] == 42


def test_client_put():
    """PUT request includes auth, JSON body, and timeout."""
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
            timeout=30,
        )
        assert result["status_code"] == 200


def test_client_delete():
    """DELETE request uses ID in URL path with timeout."""
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
            timeout=30,
        )
        assert result["status_code"] == 204


def test_client_handles_error_response():
    """Client returns error details without raising and increments error_count."""
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


def test_client_tracks_call_count():
    """Client counts total API calls made."""
    client = TripletexClient("https://example.com/v2", "token")
    assert client.call_count == 0
    with patch("tripletex_api.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"values": []}
        mock_get.return_value = mock_response
        client.get("/employee")
        client.get("/customer")
    assert client.call_count == 2


def test_client_tracks_error_count():
    """Client counts 4xx/5xx errors separately."""
    client = TripletexClient("https://example.com/v2", "token")
    with patch("tripletex_api.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"message": "validation error"}
        mock_post.return_value = mock_response
        client.post("/employee", body={})
    assert client.error_count == 1
    assert client.call_count == 1


def test_client_uses_timeout():
    """Client passes custom timeout to every request."""
    client = TripletexClient("https://example.com/v2", "token", timeout=15)
    with patch("tripletex_api.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"values": []}
        mock_get.return_value = mock_response
        client.get("/employee")
        mock_get.assert_called_once_with(
            "https://example.com/v2/employee",
            auth=("0", "token"),
            params=None,
            timeout=15,
        )
```

**Step 5: Run all tests to verify they pass**

```bash
python -m pytest tests/test_tripletex_api.py -v
```

Expected: All 9 tests PASS

---

## Task 2: Add CSV Support to File Handler

Tier 3 tasks include "bank reconciliation from CSV". The current file handler treats CSV as plain text. We need structured parsing so Gemini can reason about individual rows.

**Files:**
- Modify: `file_handler.py`
- Modify: `tests/test_file_handler.py`

**Step 1: Write the failing test**

Add to `tests/test_file_handler.py`:

```python
def test_process_csv_file():
    """CSV files are parsed into structured rows and also kept as text."""
    csv_content = "date,amount,description\n2026-01-15,1500.00,Office supplies\n2026-01-16,2300.50,Software license"
    content = base64.b64encode(csv_content.encode()).decode()
    files = [
        {
            "filename": "transactions.csv",
            "content_base64": content,
            "mime_type": "text/csv",
        }
    ]
    result = process_files(files)
    assert len(result) == 1
    assert result[0]["filename"] == "transactions.csv"
    assert result[0]["text_content"] == csv_content
    assert "structured_data" in result[0]
    assert len(result[0]["structured_data"]) == 2
    assert result[0]["structured_data"][0]["amount"] == "1500.00"
    assert result[0]["structured_data"][1]["description"] == "Software license"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_file_handler.py::test_process_csv_file -v
```

Expected: FAIL — `structured_data` key not in result

**Step 3: Update `file_handler.py`**

Replace the full file:

```python
# file_handler.py
import base64
import csv
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_files(files: list[dict]) -> list[dict]:
    """Process attached files from the /solve request.

    PDFs are extracted to text via pymupdf.
    Images are kept as raw bytes for multimodal Gemini input.
    CSV files are parsed into structured rows.
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
        elif mime_type == "text/csv" or filename.endswith(".csv"):
            text = _decode_text(raw_bytes)
            entry["text_content"] = text
            entry["structured_data"] = _parse_csv(text)
        else:
            # Assume text-like content
            entry["text_content"] = _decode_text(raw_bytes)

        processed.append(entry)

    return processed


def _decode_text(raw_bytes: bytes) -> str:
    """Decode bytes to string, trying UTF-8 first then Latin-1."""
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


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


def _parse_csv(text: str) -> list[dict]:
    """Parse CSV text into a list of row dicts."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception as e:
        logger.error(f"CSV parsing failed: {e}")
        return []
```

**Step 4: Run all file handler tests**

```bash
python -m pytest tests/test_file_handler.py -v
```

Expected: All 4 tests PASS

---

## Task 3: Create API Knowledge Cheat Sheet

This is the most score-critical piece. The cheat sheet is injected into Gemini's system prompt and determines whether the agent makes correct API calls on the first try. Every field listed here saves a potential 422 error.

**Files:**
- Create: `api_knowledge/__init__.py`
- Create: `api_knowledge/cheat_sheet.py`

**Step 1: Create `api_knowledge/__init__.py`**

```python
# empty
```

**Step 2: Create `api_knowledge/cheat_sheet.py`**

```python
# api_knowledge/cheat_sheet.py

TRIPLETEX_API_CHEAT_SHEET = """
## Tripletex v2 API — Quick Reference

### Authentication
- Basic Auth: username = "0", password = session_token
- All requests go through the provided base_url (proxy)

### Response Formats
- POST/PUT single entity: {"value": {"id": <int>, ...}}
- GET list: {"fullResultSize": <int>, "values": [{...}, ...]}
- Use ?fields=id,name,email to select specific fields
- Use ?fields=* to discover all fields on an entity
- Pagination: ?from=0&count=100

### Date Format
- Always YYYY-MM-DD (e.g., "2026-03-19")

### Important: Fresh Account
The account starts EMPTY every submission. If a task requires an invoice, you must first:
1. Create the customer
2. Create the product (if order lines are needed)
3. Create the order (links customer + products)
4. Create the invoice (from the order)

Do NOT assume any entities exist unless the task says to find/modify existing ones.

---

### Endpoints

#### POST /employee
Create an employee.
Required: firstName (string), lastName (string)
Optional: email (string), phoneNumberMobile (string),
          isAdministrator (boolean — set true for admin/"kontoadministrator" role),
          department (object: {"id": <int>}),
          employments (array)
Returns: {"value": {"id": <int>, "firstName": ..., "lastName": ..., ...}}

#### PUT /employee/{id}
Update an employee. Send the full object with changes applied.
Required: id (in URL), firstName, lastName

#### GET /employee
Search employees.
Params: firstName, lastName, email, fields, from, count
Returns: {"fullResultSize": <int>, "values": [...]}

---

#### POST /customer
Create a customer.
Required: name (string)
Optional: email (string), phoneNumber (string),
          isCustomer (boolean, default true), isSupplier (boolean),
          organizationNumber (string), accountManager (object: {"id": <int>})
Returns: {"value": {"id": <int>, "name": ..., ...}}

#### PUT /customer/{id}
Update a customer.
Required: id (in URL), name

#### GET /customer
Search customers.
Params: name, email, isCustomer, fields, from, count

---

#### POST /product
Create a product.
Required: name (string)
Optional: number (string), priceExcludingVat (number), priceIncludingVat (number),
          vatType (object: {"id": <int>}), productUnit (object: {"id": <int>}),
          account (object: {"id": <int>}), department (object: {"id": <int>})
Returns: {"value": {"id": <int>, "name": ..., ...}}

#### GET /product
Search products.
Params: name, number, fields, from, count

---

#### POST /order
Create an order. Required before creating an invoice.
Required: customer (object: {"id": <int>}),
          deliveryDate (string YYYY-MM-DD),
          orderDate (string YYYY-MM-DD)
Optional: orderLines (array of {"product": {"id": <int>}, "count": <number>,
          "unitPriceExcludingVat": <number>}),
          receiver (string)
Returns: {"value": {"id": <int>, ...}}

#### GET /order
Search orders.
Params: customerId, fields, from, count

---

#### POST /invoice
Create an invoice from one or more orders.
Required: invoiceDate (string YYYY-MM-DD),
          invoiceDueDate (string YYYY-MM-DD),
          orders (array of {"id": <int>})
Optional: comment (string)
Returns: {"value": {"id": <int>, "invoiceNumber": <int>, ...}}

#### GET /invoice
Search invoices.
Params: invoiceNumber, customerId, fields, from, count

---

#### POST /travelExpense
Create a travel expense report.
Required: employee (object: {"id": <int>}), title (string)
Optional: date (string YYYY-MM-DD), description (string),
          project (object: {"id": <int>})
Returns: {"value": {"id": <int>, ...}}

#### DELETE /travelExpense/{id}
Delete a travel expense report.

#### GET /travelExpense
Search travel expenses.
Params: employeeId, fields, from, count

---

#### POST /project
Create a project.
Required: name (string), projectManager (object: {"id": <int>})
Optional: customer (object: {"id": <int>}), number (string),
          description (string), startDate (string), endDate (string)
Returns: {"value": {"id": <int>, "name": ..., ...}}

#### GET /project
Search projects.
Params: name, fields, from, count

---

#### POST /department
Create a department.
Required: name (string), departmentNumber (int)
Optional: departmentManager (object: {"id": <int>})
Returns: {"value": {"id": <int>, "name": ..., ...}}

#### GET /department
Search departments.
Params: name, fields, from, count

---

#### GET /ledger/account
Query chart of accounts.
Params: number, from, count, fields

#### POST /ledger/voucher
Create a voucher (for journal entries, corrections).
Required: date (string YYYY-MM-DD), description (string),
          postings (array of {"account": {"id": <int>}, "amount": <number>})

#### DELETE /ledger/voucher/{id}
Delete a voucher.

#### GET /ledger/voucher
Query vouchers.
Params: dateFrom, dateTo, fields, from, count

#### GET /ledger/posting
Query ledger postings.
Params: dateFrom, dateTo, accountId, fields, from, count

---

### Common Patterns

**Create single entity:**
Task: "Create employee Ola Nordmann, ola@example.com, admin"
→ POST /employee {"firstName":"Ola","lastName":"Nordmann","email":"ola@example.com","isAdministrator":true}

**Create entity chain for invoicing:**
1. POST /customer {"name":"Acme AS"} → get customer id from response
2. POST /product {"name":"Widget","priceExcludingVat":100} → get product id
3. POST /order {"customer":{"id":<customer_id>},"deliveryDate":"2026-03-19","orderDate":"2026-03-19","orderLines":[{"product":{"id":<product_id>},"count":1,"unitPriceExcludingVat":100}]}
4. POST /invoice {"invoiceDate":"2026-03-19","invoiceDueDate":"2026-04-19","orders":[{"id":<order_id>}]}

**Find then modify:**
1. GET /customer?name=Acme&fields=id,name,email → get id from values[0]
2. PUT /customer/{id} {"id":<id>,"name":"Acme AS","email":"new@acme.no"}

**Find then delete:**
1. GET /travelExpense?employeeId=1&fields=id → get id from values[0]
2. DELETE /travelExpense/{id}

### Tips
- Norwegian characters (ae, oe, aa) work fine — send as UTF-8
- All IDs are integers
- "kontoadministrator" = isAdministrator: true on employee
- Invoice REQUIRES at least one order. Order REQUIRES a customer and delivery date.
- When the prompt says "slett" (Norwegian) = delete, "opprett" = create, "endre" = modify
- For "faktura" (invoice), always create the full chain: customer → product → order → invoice
- POST returns the created entity with its ID — use it directly, don't make a GET
"""
```

**Step 3: Verify the module imports correctly**

```bash
cd "E:/Coding Projects/Personal/AIAccountingAgent"
python -c "from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET; print(f'Cheat sheet loaded: {len(TRIPLETEX_API_CHEAT_SHEET)} chars')"
```

Expected: `Cheat sheet loaded: ~3500 chars`

---

## Task 4: Build Agent Core with Gemini Function Calling

This is the heart of the system. The agent gives Gemini a `tripletex_api` tool and runs an iterative loop: Gemini calls the tool → we execute against Tripletex → feed result back → Gemini decides next action or stops.

**Files:**
- Create: `agent.py`
- Create: `tests/test_agent.py`

**Step 1: Write the failing tests**

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_agent.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'agent'`

**Step 3: Create `agent.py`**

```python
# agent.py
"""Agentic loop using Gemini function calling to complete Tripletex accounting tasks."""

import json
import logging
import os
import time
from datetime import date

from google import genai
from google.genai import types

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET
from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
MAX_TURNS = 25
TIMEOUT_BUFFER_SECONDS = 45


def _create_genai_client():
    """Create Gemini client. Returns None if GCP credentials unavailable."""
    try:
        return genai.Client(
            vertexai=True,
            project=os.getenv("GCP_PROJECT_ID"),
            location=os.getenv("GCP_LOCATION", "global"),
        )
    except Exception as e:
        logger.warning(f"Could not initialize Gemini client: {e}")
        return None


genai_client = _create_genai_client()

TRIPLETEX_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="tripletex_api",
            description=(
                "Make a request to the Tripletex v2 REST API. "
                "Use to create, read, update, or delete accounting entities."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "method": types.Schema(
                        type="STRING",
                        description="HTTP method",
                        enum=["GET", "POST", "PUT", "DELETE"],
                    ),
                    "endpoint": types.Schema(
                        type="STRING",
                        description="API path, e.g. /employee or /customer/123",
                    ),
                    "body_json": types.Schema(
                        type="STRING",
                        description='JSON body for POST/PUT. Example: \'{"firstName":"Ola"}\'',
                    ),
                    "query_params_json": types.Schema(
                        type="STRING",
                        description='JSON query params for GET. Example: \'{"fields":"id,name"}\'',
                    ),
                },
                required=["method", "endpoint"],
            ),
        )
    ]
)


def build_system_prompt() -> str:
    """Build the system prompt with API reference and today's date."""
    today = date.today().isoformat()
    return f"""You are an expert accounting agent for Tripletex. You receive tasks in any of 7 languages (Norwegian, English, Spanish, Portuguese, Nynorsk, German, French) and complete them via API calls.

{TRIPLETEX_API_CHEAT_SHEET}

## Rules
1. Today's date: {today}. Use for all date fields unless the prompt says otherwise.
2. Account starts EMPTY. Create prerequisites before dependent entities.
3. MINIMIZE API calls — every call and error affects your score.
4. POST responses include the created entity's ID. Use it directly — don't GET to find it.
5. body_json and query_params_json must be valid JSON strings.
6. Read error messages carefully. Fix the specific issue in one retry.
7. When done, stop calling tools and respond with a brief summary.
8. Do NOT make verification GETs unless absolutely necessary.
9. Dates: YYYY-MM-DD. IDs: integers. Text: UTF-8."""


def run_agent(
    client: TripletexClient,
    prompt: str,
    file_contents: list[dict],
    deadline: float,
) -> dict:
    """Run the agentic loop to complete an accounting task.

    Args:
        client: Initialized TripletexClient
        prompt: The task prompt in any of 7 languages
        file_contents: Processed file attachments from file_handler
        deadline: Unix timestamp when we must stop

    Returns:
        {"success": bool, "summary": str, "api_calls": int, "errors": int}
    """
    if genai_client is None:
        raise RuntimeError("Gemini client not initialized. Set GCP_PROJECT_ID env var.")

    system_prompt = build_system_prompt()
    user_text = f"{system_prompt}\n\n## Task\n{prompt}"
    content_parts = [types.Part.from_text(user_text)]

    for f in file_contents:
        if "text_content" in f:
            content_parts.append(
                types.Part.from_text(f"\n## File: {f['filename']}\n{f['text_content']}")
            )
        if f.get("mime_type", "").startswith("image/") and "raw_bytes" in f:
            content_parts.append(
                types.Part.from_bytes(data=f["raw_bytes"], mime_type=f["mime_type"])
            )

    history = [types.Content(role="user", parts=content_parts)]
    config = types.GenerateContentConfig(
        tools=[TRIPLETEX_TOOL],
        temperature=0.0,
        max_output_tokens=4096,
    )

    for turn in range(MAX_TURNS):
        remaining = deadline - time.time()
        if remaining < TIMEOUT_BUFFER_SECONDS:
            logger.warning(f"Timeout: {remaining:.0f}s left, stopping")
            break

        logger.info(f"Turn {turn + 1}/{MAX_TURNS} ({remaining:.0f}s left)")

        try:
            response = genai_client.models.generate_content(
                model=MODEL, contents=history, config=config,
            )
        except Exception as e:
            logger.error(f"Gemini error on turn {turn + 1}: {e}")
            break

        model_content = response.candidates[0].content
        history.append(model_content)

        function_calls = [
            p for p in model_content.parts
            if getattr(p, "function_call", None)
        ]

        if not function_calls:
            text_parts = [
                p.text for p in model_content.parts
                if getattr(p, "text", None)
            ]
            summary = " ".join(text_parts) if text_parts else "Completed"
            logger.info(f"Done on turn {turn + 1}: {summary[:200]}")
            return {
                "success": True,
                "summary": summary,
                "api_calls": client.call_count,
                "errors": client.error_count,
            }

        fn_response_parts = []
        for part in function_calls:
            fc = part.function_call
            logger.info(f"Tool: {fc.name} args={dict(fc.args)}")
            result = _execute_tool(client, fc.name, dict(fc.args))
            fn_response_parts.append(
                types.Part.from_function_response(name=fc.name, response=result)
            )

        history.append(types.Content(role="user", parts=fn_response_parts))

    return {
        "success": False,
        "summary": "Loop ended without completion",
        "api_calls": client.call_count,
        "errors": client.error_count,
    }


def _execute_tool(client: TripletexClient, name: str, args: dict) -> dict:
    """Execute a tool call against the Tripletex API."""
    if name != "tripletex_api":
        return {"error": f"Unknown tool: {name}"}

    method = args.get("method", "GET").upper()
    endpoint = args.get("endpoint", "")
    body = _parse_json_arg(args.get("body_json"))
    params = _parse_json_arg(args.get("query_params_json"))

    if method == "GET":
        return client.get(endpoint, params=params)
    elif method == "POST":
        return client.post(endpoint, body=body)
    elif method == "PUT":
        return client.put(endpoint, body=body)
    elif method == "DELETE":
        return client.delete(endpoint)
    return {"success": False, "error": f"Unknown method: {method}"}


def _parse_json_arg(value) -> dict | None:
    """Parse a JSON argument that may be a string, dict, or None."""
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON arg: {value[:200]}")
            return None
    return None
```

**NOTE on `types.Schema`:** If `types.Schema(type="OBJECT")` doesn't work with your SDK version, try `types.Schema(type=types.Type.OBJECT)` using the enum. Similarly for STRING → `types.Type.STRING`. The exact API may vary between google-genai versions.

**Step 4: Run agent tests**

```bash
python -m pytest tests/test_agent.py -v
```

Expected: All 12 tests PASS

---

## Task 5: Rewire main.py with Agent Integration

Replace the broken planner/executor/recovery imports with the new agent module. Add timeout management and structured logging.

**Files:**
- Rewrite: `main.py`
- Create: `tests/test_integration.py`

**Step 1: Write integration tests**

```python
# tests/test_integration.py
"""Integration tests that simulate the full /solve flow with mocked Gemini."""
import json
import time
from unittest.mock import patch, MagicMock


# --- Test helpers ---

def _make_fc_response(name, args):
    """Mock Gemini response with a function call."""
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
    """Mock Gemini response with text only (task complete)."""
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


# --- Tests ---

def test_full_solve_creates_employee():
    """Full /solve flow: Gemini calls POST /employee, then completes."""
    mock_tripletex = MagicMock()
    mock_tripletex.status_code = 201
    mock_tripletex.json.return_value = {
        "value": {"id": 42, "firstName": "Ola", "lastName": "Nordmann"}
    }

    gemini_responses = [
        _make_fc_response("tripletex_api", {
            "method": "POST",
            "endpoint": "/employee",
            "body_json": '{"firstName":"Ola","lastName":"Nordmann","email":"ola@example.com","isAdministrator":true}',
        }),
        _make_text_response("Created employee Ola Nordmann with ID 42"),
    ]

    with patch("agent.genai_client") as mock_genai, \
         patch("tripletex_api.requests") as mock_requests:
        mock_genai.models.generate_content.side_effect = gemini_responses
        mock_requests.post.return_value = mock_tripletex

        from main import app
        from fastapi.testclient import TestClient
        test_client = TestClient(app)

        response = test_client.post("/solve", json={
            "prompt": "Opprett en ansatt med navn Ola Nordmann, ola@example.com. Kontoadministrator.",
            "files": [],
            "tripletex_credentials": {
                "base_url": "https://tx-proxy.ainm.no/v2",
                "session_token": "test-token",
            },
        })

    assert response.status_code == 200
    assert response.json() == {"status": "completed"}


def test_solve_returns_completed_on_gemini_error():
    """Agent returns completed even when Gemini fails — for partial credit."""
    with patch("agent.genai_client") as mock_genai:
        mock_genai.models.generate_content.side_effect = Exception("Gemini timeout")

        from main import app
        from fastapi.testclient import TestClient
        test_client = TestClient(app)

        response = test_client.post("/solve", json={
            "prompt": "Some task",
            "files": [],
            "tripletex_credentials": {
                "base_url": "https://example.com/v2",
                "session_token": "token",
            },
        })

    assert response.status_code == 200
    assert response.json() == {"status": "completed"}


def test_health_endpoint():
    """Health check returns ok."""
    from main import app
    from fastapi.testclient import TestClient
    test_client = TestClient(app)

    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Rewrite `main.py`**

```python
# main.py
import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from agent import run_agent
from file_handler import process_files
from tripletex_api import TripletexClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Accounting Agent")

API_KEY = os.getenv("API_KEY")
REQUEST_TIMEOUT = 300  # 5 minutes


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/solve")
async def solve(request: Request):
    start_time = time.time()
    deadline = start_time + REQUEST_TIMEOUT

    # Optional: API key protection
    if API_KEY:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()
    prompt = body["prompt"]
    files = body.get("files", [])
    creds = body["tripletex_credentials"]

    logger.info(f"Task received. Prompt: {prompt[:100]}... Files: {len(files)}")

    try:
        file_contents = process_files(files)
        client = TripletexClient(creds["base_url"], creds["session_token"])

        result = run_agent(
            client=client,
            prompt=prompt,
            file_contents=file_contents,
            deadline=deadline,
        )

        elapsed = time.time() - start_time
        logger.info(
            f"Agent finished in {elapsed:.1f}s. "
            f"Success: {result['success']}, "
            f"API calls: {result['api_calls']}, "
            f"Errors: {result['errors']}"
        )

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

    # Always return completed — partial work earns partial credit
    return JSONResponse({"status": "completed"})
```

**Step 3: Run integration tests**

```bash
python -m pytest tests/test_integration.py -v
```

Expected: All 3 tests PASS

**Step 4: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: All tests PASS across all test files

---

## Task 6: Configuration and Dependency Updates

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- No changes needed to `Dockerfile`

**Step 1: Update `requirements.txt`**

```
fastapi
uvicorn[standard]
requests
google-genai>=1.51.0
pymupdf
python-dotenv
httpx
```

`httpx` is required by FastAPI's TestClient (Starlette dependency).

**Step 2: Update `.env.example`**

```env
# GCP credentials (from gcplab.me account)
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=global

# Gemini model — change to test different models
# Options: gemini-2.0-flash, gemini-2.5-flash-preview-05-20, gemini-2.5-pro-preview-05-06
GEMINI_MODEL=gemini-2.0-flash

# Optional: protect your /solve endpoint
API_KEY=your-optional-api-key
```

**Step 3: Update `.env` (local only, not committed)**

Add the missing `GCP_PROJECT_ID` to your local `.env` file. Get the project ID from the GCP console (top-left dropdown when logged in with the `@gcplab.me` account).

```env
gcpaccount=devstar17993@gcplab.me
gcpassword=uqed7xYRa6
GCP_PROJECT_ID=your-actual-project-id
GCP_LOCATION=global
GEMINI_MODEL=gemini-2.0-flash
```

**Step 4: Install updated dependencies**

```bash
pip install -r requirements.txt
```

---

## Task 7: Full Test Suite Verification

**Step 1: Run the complete test suite**

```bash
cd "E:/Coding Projects/Personal/AIAccountingAgent"
python -m pytest tests/ -v
```

Expected output — all tests pass:
```
tests/test_agent.py::test_build_system_prompt_includes_date_and_cheatsheet PASSED
tests/test_agent.py::test_execute_tool_routes_get PASSED
tests/test_agent.py::test_execute_tool_routes_post PASSED
tests/test_agent.py::test_execute_tool_routes_put PASSED
tests/test_agent.py::test_execute_tool_routes_delete PASSED
tests/test_agent.py::test_execute_tool_handles_dict_body PASSED
tests/test_agent.py::test_execute_tool_unknown_tool PASSED
tests/test_agent.py::test_parse_json_arg_handles_types PASSED
tests/test_agent.py::test_run_agent_single_tool_call PASSED
tests/test_agent.py::test_run_agent_stops_at_timeout PASSED
tests/test_agent.py::test_run_agent_handles_gemini_error PASSED
tests/test_file_handler.py::test_process_empty_files PASSED
tests/test_file_handler.py::test_process_text_file PASSED
tests/test_file_handler.py::test_process_image_file PASSED
tests/test_file_handler.py::test_process_csv_file PASSED
tests/test_integration.py::test_full_solve_creates_employee PASSED
tests/test_integration.py::test_solve_returns_completed_on_gemini_error PASSED
tests/test_integration.py::test_health_endpoint PASSED
tests/test_tripletex_api.py::test_client_uses_basic_auth PASSED
tests/test_tripletex_api.py::test_client_get PASSED
tests/test_tripletex_api.py::test_client_post PASSED
tests/test_tripletex_api.py::test_client_put PASSED
tests/test_tripletex_api.py::test_client_delete PASSED
tests/test_tripletex_api.py::test_client_handles_error_response PASSED
tests/test_tripletex_api.py::test_client_tracks_call_count PASSED
tests/test_tripletex_api.py::test_client_tracks_error_count PASSED
tests/test_tripletex_api.py::test_client_uses_timeout PASSED
```

27 tests total.

**Step 2: Fix any failures**

If tests fail, read the error messages and fix the issue. Common problems:
- `types.Schema(type="OBJECT")` might need `types.Schema(type=types.Type.OBJECT)` — check your google-genai version
- `types.Part.from_function_response` API may differ — check SDK docs
- Import errors from circular dependencies — ensure agent.py doesn't import main.py

---

## Task 8: Deploy to Cloud Run

**Prerequisites:**
- `.env` has `GCP_PROJECT_ID` set
- `gcloud` CLI installed
- Logged in as the competition GCP account

**Step 1: Authenticate with GCP**

```bash
gcloud auth login
# Log in with devstar17993@gcplab.me and the password from .env
gcloud config set project YOUR_PROJECT_ID
```

**Step 2: Enable required APIs**

```bash
gcloud services enable run.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com
```

**Step 3: Set up Application Default Credentials (for Vertex AI)**

```bash
gcloud auth application-default login
```

**Step 4: Deploy to Cloud Run**

```bash
cd "E:/Coding Projects/Personal/AIAccountingAgent"
gcloud run deploy ai-accounting-agent \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --min-instances 1 \
  --set-env-vars "GCP_PROJECT_ID=YOUR_PROJECT_ID,GCP_LOCATION=global,GEMINI_MODEL=gemini-2.0-flash"
```

Replace `YOUR_PROJECT_ID` with your actual GCP project ID.

Expected: Produces URL like `https://ai-accounting-agent-xxxxx-lz.a.run.app`

**Step 5: Test the deployed endpoint**

```bash
# Health check
curl https://YOUR-URL/health
# Expected: {"status":"ok"}

# Test solve (will fail without real Tripletex creds, but should return completed)
curl -X POST https://YOUR-URL/solve \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test","files":[],"tripletex_credentials":{"base_url":"https://example.com/v2","session_token":"test"}}'
# Expected: {"status":"completed"}
```

**Step 6: Submit endpoint URL**

1. Go to `https://app.ainm.no/submit/tripletex`
2. Paste your Cloud Run URL
3. Submit — validators start calling your endpoint

---

## Post-Deployment: Sandbox Exploration (Task 9, manual)

After deployment, use the sandbox to verify and refine the cheat sheet. This is the highest-ROI optimization.

**Step 1: Get sandbox credentials from the competition platform**

**Step 2: Test each endpoint with `?fields=*`**

```bash
# Discover all employee fields
curl -u "0:YOUR_SANDBOX_TOKEN" \
  "https://kkpqfuj-amager.tripletex.dev/v2/employee?fields=*&count=1"

# Test creating an employee
curl -u "0:YOUR_SANDBOX_TOKEN" \
  -X POST "https://kkpqfuj-amager.tripletex.dev/v2/employee" \
  -H "Content-Type: application/json" \
  -d '{"firstName":"Test","lastName":"User","email":"test@example.com","isAdministrator":true}'

# Test creating the full invoice chain
# ... (customer → product → order → invoice)
```

**Step 3: Update `api_knowledge/cheat_sheet.py` with exact field names, required vs optional, default values, and any gotchas discovered**

**Step 4: Redeploy**

```bash
gcloud run deploy ai-accounting-agent --source . --region europe-north1 --allow-unauthenticated
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | TripletexClient | Metrics (call_count, error_count) + timeout |
| 2 | File Handler | CSV structured parsing |
| 3 | API Cheat Sheet | Comprehensive endpoint reference for Gemini |
| 4 | Agent Core | Gemini function calling agentic loop |
| 5 | main.py | Rewired with agent + timeout management |
| 6 | Configuration | Updated deps, env, model config |
| 7 | Test Suite | 27 tests all passing |
| 8 | Deployment | Cloud Run + submission |
| 9 | Optimization | Sandbox-verified cheat sheet refinement |

**Architecture comparison:**

| Aspect | V1 (Plan-then-Execute) | V2 (Agentic Loop) |
|--------|----------------------|-------------------|
| LLM calls per task | 1 (+ recovery) | 2-10 (iterative) |
| Error handling | Separate recovery module | Built into loop |
| Multi-step tasks | Static plan, brittle | Dynamic, adaptive |
| Code complexity | 4 modules (planner, executor, recovery, cheat_sheet) | 2 modules (agent, cheat_sheet) |
| Tier 3 readiness | Poor (needs complex plans) | Good (runtime decisions) |
