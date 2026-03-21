# Phased Agent with Structured Recipes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce API errors on complex Tripletex tasks by adding validation middleware (field guards) and pre-classification with focused prompting.

**Architecture:** Three-phase pipeline: (1) classify task + extract values, (2) focused agentic loop with scoped prompt, (3) validation middleware catches known field errors before they hit the API. Each phase is independently deployable. Guards are the highest-ROI change.

**Tech Stack:** Python 3.13, FastAPI, Anthropic Claude via Vertex AI, pytest

**Spec:** `docs/superpowers/specs/2026-03-21-phased-agent-structured-recipes-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `recipe_guards.py` | **NEW** — `RecipeGuards` class: loads `.guard.json` files, validates/transforms API requests |
| `tests/test_recipe_guards.py` | **NEW** — Unit tests for all guard behaviors |
| `recipes/_global.guard.json` | **NEW** — Global guard rules (vatType on products, isAdministrator on employees) |
| `recipes/17_travel_expense.guard.json` | **NEW** — Travel expense field guards |
| `recipes/06_create_invoice.guard.json` | **NEW** — Invoice creation field guards |
| `recipes/10_run_salary.guard.json` | **NEW** — Salary run field guards |
| `recipes/11_register_supplier_invoice.guard.json` | **NEW** — Supplier invoice field guards |
| `agent.py` | **MODIFY** — Integrate guards into `execute_tool()`, add `classify_and_extract()`, wire Phase 1 into `run_agent()` |
| `prompts.py` | **MODIFY** — Add `build_focused_prompt()`, extract shared gotchas section |
| `tests/test_classify.py` | **NEW** — Tests for classification, focused prompt, recipe mapping |
| `recipes/*.extract.json` | **NEW** — Per-task extraction schemas (one per recipe .md file) |

---

## Task 1: RecipeGuards core — global guards + body_strip

**Files:**
- Create: `recipe_guards.py`
- Create: `tests/test_recipe_guards.py`
- Create: `recipes/_global.guard.json`

- [ ] **Step 1: Write failing tests for body_strip**

```python
# tests/test_recipe_guards.py
import json
import pytest
from pathlib import Path
from recipe_guards import RecipeGuards


@pytest.fixture
def tmp_guards(tmp_path):
    """Create a minimal guard setup in a temp directory."""
    global_guard = {
        "task_type": "_global",
        "field_guards": {
            "/product": {"body_strip": ["vatType"]},
            "/employee": {"body_strip": ["isAdministrator"]},
        },
    }
    (tmp_path / "_global.guard.json").write_text(json.dumps(global_guard))
    return tmp_path


class TestBodyStrip:
    def test_strips_vattype_from_product(self, tmp_guards):
        guards = RecipeGuards(tmp_guards)
        body = {"name": "Widget", "vatType": {"id": 3}, "priceExcludingVatCurrency": 100}
        body, params, warnings = guards.validate_request("POST", "/product", body=body, params=None)
        assert "vatType" not in body
        assert body["name"] == "Widget"
        assert len(warnings) == 1
        assert "vatType" in warnings[0]

    def test_strips_isadministrator_from_employee(self, tmp_guards):
        guards = RecipeGuards(tmp_guards)
        body = {"firstName": "Ola", "isAdministrator": True}
        body, params, warnings = guards.validate_request("POST", "/employee", body=body, params=None)
        assert "isAdministrator" not in body
        assert body["firstName"] == "Ola"

    def test_unguarded_endpoint_passes_through(self, tmp_guards):
        guards = RecipeGuards(tmp_guards)
        body = {"name": "Test", "vatType": {"id": 3}}
        body, params, warnings = guards.validate_request("POST", "/customer", body=body, params=None)
        assert body["vatType"] == {"id": 3}
        assert warnings == []

    def test_no_body_passes_through(self, tmp_guards):
        guards = RecipeGuards(tmp_guards)
        body, params, warnings = guards.validate_request("GET", "/product", body=None, params=None)
        assert body is None
        assert warnings == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_recipe_guards.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'recipe_guards'`

- [ ] **Step 3: Implement RecipeGuards with body_strip**

```python
# recipe_guards.py
"""Validation middleware for Tripletex API calls.

Loads .guard.json files from the recipes directory and validates/transforms
API requests before they reach Tripletex. Catches known field-name errors
that Claude's agentic loop tends to make.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class RecipeGuards:
    """Validates and transforms API calls against structured recipe rules."""

    def __init__(self, guards_dir: Path | None = None):
        if guards_dir is None:
            guards_dir = Path(__file__).parent / "recipes"
        self._guards_dir = guards_dir
        self._global_guards = self._load_guard_file("_global")
        self._task_guards: dict = {}
        self._active_guards: dict = {}  # merged guards for current task

        # Load all task-specific guard files
        for f in guards_dir.glob("*.guard.json"):
            if f.stem == "_global":
                continue
            guard = json.loads(f.read_text())
            task_type = guard.get("task_type", f.stem)
            self._task_guards[task_type] = guard

        # Default: only global guards active
        self._active_guards = self._global_guards

    def _load_guard_file(self, name: str) -> dict:
        path = self._guards_dir / f"{name}.guard.json"
        if path.exists():
            return json.loads(path.read_text())
        return {"task_type": name, "field_guards": {}}

    def set_active_task(self, task_type: str):
        """Merge global + task-specific guards. Task-specific extends global."""
        task = self._task_guards.get(task_type, {"field_guards": {}})
        merged_guards = {}

        # Start with global guards
        for path, rules in self._global_guards.get("field_guards", {}).items():
            merged_guards[path] = dict(rules)

        # Extend with task-specific
        for path, rules in task.get("field_guards", {}).items():
            if path in merged_guards:
                existing = merged_guards[path]
                # Concatenate lists
                for key in ("body_strip", "forbidden_fields_filter", "allowed_fields_filter"):
                    if key in rules:
                        existing[key] = list(set(existing.get(key, []) + rules[key]))
                # Merge rename dicts (task-specific wins on conflicts)
                if "body_rename" in rules:
                    existing.setdefault("body_rename", {}).update(rules["body_rename"])
            else:
                merged_guards[path] = dict(rules)

        self._active_guards = {"field_guards": merged_guards}

    def validate_request(
        self, method: str, path: str, body: dict | None, params: dict | None
    ) -> tuple[dict | None, dict | None, list[str]]:
        """Validate and transform a request. Returns (body, params, warnings)."""
        warnings: list[str] = []
        guard = self._find_matching_guard(path)
        if not guard:
            return body, params, warnings

        # Apply fields filter validation (GET requests)
        if params and "fields" in params:
            params, field_warnings = self._validate_fields_filter(params, guard)
            warnings.extend(field_warnings)

        # Apply body transformations (POST/PUT)
        if body:
            body, body_warnings = self._transform_body(body, guard)
            warnings.extend(body_warnings)

        return body, params, warnings

    def _find_matching_guard(self, path: str) -> dict | None:
        """Find the best matching guard for a path using longest-prefix match."""
        guards = self._active_guards.get("field_guards", {})
        if not guards:
            return None

        # Strip trailing ID segments: /employee/123 → /employee
        normalized = re.sub(r"/\d+(/|$)", r"\1", path).rstrip("/")

        # Exact match first
        if normalized in guards:
            return guards[normalized]

        # Longest prefix match
        best_match = None
        best_len = 0
        for guard_path in guards:
            if normalized.startswith(guard_path) and len(guard_path) > best_len:
                best_match = guard_path
                best_len = len(guard_path)

        return guards[best_match] if best_match else None

    def _validate_fields_filter(
        self, params: dict, guard: dict
    ) -> tuple[dict, list[str]]:
        """Remove forbidden fields from ?fields= param."""
        warnings: list[str] = []
        fields_str = params.get("fields", "")
        if not fields_str:
            return params, warnings

        fields = [f.strip() for f in fields_str.split(",")]
        forbidden = set(guard.get("forbidden_fields_filter", []))
        allowed = set(guard.get("allowed_fields_filter", []))

        filtered = []
        for f in fields:
            if f in forbidden:
                warnings.append(f"Removed forbidden field '{f}' from fields filter")
                continue
            if allowed and f not in allowed:
                warnings.append(f"Removed unknown field '{f}' from fields filter (not in allowed list)")
                continue
            filtered.append(f)

        params = dict(params)
        if filtered:
            params["fields"] = ",".join(filtered)
        else:
            del params["fields"]
            warnings.append("All fields were filtered out — removed fields param entirely")

        return params, warnings

    def _transform_body(self, body: dict, guard: dict) -> tuple[dict, list[str]]:
        """Apply body_strip and body_rename rules."""
        warnings: list[str] = []
        body = dict(body)  # shallow copy

        # body_strip: remove forbidden keys (top-level and recursive)
        strip_keys = set(guard.get("body_strip", []))
        if strip_keys:
            body, strip_warnings = self._strip_keys(body, strip_keys)
            warnings.extend(strip_warnings)

        # body_rename: rename keys in arrays
        renames = guard.get("body_rename", {})
        for path, new_key_suffix in renames.items():
            # Parse "costs[].description" → array_key="costs", old_key="description"
            match = re.match(r"^(\w+)\[\]\.(\w+)$", path)
            if not match:
                continue
            array_key, old_key = match.groups()
            new_match = re.match(r"^(\w+)\[\]\.(\w+)$", new_key_suffix)
            if not new_match:
                logger.warning(f"Invalid body_rename target format: {new_key_suffix}")
                continue
            _, new_key = new_match.groups()

            if array_key in body and isinstance(body[array_key], list):
                for item in body[array_key]:
                    if isinstance(item, dict) and old_key in item:
                        item[new_key] = item.pop(old_key)
                        warnings.append(
                            f"Renamed '{old_key}' → '{new_key}' in {array_key}[] item"
                        )

        return body, warnings

    def _strip_keys(self, obj: dict, keys: set) -> tuple[dict, list[str]]:
        """Recursively strip forbidden keys from a dict."""
        warnings: list[str] = []
        result = {}
        for k, v in obj.items():
            if k in keys:
                warnings.append(f"Stripped forbidden field '{k}' from request body")
                continue
            if isinstance(v, dict):
                v, sub_warnings = self._strip_keys(v, keys)
                warnings.extend(sub_warnings)
            elif isinstance(v, list):
                new_list = []
                for item in v:
                    if isinstance(item, dict):
                        item, sub_warnings = self._strip_keys(item, keys)
                        warnings.extend(sub_warnings)
                    new_list.append(item)
                v = new_list
            result[k] = v
        return result, warnings
```

- [ ] **Step 4: Create global guard file**

```json
// recipes/_global.guard.json
{
  "task_type": "_global",
  "field_guards": {
    "/product": {
      "body_strip": ["vatType"]
    },
    "/employee": {
      "body_strip": ["isAdministrator"]
    }
  }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_recipe_guards.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add recipe_guards.py tests/test_recipe_guards.py recipes/_global.guard.json
git commit -m "feat: add RecipeGuards validation middleware with global body_strip rules"
```

---

## Task 2: Additional path matching + fields filter tests

**Files:**
- Modify: `tests/test_recipe_guards.py`

Note: The implementation for path matching and fields filter was included in Task 1.
These tests verify that implementation works correctly for edge cases.

- [ ] **Step 1: Add path matching and fields filter tests**

```python
# Add to tests/test_recipe_guards.py

@pytest.fixture
def travel_guards(tmp_path):
    """Guard setup with travel expense rules."""
    global_guard = {
        "task_type": "_global",
        "field_guards": {
            "/product": {"body_strip": ["vatType"]},
        },
    }
    travel_guard = {
        "task_type": "travel_expense",
        "field_guards": {
            "/travelExpense/rateCategory": {
                "allowed_fields_filter": ["id", "name", "type", "fromDate", "toDate", "isValidDomestic"],
                "forbidden_fields_filter": ["description"],
            },
            "/travelExpense/costCategory": {
                "allowed_fields_filter": ["id", "description", "showOnTravelExpenses"],
            },
        },
        "expected_calls_range": [7, 8],
        "max_errors": 0,
    }
    (tmp_path / "_global.guard.json").write_text(json.dumps(global_guard))
    (tmp_path / "17_travel_expense.guard.json").write_text(json.dumps(travel_guard))
    return tmp_path


class TestPathMatching:
    def test_exact_match(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        guards.set_active_task("travel_expense")
        guard = guards._find_matching_guard("/travelExpense/rateCategory")
        assert guard is not None
        assert "description" in guard.get("forbidden_fields_filter", [])

    def test_strips_trailing_id(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        guards.set_active_task("travel_expense")
        guard = guards._find_matching_guard("/product/123")
        assert guard is not None
        assert "vatType" in guard.get("body_strip", [])

    def test_no_match_returns_none(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        guards.set_active_task("travel_expense")
        guard = guards._find_matching_guard("/customer")
        assert guard is None


class TestFieldsFilter:
    def test_removes_forbidden_field(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        guards.set_active_task("travel_expense")
        body, params, warnings = guards.validate_request(
            "GET", "/travelExpense/rateCategory",
            body=None, params={"fields": "id,name,description"},
        )
        assert "description" not in params["fields"]
        assert "id" in params["fields"]
        assert "name" in params["fields"]
        assert len(warnings) == 1

    def test_removes_unknown_field_when_allowed_list_exists(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        guards.set_active_task("travel_expense")
        body, params, warnings = guards.validate_request(
            "GET", "/travelExpense/rateCategory",
            body=None, params={"fields": "id,name,bogusField"},
        )
        assert "bogusField" not in params["fields"]
        assert "id" in params["fields"]

    def test_all_fields_removed_drops_param(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        guards.set_active_task("travel_expense")
        body, params, warnings = guards.validate_request(
            "GET", "/travelExpense/rateCategory",
            body=None, params={"fields": "description"},
        )
        assert "fields" not in params
```

- [ ] **Step 2: Run tests to verify they pass** (implementation already covers this)

Run: `python -m pytest tests/test_recipe_guards.py -v`
Expected: All tests PASS (path matching and fields filter are already in Task 1's implementation)

- [ ] **Step 3: Commit**

```bash
git add tests/test_recipe_guards.py
git commit -m "test: add path matching and fields filter validation tests"
```

---

## Task 3: body_rename for array items

**Files:**
- Modify: `tests/test_recipe_guards.py`

- [ ] **Step 1: Write failing tests for body_rename**

```python
# Add to tests/test_recipe_guards.py

@pytest.fixture
def rename_guards(tmp_path):
    """Guard setup with body_rename rules."""
    guard = {
        "task_type": "_global",
        "field_guards": {
            "/travelExpense": {
                "body_rename": {
                    "costs[].description": "costs[].comments",
                },
            },
        },
    }
    (tmp_path / "_global.guard.json").write_text(json.dumps(guard))
    return tmp_path


class TestBodyRename:
    def test_renames_field_in_array_items(self, rename_guards):
        guards = RecipeGuards(rename_guards)
        body = {
            "employee": {"id": 1},
            "costs": [
                {"description": "Flight ticket", "amountCurrencyIncVat": 5000},
                {"description": "Taxi", "amountCurrencyIncVat": 450},
            ],
        }
        body, params, warnings = guards.validate_request("POST", "/travelExpense", body=body, params=None)
        assert body["costs"][0]["comments"] == "Flight ticket"
        assert "description" not in body["costs"][0]
        assert body["costs"][1]["comments"] == "Taxi"
        assert len(warnings) == 2

    def test_rename_skips_items_without_key(self, rename_guards):
        guards = RecipeGuards(rename_guards)
        body = {
            "costs": [
                {"comments": "Already correct", "amountCurrencyIncVat": 100},
            ],
        }
        body, params, warnings = guards.validate_request("POST", "/travelExpense", body=body, params=None)
        assert body["costs"][0]["comments"] == "Already correct"
        assert warnings == []

    def test_rename_does_nothing_if_array_missing(self, rename_guards):
        guards = RecipeGuards(rename_guards)
        body = {"employee": {"id": 1}, "title": "Trip"}
        body, params, warnings = guards.validate_request("POST", "/travelExpense", body=body, params=None)
        assert body == {"employee": {"id": 1}, "title": "Trip"}
        assert warnings == []
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_recipe_guards.py::TestBodyRename -v`
Expected: All 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_recipe_guards.py
git commit -m "test: add body_rename array item tests for travel expense"
```

---

## Task 4: Guard merging (global + task-specific)

**Files:**
- Modify: `tests/test_recipe_guards.py`

- [ ] **Step 1: Write tests for guard merging**

```python
# Add to tests/test_recipe_guards.py

class TestGuardMerging:
    def test_task_extends_global(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        guards.set_active_task("travel_expense")
        # Global: /product has body_strip: ["vatType"]
        # Task: /travelExpense/rateCategory has forbidden_fields_filter
        # Both should be active
        product_guard = guards._find_matching_guard("/product")
        assert product_guard is not None
        assert "vatType" in product_guard.get("body_strip", [])

        rate_guard = guards._find_matching_guard("/travelExpense/rateCategory")
        assert rate_guard is not None
        assert "description" in rate_guard.get("forbidden_fields_filter", [])

    def test_global_applies_without_task(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        # No set_active_task — only global guards
        body = {"name": "Widget", "vatType": {"id": 3}}
        body, _, warnings = guards.validate_request("POST", "/product", body=body, params=None)
        assert "vatType" not in body

    def test_unknown_task_uses_global_only(self, travel_guards):
        guards = RecipeGuards(travel_guards)
        guards.set_active_task("nonexistent_task")
        # Should still have global guards
        body = {"name": "Widget", "vatType": {"id": 3}}
        body, _, warnings = guards.validate_request("POST", "/product", body=body, params=None)
        assert "vatType" not in body
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_recipe_guards.py::TestGuardMerging -v`
Expected: All 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_recipe_guards.py
git commit -m "test: add guard merging tests — task-specific extends global"
```

---

## Task 5: Create task-specific guard files

**Files:**
- Create: `recipes/17_travel_expense.guard.json`
- Create: `recipes/06_create_invoice.guard.json`
- Create: `recipes/10_run_salary.guard.json`
- Create: `recipes/11_register_supplier_invoice.guard.json`

- [ ] **Step 1: Create travel_expense guard**

```json
{
  "task_type": "travel_expense",
  "field_guards": {
    "/travelExpense/rateCategory": {
      "allowed_fields_filter": ["id", "name", "type", "fromDate", "toDate", "isValidDomestic"],
      "forbidden_fields_filter": ["description"]
    },
    "/travelExpense/costCategory": {
      "allowed_fields_filter": ["id", "description", "showOnTravelExpenses"]
    },
    "/travelExpense": {
      "body_rename": {"costs[].description": "costs[].comments"},
      "body_strip": []
    }
  },
  "expected_calls_range": [7, 8],
  "max_errors": 0
}
```

- [ ] **Step 2: Create create_invoice guard**

```json
{
  "task_type": "create_invoice",
  "field_guards": {
    "/product": {
      "body_strip": ["vatType", "number"]
    },
    "/order/orderline": {
      "body_strip": ["vatType"]
    }
  },
  "expected_calls_range": [4, 6],
  "max_errors": 0
}
```

Note: `number` is stripped from products because it frequently causes "Produktnummeret X er i bruk" errors. Tripletex auto-assigns product numbers.

- [ ] **Step 3: Create run_salary guard**

```json
{
  "task_type": "run_salary",
  "field_guards": {
    "/employee": {
      "body_strip": ["isAdministrator"]
    }
  },
  "expected_calls_range": [6, 10],
  "max_errors": 0
}
```

- [ ] **Step 4: Create register_supplier_invoice guard**

```json
{
  "task_type": "register_supplier_invoice",
  "field_guards": {
    "/ledger/voucher": {
      "body_strip": []
    }
  },
  "expected_calls_range": [4, 6],
  "max_errors": 0
}
```

- [ ] **Step 5: Write a test that loads all guard files from the real recipes dir**

```python
# Add to tests/test_recipe_guards.py

class TestRealGuards:
    def test_loads_all_guard_files(self):
        """Verify all .guard.json files in recipes/ parse correctly."""
        recipes_dir = Path(__file__).parent.parent / "recipes"
        guards = RecipeGuards(recipes_dir)
        # Should have loaded global + task-specific
        assert len(guards._task_guards) >= 4
        for task_type, guard in guards._task_guards.items():
            assert "field_guards" in guard, f"{task_type} missing field_guards"

    def test_travel_expense_guards_active(self):
        recipes_dir = Path(__file__).parent.parent / "recipes"
        guards = RecipeGuards(recipes_dir)
        guards.set_active_task("travel_expense")
        # Should block description on rateCategory
        _, params, warnings = guards.validate_request(
            "GET", "/travelExpense/rateCategory",
            body=None, params={"fields": "id,name,description"},
        )
        assert "description" not in params.get("fields", "")
```

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/test_recipe_guards.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add recipes/17_travel_expense.guard.json recipes/06_create_invoice.guard.json \
       recipes/10_run_salary.guard.json recipes/11_register_supplier_invoice.guard.json \
       tests/test_recipe_guards.py
git commit -m "feat: add task-specific guard files for top 4 error-prone types"
```

---

## Task 6: Integrate guards into agent.py execute_tool()

**Files:**
- Modify: `agent.py:142-160` (execute_tool function)
- Modify: `agent.py:232-270` (run_agent function — pass guards)
- Modify: `agent.py:356-412` (tool execution loop — pass guards)

- [ ] **Step 1: Write integration test**

```python
# Add to tests/test_recipe_guards.py

class TestExecuteToolIntegration:
    def test_guards_strip_vattype_before_api_call(self, tmp_guards):
        """Verify guards transform the body before it reaches the client."""
        guards = RecipeGuards(tmp_guards)
        # We can't easily test execute_tool without a real client,
        # but we can test the guard is called correctly in the flow
        body = {"name": "Widget", "vatType": {"id": 3}}
        body, params, warnings = guards.validate_request("POST", "/product", body=body, params=None)
        assert "vatType" not in body
        assert len(warnings) == 1
```

- [ ] **Step 2: Modify execute_tool() to accept and apply guards**

In `agent.py`, change the `execute_tool` function signature and add guard application:

```python
# agent.py — modify execute_tool (around line 142)

def execute_tool(name: str, args: dict, client: TripletexClient,
                 guards: "RecipeGuards | None" = None) -> dict:
    """Execute a single tool call against the Tripletex API."""
    try:
        path = args.get("path", "")
        params = args.get("params")
        body = args.get("body")

        # Apply guards before sending
        if guards:
            body, params, warnings = guards.validate_request(
                method=name.replace("tripletex_", "").upper(),
                path=path, body=body, params=params,
            )
            for w in warnings:
                logger.warning(f"Guard: {w}")

        if name == "tripletex_get":
            return client.get(path, params=params)
        elif name == "tripletex_post":
            return client.post(path, body=body)
        elif name == "tripletex_put":
            return client.put(path, body=body, params=params)
        elif name == "tripletex_delete":
            return client.delete(path, params=params)
        else:
            return {"success": False, "error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

- [ ] **Step 3: Initialize guards in run_agent() and pass to execute_tool()**

In `agent.py`, add imports and initialization at the top of `run_agent()`, and pass `guards` in the tool execution loop:

```python
# At top of agent.py, add import:
from recipe_guards import RecipeGuards

# In run_agent(), after creating the TripletexClient (around line 238):
    guards = RecipeGuards()  # loads from recipes/ directory

# In the tool execution loop (around line 372), change:
#   result = execute_tool(block.name, block.input, client)
# to:
    result = execute_tool(block.name, block.input, client, guards=guards)
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All tests PASS. Existing tests should not break since `guards` defaults to `None`.

- [ ] **Step 5: Commit**

```bash
git add agent.py tests/test_recipe_guards.py
git commit -m "feat: integrate RecipeGuards into execute_tool() — global guards active"
```

---

## Task 7: build_focused_prompt() + recipe file mapping

**Files:**
- Modify: `prompts.py`
- Create: `tests/test_focused_prompt.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_focused_prompt.py
import pytest
from pathlib import Path
from prompts import build_focused_prompt, _build_recipe_map


class TestRecipeMap:
    def test_maps_task_type_to_recipe_file(self):
        recipe_map = _build_recipe_map()
        assert "travel_expense" in recipe_map
        assert "create_invoice" in recipe_map
        assert "create_customer" in recipe_map
        # Value should be a Path to the .md file
        assert recipe_map["travel_expense"].name == "17_travel_expense.md"

    def test_all_recipes_have_entries(self):
        recipe_map = _build_recipe_map()
        recipes_dir = Path(__file__).parent.parent / "recipes"
        md_files = list(recipes_dir.glob("[0-9]*.md"))
        assert len(recipe_map) == len(md_files)


class TestFocusedPrompt:
    def test_contains_matched_recipe(self):
        prompt = build_focused_prompt("travel_expense")
        assert "Travel Expense" in prompt or "travel expense" in prompt.lower()

    def test_contains_scoring_rules(self):
        prompt = build_focused_prompt("create_customer")
        assert "MINIMIZE API calls" in prompt

    def test_contains_gotchas(self):
        prompt = build_focused_prompt("create_invoice")
        assert "vatType" in prompt

    def test_does_not_contain_cheat_sheet(self):
        prompt = build_focused_prompt("create_customer")
        assert "Tripletex v2 API — Endpoint Reference" not in prompt

    def test_does_not_contain_other_recipes(self):
        prompt = build_focused_prompt("create_customer")
        # Should not contain travel expense recipe
        assert "rateCategory" not in prompt

    def test_unknown_task_raises(self):
        with pytest.raises(KeyError):
            build_focused_prompt("nonexistent_task_type")

    def test_today_date_substituted(self):
        from datetime import date
        prompt = build_focused_prompt("create_customer")
        assert date.today().isoformat() in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_focused_prompt.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_focused_prompt'`

- [ ] **Step 3: Implement build_focused_prompt and _build_recipe_map**

Add to `prompts.py`:

```python
# Add near top of prompts.py, after existing imports

def _build_recipe_map(recipes_dir: Path | None = None) -> dict[str, Path]:
    """Build mapping from task_type string to recipe .md file path.

    Scans recipe files named NN_task_type.md and extracts the task_type
    portion after the numeric prefix.
    """
    if recipes_dir is None:
        recipes_dir = Path(__file__).parent / "recipes"

    import re as _re
    recipe_map = {}
    for f in sorted(recipes_dir.glob("[0-9]*.md")):
        # "17_travel_expense.md" → "travel_expense"
        task_type = _re.sub(r"^\d+_", "", f.stem)
        recipe_map[task_type] = f

    return recipe_map


def build_focused_prompt(task_type: str, extracted_values: dict | None = None) -> str:
    """Build a slim system prompt with only the matched recipe + gotchas.

    Raises KeyError if task_type is not in the recipe map.
    """
    recipe_map = _build_recipe_map()
    recipe_path = recipe_map[task_type]  # KeyError if unknown

    today = date.today().isoformat()
    recipe_text = recipe_path.read_text().replace("{today}", today)

    return f"""You are an expert AI accounting agent for the Tripletex system. Your job is to complete accounting tasks by making API calls using the provided tools. Tasks may be in Norwegian, English, Spanish, Portuguese, German, or French.

Today's date: {today}

## MANDATORY: Follow the Recipe Below
The recipe contains the EXACT sequence of API calls with the EXACT field names that work.
Do NOT improvise your own approach — the recipe is tested and proven.
Do NOT use endpoints or field names not in the recipe — they cause errors.

## Scoring Rules
1. MINIMIZE API calls — fewer calls = higher efficiency bonus.
2. ZERO 4xx errors — every error reduces your score. Get it right on the first call.
3. NEVER make verification GETs after successful creates — wastes calls.
4. Use known constants directly — never look them up via API.
5. Embed orderLines in the order POST body — saves separate calls.
6. When done, STOP calling tools immediately. Do not verify your work.
7. If you get 403 "Invalid or expired proxy token" — STOP IMMEDIATELY. Do not retry.

## Known Constants (never look these up)
- NOK currency: {{"id": 1}}
- Norway country: {{"id": 162}}
- VAT types: IDs vary per environment. NEVER hardcode vatType IDs.
  For products: do NOT include vatType at all.
  For orderLines: vatType is optional — omit it.
  For voucher postings: look up with GET /ledger/vatType first.

## Critical Gotchas
- **Payment registration**: PUT /invoice/{{id}}/:payment uses QUERY PARAMS, NOT body.
- **Object refs** are ALWAYS {{"id": <int>}}, never bare integers.
- **departmentNumber** is a STRING, not an int.
- **vatType on products**: NEVER include vatType when creating or updating products.
- **Fresh account**: Tripletex starts EMPTY. Create prerequisites before dependents.
- **PUT updates**: Always include the "version" field from the GET response.
- **Error recovery**: If an API call fails mid-sequence, do NOT re-create entities that were already created successfully.
- **Smart retry**: If a call fails, read the error and CHANGE your approach. Never retry identical params.
- **403 = unrecoverable**: If ANY call returns 403 with "proxy token", STOP immediately.

## Recipe for This Task

{recipe_text}
"""
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_focused_prompt.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add prompts.py tests/test_focused_prompt.py
git commit -m "feat: add build_focused_prompt() with recipe file mapping"
```

---

## Task 8: Phase 1 — classify_and_extract()

**Files:**
- Modify: `agent.py`
- Create: `tests/test_classify.py`
- Create: `recipes/01_create_customer.extract.json` (+ 18 more)

- [ ] **Step 1: Create extraction schemas for all task types**

Create one `.extract.json` per recipe. Start with the 4 most important, then the rest. Each file follows this pattern:

```json
{
  "task_type": "create_customer",
  "description": "Create a customer with name, org number, and optional address",
  "keywords": ["customer", "kunde", "kunden", "Kunde", "client", "cliente"],
  "fields": {
    "name": {"type": "string", "required": true, "hint": "Company/person name"},
    "organization_number": {"type": "string", "required": false},
    "email": {"type": "string", "required": false},
    "address_line": {"type": "string", "required": false},
    "city": {"type": "string", "required": false},
    "postal_code": {"type": "string", "required": false}
  }
}
```

Create `.extract.json` files for all 20 recipe types. The `task_type` must match the recipe filename suffix (e.g., `01_create_customer.extract.json` has `task_type: "create_customer"`).

- [ ] **Step 2: Write tests for classify_and_extract**

```python
# tests/test_classify.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# agent.py imports google.genai at module level — mock before importing
with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock(), "google.genai.types": MagicMock()}):
    from agent import classify_and_extract, load_extraction_schemas


class TestLoadSchemas:
    def test_loads_all_extract_files(self):
        schemas = load_extraction_schemas()
        assert len(schemas) >= 4  # at minimum the ones we created
        assert "create_customer" in schemas
        assert "travel_expense" in schemas

    def test_schema_has_required_fields(self):
        schemas = load_extraction_schemas()
        for task_type, schema in schemas.items():
            assert "description" in schema, f"{task_type} missing description"
            assert "keywords" in schema, f"{task_type} missing keywords"
            assert "fields" in schema, f"{task_type} missing fields"


class TestClassifyAndExtract:
    @patch("agent.get_claude_client")
    def test_returns_classification(self, mock_get_client):
        """Mock the LLM call and verify the function handles the response."""
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = {
            "task_type": "create_customer",
            "confidence": 0.95,
            "extracted_values": {"name": "Fjordkraft AS", "organization_number": "843216285"},
        }
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_get_client.return_value.messages.create.return_value = mock_response

        schemas = load_extraction_schemas()
        result = classify_and_extract("Opprett kunden Fjordkraft AS med organisasjonsnummer 843216285", schemas)
        assert result["task_type"] == "create_customer"
        assert result["confidence"] == 0.95
        assert result["extracted_values"]["name"] == "Fjordkraft AS"

    @patch("agent.get_claude_client")
    def test_returns_unknown_on_empty_response(self, mock_get_client):
        mock_response = MagicMock()
        mock_response.content = []
        mock_get_client.return_value.messages.create.return_value = mock_response

        schemas = load_extraction_schemas()
        result = classify_and_extract("Something completely unknown", schemas)
        assert result["task_type"] == "unknown"
        assert result["confidence"] == 0.0

    @patch("agent.get_claude_client")
    def test_returns_unknown_on_exception(self, mock_get_client):
        mock_get_client.return_value.messages.create.side_effect = Exception("timeout")

        schemas = load_extraction_schemas()
        result = classify_and_extract("Any prompt", schemas)
        assert result["task_type"] == "unknown"
        assert result["confidence"] == 0.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_classify.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 4: Implement classify_and_extract and load_extraction_schemas**

Add to `agent.py`:

```python
# At top of agent.py, add import:
from pathlib import Path


def load_extraction_schemas(recipes_dir: Path | None = None) -> dict:
    """Load all .extract.json files from recipes directory."""
    if recipes_dir is None:
        recipes_dir = Path(__file__).parent / "recipes"

    schemas = {}
    for f in sorted(recipes_dir.glob("*.extract.json")):
        schema = json.loads(f.read_text())
        schemas[schema["task_type"]] = schema

    logger.info(f"Loaded {len(schemas)} extraction schemas")
    return schemas


def classify_and_extract(prompt: str, extraction_schemas: dict) -> dict:
    """Classify task type and extract values. One LLM call."""
    try:
        client = get_claude_client()

        catalog = [
            {
                "task_type": t,
                "description": s["description"],
                "keywords": s["keywords"],
                "fields": s["fields"],
            }
            for t, s in extraction_schemas.items()
        ]

        response = client.messages.create(
            model=CLAUDE_MODEL,
            system=[{"type": "text", "text":
                "You are a task classifier and value extractor for Tripletex accounting tasks. "
                "Classify the task and extract all relevant values. If unsure of the task type, "
                "return task_type: 'unknown'. Tasks may be in NO, EN, ES, PT, DE, or FR."}],
            messages=[{"role": "user", "content": f"Task types:\n{json.dumps(catalog)}\n\nPrompt:\n{prompt}"}],
            tools=[{
                "name": "classify_result",
                "description": "Return classification and extracted values",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_type": {"type": "string"},
                        "confidence": {"type": "number"},
                        "extracted_values": {"type": "object"},
                    },
                    "required": ["task_type", "confidence", "extracted_values"],
                },
            }],
            tool_choice={"type": "tool", "name": "classify_result"},
            max_tokens=2000,
        )

        for block in response.content:
            if block.type == "tool_use":
                return block.input

    except Exception as e:
        logger.warning(f"Phase 1 classify failed: {e}")

    return {"task_type": "unknown", "confidence": 0.0, "extracted_values": {}}
```

Also add `from pathlib import Path` to imports in agent.py if not already present.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_classify.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add agent.py tests/test_classify.py recipes/*.extract.json
git commit -m "feat: add classify_and_extract() with extraction schemas"
```

---

## Task 9: Wire Phase 1 + focused prompt into run_agent()

**Files:**
- Modify: `agent.py:232-270` (run_agent function)

- [ ] **Step 1: Modify run_agent() to call Phase 1 and select prompt mode**

In `agent.py`:
- Update the existing import `from prompts import build_system_prompt` to also import `build_focused_prompt`
- Modify `run_agent()` to add Phase 1 before the agentic loop:

```python
# In run_agent(), after OCR step and before "Step 2: Build messages":

    # Step 1.5: Phase 1 — Classify task and extract values
    task_type = None
    extracted_values = None
    try:
        extraction_schemas = load_extraction_schemas()
        if extraction_schemas:
            with trace_child("classify_and_extract", run_type="llm", inputs={
                "prompt_preview": prompt[:100],
            }) as classify_span:
                classification = classify_and_extract(prompt, extraction_schemas)
                task_type = classification.get("task_type")
                confidence = classification.get("confidence", 0.0)
                extracted_values = classification.get("extracted_values")

                if classify_span:
                    classify_span.end(outputs={
                        "task_type": task_type,
                        "confidence": confidence,
                        "extracted_values": extracted_values,
                    })

                logger.info(f"Phase 1: task_type={task_type} confidence={confidence:.2f}")

                # Fall back to full prompt if low confidence
                if confidence < 0.7 or task_type == "unknown":
                    logger.info("Phase 1: low confidence, falling back to full prompt")
                    task_type = None
                    extracted_values = None
    except Exception as e:
        logger.warning(f"Phase 1 failed, using full prompt: {e}")
        task_type = None
        extracted_values = None

    # Set active task on guards (for task-specific guard rules)
    if task_type:
        guards.set_active_task(task_type)

    # Step 2: Build messages
    if task_type:
        system_prompt = build_focused_prompt(task_type, extracted_values)
        logger.info(f"Using focused prompt for task_type={task_type} ({len(system_prompt)} chars)")
    else:
        system_prompt = build_system_prompt()

    user_message = build_user_message(prompt, file_contents, extracted_values)
```

- [ ] **Step 2: Update build_user_message to accept extracted_values**

In `agent.py`, modify the existing `build_user_message`:

```python
def build_user_message(prompt: str, file_contents: list[dict],
                       extracted_values: dict | None = None) -> str:
    """Build the user message from prompt and file contents."""
    parts = []

    if extracted_values:
        parts.append(f"[Pre-extracted values]\n{json.dumps(extracted_values, indent=2, ensure_ascii=False)}")

    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            parts.append(f"[Attached file: {f['filename']}]\n{text}")

    parts.append(prompt)

    return "\n\n".join(parts)
```

- [ ] **Step 3: Run all tests to verify no regression**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add agent.py
git commit -m "feat: wire Phase 1 classification + focused prompt into run_agent()"
```

---

## Task 10: Deploy and validate with save-and-replay

This task uses the existing skill pipeline, not code changes.

- [ ] **Step 1: Run unit tests one final time**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [ ] **Step 2: Deploy to dev container**

```bash
source .env
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-dev,LANGSMITH_API_KEY=$LANGSMITH_API_KEY" \
  --quiet
```

- [ ] **Step 3: Replay saved travel expense request**

```bash
source .env && export TRIPLETEX_BASE_URL TRIPLETEX_SESSION_TOKEN
python scripts/replay_request.py competition/requests/7a09d9d233f5.json
```

Expected: Error count drops from 5 to 0-1. Check LangSmith for guard warnings.

- [ ] **Step 4: Run smoke tests**

```bash
source .env && export TRIPLETEX_SESSION_TOKEN
python smoke_test.py --tier 1
python smoke_test.py --tier 2
```

Expected: No regression. Existing passing tasks still pass.

- [ ] **Step 5: If all good, deploy to competition container**

```bash
gcloud run deploy accounting-agent-comp --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-comp,LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP" \
  --quiet
```

- [ ] **Step 6: Commit any final adjustments**

Stage only the files you changed (avoid staging .idea/, competition requests, etc.):

```bash
git add agent.py prompts.py recipe_guards.py recipes/
git commit -m "chore: final adjustments from deploy validation"
```
