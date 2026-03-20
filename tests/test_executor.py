# tests/test_executor.py
"""Tests for executor.py — deterministic execution with mocked TripletexClient."""

from unittest.mock import MagicMock, patch

_mock_genai_client = MagicMock()
_mock_claude_client = MagicMock()
with patch("google.genai.Client", return_value=_mock_genai_client):
    with patch("claude_client.get_claude_client", return_value=_mock_claude_client):
        from executor import (
            execute_plan, _topological_sort, _build_payload,
            _resolve_pre_lookups, _resolve_by_search, _auto_batch,
        )
        from task_registry import BULK_ENDPOINTS


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
