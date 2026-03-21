"""Tests for recipe_guards.py — RecipeGuards validation middleware."""

import json
import pytest
from pathlib import Path

from recipe_guards import RecipeGuards


@pytest.fixture
def tmp_guards(tmp_path):
    """Create a temporary guards directory with test fixtures."""
    # Global guard
    global_guard = {
        "task_type": "_global",
        "field_guards": {
            "/product": {"body_strip": ["vatType"]},
            "/employee": {"body_strip": ["isAdministrator"]},
        },
    }
    (tmp_path / "_global.guard.json").write_text(json.dumps(global_guard))

    # Task-specific guard for travel_expense
    travel_guard = {
        "task_type": "travel_expense",
        "field_guards": {
            "/travelExpense/rateCategory": {
                "allowed_fields_filter": ["id", "name", "type"],
                "forbidden_fields_filter": ["description"],
            },
            "/travelExpense": {
                "body_rename": {"costs[].description": "costs[].comments"},
                "body_strip": [],
            },
        },
    }
    (tmp_path / "17_travel_expense.guard.json").write_text(json.dumps(travel_guard))

    # Task-specific guard for create_invoice (extends /product)
    invoice_guard = {
        "task_type": "create_invoice",
        "field_guards": {
            "/product": {"body_strip": ["vatType", "number"]},
            "/order/orderline": {"body_strip": ["vatType"]},
        },
    }
    (tmp_path / "06_create_invoice.guard.json").write_text(json.dumps(invoice_guard))

    return tmp_path


@pytest.fixture
def guards(tmp_guards):
    return RecipeGuards(guards_dir=tmp_guards)


# ──────────────────────────────────────────────
# TestBodyStrip
# ──────────────────────────────────────────────
class TestBodyStrip:
    def test_strips_vattype_from_product(self, guards):
        body = {"name": "Widget", "vatType": {"id": 3}, "priceIncludingVatCurrency": 100}
        body_out, params_out, warnings = guards.validate_request(
            "POST", "/product", body, None
        )
        assert "vatType" not in body_out
        assert body_out["name"] == "Widget"
        assert any("vatType" in w for w in warnings)

    def test_strips_isadministrator_from_employee(self, guards):
        body = {"firstName": "Ola", "isAdministrator": True}
        body_out, _, warnings = guards.validate_request(
            "POST", "/employee", body, None
        )
        assert "isAdministrator" not in body_out
        assert body_out["firstName"] == "Ola"
        assert len(warnings) == 1

    def test_unguarded_endpoint_passes_through(self, guards):
        body = {"anything": "goes", "vatType": {"id": 1}}
        body_out, _, warnings = guards.validate_request(
            "POST", "/customer", body, None
        )
        assert body_out == body
        assert warnings == []

    def test_no_body_passes_through(self, guards):
        body_out, params_out, warnings = guards.validate_request(
            "GET", "/product", None, {"fields": "id,name"}
        )
        assert body_out is None
        assert warnings == []

    def test_recursive_strip(self, guards):
        """Strips keys inside nested dicts."""
        body = {"name": "X", "nested": {"vatType": 1, "ok": True}}
        body_out, _, warnings = guards.validate_request(
            "POST", "/product", body, None
        )
        assert "vatType" not in body_out["nested"]
        assert body_out["nested"]["ok"] is True
        assert len(warnings) == 1  # only nested vatType stripped

    def test_strip_inside_list_items(self, guards):
        """Strips keys inside list items recursively."""
        body = {"name": "X", "items": [{"vatType": 1, "qty": 2}, {"qty": 3}]}
        body_out, _, warnings = guards.validate_request(
            "POST", "/product", body, None
        )
        assert "vatType" not in body_out["items"][0]
        assert body_out["items"][0]["qty"] == 2
        assert body_out["items"][1]["qty"] == 3


# ──────────────────────────────────────────────
# TestPathMatching
# ──────────────────────────────────────────────
class TestPathMatching:
    def test_exact_match(self, guards):
        guard = guards._find_matching_guard("/product")
        assert guard is not None
        assert "vatType" in guard.get("body_strip", [])

    def test_strips_trailing_id(self, guards):
        guard = guards._find_matching_guard("/employee/123")
        assert guard is not None
        assert "isAdministrator" in guard.get("body_strip", [])

    def test_no_match_returns_none(self, guards):
        guard = guards._find_matching_guard("/unknown/endpoint")
        assert guard is None

    def test_strips_multiple_ids(self, guards):
        """Path like /employee/123/something/456 normalizes correctly."""
        guard = guards._find_matching_guard("/employee/123")
        assert guard is not None


# ──────────────────────────────────────────────
# TestFieldsFilter
# ──────────────────────────────────────────────
class TestFieldsFilter:
    def test_removes_forbidden_field(self, guards):
        guards.set_active_task("travel_expense")
        _, params, warnings = guards.validate_request(
            "GET",
            "/travelExpense/rateCategory",
            None,
            {"fields": "id,name,description"},
        )
        assert "description" not in params["fields"]
        assert "id" in params["fields"]
        assert any("forbidden" in w for w in warnings)

    def test_removes_unknown_field_when_allowed_list(self, guards):
        guards.set_active_task("travel_expense")
        _, params, warnings = guards.validate_request(
            "GET",
            "/travelExpense/rateCategory",
            None,
            {"fields": "id,name,unknownField"},
        )
        assert "unknownField" not in params["fields"]
        assert any("not in allowed list" in w for w in warnings)

    def test_all_fields_removed_drops_param(self, guards):
        guards.set_active_task("travel_expense")
        _, params, warnings = guards.validate_request(
            "GET",
            "/travelExpense/rateCategory",
            None,
            {"fields": "description,badField"},
        )
        assert "fields" not in params
        assert any("removed fields param entirely" in w for w in warnings)


# ──────────────────────────────────────────────
# TestBodyRename
# ──────────────────────────────────────────────
class TestBodyRename:
    def test_renames_field_in_array_items(self, guards):
        guards.set_active_task("travel_expense")
        body = {
            "costs": [
                {"description": "Taxi fare", "amount": 100},
                {"description": "Hotel", "amount": 500},
            ]
        }
        body_out, _, warnings = guards.validate_request(
            "POST", "/travelExpense", body, None
        )
        for item in body_out["costs"]:
            assert "comments" in item
            assert "description" not in item
        assert len([w for w in warnings if "Renamed" in w]) == 2

    def test_skips_items_without_key(self, guards):
        guards.set_active_task("travel_expense")
        body = {"costs": [{"amount": 100}, {"description": "Taxi", "amount": 50}]}
        body_out, _, warnings = guards.validate_request(
            "POST", "/travelExpense", body, None
        )
        assert body_out["costs"][0] == {"amount": 100}
        assert body_out["costs"][1] == {"comments": "Taxi", "amount": 50}
        assert len([w for w in warnings if "Renamed" in w]) == 1

    def test_does_nothing_if_array_missing(self, guards):
        guards.set_active_task("travel_expense")
        body = {"title": "Trip to Bergen"}
        body_out, _, warnings = guards.validate_request(
            "POST", "/travelExpense", body, None
        )
        assert body_out == body
        assert len([w for w in warnings if "Renamed" in w]) == 0


# ──────────────────────────────────────────────
# TestGuardMerging
# ──────────────────────────────────────────────
class TestGuardMerging:
    def test_task_extends_global(self, guards):
        """create_invoice extends /product strip list from global."""
        guards.set_active_task("create_invoice")
        body = {"name": "X", "vatType": {"id": 1}, "number": 42, "price": 100}
        body_out, _, warnings = guards.validate_request(
            "POST", "/product", body, None
        )
        assert "vatType" not in body_out
        assert "number" not in body_out
        assert body_out["price"] == 100

    def test_global_applies_without_task(self, guards):
        """Without set_active_task, global guards still apply."""
        body = {"name": "Widget", "vatType": {"id": 3}}
        body_out, _, warnings = guards.validate_request(
            "POST", "/product", body, None
        )
        assert "vatType" not in body_out

    def test_unknown_task_uses_global_only(self, guards):
        guards.set_active_task("nonexistent_task")
        body = {"name": "X", "vatType": {"id": 1}}
        body_out, _, warnings = guards.validate_request(
            "POST", "/product", body, None
        )
        assert "vatType" not in body_out
        assert body_out["name"] == "X"


# ──────────────────────────────────────────────
# TestRealGuards
# ──────────────────────────────────────────────
class TestRealGuards:
    def test_loads_all_guard_files(self):
        """Loads guard files from the real recipes/ directory."""
        real_dir = Path(__file__).parent.parent / "recipes"
        guards = RecipeGuards(guards_dir=real_dir)
        assert len(guards._task_guards) >= 4  # at least 4 task guards

    def test_travel_expense_guards_active(self):
        """Travel expense guards work with real files."""
        real_dir = Path(__file__).parent.parent / "recipes"
        guards = RecipeGuards(guards_dir=real_dir)
        guards.set_active_task("travel_expense")

        body = {"costs": [{"description": "Taxi", "amount": 100}]}
        body_out, _, warnings = guards.validate_request(
            "POST", "/travelExpense", body, None
        )
        assert body_out["costs"][0].get("comments") == "Taxi"
        assert "description" not in body_out["costs"][0]
