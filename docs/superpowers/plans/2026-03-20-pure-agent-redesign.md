# Pure Agent Redesign — Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two-path deterministic+fallback architecture with a single Claude Opus 4.6 agentic loop using 4 REST tools and a recipe-enhanced system prompt. Cover all 12 observed competition task types + anticipated Tier 3.

**Architecture:** Single Claude agentic loop with streaming, adaptive thinking, and prompt caching. Gemini retained for OCR only. System prompt imports the 941-line cheat sheet from `api_knowledge/cheat_sheet.py` and adds rules + recipes for all known and anticipated task categories.

**Tech Stack:** Python 3.11 (Docker) / 3.13 (local), FastAPI, anthropic[vertex] (AnthropicVertex), google-genai (Gemini OCR), Docker, Cloud Run (europe-north1)

**Spec:** `docs/superpowers/specs/2026-03-20-pure-agent-redesign.md`

**Ground Truth:** `docs/analysis/competition-ground-truth.md` — 25 real competition requests, 12 task types

---

## What Changed Since v1

| Issue | v1 Plan | v2 Fix |
|-------|---------|--------|
| Deletes api_knowledge/ | Duplicated API ref in prompts.py (~300 lines) | **Keep** api_knowledge/cheat_sheet.py (941 lines), import it |
| Recipes incomplete | 10 recipes for basic flows | **16 recipes** covering all 12 competition task types + 4 Tier 3 |
| Missing executor behaviors | vatType retry, PM entitlements lost | Explicit gotchas/recipes in system prompt |
| main.py changes | "Simplify, minimal changes" | **Keep as-is** — already correct with GCS logging |
| System prompt size | "~3000 tokens" | **~6000 tokens** (cheat sheet ~4K + rules/recipes ~2K) |
| Tests reference old routing | Plan rewrites all tests | Preserve working tests, only rewrite routing tests |

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `prompts.py` | **Create** | Rules, recipes, gotchas. Imports cheat sheet from api_knowledge. |
| `agent.py` | **Rewrite** | Claude agentic loop (streaming, timeout, tools, OCR). No planner/executor. |
| `main.py` | **Keep as-is** | Already correct: GCS logging, bank pre-config, both POST routes. |
| `tripletex_api.py` | **Keep** | Unchanged. |
| `file_handler.py` | **Keep** | Unchanged. |
| `claude_client.py` | **Keep** | Unchanged. |
| `api_knowledge/cheat_sheet.py` | **Keep** | 941-line API reference. Actively updated. Imported by prompts.py. |
| `api_knowledge/__init__.py` | **Keep** | Package init. |
| `planner.py` | **Delete** | Replaced by Claude's own reasoning. |
| `executor.py` | **Delete** | Replaced by tool-use loop. |
| `task_registry.py` | **Delete** | Replaced by system prompt recipes. |
| `tests/test_agent.py` | **Rewrite** | New tests for pure agent loop (no routing, no FallbackContext). |
| `tests/test_prompts.py` | **Create** | Tests for system prompt construction. |
| `tests/test_main.py` | **Keep** | Already works — mocks `run_agent` which keeps same signature. |
| `tests/test_planner.py` | **Delete** | No planner. |
| `tests/test_executor.py` | **Delete** | No executor. |
| `tests/test_task_registry.py` | **Delete** | No registry. |
| `tests/test_file_handler.py` | **Keep** | Unchanged. |
| `tests/test_tripletex_api.py` | **Keep** | Unchanged. |
| `tests/competition_tasks/` | **Keep** | 23 JSON fixtures for smoke testing. |
| `smoke_test.py` | **Keep** | May need minor updates if import paths change. |

---

## Task 1: Create prompts.py — Rules + Recipes

The system prompt is the brain of the agent. It imports the full API reference from `api_knowledge/cheat_sheet.py` and adds: scoring rules, known constants, recipes for all 12+ task types, critical gotchas from executor.py, and Tier 3 exploration guidance.

**Files:**
- Create: `prompts.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompts.py
"""Tests for system prompt construction."""
from prompts import build_system_prompt


class TestSystemPromptStructure:
    def test_contains_api_reference(self):
        """System prompt includes the full Tripletex API cheat sheet."""
        prompt = build_system_prompt()
        # Core endpoints from cheat sheet
        assert "POST /employee" in prompt
        assert "POST /customer" in prompt
        assert "POST /invoice" in prompt
        assert "POST /order" in prompt
        assert "POST /travelExpense" in prompt
        assert "POST /ledger/voucher" in prompt
        # Tier 3 endpoints from expanded cheat sheet
        assert "POST /bank/reconciliation" in prompt
        assert "POST /timesheet/entry" in prompt
        assert "POST /asset" in prompt
        assert "POST /incomingInvoice" in prompt
        assert "POST /purchaseOrder" in prompt
        assert "POST /inventory" in prompt

    def test_contains_today_date(self):
        from datetime import date
        prompt = build_system_prompt()
        assert date.today().isoformat() in prompt

    def test_contains_known_constants(self):
        prompt = build_system_prompt()
        assert "162" in prompt  # Norway country ID
        assert "NOK" in prompt

    def test_contains_scoring_rules(self):
        prompt = build_system_prompt()
        assert "4xx" in prompt or "error" in prompt.lower()
        assert "minimize" in prompt.lower() or "efficiency" in prompt.lower()

    def test_contains_payment_gotcha(self):
        """Payment registration uses QUERY PARAMS, not body."""
        prompt = build_system_prompt()
        assert "QUERY" in prompt
        assert ":payment" in prompt

    def test_contains_vattype_retry_guidance(self):
        """vatType retry pattern from executor.py is preserved."""
        prompt = build_system_prompt()
        assert "Ugyldig" in prompt or "vatType" in prompt

    def test_contains_pm_entitlements_guidance(self):
        """Project manager entitlements pattern from executor.py is preserved."""
        prompt = build_system_prompt()
        assert "grantEntitlementsByTemplate" in prompt or "entitlement" in prompt.lower()


class TestRecipeCoverage:
    """Verify recipes exist for all 12 observed competition task types."""

    def test_recipe_create_customer(self):
        assert "POST /customer" in build_system_prompt()

    def test_recipe_create_employee(self):
        prompt = build_system_prompt()
        assert "userType" in prompt
        assert "GET /department" in prompt

    def test_recipe_create_supplier(self):
        assert "POST /supplier" in build_system_prompt()

    def test_recipe_create_departments_batch(self):
        prompt = build_system_prompt()
        assert "department" in prompt.lower()

    def test_recipe_create_invoice(self):
        prompt = build_system_prompt()
        assert "orderLines" in prompt
        assert "invoiceDueDate" in prompt

    def test_recipe_create_project(self):
        prompt = build_system_prompt()
        assert "projectManager" in prompt

    def test_recipe_register_payment(self):
        prompt = build_system_prompt()
        assert "paymentTypeId" in prompt
        assert "paidAmount" in prompt

    def test_recipe_run_salary(self):
        prompt = build_system_prompt()
        assert "salary" in prompt.lower()

    def test_recipe_fixed_price_project(self):
        prompt = build_system_prompt()
        assert "isFixedPrice" in prompt or "fixedprice" in prompt

    def test_recipe_register_supplier_invoice(self):
        prompt = build_system_prompt()
        assert "supplierInvoice" in prompt or "incomingInvoice" in prompt

    def test_recipe_create_order(self):
        prompt = build_system_prompt()
        assert "POST /order" in prompt

    def test_recipe_custom_dimension(self):
        prompt = build_system_prompt()
        assert "dimension" in prompt.lower() or "salesmodule" in prompt.lower()

    def test_recipe_tier3_bank_reconciliation(self):
        prompt = build_system_prompt()
        assert "reconciliation" in prompt.lower()

    def test_recipe_tier3_guidance(self):
        prompt = build_system_prompt()
        assert "fields=*" in prompt


class TestPromptImportsCheatSheet:
    def test_cheat_sheet_is_imported_not_duplicated(self):
        """prompts.py imports from api_knowledge, not a copy."""
        import prompts
        # Verify it references the cheat sheet module
        from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET
        prompt = build_system_prompt()
        # Cheat sheet content should be in the prompt
        assert "EMPLOYEE EMPLOYMENT" in prompt  # Deep content from cheat sheet
        assert "BANK RECONCILIATION" in prompt  # Tier 3 content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'prompts'`

- [ ] **Step 3: Write prompts.py**

```python
# prompts.py
"""System prompt for the Claude accounting agent.

Imports the full API reference from api_knowledge/cheat_sheet.py (941 lines,
actively maintained, covers all Tier 1-3 endpoints).

Adds: scoring rules, known constants, recipes for all observed competition
task types, critical gotchas from the old executor, and Tier 3 guidance.
"""

from datetime import date

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET


def build_system_prompt() -> str:
    """Build the complete system prompt for the Claude accounting agent."""
    today = date.today().isoformat()

    return f"""You are an expert AI accounting agent for the Tripletex system. Your job is to complete accounting tasks by making API calls using the provided tools. Tasks may be in Norwegian, English, Spanish, Portuguese, German, or French.

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
  BUT: vatType IDs vary per sandbox. If a product POST fails with "Ugyldig mva-kode",
  retry WITHOUT vatType — Tripletex assigns a valid default. For orderLines, vatType is optional.

## Critical Gotchas
- **Payment registration**: PUT /invoice/{{id}}/:payment uses QUERY PARAMS, NOT body.
  Params: ?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1
- **Object refs** are ALWAYS {{"id": <int>}}, never bare integers.
- **departmentNumber** is a STRING, not an int.
- **orderLines** MUST be embedded in the order POST body (saves calls).
- **Voucher postings** MUST balance (sum of amounts = 0). Rows start at 1 (row 0 is reserved).
- **Ledger account IDs**: Look up with GET /ledger/account?number=XXXX — never guess IDs.
- **Fresh account**: Tripletex starts EMPTY. Create prerequisites before dependents.
- **PUT updates**: Always include the "version" field from the GET response.
- **vatType retry**: If POST /product fails with "Ugyldig mva-kode", retry WITHOUT vatType.
- **PM entitlements**: Before creating a project, the projectManager employee may need
  entitlements granted via PUT /employee/entitlement/:grantEntitlementsByTemplate.
  If project creation fails with a permissions error, grant entitlements first then retry.
- **Bank account**: Invoices require a bank account on ledger 1920. This is pre-configured
  automatically, but if invoice creation fails with a bank account error, use:
  GET /ledger/account?number=1920 → PUT /ledger/account/{{id}} with bankAccountNumber.
- **Supplier invoice vs incoming invoice**: "Register supplier invoice" may use either
  POST /incomingInvoice (newer API) or POST /supplierInvoice flow. Check what the prompt
  describes and use the appropriate endpoint.

## Recipes for Known Task Types

### 1. Create Customer (Tier 1)
POST /customer {{name, email, phoneNumber, organizationNumber, physicalAddress, ...}}
Include all fields mentioned in the prompt. Address uses country: {{"id": 162}} for Norway.

### 2. Create Employee (Tier 1)
1. GET /department → capture first department ID (or create one if none exist)
2. POST /employee {{firstName, lastName, email, userType: "STANDARD", department: {{id}}}}
Include dateOfBirth, phoneNumberMobile, address if mentioned. No "isAdministrator" field exists.

### 3. Create Supplier (Tier 1)
POST /supplier {{name, email, phoneNumber, organizationNumber, ...}}
Same structure as customer but uses /supplier endpoint.

### 4. Create Departments — Batch (Tier 1)
For multiple departments, make one POST /department per department.
Each needs: name (string), departmentNumber (string — NOT int).
Number departments sequentially ("100", "200", "300") unless prompt specifies.

### 5. Create Invoice — Multi-Product (Tier 2, HIGHEST PRIORITY — 16% of competition)
1. POST /customer {{name, organizationNumber}} → capture customer_id
2. For EACH product: POST /product {{name, priceExcludingVatCurrency}} → capture product_id
   (If vatType fails, retry without it)
3. POST /order {{customer: {{id: customer_id}}, orderDate: "{today}", deliveryDate: "{today}",
   orderLines: [
     {{product: {{id: p1_id}}, count: 1, unitPriceExcludingVatCurrency: price1}},
     {{product: {{id: p2_id}}, count: 1, unitPriceExcludingVatCurrency: price2}},
     ...
   ]}} → capture order_id
4. POST /invoice {{invoiceDate: "{today}", invoiceDueDate: "30 days later",
   orders: [{{id: order_id}}]}} → capture invoice_id
5. If prompt says "send": PUT /invoice/{{invoice_id}}/:send — Body: {{"sendType": "EMAIL"}}
CRITICAL: Use UNIQUE product names/numbers. If the prompt gives specific names/prices, use them exactly.

### 6. Register Payment (Tier 2)
Full flow: create customer → products → order → invoice → payment.
1. Follow Invoice recipe above → capture invoice_id and total amount
2. GET /invoice/paymentType → find appropriate payment type ID
3. PUT /invoice/{{invoice_id}}/:payment?paymentDate={today}&paymentTypeId=N&paidAmount=TOTAL&paidAmountCurrency=1
CRITICAL: Payment uses QUERY PARAMS on PUT, NOT a request body.

### 7. Create Project (Tier 2)
1. POST /customer {{name, organizationNumber}} → capture customer_id
2. GET /department → capture dept_id (or create if needed)
3. POST /employee {{firstName: "PM Name", lastName: "...", userType: "STANDARD", department: {{id: dept_id}}}} → capture pm_id
   (Or search for existing employee if prompt references one)
4. POST /project {{name, projectManager: {{id: pm_id}}, startDate: "{today}",
   customer: {{id: customer_id}}, description, ...}} → capture project_id
5. If prompt mentions participants: POST /project/participant {{project: {{id}}, employee: {{id}}}}

### 8. Fixed-Price Project (Tier 2)
1. Follow Create Project recipe → capture project_id
2. GET /project/{{project_id}} → capture version
3. PUT /project/{{project_id}} {{id: project_id, version: V, isFixedPrice: true, fixedprice: AMOUNT}}
The fixedprice is set via PUT on the project, not a separate endpoint.

### 9. Run Salary (Tier 2)
1. Search or create employee: GET /employee?email=X or POST /employee
2. GET /employee/employment?employeeId=ID → check for existing employment
3. If no employment: POST /employee/employment {{employee: {{id}}, startDate: "{today}"}}
4. POST /employee/employment/details {{employment: {{id}}, date: "{today}",
   annualSalary: AMOUNT, employmentType: "ORDINARY"}}
5. GET /salary/type → find salary type IDs for base salary + additions
6. POST /salary/transaction {{date: "{today}", month: CURRENT_MONTH, year: CURRENT_YEAR,
   payslips: [{{employee: {{id}}, date: "{today}", specifications: [
     {{salaryType: {{id}}, rate: AMOUNT, count: 1}}
   ]}}]}}
NOTE: The salary API is complex. If the above fails, read the error message carefully.
Use GET /salary/type?fields=* to discover available salary types and their structure.

### 10. Register Supplier Invoice (Tier 2)
1. POST /supplier {{name, organizationNumber}} → capture supplier_id
2. POST /incomingInvoice {{
     invoiceHeader: {{vendorId: supplier_id, invoiceDate: "YYYY-MM-DD",
       dueDate: "YYYY-MM-DD", currencyId: 1, invoiceAmount: AMOUNT,
       description: "...", invoiceNumber: "INV-XXX"}},
     version: 0
   }}
Alternative: Some prompts may reference existing supplier invoices. Use GET /supplierInvoice to search.
For approval: PUT /supplierInvoice/{{id}}/:approve

### 11. Create Order (Tier 2)
1. POST /customer {{name, organizationNumber}} → capture customer_id
2. For each product: POST /product {{name, priceExcludingVatCurrency}} → capture product_ids
3. POST /order {{customer: {{id}}, orderDate: "{today}", deliveryDate: "{today}",
   orderLines: [{{product: {{id}}, count, unitPriceExcludingVatCurrency}}]}}

### 12. Custom Dimension + Voucher (Tier 2)
1. GET /company/salesmodules → check available modules
2. POST /company/salesmodules to activate the dimension module if needed
3. The "custom dimension" likely involves creating custom fields or categories.
   Explore with GET requests using ?fields=* to discover the dimension API.
4. If the task includes posting a voucher with the dimension:
   - GET /ledger/account?number=XXXX for each account
   - POST /ledger/voucher with postings that include the dimension reference

### Tier 3 Recipes (anticipated — opens Saturday)

### 13. Bank Reconciliation from CSV
1. Parse the CSV data from the prompt/attachment
2. GET /ledger/account?number=1920 (or the bank account specified) → account_id
3. GET /bank/reconciliation/>last?accountId=ID → check for existing reconciliation
4. POST /bank/reconciliation {{account: {{id}}, type: "MANUAL", bankAccountClosingBalanceCurrency: BALANCE}}
5. For each transaction: create matching postings or reconciliation matches
6. Use POST /bank/reconciliation/match to link transactions to postings

### 14. Timesheet / Hours Registration
1. GET /activity/>forTimeSheet?employeeId=X&date=YYYY-MM-DD → find activity
2. POST /timesheet/entry {{activity: {{id}}, employee: {{id}}, project: {{id}},
   date: "YYYY-MM-DD", hours: N, comment: "..."}}

### 15. Asset Registration
1. GET /ledger/account?number=XXXX → find asset account and depreciation account
2. POST /asset {{name, dateOfAcquisition, acquisitionCost, account: {{id}},
   lifetime: MONTHS, depreciationAccount: {{id}},
   depreciationMethod: "STRAIGHT_LINE", depreciationFrom: "YYYY-MM-DD"}}

### 16. Year-End / Ledger Corrections
1. Identify the accounts involved (GET /ledger/account?number=XXXX)
2. POST /ledger/voucher with balanced postings
3. For reversals: PUT /ledger/voucher/{{id}}/:reverse
4. Use GET /balanceSheet?dateFrom=X&dateTo=X to verify account balances

## Handling Unknown Tasks
For tasks you don't recognize:
1. Analyze the prompt carefully — what is the end goal?
2. Use GET with ?fields=* to discover entity structures you're unsure about.
3. Read error messages carefully — Tripletex tells you exactly what's missing.
4. Break complex problems into smaller API calls.
5. If a module isn't active, try POST /company/salesmodules to enable it.
6. The cheat sheet below covers ALL known endpoints — search it for the right one.

{TRIPLETEX_API_CHEAT_SHEET}
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add prompts.py tests/test_prompts.py
git commit -m "feat: system prompt with 16 recipes, scoring rules, and cheat sheet import"
```

---

## Task 2: Rewrite agent.py — Pure Agentic Loop

Replace the entire agent.py with a clean agentic loop. Remove all imports of planner/executor/task_registry. Keep: tool definitions, execute_tool, gemini_ocr, Gemini client. Add: streaming, adaptive thinking, prompt caching, build_user_message.

**Key changes from current agent.py:**
- Remove: `from planner import parse_prompt, is_known_pattern, FallbackContext`
- Remove: `from executor import execute_plan`
- Remove: `from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET`
- Add: `from prompts import build_system_prompt`
- Remove: `build_system_prompt()` (moved to prompts.py)
- Remove: `run_tool_loop()` (merged into `run_agent`)
- Rewrite: `run_agent()` — single clean loop, no deterministic path
- Add: streaming with `messages.stream()` + `get_final_message()`
- Add: `thinking={"type": "adaptive"}`
- Add: prompt caching via `cache_control` on system prompt
- Add: `build_user_message()` function
- Add: `is_error: True` on failed tool results
- Change: `MAX_ITERATIONS` from 25 to 20
- Keep: `execute_tool()` with try/except wrapping
- Keep: `gemini_ocr()` unchanged
- Keep: `TOOLS` definitions unchanged
- Keep: lazy `_get_genai_client()` pattern

**Files:**
- Rewrite: `agent.py`
- Rewrite: `tests/test_agent.py`

- [ ] **Step 1: Write the failing tests**

```python
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
        prompt = agent_module.build_system_prompt()
        assert "POST /employee" in prompt

    def test_includes_payment_gotcha(self):
        prompt = agent_module.build_system_prompt()
        assert "QUERY" in prompt

    def test_includes_known_constants(self):
        prompt = agent_module.build_system_prompt()
        assert "id=162" in prompt or '"id": 162' in prompt
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
        mock_client.delete.assert_called_once_with("/employee/1")

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
```

- [ ] **Step 2: Run test to verify failing**

Run: `python -m pytest tests/test_agent.py -v`
Expected: FAIL — ImportError on `build_user_message` (doesn't exist yet) and `from planner import` (old agent.py still has it)

- [ ] **Step 3: Rewrite agent.py**

Replace the entire file:

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
# Gemini client (retained for OCR only — lazy init, NOT module-level)
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

## Task 3: Verify main.py Compatibility

main.py is already correct. Verify it works with the new agent module.

**Files:**
- Keep: `main.py` (no changes)

- [ ] **Step 1: Run main.py tests**

Run: `python -m pytest tests/test_main.py -v`

The test mocks `run_agent` at the `main` module level, so it should pass regardless of agent.py internals. If it fails due to import-time errors from the old `planner.py` imports being gone, the test's mock setup already patches before import.

Expected: All PASS

- [ ] **Step 2: Verify both POST routes work**

The evaluator sends `POST /` (root path). main.py already handles both `@app.post("/")` and `@app.post("/solve")`. No changes needed.

- [ ] **Step 3: Verify GCS logging preserved**

main.py already has `_save_request_to_gcs()` with `REQUEST_LOG_BUCKET`. No changes needed.

---

## Task 4: Delete Old Files

Remove files replaced by the pure agent approach. Keep api_knowledge/.

**Files to delete:**
- `planner.py`
- `executor.py`
- `task_registry.py`
- `tests/test_planner.py`
- `tests/test_executor.py`
- `tests/test_task_registry.py`

- [ ] **Step 1: Delete old source files**

```bash
git rm planner.py executor.py task_registry.py
```

- [ ] **Step 2: Delete old test files**

```bash
git rm tests/test_planner.py tests/test_executor.py tests/test_task_registry.py
```

- [ ] **Step 3: Run all remaining tests**

Run: `python -m pytest tests/ -v --ignore=tests/integration`

Expected: All PASS. Specifically verify:
- `tests/test_agent.py` — new tests, no old imports
- `tests/test_main.py` — mocks run_agent, no planner/executor dependency
- `tests/test_prompts.py` — new tests
- `tests/test_file_handler.py` — unchanged, no deleted-module dependency
- `tests/test_tripletex_api.py` — unchanged

- [ ] **Step 4: Commit**

```bash
git rm planner.py executor.py task_registry.py tests/test_planner.py tests/test_executor.py tests/test_task_registry.py && git commit -m "chore: remove planner, executor, task_registry — replaced by pure agent"
```

---

## Task 5: Update CLAUDE.md

Update the project guide to reflect the new architecture.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update architecture section**

Replace the architecture section in CLAUDE.md with:

```markdown
## Architecture

```
POST / → main.py
  ├── _save_request_to_gcs()       — full payload to GCS (if REQUEST_LOG_BUCKET set)
  ├── _preconfigure_bank_account()  — ensures ledger 1920 has bank account
  ├── gemini_ocr()                 — Gemini extracts text from images (if any)
  └── Claude Opus 4.6 agentic loop — streaming, adaptive thinking, 4 REST tools
      ├── system prompt (rules + recipes + api_knowledge/cheat_sheet.py)
      ├── max 20 iterations, 270s timeout
      └── return {"status": "completed"}
```
```

- [ ] **Step 2: Update key files table**

Remove planner.py, executor.py, task_registry.py entries. Add prompts.py.

- [ ] **Step 3: Update implementation notes**

Remove references to deterministic path, FallbackContext, etc.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for pure agent architecture"
```

---

## Task 6: Local Smoke Test

Verify the new agent works end-to-end against the sandbox.

- [ ] **Step 1: Start local server**

```bash
source .env && uvicorn main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: Test simple task (Tier 1)**

```bash
curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Opprett en kunde med namn Testfirma AS og e-post post@testfirma.no",
    "files": [],
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "YOUR_SANDBOX_TOKEN"
    }
  }'
```

Expected: `{"status": "completed"}`, logs show 1 POST /customer call, 0 errors.

- [ ] **Step 3: Test multi-step task (Tier 2 — invoice)**

```bash
curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Opprett en faktura til kunden Testfaktura AS (org.nr 123456789) med en produktlinje: Konsulenttimer (10000 NOK ekskl. MVA, 5 timer)",
    "files": [],
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "YOUR_SANDBOX_TOKEN"
    }
  }'
```

Expected: `{"status": "completed"}`, logs show customer → product → order → invoice chain.

- [ ] **Step 4: Test with competition fixture**

```bash
cat tests/competition_tasks/10_create_invoice_no.json | curl -X POST http://localhost:8000/solve \
  -H "Content-Type: application/json" \
  -d @-
```

Note: Competition fixtures have truncated prompts. Use for format testing, not full correctness.

- [ ] **Step 5: Fix any issues found**

```bash
git add -A && git commit -m "fix: smoke test fixes from local testing"
```

---

## Task 7: Deploy to Dev Container

Deploy to the dev container first, then competition after verification.

- [ ] **Step 1: Deploy to dev**

```bash
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 --project ai-nm26osl-1799 --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs" --quiet
```

- [ ] **Step 2: Verify dev health**

```bash
curl https://ai-accounting-agent-det-590159115697.europe-north1.run.app/health
```

Expected: `{"status": "ok"}`

- [ ] **Step 3: Test dev with a real task**

```bash
curl -X POST https://ai-accounting-agent-det-590159115697.europe-north1.run.app/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Opprett en kunde med namn CloudTest AS og e-post test@cloud.no",
    "files": [],
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "YOUR_SANDBOX_TOKEN"
    }
  }'
```

- [ ] **Step 4: Deploy to competition (only after dev verified)**

```bash
gcloud run deploy accounting-agent-comp --source . --region europe-north1 --project ai-nm26osl-1799 --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs" --quiet
```

- [ ] **Step 5: Submit to competition**

Go to `https://app.ainm.no/submit/tripletex` and submit the competition URL.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: deploy pure agent to dev and competition"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | prompts.py | 16 recipes + rules + cheat sheet import (~6K tokens) |
| 2 | agent.py | Clean agentic loop: streaming, adaptive thinking, prompt caching |
| 3 | main.py | Verify compatibility (no changes needed) |
| 4 | Cleanup | Delete planner.py, executor.py, task_registry.py + tests |
| 5 | CLAUDE.md | Update documentation for new architecture |
| 6 | Smoke test | Local end-to-end verification against sandbox |
| 7 | Deploy | Dev container → verify → competition container |

**What's preserved:**
- `api_knowledge/cheat_sheet.py` (941 lines, actively maintained)
- `main.py` (GCS logging, bank pre-config, both POST routes)
- `claude_client.py` (AnthropicVertex singleton)
- `tripletex_api.py` (HTTP wrapper, 30s timeouts)
- `file_handler.py` (PDF/image/text processing)
- `tests/competition_tasks/` (23 fixtures)
- Lazy genai client pattern
- vatType retry guidance (now in prompt, not code)
- PM entitlements guidance (now in prompt, not code)
- Bank pre-config (still in main.py code)

**What's new:**
- `prompts.py` — system prompt brain (rules + 16 recipes + gotchas)
- Streaming with adaptive thinking
- Prompt caching via cache_control
- is_error flag on failed tool results

**After deployment:** Iterate on `prompts.py` recipes based on competition scores. Each recipe adjustment is a prompt edit → redeploy → resubmit cycle.
