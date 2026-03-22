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

    def test_safe_post_strips_nested_vatType_from_postings(self):
        """Regression test: retry_without must strip vatType from postings[] items."""
        plan = ExecutionPlan()
        client = MagicMock()
        client.post.side_effect = [
            {"success": False, "status_code": 422, "error": "vatType invalid"},
            {"success": True, "body": {"value": {"id": 1}}},
        ]
        body = {
            "date": "2026-01-01",
            "postings": [
                {
                    "account": {"id": 10},
                    "amount": 800,
                    "amountCurrency": 800,
                    "amountGross": 1000,
                    "amountGrossCurrency": 1000,
                    "vatType": {"id": 5},
                },
                {
                    "account": {"id": 20},
                    "amount": -1000,
                    "amountCurrency": -1000,
                    "amountGross": -1000,
                    "amountGrossCurrency": -1000,
                },
            ],
        }
        result = plan._safe_post(
            client, "/ledger/voucher", body, retry_without=["vatType"]
        )
        assert result["success"]
        retry_body = client.post.call_args_list[1][1].get("body") or client.post.call_args_list[1][0][1]
        # vatType must be gone from the posting that had it
        assert "vatType" not in retry_body["postings"][0]
        # amountGross must be adjusted to equal amount (no VAT auto-calc)
        assert retry_body["postings"][0]["amountGross"] == 800
        assert retry_body["postings"][0]["amountGrossCurrency"] == 800
        # The second posting (no vatType) should be unchanged
        assert retry_body["postings"][1]["amountGross"] == -1000

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

    def test_safe_post_does_not_mutate_nested_postings(self):
        """Ensure recursive stripping does not mutate the original postings."""
        plan = ExecutionPlan()
        client = MagicMock()
        client.post.side_effect = [
            {"success": False, "status_code": 422, "error": "bad"},
            {"success": True, "body": {"value": {"id": 1}}},
        ]
        posting = {"amount": 100, "amountGross": 125, "vatType": {"id": 3}}
        original = {"postings": [posting]}
        plan._safe_post(client, "/test", original, retry_without=["vatType"])
        # Original posting must still have vatType and original amountGross
        assert "vatType" in posting
        assert posting["amountGross"] == 125

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

    def test_find_or_create_returns_none_on_failure(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.get.return_value = {"success": True, "body": {"values": []}}
        client.post.return_value = {
            "success": False, "status_code": 500, "error": "server error"
        }
        result = plan._find_or_create(
            client, "/search", {}, "/create", {"name": "x"}
        )
        assert result is None

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


from execution_plans.create_customer import CreateCustomerPlan


class TestCreateCustomerPlan:
    def test_execute_simple(self):
        plan = CreateCustomerPlan()
        client = MagicMock()
        client.post.return_value = {
            "success": True,
            "status_code": 201,
            "body": {"value": {"id": 1, "name": "Test AS"}},
        }
        result = plan.execute(
            client,
            {"name": "Test AS", "org_number": "123456789"},
            start_time=time.time(),
        )
        assert result["status"] == "completed"
        assert result["api_calls"] == 1
        assert result["api_errors"] == 0
        assert result["executor"] == "deterministic"

    def test_execute_with_address(self):
        plan = CreateCustomerPlan()
        client = MagicMock()
        client.post.return_value = {
            "success": True,
            "status_code": 201,
            "body": {"value": {"id": 1}},
        }
        result = plan.execute(
            client,
            {
                "name": "Test AS",
                "org_number": "123456789",
                "email": "test@test.no",
                "phone": "12345678",
                "address": {
                    "street": "Storgata 1",
                    "postal_code": "0001",
                    "city": "Oslo",
                },
            },
            start_time=time.time(),
        )
        assert result["status"] == "completed"
        # Verify the POST body included the address
        call_body = client.post.call_args[1].get("body") or client.post.call_args[0][1]
        assert "physicalAddress" in call_body

    def test_execute_returns_errors_on_failure(self):
        plan = CreateCustomerPlan()
        client = MagicMock()
        client.post.return_value = {
            "success": False,
            "status_code": 500,
            "error": "server error",
        }
        client.get.return_value = {
            "success": True,
            "body": {"values": []},
        }
        result = plan.execute(
            client,
            {"name": "Test AS"},
            start_time=time.time(),
        )
        assert result["status"] == "completed"
        assert result["api_errors"] >= 1
