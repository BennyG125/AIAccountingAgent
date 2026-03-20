# tests/test_planner.py
"""Tests for planner.py — Claude-based parsing and pattern matching."""

import json
from unittest.mock import MagicMock, patch

# Mock the Claude client before importing planner
_mock_claude_client = MagicMock()

with patch("claude_client.get_claude_client", return_value=_mock_claude_client):
    # agent.py still imports google.genai for OCR — mock that too
    _mock_genai_client = MagicMock()
    with patch("google.genai.Client", return_value=_mock_genai_client):
        from planner import parse_prompt, is_known_pattern, PARSE_SYSTEM_PROMPT, FallbackContext
        import planner as planner_module
        import agent as _agent_module

# Ensure lazy genai client returns our mock
_agent_module._get_genai_client = lambda: _mock_genai_client


class TestParsePrompt:
    def setup_method(self):
        """Ensure planner uses our mock even if another test file imported it first."""
        self._patcher = patch.object(planner_module, "get_claude_client", return_value=_mock_claude_client)
        self._patcher.start()
        _mock_claude_client.reset_mock()

    def teardown_method(self):
        self._patcher.stop()

    def _mock_response(self, text: str) -> MagicMock:
        """Create a mock Claude response with given text content."""
        response = MagicMock()
        content_block = MagicMock()
        content_block.text = text
        response.content = [content_block]
        return response

    def test_returns_task_plan_dict(self):
        """parse_prompt returns a dict with 'actions' key."""
        plan_json = json.dumps({
            "actions": [
                {"action": "create", "entity": "department",
                 "fields": {"name": "IT", "departmentNumber": "100"},
                 "search_fields": {}, "ref": "dep1", "depends_on": {}}
            ]
        })
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        result = parse_prompt("Opprett avdeling IT", [])
        assert result is not None
        assert "actions" in result
        assert result["actions"][0]["entity"] == "department"
        assert result["actions"][0]["fields"]["name"] == "IT"

    def test_extracts_fields_and_depends_on(self):
        """Verify fields and depends_on are populated (the bug we're fixing)."""
        plan_json = json.dumps({
            "actions": [
                {"action": "create", "entity": "department",
                 "fields": {"name": "Salg", "departmentNumber": "200"},
                 "search_fields": {}, "ref": "dep1", "depends_on": {}},
                {"action": "create", "entity": "employee",
                 "fields": {"firstName": "Kari", "lastName": "Nordmann"},
                 "search_fields": {}, "ref": "emp1",
                 "depends_on": {"department": "dep1"}},
            ]
        })
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        result = parse_prompt("Opprett avdeling Salg og ansatt Kari Nordmann", [])
        assert result["actions"][0]["fields"]["name"] == "Salg"
        assert result["actions"][1]["depends_on"]["department"] == "dep1"

    def test_strips_markdown_code_fences(self):
        """Claude sometimes wraps JSON in ```json ... ``` fences."""
        plan_json = '```json\n{"actions": [{"action": "create", "entity": "department", "fields": {"name": "IT"}, "search_fields": {}, "ref": "dep1", "depends_on": {}}]}\n```'
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        result = parse_prompt("Opprett avdeling IT", [])
        assert result is not None
        assert result["actions"][0]["fields"]["name"] == "IT"

    def test_strips_code_fence_without_language(self):
        """Code fence without language tag."""
        plan_json = '```\n{"actions": [{"action": "create", "entity": "customer", "fields": {"name": "Acme"}, "search_fields": {}, "ref": "c1", "depends_on": {}}]}\n```'
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        result = parse_prompt("Opprett kunde Acme", [])
        assert result is not None
        assert result["actions"][0]["fields"]["name"] == "Acme"

    def test_returns_none_on_exception(self):
        """parse_prompt returns None if Claude call fails."""
        _mock_claude_client.messages.create.side_effect = Exception("timeout")
        result = parse_prompt("test", [])
        assert result is None
        _mock_claude_client.messages.create.side_effect = None

    def test_returns_none_on_invalid_json(self):
        """parse_prompt returns None if response is not valid JSON."""
        _mock_claude_client.messages.create.return_value = self._mock_response("not json at all")
        result = parse_prompt("test", [])
        assert result is None

    def test_returns_none_on_missing_actions(self):
        """parse_prompt returns None if JSON has no 'actions' key."""
        _mock_claude_client.messages.create.return_value = self._mock_response('{"result": "ok"}')
        result = parse_prompt("test", [])
        assert result is None

    def test_includes_file_contents_in_message(self):
        """File text is included in the user message sent to Claude."""
        plan_json = json.dumps({"actions": [{"action": "create", "entity": "department", "fields": {"name": "IT"}, "search_fields": {}, "ref": "dep1", "depends_on": {}}]})
        _mock_claude_client.messages.create.return_value = self._mock_response(plan_json)

        files = [{"filename": "data.csv", "text_content": "col1;col2\n1;2", "images": []}]
        parse_prompt("Process file", files)

        call_args = _mock_claude_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        assert "col1;col2" in user_msg
        assert "data.csv" in user_msg

    def test_parse_system_prompt_includes_field_names(self):
        assert "firstName" in PARSE_SYSTEM_PROMPT
        assert "departmentNumber" in PARSE_SYSTEM_PROMPT
        assert "priceExcludingVatCurrency" in PARSE_SYSTEM_PROMPT

    def test_parse_system_prompt_requires_json_only(self):
        assert "Output ONLY the JSON" in PARSE_SYSTEM_PROMPT


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

    def test_rejects_update_without_search_fields(self):
        plan = {"actions": [
            {"action": "update", "entity": "employee",
             "fields": {"email": "new@test.no"}, "search_fields": {},
             "ref": "emp1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_rejects_delete_without_search_fields(self):
        plan = {"actions": [
            {"action": "delete", "entity": "customer",
             "fields": {}, "search_fields": {},
             "ref": "c1", "depends_on": {}}
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

    def test_accepts_update_with_search_fields(self):
        plan = {"actions": [
            {"action": "update", "entity": "customer",
             "fields": {"email": "new@test.no"},
             "search_fields": {"name": "Acme AS"},
             "ref": "c1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_accepts_delete_with_search_fields(self):
        plan = {"actions": [
            {"action": "delete", "entity": "department",
             "fields": {}, "search_fields": {"name": "Old Dept"},
             "ref": "d1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_accepts_named_action(self):
        plan = {"actions": [
            {"action": "send_invoice", "entity": "invoice",
             "fields": {"sendType": "EMAIL"},
             "search_fields": {"customerId": "123"},
             "ref": "si1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_rejects_named_action_wrong_entity(self):
        plan = {"actions": [
            {"action": "send_invoice", "entity": "department",
             "fields": {}, "search_fields": {"name": "X"},
             "ref": "si1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is False

    def test_accepts_new_entity_types(self):
        plan = {"actions": [
            {"action": "create", "entity": "supplier",
             "fields": {"name": "Test Supplier"},
             "ref": "s1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_accepts_singleton_update_without_search_fields(self):
        plan = {"actions": [
            {"action": "update", "entity": "company",
             "fields": {"name": "New Name"},
             "search_fields": {},
             "ref": "co1", "depends_on": {}}
        ]}
        assert is_known_pattern(plan) is True

    def test_parse_system_prompt_includes_action_instructions(self):
        assert "update" in PARSE_SYSTEM_PROMPT
        assert "search_fields" in PARSE_SYSTEM_PROMPT
        assert "send_invoice" in PARSE_SYSTEM_PROMPT

    def test_parse_system_prompt_includes_examples(self):
        assert "Opprett en avdeling med navn Salg" in PARSE_SYSTEM_PROMPT
        assert "Erstellen Sie einen Mitarbeiter" in PARSE_SYSTEM_PROMPT


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
