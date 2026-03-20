# Deterministic Execution Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic execution path that parses prompts via Gemini structured output, then executes optimal API call sequences in code — falling back to the existing tool-use loop for unknown patterns.

**Architecture:** Gemini parses prompt → structured TaskPlan (1 LLM call). Code validates against entity registry, topologically sorts dependencies, executes API calls threading response IDs. Falls back to tool-use loop if pattern is unknown or execution fails.

**Tech Stack:** google-genai SDK (Vertex AI structured output), FastAPI, dataclasses

**Spec:** `docs/superpowers/specs/2026-03-20-deterministic-execution-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `task_registry.py` | **Create** | Entity schemas, known constants, lookup constants, dependency graph |
| `planner.py` | **Create** | Gemini structured output parse, pattern matcher |
| `executor.py` | **Create** | Deterministic executor: topo-sort, ref threading, payload building |
| `agent.py` | **Modify** | Router: parse → match → deterministic or tool-use fallback |
| `tests/test_task_registry.py` | **Create** | Registry completeness and DAG validation |
| `tests/test_planner.py` | **Create** | Parse + pattern matcher tests |
| `tests/test_executor.py` | **Create** | Executor logic with mocked TripletexClient |
| `tests/test_agent.py` | **Modify** | Add routing tests |

---

### Task 1: Create task_registry.py

**Files:**
- Create: `task_registry.py`
- Create: `tests/test_task_registry.py`

- [ ] **Step 1: Write registry tests**

```python
# tests/test_task_registry.py
"""Tests for task_registry.py — schema completeness and DAG validation."""

from task_registry import ENTITY_SCHEMAS, KNOWN_CONSTANTS, DEPENDENCIES, LOOKUP_CONSTANTS


class TestEntitySchemas:
    def test_all_competition_entities_covered(self):
        expected = {
            "department", "employee", "customer", "product",
            "order", "invoice", "register_payment",
            "travel_expense", "travel_expense_cost",
            "project", "contact", "voucher",
        }
        assert expected == set(ENTITY_SCHEMAS.keys())

    def test_each_schema_has_required_keys(self):
        for name, schema in ENTITY_SCHEMAS.items():
            assert "endpoint" in schema, f"{name} missing endpoint"
            assert "method" in schema, f"{name} missing method"
            assert "required" in schema, f"{name} missing required"

    def test_employee_defaults(self):
        emp = ENTITY_SCHEMAS["employee"]
        assert emp["defaults"]["userType"] == "STANDARD"

    def test_order_embeds_orderlines(self):
        assert "orderLines" in ENTITY_SCHEMAS["order"].get("embed", [])

    def test_register_payment_uses_query_params(self):
        assert ENTITY_SCHEMAS["register_payment"].get("use_query_params") is True

    def test_travel_expense_cost_has_lookup_constants(self):
        tec = ENTITY_SCHEMAS["travel_expense_cost"]
        assert "costCategory" in tec.get("lookup_constants_inject", {})
        assert "paymentType" in tec.get("lookup_constants_inject", {})


class TestKnownConstants:
    def test_vat_rates(self):
        assert KNOWN_CONSTANTS["vat_25"] == {"id": 3}
        assert KNOWN_CONSTANTS["vat_15"] == {"id": 5}
        assert KNOWN_CONSTANTS["vat_0"] == {"id": 6}

    def test_nok_and_norway(self):
        assert KNOWN_CONSTANTS["nok"] == {"id": 1}
        assert KNOWN_CONSTANTS["norway"] == {"id": 162}


class TestDependencies:
    def test_employee_depends_on_department(self):
        assert "department" in DEPENDENCIES["employee"]

    def test_invoice_depends_on_order(self):
        assert "order" in DEPENDENCIES["invoice"]

    def test_no_cycles(self):
        """Verify dependency graph is a valid DAG (no cycles)."""
        visited = set()
        in_stack = set()

        def has_cycle(node):
            if node in in_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for dep in DEPENDENCIES.get(node, []):
                if has_cycle(dep):
                    return True
            in_stack.remove(node)
            return False

        for entity in DEPENDENCIES:
            assert not has_cycle(entity), f"Cycle detected involving {entity}"

    def test_all_dependency_targets_exist_in_schemas(self):
        """Every dependency target should be a known entity."""
        for entity, deps in DEPENDENCIES.items():
            for dep in deps:
                assert dep in ENTITY_SCHEMAS or dep in DEPENDENCIES, \
                    f"{entity} depends on unknown entity {dep}"
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_task_registry.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write task_registry.py**

```python
# task_registry.py
"""Static entity registry for deterministic execution.

Contains all knowledge needed to validate and execute Tripletex API calls
without LLM involvement: entity schemas, known constants, and dependency graph.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Entity Schemas
# ---------------------------------------------------------------------------

ENTITY_SCHEMAS = {
    "department": {
        "endpoint": "/department",
        "method": "POST",
        "required": ["name", "departmentNumber"],
        "defaults": {},
        "auto_generate": ["departmentNumber"],
    },
    "employee": {
        "endpoint": "/employee",
        "method": "POST",
        "required": ["firstName", "lastName", "userType", "department"],
        "defaults": {"userType": "STANDARD"},
        "lookup_defaults": {"department": "/department"},
    },
    "customer": {
        "endpoint": "/customer",
        "method": "POST",
        "required": ["name"],
        "defaults": {},
    },
    "product": {
        "endpoint": "/product",
        "method": "POST",
        "required": ["name"],
        "defaults": {},
    },
    "order": {
        "endpoint": "/order",
        "method": "POST",
        "required": ["customer", "orderDate", "deliveryDate"],
        "defaults": {},
        "auto_generate": ["orderDate", "deliveryDate"],
        "embed": ["orderLines"],
    },
    "invoice": {
        "endpoint": "/invoice",
        "method": "POST",
        "required": ["invoiceDate", "invoiceDueDate", "orders"],
        "defaults": {},
        "auto_generate": ["invoiceDate", "invoiceDueDate"],
    },
    "register_payment": {
        "endpoint": "/invoice/{id}/:payment",
        "method": "PUT",
        "use_query_params": True,
        "required": ["paymentDate", "paidAmount", "paidAmountCurrency"],
        "defaults": {"paidAmountCurrency": 1, "paymentTypeId": 0},
        "auto_generate": ["paymentDate"],
    },
    "travel_expense": {
        "endpoint": "/travelExpense",
        "method": "POST",
        "required": ["employee", "title"],
        "defaults": {},
    },
    "travel_expense_cost": {
        "endpoint": "/travelExpense/cost",
        "method": "POST",
        "required": ["travelExpense", "date", "amountCurrencyIncVat", "costCategory", "paymentType"],
        "defaults": {"currency": {"id": 1}},
        "auto_generate": ["date"],
        "lookup_constants_inject": {
            "costCategory": "/travelExpense/costCategory",
            "paymentType": "/travelExpense/paymentType",
        },
    },
    "project": {
        "endpoint": "/project",
        "method": "POST",
        "required": ["name", "projectManager", "startDate"],
        "defaults": {},
        "auto_generate": ["startDate"],
    },
    "contact": {
        "endpoint": "/contact",
        "method": "POST",
        "required": ["firstName", "lastName", "customer"],
        "defaults": {},
    },
    "voucher": {
        "endpoint": "/ledger/voucher",
        "method": "POST",
        "required": ["date", "description", "postings"],
        "defaults": {},
        "auto_generate": ["date"],
    },
}

# ---------------------------------------------------------------------------
# Known Constants — injected automatically, never looked up via API
# ---------------------------------------------------------------------------

KNOWN_CONSTANTS = {
    "vat_25": {"id": 3},
    "vat_15": {"id": 5},
    "vat_0": {"id": 6},
    "nok": {"id": 1},
    "norway": {"id": 162},
    "paymentTypeId_default": 0,
}

# ---------------------------------------------------------------------------
# Lookup Constants — GET once per session, cache the result
# ---------------------------------------------------------------------------

LOOKUP_CONSTANTS = {
    "costCategory": "/travelExpense/costCategory",
    "paymentType_travel": "/travelExpense/paymentType",
    "rateCategory": "/travelExpense/rateCategory",
}

# ---------------------------------------------------------------------------
# Dependency Graph — directed, acyclic
# ---------------------------------------------------------------------------

DEPENDENCIES = {
    "department": [],
    "employee": ["department"],
    "customer": [],
    "product": [],
    "contact": ["customer"],
    "order": ["customer", "product"],
    "invoice": ["order"],
    "register_payment": ["invoice"],
    "travel_expense": ["employee"],
    "travel_expense_cost": ["travel_expense"],
    "project": ["employee"],
    "voucher": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_dept_counter = 100


def generate_auto_value(field: str) -> str | dict:
    """Generate a default value for auto_generate fields."""
    global _dept_counter
    if field in ("orderDate", "deliveryDate", "invoiceDate", "invoiceDueDate",
                 "startDate", "date", "paymentDate"):
        return date.today().isoformat()
    if field == "departmentNumber":
        val = str(_dept_counter)
        _dept_counter += 1
        return val
    return ""
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_task_registry.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add task_registry.py tests/test_task_registry.py
git commit -m "feat: add task_registry with entity schemas, constants, dependency graph

Static registry for deterministic execution path. Covers all 12 competition
entity types with required fields, defaults, auto-generation, and dependencies."
```

---

### Task 2: Create planner.py — structured output parse + pattern matcher

**Files:**
- Create: `planner.py`
- Create: `tests/test_planner.py`

- [ ] **Step 1: Write planner tests**

```python
# tests/test_planner.py
"""Tests for planner.py — structured output parsing and pattern matching."""

from unittest.mock import MagicMock, patch
from dataclasses import asdict

_mock_genai_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    from planner import parse_prompt, is_known_pattern, PARSE_SYSTEM_PROMPT, FallbackContext


class TestParsePrompt:
    def test_returns_task_plan_dict(self):
        """parse_prompt returns a dict with 'actions' key."""
        mock_response = MagicMock()
        mock_response.parsed = {
            "actions": [
                {"action": "create", "entity": "department",
                 "fields": {"name": "IT", "departmentNumber": "100"},
                 "ref": "dep1", "depends_on": {}}
            ]
        }
        _mock_genai_client.models.generate_content.return_value = mock_response

        result = parse_prompt("Opprett avdeling IT", [])
        assert result is not None
        assert "actions" in result
        assert result["actions"][0]["entity"] == "department"

    def test_returns_none_on_exception(self):
        """parse_prompt returns None if Gemini call fails."""
        _mock_genai_client.models.generate_content.side_effect = Exception("timeout")
        result = parse_prompt("test", [])
        assert result is None
        _mock_genai_client.models.generate_content.side_effect = None

    def test_parse_system_prompt_includes_field_names(self):
        assert "firstName" in PARSE_SYSTEM_PROMPT
        assert "departmentNumber" in PARSE_SYSTEM_PROMPT
        assert "priceExcludingVatCurrency" in PARSE_SYSTEM_PROMPT


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

    def test_rejects_update_action(self):
        plan = {"actions": [
            {"action": "update", "entity": "employee",
             "fields": {"email": "new@test.no"},
             "ref": "emp1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_rejects_delete_action(self):
        plan = {"actions": [
            {"action": "delete", "entity": "customer",
             "fields": {}, "ref": "c1", "depends_on": {}}
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
        """Employee without dept action in plan — uses lookup_defaults."""
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

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_planner.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write planner.py**

```python
# planner.py
"""Structured output parsing and pattern matching for deterministic execution.

parse_prompt() — Gemini extracts a TaskPlan from the prompt (1 LLM call).
is_known_pattern() — Checks if the plan can be executed deterministically.
FallbackContext — Shared context for tool-use fallback handoff.
"""

import logging
import os
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from task_registry import ENTITY_SCHEMAS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (shared with agent.py)
# ---------------------------------------------------------------------------

genai_client = genai.Client(
    vertexai=True,
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "global"),
)

MODEL = "gemini-3.1-pro-preview"
PARSE_TIMEOUT = 20  # seconds

# ---------------------------------------------------------------------------
# Parse prompt
# ---------------------------------------------------------------------------

PARSE_SYSTEM_PROMPT = """You are a task parser for the Tripletex accounting API.

Given an accounting task prompt (in any language: nb, nn, en, es, pt, de, fr),
extract a structured plan of actions.

For each entity to create, extract:
- entity type (department, employee, customer, product, order, invoice, etc.)
- field values using EXACT API field names
- dependencies between entities (which entity fields reference other entities)

API field names per entity:
- department: name, departmentNumber
- employee: firstName, lastName, email, userType, department
- customer: name, email, phoneNumber, organizationNumber
- product: name, priceExcludingVatCurrency, vatType
- order: customer, orderDate, deliveryDate, orderLines[{product, count, unitPriceExcludingVatCurrency, vatType}]
- invoice: invoiceDate, invoiceDueDate, orders
- register_payment: paymentDate, paidAmount, paidAmountCurrency, paymentTypeId
- travel_expense: employee, title
- travel_expense_cost: travelExpense, date, amountCurrencyIncVat, costCategory, paymentType, currency
- project: name, projectManager, startDate
- voucher: date, description, postings[{accountNumber, amount}]
- contact: firstName, lastName, email, customer

For tasks involving sending invoices, deleting entities, or modifying existing records,
output action="update"/"delete"/"send_invoice" — these will be handled by the fallback path.

Output the TaskPlan JSON. Use "ref" labels (dep1, emp1, cust1, etc.) for
cross-references. Set depends_on to map field names to refs."""


TASK_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "entity": {"type": "string"},
                    "fields": {"type": "object"},
                    "ref": {"type": "string"},
                    "depends_on": {"type": "object"},
                },
                "required": ["action", "entity", "fields", "ref", "depends_on"],
            },
        },
    },
    "required": ["actions"],
}


def parse_prompt(prompt: str, file_contents: list[dict]) -> dict | None:
    """Parse a task prompt into a structured TaskPlan via Gemini."""
    start = time.time()

    # Build user content with file attachments
    parts: list[types.Part] = []
    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            parts.append(types.Part.from_text(
                text=f"[Attached file: {f['filename']}]\n{text}"
            ))
        for img in f.get("images", []):
            parts.append(types.Part.from_bytes(
                data=img["data"], mime_type=img["mime_type"]
            ))
    parts.append(types.Part.from_text(text=prompt))

    config = types.GenerateContentConfig(
        system_instruction=PARSE_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=TASK_PLAN_SCHEMA,
        temperature=0.0,
    )

    try:
        response = genai_client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=config,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        # Extract parsed JSON
        result = response.parsed
        if isinstance(result, dict) and "actions" in result:
            actions = result["actions"]
            entities = [a.get("entity", "?") for a in actions]
            logger.info(f"parse: task_plan_actions={len(actions)} entities={entities} parse_time_ms={elapsed_ms}")
            for a in actions:
                logger.info(f"parse: action ref={a.get('ref')} action={a.get('action')} "
                           f"entity={a.get('entity')} depends_on={a.get('depends_on')}")
            return result

        logger.warning(f"parse: unexpected response format, parse_time_ms={elapsed_ms}")
        return None

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.warning(f"parse: error=\"{e}\" parse_time_ms={elapsed_ms}")
        return None


# ---------------------------------------------------------------------------
# Pattern matcher
# ---------------------------------------------------------------------------

DETERMINISTIC_ACTIONS = {"create", "register_payment", "lookup"}


def is_known_pattern(task_plan: dict | None) -> bool:
    """Check if a TaskPlan can be executed deterministically."""
    if not task_plan or not task_plan.get("actions"):
        return False

    actions = task_plan["actions"]
    all_refs = {a["ref"] for a in actions}

    for action in actions:
        # Check 1: action type supported
        if action.get("action") not in DETERMINISTIC_ACTIONS:
            logger.info(f"match: result=fallback reason=unsupported_action:{action.get('action')}")
            return False

        # Check 2: entity type known
        entity = action.get("entity", "")
        if entity not in ENTITY_SCHEMAS:
            logger.info(f"match: result=fallback reason=unknown_entity:{entity}")
            return False

        # Check 3: depends_on refs resolve
        depends_on = action.get("depends_on", {})
        for field_name, ref_val in depends_on.items():
            refs_to_check = ref_val if isinstance(ref_val, list) else [ref_val]
            for ref in refs_to_check:
                if ref not in all_refs:
                    # Check if entity has lookup_defaults for this field
                    schema = ENTITY_SCHEMAS[entity]
                    if field_name not in schema.get("lookup_defaults", {}):
                        logger.info(f"match: result=fallback reason=unresolved_ref:{ref}")
                        return False

    logger.info("match: result=deterministic")
    return True


# ---------------------------------------------------------------------------
# Fallback context
# ---------------------------------------------------------------------------

@dataclass
class FallbackContext:
    """Shared context for tool-use fallback handoff."""
    task_plan: dict | None = None
    completed_refs: dict = field(default_factory=dict)
    failed_action: dict | None = None
    error: str | None = None
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_planner.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add planner.py tests/test_planner.py
git commit -m "feat: add planner with structured output parse + pattern matcher

Gemini parses prompts into TaskPlan JSON. Pattern matcher validates
against entity registry for deterministic execution eligibility."
```

---

### Task 3: Create executor.py — deterministic execution engine

**Files:**
- Create: `executor.py`
- Create: `tests/test_executor.py`

- [ ] **Step 1: Write executor tests**

```python
# tests/test_executor.py
"""Tests for executor.py — deterministic execution with mocked TripletexClient."""

from unittest.mock import MagicMock, call
from executor import execute_plan, _topological_sort, _build_payload


class TestTopologicalSort:
    def test_single_action(self):
        actions = [
            {"action": "create", "entity": "department", "ref": "dep1",
             "fields": {"name": "IT"}, "depends_on": {}},
        ]
        result = _topological_sort(actions)
        assert [a["ref"] for a in result] == ["dep1"]

    def test_respects_dependencies(self):
        actions = [
            {"action": "create", "entity": "employee", "ref": "emp1",
             "fields": {}, "depends_on": {"department": "dep1"}},
            {"action": "create", "entity": "department", "ref": "dep1",
             "fields": {"name": "IT"}, "depends_on": {}},
        ]
        result = _topological_sort(actions)
        refs = [a["ref"] for a in result]
        assert refs.index("dep1") < refs.index("emp1")

    def test_invoice_chain(self):
        actions = [
            {"action": "create", "entity": "invoice", "ref": "inv1",
             "fields": {}, "depends_on": {"orders": ["o1"]}},
            {"action": "create", "entity": "order", "ref": "o1",
             "fields": {}, "depends_on": {"customer": "c1"}},
            {"action": "create", "entity": "customer", "ref": "c1",
             "fields": {"name": "X"}, "depends_on": {}},
        ]
        result = _topological_sort(actions)
        refs = [a["ref"] for a in result]
        assert refs.index("c1") < refs.index("o1") < refs.index("inv1")


class TestBuildPayload:
    def test_simple_department(self):
        action = {"action": "create", "entity": "department",
                  "fields": {"name": "IT", "departmentNumber": "100"},
                  "ref": "dep1", "depends_on": {}}
        payload = _build_payload(action, ref_map={})
        assert payload["body"]["name"] == "IT"
        assert payload["body"]["departmentNumber"] == "100"
        assert payload["endpoint"] == "/department"
        assert payload["method"] == "POST"

    def test_injects_dependency_id(self):
        action = {"action": "create", "entity": "employee",
                  "fields": {"firstName": "Kari", "lastName": "N"},
                  "ref": "emp1", "depends_on": {"department": "dep1"}}
        payload = _build_payload(action, ref_map={"dep1": 42})
        assert payload["body"]["department"] == {"id": 42}

    def test_injects_array_dependency(self):
        action = {"action": "create", "entity": "invoice",
                  "fields": {}, "ref": "inv1",
                  "depends_on": {"orders": ["o1", "o2"]}}
        payload = _build_payload(action, ref_map={"o1": 10, "o2": 20})
        assert payload["body"]["orders"] == [{"id": 10}, {"id": 20}]

    def test_auto_generates_dates(self):
        action = {"action": "create", "entity": "order",
                  "fields": {"customer": "ignored"}, "ref": "o1", "depends_on": {}}
        payload = _build_payload(action, ref_map={})
        assert "orderDate" in payload["body"]
        assert "deliveryDate" in payload["body"]

    def test_injects_defaults(self):
        action = {"action": "create", "entity": "employee",
                  "fields": {"firstName": "A", "lastName": "B"},
                  "ref": "e1", "depends_on": {}}
        payload = _build_payload(action, ref_map={})
        assert payload["body"]["userType"] == "STANDARD"

    def test_register_payment_uses_params(self):
        action = {"action": "register_payment", "entity": "register_payment",
                  "fields": {"paidAmount": 1000}, "ref": "pay1",
                  "depends_on": {"invoice": "inv1"}}
        payload = _build_payload(action, ref_map={"inv1": 99})
        assert payload["use_query_params"] is True
        assert payload["params"]["paidAmount"] == 1000
        assert payload["params"]["paidAmountCurrency"] == 1


class TestExecutePlan:
    def test_single_create(self):
        client = MagicMock()
        client.post.return_value = {
            "success": True, "status_code": 201,
            "body": {"value": {"id": 42}},
        }
        plan = {"actions": [
            {"action": "create", "entity": "department",
             "fields": {"name": "IT", "departmentNumber": "100"},
             "ref": "dep1", "depends_on": {}},
        ]}
        result = execute_plan(client, plan)
        assert result["success"] is True
        client.post.assert_called_once()

    def test_threads_ids_between_actions(self):
        client = MagicMock()
        client.post.side_effect = [
            {"success": True, "status_code": 201, "body": {"value": {"id": 10}}},
            {"success": True, "status_code": 201, "body": {"value": {"id": 20}}},
        ]
        plan = {"actions": [
            {"action": "create", "entity": "department",
             "fields": {"name": "IT", "departmentNumber": "100"},
             "ref": "dep1", "depends_on": {}},
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "K", "lastName": "N"},
             "ref": "emp1", "depends_on": {"department": "dep1"}},
        ]}
        result = execute_plan(client, plan)
        assert result["success"] is True
        # Second call should have department: {"id": 10}
        second_call_body = client.post.call_args_list[1][1].get("body", {})
        assert second_call_body.get("department") == {"id": 10}

    def test_stops_on_4xx_returns_fallback_context(self):
        client = MagicMock()
        client.post.side_effect = [
            {"success": True, "status_code": 201, "body": {"value": {"id": 10}}},
            {"success": False, "status_code": 422, "error": "Validation failed", "body": {}},
        ]
        plan = {"actions": [
            {"action": "create", "entity": "department",
             "fields": {"name": "IT", "departmentNumber": "100"},
             "ref": "dep1", "depends_on": {}},
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "K", "lastName": "N"},
             "ref": "emp1", "depends_on": {"department": "dep1"}},
        ]}
        result = execute_plan(client, plan)
        assert result["success"] is False
        ctx = result["fallback_context"]
        assert ctx.completed_refs == {"dep1": 10}
        assert ctx.failed_action["ref"] == "emp1"
        assert "Validation" in ctx.error

    def test_lookup_defaults_inserts_get(self):
        """Employee without dept in plan triggers GET /department."""
        client = MagicMock()
        client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 55, "name": "Default"}]},
        }
        client.post.return_value = {
            "success": True, "status_code": 201,
            "body": {"value": {"id": 20}},
        }
        plan = {"actions": [
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "K", "lastName": "N"},
             "ref": "emp1", "depends_on": {}},
        ]}
        result = execute_plan(client, plan)
        assert result["success"] is True
        client.get.assert_called_once()  # looked up department
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_executor.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write executor.py**

```python
# executor.py
"""Deterministic executor — runs a validated TaskPlan against the Tripletex API.

Takes a TaskPlan (from planner.py), topologically sorts actions by dependencies,
builds payloads from the entity registry, and executes API calls in order —
threading response IDs into subsequent calls.
"""

import logging
import time
from datetime import date

from task_registry import ENTITY_SCHEMAS, KNOWN_CONSTANTS, generate_auto_value
from planner import FallbackContext
from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)


def execute_plan(client: TripletexClient, task_plan: dict) -> dict:
    """Execute a TaskPlan deterministically. Returns success or FallbackContext."""
    actions = _topological_sort(task_plan["actions"])
    ref_map: dict[str, int] = {}  # ref label → real API id
    total_api_calls = 0
    start = time.time()

    # Resolve lookup_defaults before execution
    _resolve_lookup_defaults(client, actions, ref_map)

    for i, action in enumerate(actions):
        step = f"{i + 1}/{len(actions)}"
        payload = _build_payload(action, ref_map)

        method = payload["method"]
        endpoint = payload["endpoint"]
        logger.info(f"exec: step={step} method={method} endpoint={endpoint} ref={action['ref']}")

        call_start = time.time()
        if payload.get("use_query_params"):
            result = client.put(endpoint, params=payload.get("params"))
        elif method == "POST":
            result = client.post(endpoint, body=payload.get("body"))
        elif method == "PUT":
            result = client.put(endpoint, body=payload.get("body"), params=payload.get("params"))
        elif method == "GET":
            result = client.get(endpoint, params=payload.get("params"))
        else:
            result = {"success": False, "error": f"Unsupported method: {method}"}

        call_ms = int((time.time() - call_start) * 1000)
        total_api_calls += 1

        if not result["success"]:
            error_msg = result.get("error", str(result.get("body", "")))
            logger.warning(f"exec: step={step} method={method} endpoint={endpoint} "
                         f"status={result.get('status_code')} error=\"{error_msg}\" "
                         f"body={result.get('body')} time_ms={call_ms}")
            logger.info(f"exec: fallback_triggered completed_refs={ref_map} failed_action={action['ref']}")

            return {
                "success": False,
                "fallback_context": FallbackContext(
                    task_plan=task_plan,
                    completed_refs=dict(ref_map),
                    failed_action=action,
                    error=error_msg,
                ),
            }

        # Extract created entity ID
        entity_id = _extract_id(result)
        if entity_id is not None:
            ref_map[action["ref"]] = entity_id

        logger.info(f"exec: step={step} status={result.get('status_code')} success=true "
                    f"ref={action['ref']} id={entity_id} time_ms={call_ms}")

    total_ms = int((time.time() - start) * 1000)
    logger.info(f"exec: completed total_api_calls={total_api_calls} total_time_ms={total_ms}")

    return {"success": True, "ref_map": ref_map, "api_calls": total_api_calls}


def _topological_sort(actions: list[dict]) -> list[dict]:
    """Sort actions so dependencies come first."""
    ref_to_action = {a["ref"]: a for a in actions}
    visited = set()
    result = []

    def visit(ref):
        if ref in visited:
            return
        visited.add(ref)
        action = ref_to_action.get(ref)
        if not action:
            return
        for dep_ref in _all_dep_refs(action):
            visit(dep_ref)
        result.append(action)

    for action in actions:
        visit(action["ref"])
    return result


def _all_dep_refs(action: dict) -> list[str]:
    """Extract all dependency refs from an action (handles both single and array)."""
    refs = []
    for val in action.get("depends_on", {}).values():
        if isinstance(val, list):
            refs.extend(val)
        else:
            refs.append(val)
    return refs


def _build_payload(action: dict, ref_map: dict) -> dict:
    """Build the API payload for an action using the registry."""
    entity = action["entity"]
    schema = ENTITY_SCHEMAS[entity]

    body = dict(action.get("fields", {}))

    # Inject defaults
    for key, val in schema.get("defaults", {}).items():
        if key not in body:
            body[key] = val

    # Auto-generate missing values
    for field in schema.get("auto_generate", []):
        if field not in body:
            body[field] = generate_auto_value(field)

    # Resolve dependency refs → {"id": real_id}
    for field_name, ref_val in action.get("depends_on", {}).items():
        if isinstance(ref_val, list):
            body[field_name] = [{"id": ref_map[r]} for r in ref_val if r in ref_map]
        elif ref_val in ref_map:
            body[field_name] = {"id": ref_map[ref_val]}

    # Resolve endpoint (may have {id} placeholder)
    endpoint = schema["endpoint"]
    if "{id}" in endpoint:
        # For register_payment, the invoice ID comes from depends_on
        invoice_ref = action.get("depends_on", {}).get("invoice")
        if invoice_ref and invoice_ref in ref_map:
            endpoint = endpoint.replace("{id}", str(ref_map[invoice_ref]))

    # Build result
    result = {
        "method": schema["method"],
        "endpoint": endpoint,
    }

    if schema.get("use_query_params"):
        result["use_query_params"] = True
        result["params"] = body
    else:
        result["body"] = body

    return result


def _resolve_lookup_defaults(client: TripletexClient, actions: list[dict], ref_map: dict):
    """Insert GET lookups for entities that need dependencies not in the plan."""
    all_refs = {a["ref"] for a in actions}

    for action in actions:
        entity = action["entity"]
        schema = ENTITY_SCHEMAS.get(entity, {})
        lookup_defaults = schema.get("lookup_defaults", {})

        for field_name, endpoint in lookup_defaults.items():
            # Check if this field is already provided via depends_on
            dep_ref = action.get("depends_on", {}).get(field_name)
            if dep_ref and (dep_ref in all_refs or dep_ref in ref_map):
                continue

            # Need to look up a default
            logger.info(f"exec: lookup_default field={field_name} endpoint={endpoint}")
            result = client.get(endpoint, params={"fields": "id,name", "count": "1"})
            if result["success"] and result["body"].get("values"):
                default_id = result["body"]["values"][0]["id"]
                # Create a synthetic ref and inject into depends_on
                synth_ref = f"_lookup_{field_name}"
                ref_map[synth_ref] = default_id
                action.setdefault("depends_on", {})[field_name] = synth_ref


def _extract_id(result: dict) -> int | None:
    """Extract the entity ID from an API response."""
    body = result.get("body", {})
    if isinstance(body, dict):
        value = body.get("value", {})
        if isinstance(value, dict) and "id" in value:
            return value["id"]
    return None
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_executor.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add executor.py tests/test_executor.py
git commit -m "feat: deterministic executor with topo-sort and ref threading

Executes TaskPlan actions in dependency order. Threads response IDs
between calls. Returns FallbackContext on 4xx for tool-use handoff."
```

---

### Task 4: Modify agent.py — router with deterministic + fallback paths

**Files:**
- Modify: `agent.py`
- Modify: `tests/test_agent.py`

- [ ] **Step 1: Add routing tests to test_agent.py**

Add these new test classes to the existing `tests/test_agent.py`:

```python
# Add to tests/test_agent.py (after existing tests)

class TestRouting:
    """Test the run_agent router logic."""

    @patch("agent.run_tool_loop")
    @patch("agent.execute_plan", return_value={"success": True, "ref_map": {}, "api_calls": 1})
    @patch("agent.is_known_pattern", return_value=True)
    @patch("agent.parse_prompt", return_value={"actions": [{"action": "create", "entity": "department", "fields": {"name": "IT"}, "ref": "d1", "depends_on": {}}]})
    def test_deterministic_path(self, mock_parse, mock_match, mock_exec, mock_fallback):
        result = agent_module.run_agent("Create dept", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_exec.assert_called_once()
        mock_fallback.assert_not_called()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.is_known_pattern", return_value=False)
    @patch("agent.parse_prompt", return_value={"actions": [{"action": "update", "entity": "employee", "fields": {}, "ref": "e1", "depends_on": {}}]})
    def test_fallback_on_unknown_pattern(self, mock_parse, mock_match, mock_fallback):
        result = agent_module.run_agent("Update employee", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_fallback.assert_called_once()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.parse_prompt", return_value=None)
    def test_fallback_on_parse_failure(self, mock_parse, mock_fallback):
        result = agent_module.run_agent("???", [], "http://x/v2", "tok")
        assert result["status"] == "completed"
        mock_fallback.assert_called_once()

    @patch("agent.run_tool_loop", return_value={"status": "completed"})
    @patch("agent.execute_plan")
    @patch("agent.is_known_pattern", return_value=True)
    @patch("agent.parse_prompt", return_value={"actions": []})
    def test_fallback_on_execution_failure(self, mock_parse, mock_match, mock_exec, mock_fallback):
        from planner import FallbackContext
        mock_exec.return_value = {
            "success": False,
            "fallback_context": FallbackContext(error="422 failed"),
        }
        result = agent_module.run_agent("Create employee", [], "http://x/v2", "tok")
        mock_fallback.assert_called_once()
```

- [ ] **Step 2: Refactor agent.py**

Modify `agent.py` to:
1. Move the current `run_agent()` to `run_tool_loop()` (with `fallback_context` parameter)
2. Create new `run_agent()` as the router
3. Keep all existing tool definitions, system prompt, etc. intact

The key changes:
- Rename `run_agent` → `run_tool_loop`, add `fallback_context` param
- `run_tool_loop` injects `FallbackContext` info into system prompt
- New `run_agent` calls `parse_prompt` → `is_known_pattern` → `execute_plan` or `run_tool_loop`
- Add summary logging at the end

```python
# In agent.py, add imports at top:
from planner import parse_prompt, is_known_pattern, FallbackContext
from executor import execute_plan

# Rename existing run_agent to run_tool_loop:
def run_tool_loop(prompt: str, file_contents: list[dict], client: TripletexClient,
                  fallback_context: FallbackContext | None = None) -> dict:
    """Run the Gemini tool-use agent loop (fallback path)."""
    start_time = time.time()
    reason = "parse_failure"
    if fallback_context:
        if fallback_context.failed_action:
            reason = "execution_error"
        elif fallback_context.task_plan:
            reason = "pattern_mismatch"
    logger.info(f"fallback: reason={reason} context_refs={len(fallback_context.completed_refs) if fallback_context else 0}")

    system_prompt = build_system_prompt()

    # Inject fallback context
    if fallback_context:
        extra = []
        if fallback_context.completed_refs:
            extra.append(f"These entities were already created: {json.dumps(fallback_context.completed_refs)}")
        if fallback_context.failed_action and fallback_context.error:
            extra.append(f"This action failed: {json.dumps(fallback_context.failed_action)}. Error: {fallback_context.error}. Fix and continue.")
        if fallback_context.task_plan:
            extra.append(f"Parsed task plan for context: {json.dumps(fallback_context.task_plan)}")
        if extra:
            system_prompt += "\n\n## Context from previous attempt\n" + "\n".join(extra)

    # ... rest of existing loop code unchanged ...
```

New `run_agent`:

```python
def run_agent(prompt: str, file_contents: list[dict], base_url: str, session_token: str) -> dict:
    """Route: parse → deterministic execution or tool-use fallback."""
    start_time = time.time()
    client = TripletexClient(base_url, session_token)
    path = "fallback"
    total_api_calls = 0
    errors_4xx = 0
    llm_calls = 0

    # Step 1: Parse prompt
    task_plan = parse_prompt(prompt, file_contents)
    llm_calls += 1

    # Step 2: Try deterministic path
    if task_plan and is_known_pattern(task_plan):
        result = execute_plan(client, task_plan)
        total_api_calls += result.get("api_calls", 0)
        if result["success"]:
            path = "deterministic"
            total_ms = int((time.time() - start_time) * 1000)
            logger.info(f"result: status=completed path={path} total_api_calls={total_api_calls} "
                       f"errors_4xx=0 llm_calls={llm_calls} total_time_ms={total_ms}")
            return {"status": "completed", "path": path}
        fallback_ctx = result["fallback_context"]
        path = "deterministic+fallback"
    else:
        fallback_ctx = FallbackContext(task_plan=task_plan)

    # Step 3: Tool-use fallback
    loop_result = run_tool_loop(prompt, file_contents, client, fallback_ctx)
    total_ms = int((time.time() - start_time) * 1000)
    logger.info(f"result: status=completed path={path} total_api_calls={total_api_calls} "
               f"llm_calls={llm_calls} total_time_ms={total_ms}")
    return {"status": "completed", "path": path}
```

- [ ] **Step 3: Run ALL tests**

Run: `python -m pytest tests/test_agent.py tests/test_planner.py tests/test_executor.py tests/test_task_registry.py tests/test_file_handler.py tests/test_main.py tests/test_tripletex_api.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: agent router — deterministic path with tool-use fallback

run_agent() now: parse → pattern match → deterministic execute or tool-use.
Existing tool-use loop preserved as run_tool_loop() with FallbackContext
injection. Summary logging on every request."
```

---

### Task 5: Deploy and smoke test

**Files:**
- No new files

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [ ] **Step 2: Deploy to Cloud Run**

```bash
gcloud run deploy ai-accounting-agent --source . --region europe-north1 \
  --project ai-nm26osl-1799 --no-allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global" --quiet
```

- [ ] **Step 3: Test deterministic path (simple create)**

```bash
DEPLOY_URL="https://ai-accounting-agent-590159115697.europe-north1.run.app"
TOKEN=$(gcloud auth print-identity-token)
curl -s -X POST "$DEPLOY_URL/solve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Opprett en avdeling med navn Finans og avdelingsnummer 300",
    "files": [],
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "'"$TRIPLETEX_SESSION_TOKEN"'"
    }
  }' --max-time 300
```

Expected: `{"status":"completed"}`. Check logs for `path=deterministic`.

- [ ] **Step 4: Test fallback path (update task)**

```bash
curl -s -X POST "$DEPLOY_URL/solve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Finn kunden Acme AS og oppdater e-posten til ny@acme.no",
    "files": [],
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "'"$TRIPLETEX_SESSION_TOKEN"'"
    }
  }' --max-time 300
```

Expected: `{"status":"completed"}`. Check logs for `path=fallback`.

- [ ] **Step 5: Check logs**

```bash
gcloud run services logs read ai-accounting-agent --project ai-nm26osl-1799 \
  --region europe-north1 --limit 50 | grep "result:"
```

Expected: See summary lines with `path=deterministic` and `path=fallback`.

- [ ] **Step 6: Commit any fixes**

```bash
git add -A && git commit -m "test: smoke test deterministic + fallback paths verified"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Entity registry | `task_registry.py`, `tests/test_task_registry.py` |
| 2 | Planner (parse + pattern match) | `planner.py`, `tests/test_planner.py` |
| 3 | Deterministic executor | `executor.py`, `tests/test_executor.py` |
| 4 | Agent router refactor | `agent.py`, `tests/test_agent.py` |
| 5 | Deploy + smoke test | (no new files) |
