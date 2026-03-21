"""Tests for execution plan base class and registry."""
import time
import pytest
from unittest.mock import MagicMock

from execution_plans._base import ExecutionPlan, EXECUTOR_TIMEOUT
from execution_plans._registry import PLANS, register


class TestExecutionPlanBase:
    def test_check_timeout_within_limit(self):
        plan = ExecutionPlan()
        # Should not raise
        plan._check_timeout(time.time())

    def test_check_timeout_exceeded(self):
        plan = ExecutionPlan()
        # start_time far in the past
        with pytest.raises(TimeoutError):
            plan._check_timeout(time.time() - EXECUTOR_TIMEOUT - 1)

    def test_safe_post_success(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.post.return_value = {"success": True, "body": {"value": {"id": 1}}}
        result = plan._safe_post(client, "/test", {"name": "x"})
        assert result["success"]
        client.post.assert_called_once_with("/test", body={"name": "x"})

    def test_safe_post_retries_without_fields_on_422(self):
        plan = ExecutionPlan()
        client = MagicMock()
        # First call fails with 422, second succeeds
        client.post.side_effect = [
            {"success": False, "status_code": 422, "error": "bad field"},
            {"success": True, "body": {"value": {"id": 1}}},
        ]
        result = plan._safe_post(
            client, "/test", {"name": "x", "vatType": "bad"}, retry_without=["vatType"]
        )
        assert result["success"]
        assert client.post.call_count == 2
        # Second call should not have vatType
        second_call_body = client.post.call_args_list[1][1].get("body") or client.post.call_args_list[1][0][1]
        assert "vatType" not in second_call_body

    def test_safe_post_does_not_mutate_original_body(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.post.side_effect = [
            {"success": False, "status_code": 422, "error": "bad"},
            {"success": True, "body": {"value": {"id": 1}}},
        ]
        original = {"name": "x", "vatType": "bad"}
        plan._safe_post(client, "/test", original, retry_without=["vatType"])
        assert "vatType" in original  # original unchanged

    def test_find_or_create_finds_existing(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.get.return_value = {
            "success": True,
            "body": {"values": [{"id": 42, "name": "existing"}]},
        }
        result = plan._find_or_create(
            client, "/search", {"name": "x"}, "/create", {"name": "x"}
        )
        assert result == 42
        client.post.assert_not_called()

    def test_find_or_create_creates_when_not_found(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.get.return_value = {"success": True, "body": {"values": []}}
        client.post.return_value = {"success": True, "body": {"value": {"id": 99}}}
        result = plan._find_or_create(
            client, "/search", {"name": "x"}, "/create", {"name": "x"}
        )
        assert result == 99

    def test_find_or_create_raises_on_failure(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.get.return_value = {"success": True, "body": {"values": []}}
        client.post.return_value = {
            "success": False, "status_code": 500, "error": "server error"
        }
        with pytest.raises(RuntimeError, match="Failed to find or create"):
            plan._find_or_create(
                client, "/search", {}, "/create", {"name": "x"}
            )

    def test_make_result_shape(self):
        plan = ExecutionPlan()
        result = plan._make_result(api_calls=3, api_errors=1, time_ms=500)
        assert result == {
            "status": "completed",
            "iterations": 1,
            "time_ms": 500,
            "api_calls": 3,
            "api_errors": 1,
            "error_details": None,
            "executor": "deterministic",
        }


class TestRegistry:
    def test_register_decorator(self):
        @register
        class TestPlan(ExecutionPlan):
            task_type = "test_task_for_registry"

        assert "test_task_for_registry" in PLANS
        assert isinstance(PLANS["test_task_for_registry"], TestPlan)
        # Cleanup
        del PLANS["test_task_for_registry"]
