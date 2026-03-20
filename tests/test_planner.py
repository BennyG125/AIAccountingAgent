# tests/test_planner.py
"""Tests for planner.py — structured output parsing and pattern matching."""

from unittest.mock import MagicMock, patch
from dataclasses import asdict

_mock_genai_client = MagicMock()

with patch("google.genai.Client", return_value=_mock_genai_client):
    from planner import parse_prompt, is_known_pattern, PARSE_SYSTEM_PROMPT, FallbackContext


class TestParsePrompt:
    def test_returns_task_plan_dict(self):
        """parse_prompt returns a dict with 'actions' key."""
        mock_response = MagicMock()
        mock_response.parsed = {
            "actions": [
                {"action": "create", "entity": "department",
                 "fields": {"name": "IT", "departmentNumber": "100"},
                 "ref": "dep1", "depends_on": {}}
            ]
        }
        _mock_genai_client.models.generate_content.return_value = mock_response

        result = parse_prompt("Opprett avdeling IT", [])
        assert result is not None
        assert "actions" in result
        assert result["actions"][0]["entity"] == "department"

    def test_returns_none_on_exception(self):
        """parse_prompt returns None if Gemini call fails."""
        _mock_genai_client.models.generate_content.side_effect = Exception("timeout")
        result = parse_prompt("test", [])
        assert result is None
        _mock_genai_client.models.generate_content.side_effect = None

    def test_parse_system_prompt_includes_field_names(self):
        assert "firstName" in PARSE_SYSTEM_PROMPT
        assert "departmentNumber" in PARSE_SYSTEM_PROMPT
        assert "priceExcludingVatCurrency" in PARSE_SYSTEM_PROMPT


class TestIsKnownPattern:
    def test_simple_create_department(self):
        plan = {"actions": [
            {"action": "create", "entity": "department",
             "fields": {"name": "IT", "departmentNumber": "100"},
             "ref": "dep1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_create_employee_with_department_dep(self):
        plan = {"actions": [
            {"action": "create", "entity": "department",
             "fields": {"name": "IT", "departmentNumber": "100"},
             "ref": "dep1", "depends_on": {}},
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "Kari", "lastName": "Nordmann"},
             "ref": "emp1", "depends_on": {"department": "dep1"}},
        ]}
        assert is_known_pattern(plan) is True

    def test_rejects_update_action(self):
        plan = {"actions": [
            {"action": "update", "entity": "employee",
             "fields": {"email": "new@test.no"},
             "ref": "emp1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_rejects_delete_action(self):
        plan = {"actions": [
            {"action": "delete", "entity": "customer",
             "fields": {}, "ref": "c1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_rejects_unknown_entity(self):
        plan = {"actions": [
            {"action": "create", "entity": "spaceship",
             "fields": {"name": "X"}, "ref": "s1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_rejects_unresolved_ref(self):
        plan = {"actions": [
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "Kari", "lastName": "N"},
             "ref": "emp1", "depends_on": {"department": "nonexistent_ref"}},
        ]}
        assert is_known_pattern(plan) is False

    def test_accepts_employee_without_department_action(self):
        """Employee without dept action in plan — uses lookup_defaults."""
        plan = {"actions": [
            {"action": "create", "entity": "employee",
             "fields": {"firstName": "Kari", "lastName": "N"},
             "ref": "emp1", "depends_on": {}},
        ]}
        assert is_known_pattern(plan) is True

    def test_accepts_invoice_with_array_dep(self):
        plan = {"actions": [
            {"action": "create", "entity": "customer",
             "fields": {"name": "Acme"}, "ref": "c1", "depends_on": {}},
            {"action": "create", "entity": "product",
             "fields": {"name": "Thing"}, "ref": "p1", "depends_on": {}},
            {"action": "create", "entity": "order",
             "fields": {}, "ref": "o1",
             "depends_on": {"customer": "c1", "product": "p1"}},
            {"action": "create", "entity": "invoice",
             "fields": {}, "ref": "inv1",
             "depends_on": {"orders": ["o1"]}},
        ]}
        assert is_known_pattern(plan) is True

    def test_rejects_none_plan(self):
        assert is_known_pattern(None) is False

    def test_rejects_empty_actions(self):
        assert is_known_pattern({"actions": []}) is False


class TestFallbackContext:
    def test_default_values(self):
        ctx = FallbackContext()
        assert ctx.task_plan is None
        assert ctx.completed_refs == {}
        assert ctx.failed_action is None
        assert ctx.error is None

    def test_with_values(self):
        ctx = FallbackContext(
            task_plan={"actions": []},
            completed_refs={"dep1": 123},
            failed_action={"entity": "employee"},
            error="422 Validation failed",
        )
        assert ctx.completed_refs["dep1"] == 123
