"""Tests for executor.py — all mock TripletexClient, no real API calls."""

import copy
import json
from unittest.mock import MagicMock

import pytest

from executor import execute_plan, _substitute_value, _resolve_capture_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_client(**method_responses):
    """Create a mock TripletexClient with configurable responses per method.

    Usage: _mock_client(post={"success": True, "status_code": 201, "body": {...}})
    For multi-call sequences, pass a list: post=[resp1, resp2]
    """
    client = MagicMock()
    for method, resp in method_responses.items():
        mock_method = getattr(client, method)
        if isinstance(resp, list):
            mock_method.side_effect = resp
        else:
            mock_method.return_value = resp
    return client


def _ok(body: dict, status_code: int = 200) -> dict:
    return {"success": True, "status_code": status_code, "body": body}


def _fail(body: dict = None, status_code: int = 422, error: str = "Validation error") -> dict:
    return {
        "success": False,
        "status_code": status_code,
        "body": body or {},
        "error": error,
    }


def _plan(*steps) -> dict:
    return {"steps": list(steps)}


RESULT_KEYS_SUCCESS = {"success", "variables", "completed_steps", "results"}
RESULT_KEYS_FAILURE = RESULT_KEYS_SUCCESS | {"failed_step", "error", "remaining_steps"}
NORMALIZED_RESULT_KEYS = {"step_index", "method", "endpoint", "success", "status_code", "body", "error"}


# ===================================================================
# Happy path tests (1–14)
# ===================================================================


class TestHappyPath:
    def test_single_post_with_capture(self):
        """1. Single POST with capture."""
        client = _mock_client(post=_ok({"value": {"id": 42, "firstName": "Ola"}}))
        plan = _plan({
            "method": "POST",
            "endpoint": "/employee",
            "body": {"firstName": "Ola"},
            "capture": {"employee_id": "value.id"},
        })

        result = execute_plan(client, plan)

        assert result["success"] is True
        assert result["variables"]["employee_id"] == 42
        assert result["completed_steps"] == [0]
        client.post.assert_called_once_with("/employee", body={"firstName": "Ola"})

    def test_two_step_variable_threading(self):
        """2. POST captures ID, PUT uses it in endpoint."""
        client = _mock_client(
            post=_ok({"value": {"id": 42}}),
            put=_ok({"value": {"id": 42, "email": "ola@acme.no"}}),
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/employee",
                "body": {"firstName": "Ola"},
                "capture": {"employee_id": "value.id"},
            },
            {
                "method": "PUT",
                "endpoint": "/employee/{employee_id}",
                "body": {"email": "ola@acme.no"},
            },
        )

        result = execute_plan(client, plan)

        assert result["success"] is True
        assert result["completed_steps"] == [0, 1]
        client.put.assert_called_once_with("/employee/42", body={"email": "ola@acme.no"})

    def test_get_with_params(self):
        """3. GET with params."""
        client = _mock_client(get=_ok({"values": []}))
        plan = _plan({"method": "GET", "endpoint": "/employee", "params": {"firstName": "Ola"}})

        result = execute_plan(client, plan)

        assert result["success"] is True
        client.get.assert_called_once_with("/employee", params={"firstName": "Ola"})

    def test_delete_bare(self):
        """4. DELETE with no params."""
        client = _mock_client(delete=_ok({}))
        plan = _plan({"method": "DELETE", "endpoint": "/employee/42"})

        result = execute_plan(client, plan)

        assert result["success"] is True
        client.delete.assert_called_once_with("/employee/42")

    def test_delete_with_params(self):
        """5. DELETE with params encoded as query string."""
        client = _mock_client(delete=_ok({}))
        plan = _plan({"method": "DELETE", "endpoint": "/employee", "params": {"id": "42"}})

        result = execute_plan(client, plan)

        assert result["success"] is True
        client.delete.assert_called_once_with("/employee?id=42")

    def test_delete_with_empty_params(self):
        """6. DELETE with empty params dict does NOT append ?."""
        client = _mock_client(delete=_ok({}))
        plan = _plan({"method": "DELETE", "endpoint": "/employee/42"})

        result = execute_plan(client, plan)

        assert result["success"] is True
        call_arg = client.delete.call_args[0][0]
        assert "?" not in call_arg

    def test_whole_string_placeholder_preserves_type(self):
        """7. Whole-string placeholder preserves int type."""
        client = _mock_client(
            post=_ok({"value": {"id": 42}}),
            put=_ok({"value": {"id": 42}}),
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/customer",
                "body": {"name": "Acme"},
                "capture": {"cust_id": "value.id"},
            },
            {
                "method": "PUT",
                "endpoint": "/order/1",
                "body": {"customer": {"id": "{cust_id}"}},
            },
        )

        result = execute_plan(client, plan)

        assert result["success"] is True
        put_call = client.put.call_args
        assert put_call.kwargs["body"]["customer"]["id"] == 42
        assert isinstance(put_call.kwargs["body"]["customer"]["id"], int)

    def test_embedded_placeholder_in_endpoint(self):
        """8. Embedded placeholder in endpoint becomes string."""
        client = _mock_client(
            post=_ok({"value": {"id": 42}}),
            get=_ok({"value": {"id": 42}}),
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/employee",
                "body": {"firstName": "Ola"},
                "capture": {"eid": "value.id"},
            },
            {"method": "GET", "endpoint": "/employee/{eid}"},
        )

        result = execute_plan(client, plan)

        assert result["success"] is True
        client.get.assert_called_once_with("/employee/42", params=None)

    def test_repeated_embedded_placeholder(self):
        """9. Repeated embedded placeholder replaces both occurrences."""
        result = _substitute_value("/employee/{id}/manager/{id}", {"id": 99})
        assert result == "/employee/99/manager/99"

    def test_nested_body_with_placeholders(self):
        """10. Nested body with placeholders resolves correctly."""
        client = _mock_client(
            post=_ok({"value": {"id": 5}}),
            put=_ok({"value": {}}),
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/customer",
                "body": {"name": "Acme"},
                "capture": {"cust_id": "value.id"},
            },
            {
                "method": "PUT",
                "endpoint": "/order/1",
                "body": {"customer": {"id": "{cust_id}"}, "ref": "Order for {cust_id}"},
            },
        )

        result = execute_plan(client, plan)

        assert result["success"] is True
        put_body = client.put.call_args.kwargs["body"]
        assert put_body["customer"]["id"] == 5
        assert put_body["ref"] == "Order for 5"

    def test_list_body_with_placeholders(self):
        """11. List body with placeholders preserves whole-placeholder types."""
        result = _substitute_value({"ids": ["{a}", "{b}"]}, {"a": 1, "b": 2})
        assert result == {"ids": [1, 2]}

    def test_bare_get_no_body_params_capture(self):
        """12. Step with no body, no params, no capture."""
        client = _mock_client(get=_ok({"values": []}))
        plan = _plan({"method": "GET", "endpoint": "/employee"})

        result = execute_plan(client, plan)

        assert result["success"] is True
        assert result["completed_steps"] == [0]

    def test_capture_path_into_list(self):
        """13. Capture path 'values.0.id' resolves list index."""
        client = _mock_client(get=_ok({"values": [{"id": 77}]}))
        plan = _plan({
            "method": "GET",
            "endpoint": "/employee",
            "capture": {"eid": "values.0.id"},
        })

        result = execute_plan(client, plan)

        assert result["success"] is True
        assert result["variables"]["eid"] == 77

    def test_capture_overwrite(self):
        """14. Same variable captured twice, later value wins."""
        client = _mock_client(
            post=[
                _ok({"value": {"id": 10}}),
                _ok({"value": {"id": 20}}),
            ]
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/customer",
                "body": {"name": "A"},
                "capture": {"eid": "value.id"},
            },
            {
                "method": "POST",
                "endpoint": "/customer",
                "body": {"name": "B"},
                "capture": {"eid": "value.id"},
            },
        )

        result = execute_plan(client, plan)

        assert result["success"] is True
        assert result["variables"]["eid"] == 20


# ===================================================================
# Failure tests (15–22)
# ===================================================================


class TestFailures:
    def test_first_step_fails(self):
        """15. First step fails with 422."""
        client = _mock_client(post=_fail(status_code=422, error="email required"))
        plan = _plan(
            {"method": "POST", "endpoint": "/employee", "body": {"firstName": "Ola"}},
            {"method": "GET", "endpoint": "/employee"},
        )

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert result["failed_step"] == 0
        assert result["completed_steps"] == []
        assert len(result["remaining_steps"]) == 2
        assert result["error"] == "email required"

    def test_second_step_fails(self):
        """16. Second step fails, first completed."""
        client = _mock_client(
            post=_ok({"value": {"id": 1}}),
            put=_fail(status_code=404, error="Not found"),
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/employee",
                "body": {"firstName": "Ola"},
                "capture": {"eid": "value.id"},
            },
            {"method": "PUT", "endpoint": "/employee/{eid}", "body": {"email": "x"}},
        )

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert result["completed_steps"] == [0]
        assert result["failed_step"] == 1
        assert len(result["remaining_steps"]) == 1

    def test_missing_variable_in_body(self):
        """17. Missing variable in placeholder — failure before API call."""
        client = _mock_client()
        plan = _plan({
            "method": "POST",
            "endpoint": "/order",
            "body": {"customer": {"id": "{cust_id}"}},
        })

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert result["failed_step"] == 0
        assert result["results"][0]["status_code"] == 0
        assert "cust_id" in result["error"]
        client.post.assert_not_called()

    def test_capture_path_not_found(self):
        """18. Capture path not found — API succeeds, capture fails."""
        client = _mock_client(post=_ok({"value": {"name": "Ola"}}))
        plan = _plan({
            "method": "POST",
            "endpoint": "/employee",
            "body": {"firstName": "Ola"},
            "capture": {"eid": "value.id"},
        })

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert result["failed_step"] == 0
        assert 0 not in result["completed_steps"]
        # Real API body should be retained
        assert result["results"][0]["body"] == {"value": {"name": "Ola"}}

    def test_capture_path_out_of_range(self):
        """19. Capture path out-of-range list index."""
        client = _mock_client(get=_ok({"values": []}))
        plan = _plan({
            "method": "GET",
            "endpoint": "/employee",
            "capture": {"eid": "values.0.id"},
        })

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert "out of range" in result["error"]

    def test_negative_list_index_in_capture(self):
        """20. Negative list index in capture path."""
        path = "values.-1.id"
        body = {"values": [{"id": 1}]}

        with pytest.raises(ValueError, match="negative index"):
            _resolve_capture_path(body, path)

    def test_malformed_client_response(self):
        """21. Malformed client response — missing 'success' key."""
        client = _mock_client(post={"status_code": 200, "body": {}})  # missing 'success'
        plan = _plan({"method": "POST", "endpoint": "/employee", "body": {"name": "Ola"}})

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert "missing keys" in result["error"]
        assert result["results"][0]["status_code"] == 0

    def test_missing_variable_in_endpoint(self):
        """22. Missing variable specifically in endpoint."""
        client = _mock_client()
        plan = _plan({"method": "GET", "endpoint": "/employee/{eid}"})

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert result["failed_step"] == 0
        assert result["results"][0]["status_code"] == 0
        assert "eid" in result["error"]
        client.get.assert_not_called()


# ===================================================================
# Contract tests (23–32)
# ===================================================================


class TestContract:
    def test_success_result_keys(self):
        """23. Success result has all required keys."""
        client = _mock_client(get=_ok({"values": []}))
        plan = _plan({"method": "GET", "endpoint": "/employee"})

        result = execute_plan(client, plan)

        assert RESULT_KEYS_SUCCESS <= set(result.keys())
        assert "failed_step" not in result

    def test_failure_result_keys(self):
        """24. Failure result has all required keys."""
        client = _mock_client(post=_fail())
        plan = _plan({"method": "POST", "endpoint": "/employee", "body": {"name": "Ola"}})

        result = execute_plan(client, plan)

        assert RESULT_KEYS_FAILURE <= set(result.keys())

    def test_normalized_result_shape(self):
        """25. Every item in results has all required fields."""
        client = _mock_client(
            post=_ok({"value": {"id": 1}}),
            get=_ok({"values": []}),
        )
        plan = _plan(
            {"method": "POST", "endpoint": "/employee", "body": {"name": "Ola"}},
            {"method": "GET", "endpoint": "/employee"},
        )

        result = execute_plan(client, plan)

        for entry in result["results"]:
            assert NORMALIZED_RESULT_KEYS == set(entry.keys()), f"Entry keys: {entry.keys()}"

    def test_results_length_matches_attempted(self):
        """26. Results list length equals number of attempted steps."""
        client = _mock_client(
            post=_ok({"value": {"id": 1}}),
            get=_fail(),
        )
        plan = _plan(
            {"method": "POST", "endpoint": "/employee", "body": {"name": "Ola"}},
            {"method": "GET", "endpoint": "/employee"},
            {"method": "GET", "endpoint": "/customer"},
        )

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert len(result["results"]) == 2  # attempted 2, 3rd never executed

    def test_variables_accumulate(self):
        """27. Variables accumulate across steps."""
        client = _mock_client(
            post=[
                _ok({"value": {"id": 10}}),
                _ok({"value": {"id": 20}}),
            ]
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/customer",
                "body": {"name": "A"},
                "capture": {"cust_id": "value.id"},
            },
            {
                "method": "POST",
                "endpoint": "/product",
                "body": {"name": "P"},
                "capture": {"prod_id": "value.id"},
            },
        )

        result = execute_plan(client, plan)

        assert result["success"] is True
        assert result["variables"] == {"cust_id": 10, "prod_id": 20}

    def test_input_plan_not_mutated(self):
        """28. Input plan is not mutated by execution."""
        client = _mock_client(
            post=_ok({"value": {"id": 42}}),
            put=_ok({"value": {}}),
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/customer",
                "body": {"name": "Acme"},
                "capture": {"cid": "value.id"},
            },
            {
                "method": "PUT",
                "endpoint": "/order/{cid}",
                "body": {"customer": {"id": "{cid}"}},
            },
        )
        plan_copy = copy.deepcopy(plan)

        execute_plan(client, plan)

        assert plan == plan_copy

    def test_remaining_steps_are_raw(self):
        """29. remaining_steps contain raw original steps with unexpanded placeholders."""
        client = _mock_client(
            post=_ok({"value": {"id": 42}}),
            put=_fail(error="Bad request"),
        )
        plan = _plan(
            {
                "method": "POST",
                "endpoint": "/customer",
                "body": {"name": "Acme"},
                "capture": {"cid": "value.id"},
            },
            {
                "method": "PUT",
                "endpoint": "/order/{cid}",
                "body": {"customer": {"id": "{cid}"}},
            },
        )

        result = execute_plan(client, plan)

        assert result["success"] is False
        remaining = result["remaining_steps"]
        assert remaining[0]["endpoint"] == "/order/{cid}"
        assert remaining[0]["body"]["customer"]["id"] == "{cid}"

    def test_invalid_placeholder_literal(self):
        """30. Invalid placeholder-like text remains literal."""
        result = _substitute_value("{123bad}", {})
        assert result == "{123bad}"

        result2 = _substitute_value("{foo-bar}", {})
        assert result2 == "{foo-bar}"

    def test_api_failure_retains_real_body(self):
        """31. API failure retains real response body."""
        error_body = {"message": "Email required", "code": 422}
        client = _mock_client(post=_fail(body=error_body, error="Email required"))
        plan = _plan({"method": "POST", "endpoint": "/employee", "body": {"name": "Ola"}})

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert result["results"][0]["body"] == error_body

    def test_capture_failure_retains_real_body(self):
        """32. Capture failure retains real API body, not {}."""
        real_body = {"value": {"name": "Ola"}}
        client = _mock_client(post=_ok(real_body))
        plan = _plan({
            "method": "POST",
            "endpoint": "/employee",
            "body": {"firstName": "Ola"},
            "capture": {"eid": "value.nonexistent"},
        })

        result = execute_plan(client, plan)

        assert result["success"] is False
        assert result["results"][0]["body"] == real_body
        assert result["results"][0]["success"] is False  # mutated to False
