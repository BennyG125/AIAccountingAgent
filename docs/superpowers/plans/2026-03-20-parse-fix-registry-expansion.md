# Parse Fix + Registry Expansion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the empty `fields` parse bug and expand the entity registry from 12 to 27 types with 15 action patterns, 6 bulk create endpoints, and search-then-act flows.

**Architecture:** Gemini parses prompt → structured TaskPlan (1 LLM call). Pattern matcher validates against expanded registry. Executor handles creates, updates, deletes, named actions, and auto-batches bulk creates. Falls back to tool-use loop for unrecognized patterns.

**Tech Stack:** google-genai SDK (Vertex AI structured output), FastAPI, dataclasses

**Spec:** `docs/superpowers/specs/2026-03-20-parse-fix-registry-expansion-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `task_registry.py` | **Modify** | 18 new entities, ACTION_SCHEMAS, BULK_ENDPOINTS, SEARCH_PARAMS, pre_lookups migration, DEPENDENCIES |
| `planner.py` | **Modify** | Schema fix, few-shot examples, action types in prompt, is_known_pattern rewrite |
| `executor.py` | **Modify** | `_resolve_pre_lookups()`, `_resolve_by_search()`, `_auto_batch()`, action dispatch |
| `tests/test_task_registry.py` | **Modify** | Tests for 30 entities, ACTION_SCHEMAS, BULK_ENDPOINTS, SEARCH_PARAMS, no LOOKUP_CONSTANTS |
| `tests/test_planner.py` | **Modify** | Parse schema tests, updated pattern matcher tests |
| `tests/test_executor.py` | **Modify** | Pre-lookups, search-then-act, auto-batch, action dispatch tests |
| `smoke_test.py` | **Modify** | Add update/delete test cases |

---

### Task 1: Expand task_registry.py — 30 entities + actions + bulk

**Files:**
- Modify: `task_registry.py`
- Modify: `tests/test_task_registry.py`

- [ ] **Step 1: Write registry tests**

Update `tests/test_task_registry.py` to test the expanded registry. Replace the entire file:

```python
# tests/test_task_registry.py
"""Tests for task_registry.py — expanded registry with 30 entities + actions."""

from task_registry import (
    ENTITY_SCHEMAS, KNOWN_CONSTANTS, DEPENDENCIES,
    ACTION_SCHEMAS, BULK_ENDPOINTS, SEARCH_PARAMS,
    generate_auto_value,
)


class TestEntitySchemas:
    def test_all_27_entities_covered(self):
        expected = {
            "department", "employee", "customer", "product",
            "order", "invoice", "register_payment",
            "travel_expense", "travel_expense_cost",
            "project", "contact", "voucher",
            # new
            "employee_employment", "employee_employment_details",
            "supplier", "supplier_invoice", "customer_category",
            "product_unit", "order_line", "project_participant",
            "travel_expense_per_diem", "travel_expense_mileage",
            "travel_expense_accommodation",
            "ledger_account", "salary_transaction",
            "delivery_address", "company",
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

    def test_no_lookup_defaults_key(self):
        """lookup_defaults was migrated to pre_lookups."""
        for name, schema in ENTITY_SCHEMAS.items():
            assert "lookup_defaults" not in schema, f"{name} still has lookup_defaults"

    def test_no_lookup_constants_inject_key(self):
        """lookup_constants_inject was migrated to pre_lookups."""
        for name, schema in ENTITY_SCHEMAS.items():
            assert "lookup_constants_inject" not in schema, f"{name} still has lookup_constants_inject"

    def test_employee_has_pre_lookups(self):
        emp = ENTITY_SCHEMAS["employee"]
        assert "department" in emp.get("pre_lookups", {})

    def test_travel_expense_cost_has_pre_lookups(self):
        tec = ENTITY_SCHEMAS["travel_expense_cost"]
        assert "costCategory" in tec.get("pre_lookups", {})
        assert "paymentType" in tec.get("pre_lookups", {})

    def test_travel_expense_per_diem_has_pre_lookups(self):
        te = ENTITY_SCHEMAS["travel_expense_per_diem"]
        assert "rateCategory" in te.get("pre_lookups", {})

    def test_company_is_singleton(self):
        assert ENTITY_SCHEMAS["company"].get("singleton") is True


class TestKnownConstants:
    def test_vat_rates(self):
        assert KNOWN_CONSTANTS["vat_25"] == {"id": 3}
        assert KNOWN_CONSTANTS["vat_15"] == {"id": 5}
        assert KNOWN_CONSTANTS["vat_0"] == {"id": 6}

    def test_nok_and_norway(self):
        assert KNOWN_CONSTANTS["nok"] == {"id": 1}
        assert KNOWN_CONSTANTS["norway"] == {"id": 162}


class TestNoLookupConstants:
    def test_lookup_constants_removed(self):
        """LOOKUP_CONSTANTS dict should no longer exist."""
        import task_registry
        assert not hasattr(task_registry, "LOOKUP_CONSTANTS"), "LOOKUP_CONSTANTS should be removed"


class TestActionSchemas:
    def test_has_15_action_types(self):
        assert len(ACTION_SCHEMAS) == 15

    def test_generic_actions(self):
        assert "update" in ACTION_SCHEMAS
        assert "delete" in ACTION_SCHEMAS
        assert ACTION_SCHEMAS["update"]["flow"] == "search_put"
        assert ACTION_SCHEMAS["delete"]["flow"] == "search_delete"

    def test_invoice_actions(self):
        for action in ("send_invoice", "create_credit_note", "create_reminder"):
            assert action in ACTION_SCHEMAS
            assert ACTION_SCHEMAS[action]["entity"] == "invoice"

    def test_travel_expense_actions(self):
        for action in ("approve_travel_expense", "deliver_travel_expense", "unapprove_travel_expense"):
            assert action in ACTION_SCHEMAS
            assert ACTION_SCHEMAS[action].get("body_from_search") is True

    def test_supplier_invoice_actions(self):
        for action in ("approve_supplier_invoice", "reject_supplier_invoice", "pay_supplier_invoice"):
            assert action in ACTION_SCHEMAS

    def test_grant_entitlements_uses_query_params(self):
        ge = ACTION_SCHEMAS["grant_entitlements"]
        assert "action_params_from_search" in ge
        assert ge["action_params_from_search"]["employeeId"] == "id"


class TestBulkEndpoints:
    def test_has_6_bulk_types(self):
        assert len(BULK_ENDPOINTS) == 6

    def test_employee_bulk(self):
        assert BULK_ENDPOINTS["employee"] == "/employee/list"

    def test_all_bulk_entities_in_schemas(self):
        for entity in BULK_ENDPOINTS:
            assert entity in ENTITY_SCHEMAS, f"bulk entity {entity} not in ENTITY_SCHEMAS"


class TestSearchParams:
    def test_core_entities_have_search_params(self):
        for entity in ("department", "employee", "customer", "product", "supplier", "project"):
            assert entity in SEARCH_PARAMS, f"{entity} missing from SEARCH_PARAMS"

    def test_employee_search_fields(self):
        assert SEARCH_PARAMS["employee"]["firstName"] == "firstName"
        assert SEARCH_PARAMS["employee"]["lastName"] == "lastName"


class TestDependencies:
    def test_all_entities_in_dependencies(self):
        for entity in ENTITY_SCHEMAS:
            assert entity in DEPENDENCIES, f"{entity} missing from DEPENDENCIES"

    def test_employee_depends_on_department(self):
        assert "department" in DEPENDENCIES["employee"]

    def test_invoice_depends_on_order(self):
        assert "order" in DEPENDENCIES["invoice"]

    def test_new_entities_have_correct_deps(self):
        assert "employee" in DEPENDENCIES["employee_employment"]
        assert "employee_employment" in DEPENDENCIES["employee_employment_details"]
        assert "project" in DEPENDENCIES["project_participant"]
        assert "travel_expense" in DEPENDENCIES["travel_expense_per_diem"]

    def test_no_cycles(self):
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
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_task_registry.py -v`
Expected: FAIL (imports fail — ACTION_SCHEMAS, BULK_ENDPOINTS, SEARCH_PARAMS not found)

- [ ] **Step 3: Write the expanded task_registry.py**

Replace the entire file. Key changes:
1. Add 15 new entity schemas (see spec Section 2 "New entity types") PLUS `supplier_invoice`:
   ```python
   "supplier_invoice": {
       "endpoint": "/supplierInvoice",
       "method": "GET",  # read-only — actions use ACTION_SCHEMAS endpoints
       "required": [],
       "defaults": {},
   },
   ```
2. Migrate `employee.lookup_defaults` → `employee.pre_lookups: {"department": "/department"}`
3. Migrate `travel_expense_cost.lookup_constants_inject` → `travel_expense_cost.pre_lookups`
4. Remove `LOOKUP_CONSTANTS` dict entirely
5. Add `ACTION_SCHEMAS` (15 actions — spec Section 2 "Action schemas")
6. Add `BULK_ENDPOINTS` (6 types — spec Section 2 "Bulk create endpoints")
7. Add `SEARCH_PARAMS` (spec Section 2 — add `"supplier_invoice": {}` entry too)
8. Expand `DEPENDENCIES` to 27 entities (spec Section 2 + `"supplier_invoice": []`)

All data is in the spec. The file structure:

```python
# task_registry.py
"""Static entity registry for deterministic execution.

Contains all knowledge needed to validate and execute Tripletex API calls
without LLM involvement: entity schemas, known constants, dependency graph,
action schemas, bulk endpoints, and search parameter mappings.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Entity Schemas (27 entities)
# ---------------------------------------------------------------------------

ENTITY_SCHEMAS = {
    # ... all 12 existing entities (with pre_lookups migration on employee + travel_expense_cost) ...
    # ... plus 15 new entities from spec + supplier_invoice ...
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

# NOTE: LOOKUP_CONSTANTS removed — migrated to pre_lookups on individual schemas

# ---------------------------------------------------------------------------
# Action Schemas — for update/delete/named action patterns
# ---------------------------------------------------------------------------

ACTION_SCHEMAS = {
    # ... 15 action types from spec ...
}

# ---------------------------------------------------------------------------
# Bulk Endpoints — POST /*/list for batch creation
# ---------------------------------------------------------------------------

BULK_ENDPOINTS = {
    "employee": "/employee/list",
    "customer": "/customer/list",
    "contact": "/contact/list",
    "product": "/product/list",
    "order_line": "/order/orderline/list",
    "project_participant": "/project/participant/list",
}

# ---------------------------------------------------------------------------
# Search Parameters — field name → query param mapping per entity
# ---------------------------------------------------------------------------

SEARCH_PARAMS = {
    # ... all entries from spec ...
}

# ---------------------------------------------------------------------------
# Dependency Graph — directed, acyclic (27 entities)
# ---------------------------------------------------------------------------

DEPENDENCIES = {
    # ... expanded graph from spec ...
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

Copy ALL entity schemas, action schemas, search params, dependencies, and bulk endpoints exactly from the spec. The spec has complete code for each section.

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_task_registry.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add task_registry.py tests/test_task_registry.py
git commit -m "feat: expand registry to 30 entities, 15 actions, 6 bulk endpoints

Migrates lookup_defaults/lookup_constants_inject to unified pre_lookups.
Adds ACTION_SCHEMAS, BULK_ENDPOINTS, SEARCH_PARAMS. Removes LOOKUP_CONSTANTS.
Covers full Tripletex API surface for deterministic execution."
```

---

### Task 2: Fix planner.py — parse schema + pattern matcher

**Files:**
- Modify: `planner.py`
- Modify: `tests/test_planner.py`

- [ ] **Step 1: Write updated planner tests**

Add new tests and update existing ones in `tests/test_planner.py`. Keep all existing passing tests. Changes:

1. Replace `test_rejects_update_action` and `test_rejects_delete_action` with new versions
2. Add tests for new action types in is_known_pattern
3. Add test for `search_fields` in schema

```python
# Add/replace in tests/test_planner.py

# Replace test_rejects_update_action with:
def test_rejects_update_without_search_fields(self):
    plan = {"actions": [
        {"action": "update", "entity": "employee",
         "fields": {"email": "new@test.no"}, "search_fields": {},
         "ref": "emp1", "depends_on": {}}
    ]}
    assert is_known_pattern(plan) is False

# Replace test_rejects_delete_action with:
def test_rejects_delete_without_search_fields(self):
    plan = {"actions": [
        {"action": "delete", "entity": "customer",
         "fields": {}, "search_fields": {},
         "ref": "c1", "depends_on": {}}
    ]}
    assert is_known_pattern(plan) is False

# Add new tests:
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
    """New entities like supplier, project_participant are recognized."""
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
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_planner.py -v`
Expected: FAIL (new tests fail, some old tests may fail due to import changes)

- [ ] **Step 3: Update planner.py**

Key changes:

1. **Add import** for `ACTION_SCHEMAS`:
```python
from task_registry import ENTITY_SCHEMAS, ACTION_SCHEMAS
```

2. **Replace `PARSE_SYSTEM_PROMPT`** with expanded version including:
   - All 27 entity field names. Add these NEW entries to the "API field names per entity" list:
     ```
     - employee_employment: employee, startDate, endDate, taxDeductionCode, isMainEmployer
     - employee_employment_details: employment, date, employmentType, annualSalary, hourlyWage
     - supplier: name, email, phoneNumber, organizationNumber, supplierNumber
     - customer_category: name, number, description, type
     - product_unit: name, nameShort, commonCode
     - order_line: order, product, count, unitPriceExcludingVatCurrency, vatType, discount
     - project_participant: project, employee, adminAccess
     - travel_expense_per_diem: travelExpense, rateCategory, rateType, countryCode, location, count, amount, overnightAccommodation
     - travel_expense_mileage: travelExpense, rateCategory, rateType, date, departureLocation, destination, km, rate
     - travel_expense_accommodation: travelExpense, rateCategory, rateType, location, count, rate, amount
     - ledger_account: number, name
     - salary_transaction: date, month, year, payslips, isHistorical
     - delivery_address: (updated via PUT with full object)
     - company: name, organizationNumber (singleton — update only)
     - supplier_invoice: (read-only — use action patterns for approve/reject/pay)
     ```
   - Action pattern instructions (update, delete, send_invoice, etc.) — from spec Section 1
   - 3 few-shot examples (nb, en, de) — from spec Section 1
   - Bulk operations note — from spec Section 1
   - REMOVE the old sentence "these will be handled by the fallback path" (contradicts new action support)

3. **Replace `TASK_PLAN_SCHEMA`** with the version from spec Section 1 (adds `fields` description and `search_fields` property)

4. **Replace `DETERMINISTIC_ACTIONS` and `is_known_pattern()`** with the full rewrite from spec Section 3 "Pattern matcher"

**Important:** Add singleton exception in is_known_pattern. For `update` actions where the entity has `"singleton": True` in ENTITY_SCHEMAS, skip the `search_fields` requirement:

```python
elif action_type in ("update", "delete"):
    if entity not in ENTITY_SCHEMAS:
        ...return False
    # Singletons (e.g., company) don't need search_fields
    if not ENTITY_SCHEMAS[entity].get("singleton") and not action.get("search_fields"):
        ...return False
```

All other replacement code is in the spec. Copy exactly, adding the singleton check.

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_planner.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add planner.py tests/test_planner.py
git commit -m "feat: fix parse schema + expand pattern matcher for all action types

Adds field descriptions and search_fields to TASK_PLAN_SCHEMA.
3 few-shot examples (nb/en/de) guide field extraction.
Pattern matcher now accepts update/delete/named actions.
DETERMINISTIC_ACTIONS expanded to 15 action types."
```

---

### Task 3: Expand executor.py — pre-lookups, search, batch, actions

**Files:**
- Modify: `executor.py`
- Modify: `tests/test_executor.py`

- [ ] **Step 1: Write executor tests**

Add to `tests/test_executor.py`. Keep all existing tests EXCEPT:
- **Replace `test_lookup_defaults_inserts_get`** — this tests the old `_resolve_lookup_defaults()` which is being replaced by `_resolve_pre_lookups()`. The new `TestResolvePreLookups` class covers the same behavior.

Add new test classes:

```python
# Add to tests/test_executor.py

# Need mock for the new imports
from unittest.mock import MagicMock, patch, call

_mock_genai_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    from executor import (
        execute_plan, _topological_sort, _build_payload,
        _resolve_pre_lookups, _resolve_by_search, _auto_batch,
    )
    from task_registry import BULK_ENDPOINTS


class TestResolvePreLookups:
    def test_injects_ids_from_get(self):
        client = MagicMock()
        client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 55, "name": "Default Category"}]},
        }
        actions = [
            {"action": "create", "entity": "travel_expense_cost",
             "fields": {"amountCurrencyIncVat": 500}, "ref": "tec1", "depends_on": {}},
        ]
        ref_map = {}
        lookup_cache = {}
        _resolve_pre_lookups(client, actions, ref_map, lookup_cache)
        assert actions[0]["fields"]["costCategory"] == {"id": 55}
        assert "costCategory" in lookup_cache

    def test_caches_lookups(self):
        client = MagicMock()
        client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 55}]},
        }
        actions = [
            {"action": "create", "entity": "travel_expense_cost",
             "fields": {}, "ref": "tec1", "depends_on": {}},
            {"action": "create", "entity": "travel_expense_cost",
             "fields": {}, "ref": "tec2", "depends_on": {}},
        ]
        lookup_cache = {}
        _resolve_pre_lookups(client, actions, {}, lookup_cache)
        # costCategory and paymentType looked up once each, not twice
        assert client.get.call_count == 2  # costCategory + paymentType

    def test_skips_if_field_already_set(self):
        client = MagicMock()
        actions = [
            {"action": "create", "entity": "employee",
             "fields": {"department": {"id": 99}}, "ref": "e1", "depends_on": {}},
        ]
        _resolve_pre_lookups(client, actions, {}, {})
        client.get.assert_not_called()


class TestResolveBySearch:
    def test_finds_entity(self):
        client = MagicMock()
        client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 42, "name": "Acme", "version": 1}]},
        }
        action = {"action": "update", "entity": "customer",
                  "search_fields": {"name": "Acme"}, "fields": {}, "ref": "c1"}
        result = _resolve_by_search(client, action)
        assert result["id"] == 42

    def test_returns_none_when_not_found(self):
        client = MagicMock()
        client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": []},
        }
        action = {"action": "delete", "entity": "department",
                  "search_fields": {"name": "Nonexistent"}, "fields": {}, "ref": "d1"}
        result = _resolve_by_search(client, action)
        assert result is None

    def test_returns_none_with_empty_search_fields(self):
        client = MagicMock()
        action = {"action": "update", "entity": "customer",
                  "search_fields": {}, "fields": {}, "ref": "c1"}
        result = _resolve_by_search(client, action)
        assert result is None
        client.get.assert_not_called()


class TestAutoBatch:
    def test_batches_independent_creates(self):
        actions = [
            {"action": "create", "entity": "employee", "fields": {"firstName": "A"}, "ref": "e1", "depends_on": {}},
            {"action": "create", "entity": "employee", "fields": {"firstName": "B"}, "ref": "e2", "depends_on": {}},
            {"action": "create", "entity": "employee", "fields": {"firstName": "C"}, "ref": "e3", "depends_on": {}},
        ]
        result = _auto_batch(actions)
        batch_actions = [a for a in result if a.get("action") == "create_batch"]
        assert len(batch_actions) == 1
        assert batch_actions[0]["entity"] == "employee"
        assert len(batch_actions[0]["batch_items"]) == 3

    def test_does_not_batch_with_cross_deps(self):
        actions = [
            {"action": "create", "entity": "customer", "fields": {"name": "A"}, "ref": "c1", "depends_on": {}},
            {"action": "create", "entity": "customer", "fields": {"name": "B"}, "ref": "c2", "depends_on": {"parent": "c1"}},
        ]
        result = _auto_batch(actions)
        batch_actions = [a for a in result if a.get("action") == "create_batch"]
        assert len(batch_actions) == 0

    def test_does_not_batch_non_bulk_entities(self):
        actions = [
            {"action": "create", "entity": "department", "fields": {"name": "A"}, "ref": "d1", "depends_on": {}},
            {"action": "create", "entity": "department", "fields": {"name": "B"}, "ref": "d2", "depends_on": {}},
        ]
        result = _auto_batch(actions)
        batch_actions = [a for a in result if a.get("action") == "create_batch"]
        assert len(batch_actions) == 0  # department not in BULK_ENDPOINTS

    def test_does_not_batch_single_entity(self):
        actions = [
            {"action": "create", "entity": "employee", "fields": {"firstName": "A"}, "ref": "e1", "depends_on": {}},
        ]
        result = _auto_batch(actions)
        assert len(result) == 1
        assert result[0]["action"] == "create"


class TestActionDispatch:
    def test_update_searches_and_puts(self):
        client = MagicMock()
        client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 42, "name": "Old", "version": 1}]},
        }
        client.put.return_value = {
            "success": True, "status_code": 200,
            "body": {"value": {"id": 42}},
        }
        plan = {"actions": [
            {"action": "update", "entity": "customer",
             "fields": {"email": "new@test.no"},
             "search_fields": {"name": "Old"},
             "ref": "c1", "depends_on": {}},
        ]}
        result = execute_plan(client, plan)
        assert result["success"] is True
        client.get.assert_called_once()
        client.put.assert_called_once()

    def test_delete_searches_and_deletes(self):
        client = MagicMock()
        client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": [{"id": 42, "name": "Dept", "version": 1}]},
        }
        client.delete.return_value = {
            "success": True, "status_code": 200, "body": {},
        }
        plan = {"actions": [
            {"action": "delete", "entity": "department",
             "fields": {}, "search_fields": {"name": "Dept"},
             "ref": "d1", "depends_on": {}},
        ]}
        result = execute_plan(client, plan)
        assert result["success"] is True
        client.delete.assert_called_once()

    def test_search_not_found_returns_fallback(self):
        client = MagicMock()
        client.get.return_value = {
            "success": True, "status_code": 200,
            "body": {"values": []},
        }
        plan = {"actions": [
            {"action": "update", "entity": "customer",
             "fields": {"email": "x"}, "search_fields": {"name": "Missing"},
             "ref": "c1", "depends_on": {}},
        ]}
        result = execute_plan(client, plan)
        assert result["success"] is False
        assert "0 results" in result["fallback_context"].error

    def test_batch_create(self):
        client = MagicMock()
        client.post.return_value = {
            "success": True, "status_code": 201,
            "body": {"values": [{"id": 10}, {"id": 11}]},
        }
        plan = {"actions": [
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "A", "lastName": "A"}, "ref": "e1", "depends_on": {}},
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "B", "lastName": "B"}, "ref": "e2", "depends_on": {}},
        ]}
        result = execute_plan(client, plan)
        assert result["success"] is True
        # Should have used /employee/list (1 call, not 2)
        assert client.post.call_count == 1
        call_args = client.post.call_args
        assert "/list" in call_args[0][0] or "/list" in str(call_args)
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `python -m pytest tests/test_executor.py -v`
Expected: FAIL (new imports/functions not found)

- [ ] **Step 3: Update executor.py**

Key changes:

1. **Update imports:**
```python
from task_registry import (
    ENTITY_SCHEMAS, KNOWN_CONSTANTS, generate_auto_value,
    ACTION_SCHEMAS, BULK_ENDPOINTS, SEARCH_PARAMS,
)
```
Remove unused `from datetime import date`.

2. **Replace `_resolve_lookup_defaults()`** with `_resolve_pre_lookups()` (spec Section 3)

3. **Add `_resolve_by_search()`** (spec Section 3)

4. **Add `_auto_batch()`** (spec Section 2 "Bulk create endpoints")

5. **Rewrite `execute_plan()` main loop** to:
   - Call `_auto_batch(actions)` after topo-sort
   - Call `_resolve_pre_lookups()` instead of `_resolve_lookup_defaults()`
   - Add action type dispatch: create/register_payment → existing flow, update → search+put, delete → search+delete, named actions → search+action, create_batch → bulk post
   - All dispatch code is in spec Section 3

6. **Keep `_topological_sort`, `_all_dep_refs`, `_build_payload`, `_extract_id` unchanged** (they still work for creates)

7. **Note: `execute_plan()` must create `lookup_cache = {}` dict** and pass it to `_resolve_pre_lookups()`.

8. **Batch partial failure:** If a bulk POST fails (422), the executor returns a FallbackContext like any other failure. The tool-use fallback handles retrying individual creates. Retry-as-individual within the executor is deferred (not implemented in this iteration — the fallback covers it).

All replacement code is in the spec Section 3.

- [ ] **Step 4: Run tests — expect PASS**

Run: `python -m pytest tests/test_executor.py -v`
Expected: All PASS

- [ ] **Step 5: Run ALL tests**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add executor.py tests/test_executor.py
git commit -m "feat: executor supports update/delete/actions, pre-lookups, auto-batching

Replaces _resolve_lookup_defaults with unified _resolve_pre_lookups.
Adds _resolve_by_search for update/delete/named action patterns.
Adds _auto_batch for bulk POST /*/list optimization.
Action dispatch handles 15 action types with FallbackContext on search miss."
```

---

### Task 4: Integration test + deploy + smoke test

**Files:**
- Modify: `smoke_test.py`
- No new files

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [ ] **Step 2: Add action pattern smoke tests**

Add to `smoke_test.py` TASKS dict:

```python
"update_customer": {
    "tier": 2,
    "prompt": (
        f"Opprett en kunde med navn '{u('UpdateTest AS')}', "
        f"deretter oppdater e-posten til kunden til test_{_run_id}@update.no"
    ),
    "verify": {
        "endpoint": "/customer",
        "search": {"name": u("UpdateTest AS")},
        "expect": {"email": f"test_{_run_id}@update.no"},
    },
},
"delete_department": {
    "tier": 2,
    "prompt": (
        f"Opprett en avdeling med navn '{u('SlettMeg')}' og avdelingsnummer '{_run_id[:3]}1', "
        f"deretter slett avdelingen"
    ),
    "verify": {
        "endpoint": "/department",
        "search": {"name": u("SlettMeg")},
        "expect": {},  # should NOT be found
    },
},
```

- [ ] **Step 3: Deploy to Cloud Run**

```bash
gcloud run deploy ai-accounting-agent-det --source . \
  --region europe-north1 --project ai-nm26osl-1799 \
  --no-allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global" \
  --quiet
```

- [ ] **Step 4: Run Tier 1 smoke tests**

```bash
source .env && export TRIPLETEX_SESSION_TOKEN
python smoke_test.py --tier 1
```

Expected: All Tier 1 tasks PASS with verify=PASS.
Check logs for `path=deterministic` (not `path=deterministic+fallback`).

- [ ] **Step 5: Run Tier 2 smoke tests**

```bash
python smoke_test.py --tier 2
```

Expected: Most Tier 2 tasks PASS. Some may fall back but should still complete.

- [ ] **Step 6: Check logs for routing**

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="ai-accounting-agent-det" AND textPayload=~"result:"' \
  --project ai-nm26osl-1799 --limit 20 --format="value(textPayload)" --freshness=15m
```

Expected: See `path=deterministic` for simple creates, `path=fallback` for complex patterns.

- [ ] **Step 7: Commit any fixes**

```bash
git add smoke_test.py && git commit -m "test: smoke test verified — deterministic path working for Tier 1+2"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Registry: 27 entities, 15 actions, 6 bulk, search params | `task_registry.py`, `tests/test_task_registry.py` |
| 2 | Planner: parse fix, few-shot examples, pattern matcher rewrite | `planner.py`, `tests/test_planner.py` |
| 3 | Executor: pre-lookups, search, batch, action dispatch | `executor.py`, `tests/test_executor.py` |
| 4 | Deploy + smoke test | `smoke_test.py` |
