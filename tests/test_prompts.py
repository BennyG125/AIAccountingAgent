# tests/test_prompts.py
"""Tests for system prompt construction."""
from prompts import build_system_prompt


class TestSystemPromptStructure:
    def test_contains_api_reference(self):
        """System prompt includes the full Tripletex API cheat sheet."""
        prompt = build_system_prompt()
        # Core endpoints from cheat sheet
        assert "POST /employee" in prompt
        assert "POST /customer" in prompt
        assert "POST /invoice" in prompt
        assert "POST /order" in prompt
        assert "POST /travelExpense" in prompt
        assert "POST /ledger/voucher" in prompt
        # Tier 3 endpoints from expanded cheat sheet
        assert "POST /bank/reconciliation" in prompt
        assert "POST /timesheet/entry" in prompt
        assert "POST /asset" in prompt
        assert "POST /incomingInvoice" in prompt
        assert "POST /purchaseOrder" in prompt
        assert "POST /inventory" in prompt

    def test_contains_today_date(self):
        from datetime import date
        prompt = build_system_prompt()
        assert date.today().isoformat() in prompt

    def test_contains_known_constants(self):
        prompt = build_system_prompt()
        assert "162" in prompt  # Norway country ID
        assert "NOK" in prompt

    def test_contains_scoring_rules(self):
        prompt = build_system_prompt()
        assert "4xx" in prompt or "error" in prompt.lower()
        assert "minimize" in prompt.lower() or "efficiency" in prompt.lower()

    def test_contains_payment_gotcha(self):
        """Payment registration uses QUERY PARAMS, not body."""
        prompt = build_system_prompt()
        assert "QUERY" in prompt
        assert ":payment" in prompt

    def test_contains_vattype_retry_guidance(self):
        """vatType retry pattern from executor.py is preserved."""
        prompt = build_system_prompt()
        assert "Ugyldig" in prompt or "vatType" in prompt

    def test_contains_pm_entitlements_guidance(self):
        """Project manager entitlements pattern from executor.py is preserved."""
        prompt = build_system_prompt()
        assert "grantEntitlementsByTemplate" in prompt or "entitlement" in prompt.lower()


class TestRecipeCoverage:
    """Verify recipes exist for all 12 observed competition task types."""

    def test_recipe_create_customer(self):
        assert "POST /customer" in build_system_prompt()

    def test_recipe_create_employee(self):
        prompt = build_system_prompt()
        assert "userType" in prompt
        assert "GET /department" in prompt

    def test_recipe_create_supplier(self):
        assert "POST /supplier" in build_system_prompt()

    def test_recipe_create_departments_batch(self):
        prompt = build_system_prompt()
        assert "department" in prompt.lower()

    def test_recipe_create_invoice(self):
        prompt = build_system_prompt()
        assert "orderLines" in prompt
        assert "invoiceDueDate" in prompt

    def test_recipe_create_project(self):
        prompt = build_system_prompt()
        assert "projectManager" in prompt

    def test_recipe_register_payment(self):
        prompt = build_system_prompt()
        assert "paymentTypeId" in prompt
        assert "paidAmount" in prompt

    def test_recipe_run_salary(self):
        prompt = build_system_prompt()
        assert "salary" in prompt.lower()

    def test_recipe_fixed_price_project(self):
        prompt = build_system_prompt()
        assert "isFixedPrice" in prompt or "fixedprice" in prompt

    def test_recipe_register_supplier_invoice(self):
        prompt = build_system_prompt()
        assert "supplierInvoice" in prompt or "incomingInvoice" in prompt

    def test_recipe_create_order(self):
        prompt = build_system_prompt()
        assert "POST /order" in prompt

    def test_recipe_custom_dimension(self):
        prompt = build_system_prompt()
        assert "dimension" in prompt.lower() or "salesmodule" in prompt.lower()

    def test_recipe_tier3_bank_reconciliation(self):
        prompt = build_system_prompt()
        assert "reconciliation" in prompt.lower()

    def test_recipe_tier3_guidance(self):
        prompt = build_system_prompt()
        assert "fields=*" in prompt


class TestPromptImportsCheatSheet:
    def test_cheat_sheet_is_imported_not_duplicated(self):
        """prompts.py imports from api_knowledge, not a copy."""
        import prompts
        # Verify it references the cheat sheet module
        from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET
        prompt = build_system_prompt()
        # Cheat sheet content should be in the prompt
        assert "EMPLOYEE EMPLOYMENT" in prompt  # Deep content from cheat sheet
        assert "BANK RECONCILIATION" in prompt  # Tier 3 content
