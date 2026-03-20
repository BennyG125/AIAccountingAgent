"""Tests for recovery.py — all mock Gemini and executor, no real API calls."""

import json
from datetime import date
from unittest.mock import MagicMock, patch, call

import pytest

# Patch genai client before importing recovery (which imports planner)
_mock_genai_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    from recovery import (
        build_recovery_prompt,
        recover_and_execute,
        _is_valid_failure_result,
        MAX_RECOVERY_ATTEMPTS,
    )

# Get a reference to the actual genai_client used by recovery module
import recovery as _recovery_module
_recovery_genai_client = _recovery_module.genai_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gemini_response(plan_dict: dict) -> MagicMock:
    mock = MagicMock()
    mock.text = json.dumps(plan_dict)
    return mock


def _valid_corrected_plan(**overrides) -> dict:
    plan = {
        "reasoning": "Fix the error",
        "steps": [
            {"method": "POST", "endpoint": "/employee", "body": {"firstName": "Ola"}},
        ],
    }
    plan.update(overrides)
    return plan


def _execution_failure(
    failed_step: int = 1,
    error: str = "Validation failed: email required",
    completed_steps: list | None = None,
    variables: dict | None = None,
    results: list | None = None,
    remaining_steps: list | None = None,
) -> dict:
    """Build a realistic executor failure result."""
    if completed_steps is None:
        completed_steps = [0]
    if variables is None:
        variables = {"employee_id": 42}
    if results is None:
        results = [
            {
                "step_index": 0,
                "method": "POST",
                "endpoint": "/employee",
                "success": True,
                "status_code": 201,
                "body": {"value": {"id": 42}},
                "error": None,
            },
            {
                "step_index": 1,
                "method": "PUT",
                "endpoint": "/employee/42",
                "success": False,
                "status_code": 422,
                "body": {"message": "email required"},
                "error": error,
            },
        ]
    if remaining_steps is None:
        remaining_steps = [
            {"method": "PUT", "endpoint": "/employee/{employee_id}", "body": {"email": "ola@acme.no"}},
        ]
    return {
        "success": False,
        "failed_step": failed_step,
        "error": error,
        "completed_steps": completed_steps,
        "variables": variables,
        "results": results,
        "remaining_steps": remaining_steps,
    }


def _executor_success() -> dict:
    return {
        "success": True,
        "variables": {"employee_id": 42},
        "completed_steps": [0],
        "results": [
            {
                "step_index": 0,
                "method": "POST",
                "endpoint": "/employee",
                "success": True,
                "status_code": 201,
                "body": {"value": {"id": 42}},
                "error": None,
            },
        ],
    }


def _executor_failure_2() -> dict:
    """A second distinct failure for multi-attempt tests."""
    return {
        "success": False,
        "failed_step": 0,
        "error": "Different error",
        "completed_steps": [],
        "variables": {"employee_id": 42},
        "results": [
            {
                "step_index": 0,
                "method": "POST",
                "endpoint": "/employee",
                "success": False,
                "status_code": 400,
                "body": {"message": "bad request"},
                "error": "Different error",
            },
        ],
        "remaining_steps": [
            {"method": "POST", "endpoint": "/employee", "body": {"email": "ola@acme.no"}},
        ],
    }


WRAPPED_KEYS = {"success", "recovery_attempts_used", "recovery_succeeded", "last_corrected_plan", "final_result"}


# ===================================================================
# Prompt-building tests (1–12)
# ===================================================================


class TestBuildRecoveryPrompt:
    def setup_method(self):
        self.exec_result = _execution_failure()
        self.plan = {"steps": [
            {"method": "POST", "endpoint": "/employee", "body": {"firstName": "Ola"}},
            {"method": "PUT", "endpoint": "/employee/{employee_id}", "body": {"email": "ola@acme.no"}},
        ]}

    def test_includes_error_message(self):
        """1. Includes error message."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "email required" in prompt

    def test_includes_original_task(self):
        """2. Includes original task."""
        prompt = build_recovery_prompt("Opprett ansatt Ola", [], self.plan, self.exec_result)
        assert "Opprett ansatt Ola" in prompt

    def test_includes_completed_steps_summary(self):
        """3. Includes completed steps summary."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "Step 0" in prompt
        assert "POST" in prompt
        assert "/employee" in prompt
        assert "201" in prompt

    def test_includes_captured_variables(self):
        """4. Includes captured variables."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "employee_id" in prompt
        assert "42" in prompt

    def test_includes_failed_step_details(self):
        """5. Includes failed step dict."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "PUT" in prompt
        assert "/employee/{employee_id}" in prompt

    def test_includes_error_response_body(self):
        """6. Includes error response body from failed result entry."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "email required" in prompt

    def test_includes_cheat_sheet(self):
        """7. Includes cheat sheet."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "Tripletex v2 API" in prompt

    def test_includes_todays_date(self):
        """8. Includes today's date."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert date.today().isoformat() in prompt

    def test_includes_file_text(self):
        """9. Includes file text."""
        files = [{"filename": "doc.pdf", "mime_type": "application/pdf",
                  "raw_bytes": b"x", "text_content": "Invoice #999"}]
        prompt = build_recovery_prompt("Process", files, self.plan, self.exec_result)
        assert "Invoice #999" in prompt

    def test_contains_do_not_repeat(self):
        """10. Contains 'DO NOT repeat' instruction."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "DO NOT repeat" in prompt

    def test_contains_remote_state_instruction(self):
        """11. Contains 'already changed remote state' instruction."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "remote state" in prompt.lower()

    def test_contains_use_captured_ids(self):
        """12. Contains 'use captured IDs' instruction."""
        prompt = build_recovery_prompt("Create employee", [], self.plan, self.exec_result)
        assert "captured" in prompt.lower()
        assert "instead of searching" in prompt.lower()


# ===================================================================
# Recovery success tests (13–15)
# ===================================================================


class TestRecoverySuccess:
    def setup_method(self):
        _recovery_genai_client.models.generate_content.reset_mock()
        _recovery_genai_client.models.generate_content.side_effect = None

    def test_succeeds_on_first_attempt(self):
        """13. Recovery succeeds on first attempt."""
        corrected = _valid_corrected_plan()
        _recovery_genai_client.models.generate_content.return_value = _make_gemini_response(corrected)

        with patch("recovery.execute_plan", return_value=_executor_success()) as mock_exec:
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert result["success"] is True
        assert result["recovery_succeeded"] is True
        assert result["recovery_attempts_used"] == 1
        assert result["last_corrected_plan"] == corrected

    def test_succeeds_on_second_attempt(self):
        """14. Recovery succeeds on second attempt."""
        corrected = _valid_corrected_plan()
        _recovery_genai_client.models.generate_content.return_value = _make_gemini_response(corrected)

        with patch("recovery.execute_plan", side_effect=[
            _executor_failure_2(),
            _executor_success(),
        ]):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert result["success"] is True
        assert result["recovery_succeeded"] is True
        assert result["recovery_attempts_used"] == 2

    def test_context_updates_between_attempts(self):
        """15. Second attempt receives first recovery's failure, not original."""
        corrected = _valid_corrected_plan()
        _recovery_genai_client.models.generate_content.return_value = _make_gemini_response(corrected)

        second_failure = _executor_failure_2()

        with patch("recovery.execute_plan", side_effect=[
            second_failure,
            _executor_success(),
        ]):
            with patch("recovery.build_recovery_prompt", wraps=build_recovery_prompt) as mock_prompt:
                result = recover_and_execute(
                    MagicMock(), "task", [], {"steps": []}, _execution_failure()
                )

        # Second call should receive the second_failure, not the original
        second_call_args = mock_prompt.call_args_list[1]
        passed_result = second_call_args[0][3]  # 4th positional arg = execution_result
        assert passed_result["error"] == "Different error"


# ===================================================================
# Recovery failure tests (16–19)
# ===================================================================


class TestRecoveryFailure:
    def setup_method(self):
        _recovery_genai_client.models.generate_content.reset_mock()
        _recovery_genai_client.models.generate_content.side_effect = None

    def test_all_attempts_exhausted(self):
        """16. Both corrections fail execution."""
        corrected = _valid_corrected_plan()
        _recovery_genai_client.models.generate_content.return_value = _make_gemini_response(corrected)

        with patch("recovery.execute_plan", return_value=_executor_failure_2()):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert result["success"] is False
        assert result["recovery_succeeded"] is False
        assert result["recovery_attempts_used"] == MAX_RECOVERY_ATTEMPTS

    def test_gemini_invalid_json(self):
        """17. Gemini returns invalid JSON — attempt consumed, continues."""
        bad_resp = MagicMock()
        bad_resp.text = "not json at all"
        good_resp = _make_gemini_response(_valid_corrected_plan())
        _recovery_genai_client.models.generate_content.side_effect = [bad_resp, good_resp]

        with patch("recovery.execute_plan", return_value=_executor_success()):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert result["success"] is True
        assert result["recovery_attempts_used"] == 2

    def test_gemini_invalid_plan(self):
        """18. Gemini returns invalid plan — attempt consumed, continues."""
        bad_plan = {"steps": []}  # empty steps = invalid
        good_plan = _valid_corrected_plan()
        _recovery_genai_client.models.generate_content.side_effect = [
            _make_gemini_response(bad_plan),
            _make_gemini_response(good_plan),
        ]

        with patch("recovery.execute_plan", return_value=_executor_success()):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert result["success"] is True
        assert result["recovery_attempts_used"] == 2

    def test_gemini_api_error(self):
        """19. Gemini API error — attempt consumed, continues."""
        _recovery_genai_client.models.generate_content.side_effect = [
            RuntimeError("Network error"),
            _make_gemini_response(_valid_corrected_plan()),
        ]

        with patch("recovery.execute_plan", return_value=_executor_success()):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert result["success"] is True
        assert result["recovery_attempts_used"] == 2


# ===================================================================
# Context preservation tests (20–23)
# ===================================================================


class TestContextPreservation:
    def setup_method(self):
        _recovery_genai_client.models.generate_content.reset_mock()
        _recovery_genai_client.models.generate_content.side_effect = None

    def test_parse_failure_preserves_context(self):
        """20. Parse failure does not overwrite context."""
        bad_resp = MagicMock()
        bad_resp.text = "garbage"
        good_resp = _make_gemini_response(_valid_corrected_plan())
        _recovery_genai_client.models.generate_content.side_effect = [bad_resp, good_resp]

        original_failure = _execution_failure()

        with patch("recovery.execute_plan", return_value=_executor_success()):
            with patch("recovery.build_recovery_prompt", wraps=build_recovery_prompt) as mock_prompt:
                recover_and_execute(
                    MagicMock(), "task", [], {"steps": []}, original_failure
                )

        # Second attempt should still use the original failure
        second_call_result = mock_prompt.call_args_list[1][0][3]
        assert second_call_result["error"] == original_failure["error"]

    def test_validation_failure_preserves_context(self):
        """21. Validation failure does not overwrite context."""
        bad_plan = {"steps": []}  # invalid: empty
        good_plan = _valid_corrected_plan()
        _recovery_genai_client.models.generate_content.side_effect = [
            _make_gemini_response(bad_plan),
            _make_gemini_response(good_plan),
        ]

        original_failure = _execution_failure()

        with patch("recovery.execute_plan", return_value=_executor_success()):
            with patch("recovery.build_recovery_prompt", wraps=build_recovery_prompt) as mock_prompt:
                recover_and_execute(
                    MagicMock(), "task", [], {"steps": []}, original_failure
                )

        second_call_result = mock_prompt.call_args_list[1][0][3]
        assert second_call_result["error"] == original_failure["error"]

    def test_malformed_execution_result(self):
        """22. Malformed execution_result returns immediately with 0 attempts."""
        result = recover_and_execute(
            MagicMock(), "task", [], {"steps": []}, {"garbage": True}
        )

        assert result["success"] is False
        assert result["recovery_attempts_used"] == 0
        assert result["recovery_succeeded"] is False

    def test_missing_failed_result_entry(self):
        """23. Results has no entry matching failed_step — treated as malformed."""
        bad_result = _execution_failure()
        # Remove the failed result entry
        bad_result["results"] = [r for r in bad_result["results"] if r["step_index"] != 1]

        result = recover_and_execute(
            MagicMock(), "task", [], {"steps": []}, bad_result
        )

        assert result["success"] is False
        assert result["recovery_attempts_used"] == 0


# ===================================================================
# Contract tests (24–30)
# ===================================================================


class TestContract:
    def setup_method(self):
        """Reset mock state between tests."""
        _recovery_genai_client.models.generate_content.reset_mock()
        _recovery_genai_client.models.generate_content.side_effect = None

    def test_wrapped_return_on_success(self):
        """24. Wrapped return on success has all required keys."""
        _recovery_genai_client.models.generate_content.return_value = _make_gemini_response(
            _valid_corrected_plan()
        )

        with patch("recovery.execute_plan", return_value=_executor_success()):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert WRAPPED_KEYS == set(result.keys())
        assert result["recovery_succeeded"] is True

    def test_wrapped_return_on_exhaustion(self):
        """25. Wrapped return on exhaustion has all required keys."""
        _recovery_genai_client.models.generate_content.return_value = _make_gemini_response(
            _valid_corrected_plan()
        )

        with patch("recovery.execute_plan", return_value=_executor_failure_2()):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert WRAPPED_KEYS == set(result.keys())
        assert result["recovery_succeeded"] is False

    def test_never_raises(self):
        """26. Never raises — even with Gemini errors, returns a dict."""
        _recovery_genai_client.models.generate_content.side_effect = RuntimeError("boom")

        result = recover_and_execute(
            MagicMock(), "task", [], {"steps": []}, _execution_failure()
        )

        assert isinstance(result, dict)
        assert result["success"] is False

    def test_images_sent_as_multimodal(self):
        """27. Images sent as multimodal parts."""
        _recovery_genai_client.models.generate_content.return_value = _make_gemini_response(
            _valid_corrected_plan()
        )
        files = [{"filename": "r.png", "mime_type": "image/png", "raw_bytes": b"IMG"}]

        with patch("recovery.execute_plan", return_value=_executor_success()):
            with patch("recovery.types.Part.from_bytes", return_value="img_part") as mock_fb:
                recover_and_execute(
                    MagicMock(), "task", files, {"steps": []}, _execution_failure()
                )

        mock_fb.assert_called_with(data=b"IMG", mime_type="image/png")

    def test_attempts_used_reflects_consumed(self):
        """28. recovery_attempts_used reflects actual attempts consumed."""
        # First attempt: Gemini error, second: success
        _recovery_genai_client.models.generate_content.side_effect = [
            RuntimeError("fail"),
            _make_gemini_response(_valid_corrected_plan()),
        ]

        with patch("recovery.execute_plan", return_value=_executor_success()):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert result["recovery_attempts_used"] == 2

    def test_last_corrected_plan_tracks_valid_plans(self):
        """29. last_corrected_plan is the last structurally valid plan from Gemini."""
        plan_a = _valid_corrected_plan(reasoning="Plan A")
        plan_b = _valid_corrected_plan(reasoning="Plan B")

        _recovery_genai_client.models.generate_content.side_effect = [
            _make_gemini_response(plan_a),
            _make_gemini_response(plan_b),
        ]

        with patch("recovery.execute_plan", return_value=_executor_failure_2()):
            result = recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert result["last_corrected_plan"]["reasoning"] == "Plan B"

    def test_short_circuit_on_success(self):
        """30. After first attempt succeeds, Gemini is not called again."""
        _recovery_genai_client.models.generate_content.return_value = _make_gemini_response(
            _valid_corrected_plan()
        )

        with patch("recovery.execute_plan", return_value=_executor_success()):
            recover_and_execute(
                MagicMock(), "task", [], {"steps": []}, _execution_failure()
            )

        assert _recovery_genai_client.models.generate_content.call_count == 1
