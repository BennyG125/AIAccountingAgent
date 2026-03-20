"""Tests for planner.py — all mock Gemini, no real API calls."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# We patch the genai client at module level to avoid needing real GCP creds at import.
# The planner imports google.genai at module level and creates a client immediately,
# so we must patch before importing planner.
_mock_genai_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    from planner import (
        build_planning_prompt,
        plan_task,
        _validate_plan,
        _parse_json,
        PLAN_JSON_SCHEMA,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gemini_response(plan_dict: dict) -> MagicMock:
    """Create a mock Gemini response returning the given plan as JSON text."""
    mock = MagicMock()
    mock.text = json.dumps(plan_dict)
    return mock


def _valid_plan(**overrides) -> dict:
    """Return a minimal valid plan dict, with optional overrides."""
    plan = {
        "reasoning": "Test plan",
        "steps": [
            {
                "method": "POST",
                "endpoint": "/employee",
                "body": {"firstName": "Ola", "lastName": "Nordmann"},
                "capture": {"employee_id": "value.id"},
            }
        ],
    }
    plan.update(overrides)
    return plan


def _valid_step(**overrides) -> dict:
    """Return a minimal valid step dict, with optional overrides."""
    step = {"method": "POST", "endpoint": "/employee", "body": {"firstName": "Ola"}}
    step.update(overrides)
    return step


# ===================================================================
# Prompt-building tests (1–6)
# ===================================================================


class TestBuildPlanningPrompt:
    def test_includes_cheat_sheet(self):
        """1. Includes cheat sheet content."""
        prompt = build_planning_prompt("Create employee", [])
        assert "Tripletex v2 API" in prompt
        assert "POST /employee" in prompt

    def test_includes_task_prompt(self):
        """2. Includes task prompt text."""
        prompt = build_planning_prompt("Opprett en ansatt med navn Ola", [])
        assert "Opprett en ansatt med navn Ola" in prompt

    def test_includes_file_text(self):
        """3. Includes extracted file text from PDF/text attachments."""
        files = [
            {
                "filename": "invoice.pdf",
                "mime_type": "application/pdf",
                "raw_bytes": b"pdf-data",
                "text_content": "Invoice #123 for Acme AS",
            }
        ]
        prompt = build_planning_prompt("Process invoice", files)
        assert "Invoice #123 for Acme AS" in prompt
        assert "invoice.pdf" in prompt

    def test_includes_todays_date(self):
        """4. Includes today's date in ISO format."""
        prompt = build_planning_prompt("Create employee", [])
        assert date.today().isoformat() in prompt

    def test_excludes_image_bytes(self):
        """5. Excludes image bytes from prompt text."""
        files = [
            {
                "filename": "receipt.png",
                "mime_type": "image/png",
                "raw_bytes": b"PNG_IMAGE_DATA_HERE",
            }
        ]
        prompt = build_planning_prompt("Process receipt", files)
        assert b"PNG_IMAGE_DATA_HERE".decode("ascii", errors="ignore") not in prompt
        # Image filename should NOT appear as a text section
        assert "### Attached file: receipt.png" not in prompt

    def test_ignores_binary_non_image_no_text(self):
        """6. Ignores binary non-image files with no text_content."""
        files = [
            {
                "filename": "data.bin",
                "mime_type": "application/octet-stream",
                "raw_bytes": b"\x00\x01\x02SECRETBINARY",
            }
        ]
        prompt = build_planning_prompt("Process data", files)
        assert "data.bin" not in prompt
        assert "SECRETBINARY" not in prompt


# ===================================================================
# Planning success tests (7–10)
# ===================================================================


class TestPlanTaskSuccess:
    def test_returns_valid_plan(self):
        """7. Returns parsed dict with 'steps' from valid Gemini JSON."""
        plan_dict = _valid_plan()
        _mock_genai_client.models.generate_content.return_value = _make_gemini_response(
            plan_dict
        )

        result = plan_task("Create employee Ola Nordmann", [])

        assert result["steps"] == plan_dict["steps"]
        assert result["reasoning"] == "Test plan"

    def test_strips_markdown_fences(self):
        """8. Strips markdown fences and parses successfully."""
        plan_dict = _valid_plan()
        fenced = f"```json\n{json.dumps(plan_dict)}\n```"
        mock_resp = MagicMock()
        mock_resp.text = fenced
        _mock_genai_client.models.generate_content.return_value = mock_resp

        result = plan_task("Create employee", [])
        assert "steps" in result
        assert len(result["steps"]) == 1

    def test_sends_images_as_multimodal(self):
        """9. Sends image attachments via multimodal Part.from_bytes."""
        plan_dict = _valid_plan()
        _mock_genai_client.models.generate_content.return_value = _make_gemini_response(
            plan_dict
        )
        files = [
            {
                "filename": "receipt.png",
                "mime_type": "image/png",
                "raw_bytes": b"PNG_DATA",
            }
        ]

        with patch("planner.types.Part.from_bytes", return_value="fake_image_part") as mock_fb:
            plan_task("Process receipt", files)

        mock_fb.assert_called_once_with(data=b"PNG_DATA", mime_type="image/png")

        # Verify the image part was included in the contents
        call_kwargs = _mock_genai_client.models.generate_content.call_args
        contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents")
        assert "fake_image_part" in contents

    def test_passes_structured_output_config(self):
        """10. Passes structured-output config including JSON MIME type and schema."""
        plan_dict = _valid_plan()
        _mock_genai_client.models.generate_content.return_value = _make_gemini_response(
            plan_dict
        )

        plan_task("Create employee", [])

        call_kwargs = _mock_genai_client.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.response_mime_type == "application/json"


# ===================================================================
# Validation failure tests (11–26)
# ===================================================================


class TestValidationFailures:
    def _plan_task_with_response(self, raw_text: str):
        """Helper: run plan_task with a mock Gemini response returning raw_text."""
        mock_resp = MagicMock()
        mock_resp.text = raw_text
        _mock_genai_client.models.generate_content.return_value = mock_resp
        return plan_task("test", [])

    def test_invalid_json(self):
        """11. Raises ValueError on invalid JSON (garbage text)."""
        with pytest.raises(ValueError, match="Failed to parse"):
            self._plan_task_with_response("This is not JSON at all")

    def test_steps_missing(self):
        """12. Raises ValueError when 'steps' missing."""
        with pytest.raises(ValueError, match="steps"):
            self._plan_task_with_response('{"reasoning": "oops"}')

    def test_steps_empty(self):
        """13. Raises ValueError when 'steps' is empty list."""
        with pytest.raises(ValueError, match="non-empty"):
            self._plan_task_with_response('{"steps": []}')

    def test_steps_not_list(self):
        """14. Raises ValueError when 'steps' is not a list."""
        with pytest.raises(ValueError, match="list"):
            self._plan_task_with_response('{"steps": "not a list"}')

    def test_invalid_method(self):
        """15. Raises ValueError on invalid method."""
        plan = _valid_plan(steps=[_valid_step(method="PATCH")])
        with pytest.raises(ValueError, match="method"):
            _validate_plan(plan)

    def test_endpoint_no_slash(self):
        """16. Raises ValueError on endpoint not starting with '/'."""
        plan = _valid_plan(steps=[_valid_step(endpoint="employee")])
        with pytest.raises(ValueError, match="start with '/'"):
            _validate_plan(plan)

    def test_endpoint_query_string(self):
        """17. Raises ValueError on endpoint containing '?'."""
        plan = _valid_plan(steps=[_valid_step(endpoint="/employee?id=42")])
        with pytest.raises(ValueError, match="\\?"):
            _validate_plan(plan)

    def test_body_on_get(self):
        """18. Raises ValueError when body appears on GET."""
        step = {"method": "GET", "endpoint": "/employee", "body": {"x": 1}}
        plan = _valid_plan(steps=[step])
        with pytest.raises(ValueError, match="body not allowed for GET"):
            _validate_plan(plan)

    def test_body_on_delete(self):
        """19. Raises ValueError when body appears on DELETE."""
        step = {"method": "DELETE", "endpoint": "/employee/1", "body": {"x": 1}}
        plan = _valid_plan(steps=[step])
        with pytest.raises(ValueError, match="body not allowed for DELETE"):
            _validate_plan(plan)

    def test_params_on_post(self):
        """20. Raises ValueError when params appears on POST."""
        step = {
            "method": "POST",
            "endpoint": "/employee",
            "body": {"firstName": "Ola"},
            "params": {"fields": "id"},
        }
        plan = _valid_plan(steps=[step])
        with pytest.raises(ValueError, match="params not allowed for POST"):
            _validate_plan(plan)

    def test_params_on_put(self):
        """21. Raises ValueError when params appears on PUT."""
        step = {
            "method": "PUT",
            "endpoint": "/employee/1",
            "body": {"firstName": "Ola"},
            "params": {"fields": "id"},
        }
        plan = _valid_plan(steps=[step])
        with pytest.raises(ValueError, match="params not allowed for PUT"):
            _validate_plan(plan)

    def test_invalid_capture_key(self):
        """22. Raises ValueError on invalid capture variable name."""
        step = _valid_step(capture={"123bad": "value.id"})
        plan = _valid_plan(steps=[step])
        with pytest.raises(ValueError, match="not a valid identifier"):
            _validate_plan(plan)

    def test_unknown_top_level_key(self):
        """23. Raises ValueError on unknown top-level key."""
        plan = _valid_plan()
        plan["notes"] = "extra field"
        with pytest.raises(ValueError, match="Unknown top-level"):
            _validate_plan(plan)

    def test_unknown_step_key(self):
        """24. Raises ValueError on unknown step key."""
        step = _valid_step()
        step["description"] = "some note"
        plan = _valid_plan(steps=[step])
        with pytest.raises(ValueError, match="unknown keys"):
            _validate_plan(plan)

    def test_endpoint_double_slash(self):
        """25. Raises ValueError on endpoint containing '//'."""
        plan = _valid_plan(steps=[_valid_step(endpoint="/employee//1")])
        with pytest.raises(ValueError, match="//"):
            _validate_plan(plan)

    def test_endpoint_trailing_whitespace(self):
        """26. Raises ValueError on endpoint with trailing whitespace."""
        plan = _valid_plan(steps=[_valid_step(endpoint="/employee ")])
        with pytest.raises(ValueError, match="whitespace"):
            _validate_plan(plan)


# ===================================================================
# Regression / integration-like tests (27–29)
# ===================================================================


class TestRegression:
    def test_multilingual_prompt_with_pdf(self):
        """27. Norwegian prompt + PDF text snippet both appear in prompt."""
        files = [
            {
                "filename": "faktura.pdf",
                "mime_type": "application/pdf",
                "raw_bytes": b"pdf-bytes",
                "text_content": "Fakturanummer: 2026-001\nBeløp: 15 000 NOK",
            }
        ]
        prompt = build_planning_prompt(
            "Opprett en faktura for kunden Nordmann AS med beløp 15 000 NOK", files
        )
        assert "Opprett en faktura for kunden Nordmann AS" in prompt
        assert "Fakturanummer: 2026-001" in prompt
        assert "15 000 NOK" in prompt

    def test_binary_non_image_no_leak_in_plan_task(self):
        """28. Binary non-image attachment does not leak bytes into prompt."""
        plan_dict = _valid_plan()
        _mock_genai_client.models.generate_content.return_value = _make_gemini_response(
            plan_dict
        )
        files = [
            {
                "filename": "data.bin",
                "mime_type": "application/octet-stream",
                "raw_bytes": b"\x00\x01SECRET_BINARY_DATA",
            }
        ]

        with patch("planner.types.Part.from_bytes") as mock_fb:
            plan_task("Process data", files)
            # Should NOT have been sent as an image part
            mock_fb.assert_not_called()

        # Verify the binary content was not in the text prompt
        call_kwargs = _mock_genai_client.models.generate_content.call_args
        contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents")
        text_part = contents[0]  # First part is always the text prompt
        assert "SECRET_BINARY_DATA" not in text_part

    def test_fenced_json_with_surrounding_prose_fails(self):
        """29. Fenced JSON with surrounding prose should fail (not unwrapped)."""
        plan_dict = _valid_plan()
        prose_wrapped = f"Here is the plan:\n```json\n{json.dumps(plan_dict)}\n```\nHope this helps!"

        with pytest.raises(ValueError, match="Failed to parse"):
            _parse_json(prose_wrapped)
