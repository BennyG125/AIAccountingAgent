# Pure Agent Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two-path deterministic+fallback architecture with a single Claude Opus 4.6 agentic loop using 4 REST tools and a recipe-enhanced system prompt.

**Architecture:** Single Claude agentic loop with streaming, adaptive thinking, and prompt caching. Gemini retained for OCR only. System prompt contains full API reference, step-by-step recipes for known flows, and guidance for unknown Tier 3 tasks.

**Tech Stack:** Python 3.11, FastAPI, anthropic[vertex] (AnthropicVertex), google-genai (Gemini OCR), Docker, Cloud Run

**Spec:** `docs/superpowers/specs/2026-03-20-pure-agent-redesign.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `prompts.py` | **Create** | System prompt: API reference, recipes, rules, constants |
| `agent.py` | **Rewrite** | Claude agentic loop (streaming, timeout, tools, OCR) |
| `main.py` | **Simplify** | FastAPI endpoint — parse payload, call agent, return completed |
| `tripletex_api.py` | **Keep** | Tripletex HTTP wrapper (unchanged) |
| `file_handler.py` | **Keep** | PDF/image/text processing (unchanged) |
| `claude_client.py` | **Keep** | AnthropicVertex cached client (unchanged) |
| `planner.py` | **Delete** | Replaced by Claude's reasoning |
| `executor.py` | **Delete** | Replaced by tool-use loop |
| `task_registry.py` | **Delete** | Replaced by system prompt recipes |
| `api_knowledge/` | **Delete** | Merged into prompts.py |
| `tests/test_agent.py` | **Rewrite** | Tests for new agent loop |
| `tests/test_prompts.py` | **Create** | Tests for system prompt construction |
| `tests/test_planner.py` | **Delete** | No planner in new architecture |
| `tests/test_executor.py` | **Delete** | No executor in new architecture |
| `tests/test_task_registry.py` | **Delete** | No registry in new architecture |

---

## Task 1: Create prompts.py — The System Prompt

The system prompt is the brain of the agent. It contains the full API reference (migrated from `api_knowledge/cheat_sheet.py`), task-category recipes, scoring rules, and Tier 3 guidance.

**Files:**
- Create: `prompts.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompts.py
from prompts import build_system_prompt


def test_system_prompt_contains_api_reference():
    """System prompt includes the Tripletex API reference."""
    prompt = build_system_prompt()
    assert "POST /employee" in prompt
    assert "POST /customer" in prompt
    assert "POST /invoice" in prompt
    assert "POST /order" in prompt
    assert "POST /travelExpense" in prompt
    assert "POST /ledger/voucher" in prompt


def test_system_prompt_contains_recipes():
    """System prompt includes step-by-step recipes for known flows."""
    prompt = build_system_prompt()
    assert "Recipe" in prompt or "recipe" in prompt
    # Invoice flow recipe
    assert "orderLines" in prompt
    assert ":payment" in prompt
    # Employee recipe
    assert "userType" in prompt
    assert "department" in prompt


def test_system_prompt_contains_rules():
    """System prompt includes scoring-aware rules."""
    prompt = build_system_prompt()
    assert "4xx" in prompt or "error" in prompt.lower()
    assert "minimize" in prompt.lower() or "efficiency" in prompt.lower()


def test_system_prompt_contains_constants():
    """System prompt includes known constants."""
    prompt = build_system_prompt()
    assert "NOK" in prompt
    assert "162" in prompt  # Norway country ID


def test_system_prompt_contains_date():
    """System prompt includes today's date."""
    from datetime import date
    prompt = build_system_prompt()
    assert date.today().isoformat() in prompt


def test_system_prompt_contains_gotchas():
    """System prompt includes common gotchas."""
    prompt = build_system_prompt()
    # Payment registration uses query params, not body
    assert "QUERY" in prompt or "query" in prompt
    # Object refs are {id: N}
    assert '{"id"' in prompt or "{id:" in prompt


def test_system_prompt_contains_tier3_guidance():
    """System prompt includes guidance for unknown task types."""
    prompt = build_system_prompt()
    assert "fields=*" in prompt or "?fields=" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'prompts'`

- [ ] **Step 3: Write prompts.py**

Create `prompts.py` with the following content. The API reference section is migrated from `api_knowledge/cheat_sheet.py` and the rules/recipes are expanded from `agent.py:build_system_prompt()`.

```python
# prompts.py
"""System prompt for the Claude accounting agent.

This is the brain of the agent. It contains:
- Role and scoring rules
- Full Tripletex API reference (from sandbox testing)
- Step-by-step recipes for known task categories
- Common gotchas and Tier 3 guidance
"""

from datetime import date

# ---------------------------------------------------------------------------
# API reference — migrated from api_knowledge/cheat_sheet.py
# ---------------------------------------------------------------------------

API_REFERENCE = """
## Tripletex v2 API — Endpoint Reference

### Authentication
- Basic Auth: username = "0", password = session_token
- All requests go through the provided base_url (includes /v2)

### Response Format
- Single entity: {"value": {<entity>}}
- List: {"fullResultSize": N, "values": [{...}, ...]}
- POST returns the created entity with its assigned ID inside "value"
- Errors: {"status": 4xx, "message": "..."}

### Query Parameters (all GET list endpoints)
- fields: comma-separated names, * for all (e.g. ?fields=id,name)
- from: pagination offset (default 0), count: page size (default 1000)

### Object References
References to other entities are always objects: {"id": <int>}
Example: "department": {"id": 42}  — NEVER bare integers.

### Date Format
All dates: YYYY-MM-DD strings.

---

## DEPARTMENT
POST /department — Required: name (string), departmentNumber (string — NOT int)
  Optional: departmentManager ({id})
GET /department — Search: ?name=X&departmentNumber=X
PUT /department/{id} — Update (include version field)
DELETE /department/{id}

## EMPLOYEE
POST /employee — Required: firstName, lastName, userType ("STANDARD"|"EXTENDED"|"NO_ACCESS"), department ({id})
  Optional: email, phoneNumberMobile, dateOfBirth, nationalIdentityNumber, employeeNumber,
            bankAccountNumber, address ({addressLine1, city, postalCode, country: {id}}),
            employeeCategory ({id}), employments (array)
  NOTE: No "isAdministrator" field — admin access is via entitlements.
  NOTE: If task doesn't specify department, GET /department and use first one.
GET /employee — Search: ?firstName=X&lastName=X&email=X&employeeNumber=X
PUT /employee/{id} — Update (include version)
POST /employee/list — Bulk create

POST /employee/employment — Required: employee ({id}), startDate
  Optional: endDate, taxDeductionCode, isMainEmployer, employmentDetails (array)
POST /employee/employment/details — Required: employment ({id}), date
  Optional: employmentType, annualSalary, hourlyWage, occupationCode ({id})
GET /employee/employment — Params: employeeId
PUT /employee/employment/{id}

GET /employee/entitlement — Params: employeeId
PUT /employee/entitlement/:grantEntitlementsByTemplate — Grant roles/permissions

## CUSTOMER
POST /customer — Required: name
  Optional: email, phoneNumber, organizationNumber, customerNumber, invoiceEmail,
            physicalAddress, postalAddress, deliveryAddress,
            accountManager ({id}), department ({id}), currency ({id}),
            invoiceSendMethod ("EMAIL"|"EHF"|"EFAKTURA"|"PAPER"|"MANUAL"),
            category1 ({id}), category2 ({id}), category3 ({id}),
            isPrivateIndividual (boolean), language ("NO"|"EN")
GET /customer — Search: ?name=X&email=X&customerNumber=X&organizationNumber=X
PUT /customer/{id} — Update (include version)
DELETE /customer/{id}
POST /customer/list — Bulk create

POST /customer/category — Fields: name, number, description, type (int)
GET /customer/category

## CONTACT
POST /contact — Fields: firstName, lastName, email, phoneNumberMobile, customer ({id})
GET /contact — Search: ?firstName=X&lastName=X&customerId=X
PUT /contact/{id}
POST /contact/list — Bulk create

## SUPPLIER
POST /supplier — Required: name
  Optional: email, phoneNumber, organizationNumber, supplierNumber,
            physicalAddress, postalAddress, accountManager ({id}), currency ({id}),
            category1 ({id}), category2 ({id}), category3 ({id})
GET /supplier — Search: ?name=X&organizationNumber=X&supplierNumber=X
PUT /supplier/{id} — Update (include version)
DELETE /supplier/{id}

## PRODUCT
POST /product — Required: name
  Optional: number (string), priceExcludingVatCurrency, priceIncludingVatCurrency,
            vatType ({id}), productUnit ({id}), account ({id}),
            department ({id}), supplier ({id}), currency ({id}), description
GET /product — Search: ?name=X&number=X
PUT /product/{id} — Update (include version)
DELETE /product/{id}
POST /product/list — Bulk create

GET /product/unit — Search: ?name=X&nameShort=X

## ORDER
POST /order — Required: customer ({id}), deliveryDate, orderDate
  Optional: orderLines (array — EMBED HERE to save calls),
            receiverEmail, reference, department ({id}), project ({id}),
            currency ({id}), invoicesDueIn, invoicesDueInType
  OrderLine fields: product ({id}), count, unitPriceExcludingVatCurrency, vatType ({id}), description
GET /order — Search: ?customerName=X&number=X
PUT /order/{id}
DELETE /order/{id}

POST /order/orderline — Create single orderline: order ({id}), product ({id}), count, unitPriceExcludingVatCurrency
POST /order/orderline/list — Bulk create orderlines

## INVOICE
POST /invoice — Required: invoiceDate, invoiceDueDate, orders (array of {id})
  Optional: comment, customer ({id}), invoiceNumber (0=auto)
  NOTE: Order must have orderLines. Company must have bank account on ledger 1920.
GET /invoice — Search: ?invoiceDateFrom=X&invoiceDateTo=X&customerId=X
GET /invoice/{id}

PUT /invoice/{id}/:payment — QUERY PARAMS ONLY (NOT body):
  ?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1
PUT /invoice/{id}/:send — Body: sendType ("EMAIL"|"EHF"|"EFAKTURA"), overrideEmailAddress
PUT /invoice/{id}/:createCreditNote
PUT /invoice/{id}/:createReminder

GET /invoice/paymentType — List payment types

## SUPPLIER INVOICE
GET /supplierInvoice — Search supplier invoices
POST /supplierInvoice/{id}/:addPayment — Body: paymentType, amount, paymentDate
PUT /supplierInvoice/{id}/:approve
PUT /supplierInvoice/{id}/:reject

## PROJECT
POST /project — Required: name, projectManager ({id}), startDate
  Optional: description, endDate, customer ({id}), department ({id}),
            number, isInternal, isClosed, participants (array)
GET /project — Search: ?name=X&number=X&projectManagerId=X
PUT /project/{id}
DELETE /project/{id}

POST /project/participant — Fields: project ({id}), employee ({id}), adminAccess
POST /project/participant/list — Bulk add participants

## TRAVEL EXPENSE
POST /travelExpense — Required: employee ({id}), title
  Optional: project ({id}), department ({id}),
            costs (array — can embed), perDiemCompensations (array — can embed)
  NOTE: mileageAllowances and accommodationAllowances are READ-ONLY here —
        create them via their own POST endpoints below.
GET /travelExpense — Search: ?employeeId=X&departmentId=X
DELETE /travelExpense/{id}
PUT /travelExpense/:approve — Body: list of IDs
PUT /travelExpense/:deliver
PUT /travelExpense/:unapprove

POST /travelExpense/cost — Fields: travelExpense ({id}), date, costCategory ({id}),
  paymentType ({id}), currency ({id}), amountCurrencyIncVat
GET /travelExpense/cost — Params: travelExpenseId
GET /travelExpense/costCategory — List cost categories
GET /travelExpense/paymentType — List payment types

POST /travelExpense/perDiemCompensation — Fields: travelExpense ({id}), rateCategory ({id}),
  rateType ({id}), countryCode, location, count, overnightAccommodation
GET /travelExpense/perDiemCompensation — Params: travelExpenseId
GET /travelExpense/rateCategory — List rate categories
GET /travelExpense/rate — List rates

POST /travelExpense/mileageAllowance — Fields: travelExpense ({id}), rateCategory ({id}),
  rateType ({id}), date, departureLocation, destination, km
GET /travelExpense/mileageAllowance — Params: travelExpenseId

POST /travelExpense/accommodationAllowance — Fields: travelExpense ({id}),
  rateCategory ({id}), rateType ({id}), location, count
GET /travelExpense/accommodationAllowance — Params: travelExpenseId

## LEDGER / VOUCHER
POST /ledger/voucher — Required: date, description, postings (array)
  Each posting: account ({id}), amount, row (integer >= 1, row 0 is system-reserved)
  Optional posting fields: currency ({id}), customer ({id}), supplier ({id}),
    employee ({id}), project ({id}), department ({id}), vatType ({id})
  IMPORTANT: Postings MUST balance (sum of amounts = 0). Only gross amounts needed.
  IMPORTANT: Look up account IDs with GET /ledger/account?number=XXXX — never guess.
GET /ledger/voucher — Search: ?dateFrom=X&dateTo=X&number=X
DELETE /ledger/voucher/{id}
PUT /ledger/voucher/{id}/:reverse

GET /ledger/account — Search: ?number=X&name=X
POST /ledger/account — Fields: number (int), name
GET /ledger/posting — Search: ?dateFrom=X&dateTo=X
GET /ledger/vatType — Search VAT types

## SALARY
GET /salary/type — List salary types
POST /salary/transaction — Fields: date, month, year, payslips (array)
GET /salary/payslip — Params: employeeId, yearFrom, yearTo

## COMPANY
GET /company/{id} — Company info
PUT /company — Update company
GET /company/salesmodules — Active modules
POST /company/salesmodules — Activate module

## REFERENCE
GET /country — Params: code (e.g. "NO")
GET /currency — Params: code (e.g. "NOK")
GET /municipality
GET /deliveryAddress
"""


def build_system_prompt() -> str:
    """Build the complete system prompt for the Claude accounting agent."""
    today = date.today().isoformat()

    return f"""You are an expert AI accounting agent for the Tripletex system. Your job is to complete accounting tasks by making API calls using the provided tools.

Today's date: {today}

## Scoring Rules
1. MINIMIZE API calls — fewer calls = higher efficiency bonus.
2. ZERO 4xx errors — every error reduces your score. Get it right on the first call.
3. NEVER make verification GETs after successful creates — wastes calls.
4. Use known constants directly — never look them up via API.
5. Embed orderLines in the order POST body — saves separate calls.
6. When done, STOP calling tools immediately. Do not verify your work.

## Known Constants (never look these up)
- NOK currency: {{"id": 1}}
- Norway country: {{"id": 162}}
- VAT 25%: {{"id": 3}}, VAT 15%: {{"id": 5}}, VAT 0%: {{"id": 6}}
  (If a vatType fails, retry WITHOUT it — Tripletex assigns a valid default)

## Critical Gotchas
- Payment registration: PUT /invoice/{{id}}/:payment uses QUERY PARAMS, NOT request body.
  Params: ?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1
- Object refs are ALWAYS {{"id": <int>}}, never bare integers.
- departmentNumber is a STRING, not an int.
- orderLines MUST be embedded in the order POST body.
- Voucher postings MUST balance (sum of amounts = 0). Rows start at 1 (row 0 is system-reserved).
- Look up ledger account IDs with GET /ledger/account?number=XXXX — never guess.
- The Tripletex account starts EMPTY. Create prerequisites before dependents.
- Always include the "version" field when doing PUT updates.
- If task mentions attached files, extract data (amounts, dates, names) from the file content provided.

## Recipes (Optimal Sequences for Known Tasks)

### Employee
1. GET /department (find existing department, use first result)
2. POST /employee {{firstName, lastName, email, userType: "STANDARD", department: {{id}}}}

### Customer
POST /customer {{name, email, phoneNumber, organizationNumber, ...}}

### Supplier
POST /supplier {{name, email, phoneNumber, organizationNumber, ...}}

### Product
POST /product {{name, number, priceExcludingVatCurrency, vatType: {{id: 3}}}}

### Invoice Flow (customer → product → order → invoice)
1. POST /customer {{name}} → capture customer_id
2. POST /product {{name, priceExcludingVatCurrency}} → capture product_id
3. POST /order {{customer: {{id: customer_id}}, orderDate: "{today}", deliveryDate: "{today}",
   orderLines: [{{product: {{id: product_id}}, count: 1, unitPriceExcludingVatCurrency: price}}]}}
   → capture order_id
4. POST /invoice {{invoiceDate: "{today}", invoiceDueDate: "30 days later", orders: [{{id: order_id}}]}}
   → capture invoice_id

### Payment Registration
PUT /invoice/{{invoice_id}}/:payment?paymentDate={today}&paymentTypeId=0&paidAmount=X&paidAmountCurrency=1
(paymentTypeId 0 = default. Or GET /invoice/paymentType to find the right one.)

### Send Invoice
PUT /invoice/{{invoice_id}}/:send — Body: {{"sendType": "EMAIL"}}

### Credit Note
PUT /invoice/{{invoice_id}}/:createCreditNote

### Travel Expense
1. POST /travelExpense {{employee: {{id}}, title}} → capture expense_id
2. GET /travelExpense/costCategory → find correct category
3. GET /travelExpense/paymentType → find payment type
4. POST /travelExpense/cost {{travelExpense: {{id: expense_id}}, date, costCategory: {{id}}, paymentType: {{id}}, amountCurrencyIncVat}}

For mileage: GET /travelExpense/rateCategory, then POST /travelExpense/mileageAllowance
For per diem: GET /travelExpense/rateCategory + rate, then POST /travelExpense/perDiemCompensation
For accommodation: POST /travelExpense/accommodationAllowance

### Project
1. POST /project {{name, projectManager: {{id}}, startDate: "{today}"}} → capture project_id
2. POST /project/participant {{project: {{id: project_id}}, employee: {{id}}}}

### Department
POST /department {{name, departmentNumber: "string"}}

### Voucher (Journal Entry)
1. GET /ledger/account?number=XXXX → capture debit_account_id
2. GET /ledger/account?number=YYYY → capture credit_account_id
3. POST /ledger/voucher {{date: "{today}", description, postings: [
     {{account: {{id: debit_id}}, amount: X, row: 1}},
     {{account: {{id: credit_id}}, amount: -X, row: 2}}
   ]}}

## Handling Unknown Tasks (Tier 3)
For tasks you don't recognize:
1. Analyze the prompt carefully — what is the end goal?
2. Use GET with ?fields=* to discover entity structures you're unsure about.
3. Read error messages carefully — Tripletex tells you exactly what's missing.
4. Break complex problems into smaller API calls.
5. If you need to find a salary type or obscure entity, use GET to discover what's available.

{API_REFERENCE}
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add prompts.py tests/test_prompts.py
git commit -m "feat: system prompt with API reference, recipes, and scoring rules"
```

---

## Task 2: Rewrite agent.py — Clean Agentic Loop

Rewrite `agent.py` to remove all planner/executor imports and the deterministic path. Keep the existing tool definitions, `execute_tool`, and `gemini_ocr` functions. Replace `run_agent` and `run_tool_loop` with a single clean agentic loop using streaming and adaptive thinking.

**Files:**
- Rewrite: `agent.py`
- Create: `tests/test_agent.py` (rewrite)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent.py
"""Tests for the pure Claude agentic loop."""
import json
from unittest.mock import MagicMock, patch, PropertyMock

# Mock external dependencies before importing agent
_mock_genai_client = MagicMock()
_mock_claude_client = MagicMock()

with patch("claude_client.get_claude_client", return_value=_mock_claude_client):
    with patch("google.genai.Client", return_value=_mock_genai_client):
        from agent import (
            TOOLS,
            execute_tool,
            gemini_ocr,
            run_agent,
            build_user_message,
            MAX_ITERATIONS,
            TIMEOUT_SECONDS,
        )


def _mock_tripletex_client():
    from tripletex_api import TripletexClient
    return MagicMock(spec=TripletexClient)


class TestToolDefinitions:
    def test_four_tools_defined(self):
        """Exactly 4 generic REST tools."""
        assert len(TOOLS) == 4
        names = {t["name"] for t in TOOLS}
        assert names == {"tripletex_get", "tripletex_post", "tripletex_put", "tripletex_delete"}

    def test_post_requires_path_and_body(self):
        """POST tool requires both path and body."""
        post_tool = next(t for t in TOOLS if t["name"] == "tripletex_post")
        assert "path" in post_tool["input_schema"]["required"]
        assert "body" in post_tool["input_schema"]["required"]

    def test_put_has_params_for_payment(self):
        """PUT tool has params field for payment registration."""
        put_tool = next(t for t in TOOLS if t["name"] == "tripletex_put")
        assert "params" in put_tool["input_schema"]["properties"]


class TestExecuteTool:
    def test_get(self):
        client = _mock_tripletex_client()
        client.get.return_value = {"success": True, "body": {"values": []}}
        result = execute_tool("tripletex_get", {"path": "/employee", "params": {"firstName": "Ola"}}, client)
        client.get.assert_called_once_with("/employee", params={"firstName": "Ola"})

    def test_post(self):
        client = _mock_tripletex_client()
        client.post.return_value = {"success": True, "body": {"value": {"id": 1}}}
        result = execute_tool("tripletex_post", {"path": "/employee", "body": {"firstName": "Ola"}}, client)
        client.post.assert_called_once_with("/employee", body={"firstName": "Ola"})

    def test_put_with_params(self):
        client = _mock_tripletex_client()
        client.put.return_value = {"success": True, "body": {}}
        result = execute_tool("tripletex_put", {
            "path": "/invoice/1/:payment",
            "params": {"paymentDate": "2026-03-20", "paidAmount": "1000"}
        }, client)
        client.put.assert_called_once_with("/invoice/1/:payment", body=None, params={"paymentDate": "2026-03-20", "paidAmount": "1000"})

    def test_delete(self):
        client = _mock_tripletex_client()
        client.delete.return_value = {"success": True, "body": {}}
        result = execute_tool("tripletex_delete", {"path": "/employee/1"}, client)
        client.delete.assert_called_once_with("/employee/1")

    def test_unknown_tool(self):
        client = _mock_tripletex_client()
        result = execute_tool("unknown_tool", {}, client)
        assert result["success"] is False

    def test_exception_handling(self):
        client = _mock_tripletex_client()
        client.post.side_effect = Exception("connection timeout")
        result = execute_tool("tripletex_post", {"path": "/employee", "body": {}}, client)
        assert result["success"] is False
        assert "connection timeout" in result["error"]


class TestBuildUserMessage:
    def test_prompt_only(self):
        msg = build_user_message("Create employee Ola", [])
        assert "Create employee Ola" in msg

    def test_with_file_text(self):
        files = [{"filename": "data.csv", "text_content": "Name,Amount\nOla,1000", "images": []}]
        msg = build_user_message("Process this", files)
        assert "data.csv" in msg
        assert "Name,Amount" in msg

    def test_with_ocr_text(self):
        files = [{"filename": "_ocr_extracted.txt", "text_content": "Invoice #123", "images": []}]
        msg = build_user_message("Process invoice", files)
        assert "Invoice #123" in msg


class TestConstants:
    def test_max_iterations(self):
        assert MAX_ITERATIONS == 20

    def test_timeout(self):
        assert TIMEOUT_SECONDS == 270
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_agent.py -v`
Expected: FAIL — ImportError on `build_user_message` (doesn't exist in current agent.py)

- [ ] **Step 3: Rewrite agent.py**

Replace the entire contents of `agent.py` with:

```python
# agent.py
"""Pure Claude agentic loop for Tripletex accounting tasks.

Single code path: OCR (Gemini) → Claude tool-use loop → done.
No deterministic path, no pattern matching, no executor.
"""

import json
import logging
import os
import time
from typing import Any

from google import genai
from google.genai import types

from claude_client import get_claude_client, CLAUDE_MODEL
from prompts import build_system_prompt
from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (retained for OCR only)
# ---------------------------------------------------------------------------

_genai_client = None


def _get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=os.getenv("GCP_PROJECT_ID"),
            location=os.getenv("GCP_LOCATION", "global"),
        )
    return _genai_client

GEMINI_MODEL = "gemini-3.1-pro-preview"
MAX_ITERATIONS = 20
TIMEOUT_SECONDS = 270  # 30s buffer before 300s competition hard limit

# ---------------------------------------------------------------------------
# Tool definitions (Anthropic format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "tripletex_get",
        "description": "GET request to Tripletex API. Use for searching/listing entities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee', '/customer/123'"},
                "params": {"type": "object", "description": "Query params e.g. {\"fields\": \"id,name\"}"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "tripletex_post",
        "description": "POST request to create entities. Include body with JSON payload.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee'"},
                "body": {"type": "object", "description": "JSON request body"},
                "params": {"type": "object", "description": "Query params (rare for POST)"},
            },
            "required": ["path", "body"],
        },
    },
    {
        "name": "tripletex_put",
        "description": "PUT request for updates and action endpoints. "
                       "For payment registration, use params for query parameters, NOT body.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/invoice/123/:payment'"},
                "body": {"type": "object", "description": "JSON body (optional for action endpoints)"},
                "params": {"type": "object", "description": "Query params — use for payment registration"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "tripletex_delete",
        "description": "DELETE request for removing entities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee/123'"},
            },
            "required": ["path"],
        },
    },
]


# ---------------------------------------------------------------------------
# Gemini OCR
# ---------------------------------------------------------------------------

def gemini_ocr(file_contents: list[dict]) -> str:
    """Use Gemini to extract text from images. Returns OCR text or empty string."""
    image_parts = []
    for f in file_contents:
        for img in f.get("images", []):
            image_parts.append(types.Part.from_bytes(
                data=img["data"], mime_type=img["mime_type"]
            ))

    if not image_parts:
        return ""

    image_parts.append(types.Part.from_text(
        text="Extract all text, numbers, dates, names, and amounts from these images. "
             "Return the extracted data as structured text."
    ))

    config = types.GenerateContentConfig(temperature=0.0)
    response = _get_genai_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=image_parts)],
        config=config,
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: dict, client: TripletexClient) -> dict:
    """Execute a single tool call against the Tripletex API."""
    try:
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
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Message building
# ---------------------------------------------------------------------------

def build_user_message(prompt: str, file_contents: list[dict]) -> str:
    """Build the user message from prompt and file contents."""
    parts = []

    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            parts.append(f"[Attached file: {f['filename']}]\n{text}")

    parts.append(prompt)

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

def run_agent(prompt: str, file_contents: list[dict], base_url: str, session_token: str) -> dict:
    """Run the pure Claude agentic loop.

    Flow: OCR (if images) → Claude tool-use loop → done.
    """
    start_time = time.time()
    client = TripletexClient(base_url, session_token)

    # Step 1: OCR — extract text from images via Gemini
    ocr_text = gemini_ocr(file_contents)
    if ocr_text:
        logger.info(f"OCR extracted {len(ocr_text)} chars")
        file_contents.append({
            "filename": "_ocr_extracted.txt",
            "text_content": ocr_text,
            "images": [],
        })

    # Step 2: Build messages
    system_prompt = build_system_prompt()
    user_message = build_user_message(prompt, file_contents)
    messages = [{"role": "user", "content": user_message}]

    claude_client = get_claude_client()

    # Step 3: Agentic loop
    iteration = 0
    for iteration in range(MAX_ITERATIONS):
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            logger.warning(f"Timeout after {elapsed:.0f}s at iteration {iteration}")
            break

        logger.info(f"Iteration {iteration + 1}/{MAX_ITERATIONS} ({elapsed:.0f}s elapsed)")

        with claude_client.messages.stream(
            model=CLAUDE_MODEL,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=messages,
            tools=TOOLS,
            max_tokens=16000,
            thinking={"type": "adaptive"},
        ) as stream:
            response = stream.get_final_message()

        # Check if agent is done
        if response.stop_reason == "end_turn":
            logger.info(f"Agent completed after {iteration + 1} iterations")
            break

        # Append assistant response (preserves tool_use + thinking blocks)
        messages.append({"role": "assistant", "content": response.content})

        # Execute tool calls
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            logger.info(f"No tool calls, stopping after {iteration + 1} iterations")
            break

        tool_results = []
        for block in tool_use_blocks:
            logger.info(f"  Tool: {block.name}({json.dumps(block.input, ensure_ascii=False)[:200]})")

            result = execute_tool(block.name, block.input, client)

            status = result.get("status_code", "?")
            logger.info(f"  -> {status} success={result.get('success')}")

            content = json.dumps(result)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                **({"is_error": True} if not result.get("success") else {}),
            })

        messages.append({"role": "user", "content": tool_results})

    total_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Agent done: {iteration + 1} iterations, {total_ms}ms total")

    return {"status": "completed", "iterations": iteration + 1, "time_ms": total_ms}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_agent.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: rewrite agent as pure Claude agentic loop with streaming and adaptive thinking"
```

---

## Task 3: Simplify main.py

Remove any references to the old planner/executor. Keep `_preconfigure_bank_account` (it's needed for invoice tasks). The main change: `run_agent` signature stays the same, so `main.py` barely changes.

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Verify main.py works with new agent**

The current `main.py` already calls `run_agent(prompt, file_contents, base_url, session_token)` — this signature is preserved in the new `agent.py`. The only change needed is removing the import of `file_handler.process_files` being fine (it's unchanged) and verifying no stale imports.

Read `main.py` and confirm it only imports `run_agent` from `agent` and `process_files` from `file_handler`. Both are preserved. No changes needed to main.py.

- [ ] **Step 2: Run existing main test**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS (or if tests reference old imports, they need updating — see Task 5)

- [ ] **Step 3: Commit (if any changes)**

```bash
git add main.py
git commit -m "chore: verify main.py works with new agent module"
```

---

## Task 4: Delete Old Files

Remove the old deterministic path files that are now replaced by the pure agent approach.

**Files to delete:**
- `planner.py`
- `executor.py`
- `task_registry.py`
- `api_knowledge/cheat_sheet.py`
- `api_knowledge/__init__.py`
- `tests/test_planner.py`
- `tests/test_executor.py`
- `tests/test_task_registry.py`

- [ ] **Step 1: Delete old source files**

```bash
git rm planner.py executor.py task_registry.py
git rm -r api_knowledge/
```

- [ ] **Step 2: Delete old test files**

```bash
git rm tests/test_planner.py tests/test_executor.py tests/test_task_registry.py
```

- [ ] **Step 3: Run remaining tests to ensure nothing breaks**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All remaining tests PASS. No imports of deleted modules.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove planner, executor, task_registry, api_knowledge — replaced by pure agent"
```

---

## Task 5: Update Remaining Tests

Fix `tests/test_main.py` and `tests/test_file_handler.py` if they have stale imports or references to deleted modules.

**Files:**
- Modify: `tests/test_main.py` (if needed)
- Modify: `tests/test_file_handler.py` (if needed)

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v --ignore=tests/integration`

If there are import errors or failures referencing `planner`, `executor`, or `task_registry`, fix them. The test for `file_handler.py` should pass unchanged. The test for `main.py` may need mock updates if it mocked planner/executor.

- [ ] **Step 2: Fix any broken tests**

Common fixes:
- `tests/test_main.py`: If it mocks `planner.parse_prompt` or `executor.execute_plan`, update to mock `agent.run_agent` instead.
- `tests/test_file_handler.py`: Should pass unchanged — no dependency on deleted modules.

- [ ] **Step 3: Run full suite again to confirm**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "fix: update tests for pure agent architecture"
```

---

## Task 6: Local Smoke Test

Verify the new agent works end-to-end against the sandbox before deploying.

**Files:**
- Modify: `smoke_test.py` (if needed to work with new agent)

- [ ] **Step 1: Start the local server**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: Send a simple test request**

```bash
curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Opprett en avdeling med navn Salg og avdelingsnummer 100",
    "files": [],
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "YOUR_SANDBOX_TOKEN"
    }
  }'
```

Expected: `{"status": "completed"}` and logs showing Claude making 1 POST /department call.

- [ ] **Step 3: Test a multi-step flow**

```bash
curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a customer named Test AS, then create a product named Consulting at 1000 NOK excl VAT, then create an order and invoice for this customer with 1 unit of the product",
    "files": [],
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "YOUR_SANDBOX_TOKEN"
    }
  }'
```

Expected: `{"status": "completed"}` with logs showing customer → product → order → invoice chain.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: smoke test fixes from local testing"
```

---

## Task 7: Deploy to Cloud Run

Deploy the new pure agent to Cloud Run and submit to the competition.

- [ ] **Step 1: Deploy**

```bash
gcloud run deploy ai-accounting-agent-det \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --set-env-vars GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global \
  --min-instances 1
```

- [ ] **Step 2: Verify health endpoint**

```bash
curl https://YOUR-CLOUD-RUN-URL/health
```

Expected: `{"status": "ok"}`

- [ ] **Step 3: Submit to competition**

Go to `https://app.ainm.no/submit/tripletex` and submit the Cloud Run URL.

- [ ] **Step 4: Monitor results**

Watch the competition dashboard for scores. The key metric: do Tier 2/3 multi-step tasks that previously scored 0% now score >0%?

- [ ] **Step 5: Commit deployment config**

```bash
git add -A
git commit -m "chore: deploy pure agent to Cloud Run"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | prompts.py | System prompt with API ref + recipes + rules |
| 2 | agent.py | Clean agentic loop with streaming + adaptive thinking |
| 3 | main.py | Verified compatibility (minimal changes) |
| 4 | Cleanup | Delete planner, executor, registry, api_knowledge |
| 5 | Tests | Updated test suite for new architecture |
| 6 | Smoke test | Local end-to-end verification |
| 7 | Deploy | Cloud Run deployment + competition submission |

**Total estimated code:** ~650 lines (down from 2000+). One code path. One prompt to iterate on.

**After deployment:** The fastest path to improving scores is prompt iteration: submit → read results → adjust recipes/rules in prompts.py → redeploy → repeat.
