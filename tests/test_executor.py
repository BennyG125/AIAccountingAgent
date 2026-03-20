# tests/test_executor.py
"""Tests for executor.py — deterministic execution with mocked TripletexClient."""

from unittest.mock import MagicMock, patch

_mock_genai_client = MagicMock()
with patch("google.genai.Client", return_value=_mock_genai_client):
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
