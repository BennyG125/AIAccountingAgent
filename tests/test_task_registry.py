# tests/test_task_registry.py
"""Tests for task_registry.py — expanded registry with 27 entities + actions."""

from task_registry import (
    ENTITY_SCHEMAS, KNOWN_CONSTANTS, DEPENDENCIES,
    ACTION_SCHEMAS, BULK_ENDPOINTS, SEARCH_PARAMS,
    generate_auto_value,
)


class TestEntitySchemas:
    def test_all_27_entities_covered(self):
        expected = {
            "department", "employee", "customer", "product",
            "order", "invoice", "register_payment",
            "travel_expense", "travel_expense_cost",
            "project", "contact", "voucher",
            # new
            "employee_employment", "employee_employment_details",
            "supplier", "supplier_invoice", "customer_category",
            "product_unit", "order_line", "project_participant",
            "travel_expense_per_diem", "travel_expense_mileage",
            "travel_expense_accommodation",
            "ledger_account", "salary_transaction",
            "delivery_address", "company",
        }
        assert expected == set(ENTITY_SCHEMAS.keys())

    def test_each_schema_has_required_keys(self):
        for name, schema in ENTITY_SCHEMAS.items():
            assert "endpoint" in schema, f"{name} missing endpoint"
            assert "method" in schema, f"{name} missing method"
            assert "required" in schema, f"{name} missing required"

    def test_employee_defaults(self):
        emp = ENTITY_SCHEMAS["employee"]
        assert emp["defaults"]["userType"] == "STANDARD"

    def test_order_embeds_orderlines(self):
        assert "orderLines" in ENTITY_SCHEMAS["order"].get("embed", [])

    def test_register_payment_uses_query_params(self):
        assert ENTITY_SCHEMAS["register_payment"].get("use_query_params") is True

    def test_no_lookup_defaults_key(self):
        """lookup_defaults was migrated to pre_lookups."""
        for name, schema in ENTITY_SCHEMAS.items():
            assert "lookup_defaults" not in schema, f"{name} still has lookup_defaults"

    def test_no_lookup_constants_inject_key(self):
        """lookup_constants_inject was migrated to pre_lookups."""
        for name, schema in ENTITY_SCHEMAS.items():
            assert "lookup_constants_inject" not in schema, f"{name} still has lookup_constants_inject"

    def test_employee_has_pre_lookups(self):
        emp = ENTITY_SCHEMAS["employee"]
        assert "department" in emp.get("pre_lookups", {})

    def test_travel_expense_cost_has_pre_lookups(self):
        tec = ENTITY_SCHEMAS["travel_expense_cost"]
        assert "costCategory" in tec.get("pre_lookups", {})
        assert "paymentType" in tec.get("pre_lookups", {})

    def test_travel_expense_per_diem_has_pre_lookups(self):
        te = ENTITY_SCHEMAS["travel_expense_per_diem"]
        assert "rateCategory" in te.get("pre_lookups", {})

    def test_company_is_singleton(self):
        assert ENTITY_SCHEMAS["company"].get("singleton") is True


class TestKnownConstants:
    def test_vat_rates(self):
        assert KNOWN_CONSTANTS["vat_25"] == {"id": 3}
        assert KNOWN_CONSTANTS["vat_15"] == {"id": 5}
        assert KNOWN_CONSTANTS["vat_0"] == {"id": 6}

    def test_nok_and_norway(self):
        assert KNOWN_CONSTANTS["nok"] == {"id": 1}
        assert KNOWN_CONSTANTS["norway"] == {"id": 162}


class TestNoLookupConstants:
    def test_lookup_constants_removed(self):
        """LOOKUP_CONSTANTS dict should no longer exist."""
        import task_registry
        assert not hasattr(task_registry, "LOOKUP_CONSTANTS"), "LOOKUP_CONSTANTS should be removed"


class TestActionSchemas:
    def test_has_13_action_types(self):
        assert len(ACTION_SCHEMAS) == 13

    def test_generic_actions(self):
        assert "update" in ACTION_SCHEMAS
        assert "delete" in ACTION_SCHEMAS
        assert ACTION_SCHEMAS["update"]["flow"] == "search_put"
        assert ACTION_SCHEMAS["delete"]["flow"] == "search_delete"

    def test_invoice_actions(self):
        for action in ("send_invoice", "create_credit_note", "create_reminder"):
            assert action in ACTION_SCHEMAS
            assert ACTION_SCHEMAS[action]["entity"] == "invoice"

    def test_travel_expense_actions(self):
        for action in ("approve_travel_expense", "deliver_travel_expense", "unapprove_travel_expense"):
            assert action in ACTION_SCHEMAS
            assert ACTION_SCHEMAS[action].get("body_from_search") is True

    def test_supplier_invoice_actions(self):
        for action in ("approve_supplier_invoice", "reject_supplier_invoice", "pay_supplier_invoice"):
            assert action in ACTION_SCHEMAS

    def test_grant_entitlements_uses_query_params(self):
        ge = ACTION_SCHEMAS["grant_entitlements"]
        assert "action_params_from_search" in ge
        assert ge["action_params_from_search"]["employeeId"] == "id"


class TestBulkEndpoints:
    def test_has_6_bulk_types(self):
        assert len(BULK_ENDPOINTS) == 6

    def test_employee_bulk(self):
        assert BULK_ENDPOINTS["employee"] == "/employee/list"

    def test_all_bulk_entities_in_schemas(self):
        for entity in BULK_ENDPOINTS:
            assert entity in ENTITY_SCHEMAS, f"bulk entity {entity} not in ENTITY_SCHEMAS"


class TestSearchParams:
    def test_core_entities_have_search_params(self):
        for entity in ("department", "employee", "customer", "product", "supplier", "project"):
            assert entity in SEARCH_PARAMS, f"{entity} missing from SEARCH_PARAMS"

    def test_employee_search_fields(self):
        assert SEARCH_PARAMS["employee"]["firstName"] == "firstName"
        assert SEARCH_PARAMS["employee"]["lastName"] == "lastName"


class TestDependencies:
    def test_all_entities_in_dependencies(self):
        for entity in ENTITY_SCHEMAS:
            assert entity in DEPENDENCIES, f"{entity} missing from DEPENDENCIES"

    def test_employee_depends_on_department(self):
        assert "department" in DEPENDENCIES["employee"]

    def test_invoice_depends_on_order(self):
        assert "order" in DEPENDENCIES["invoice"]

    def test_new_entities_have_correct_deps(self):
        assert "employee" in DEPENDENCIES["employee_employment"]
        assert "employee_employment" in DEPENDENCIES["employee_employment_details"]
        assert "project" in DEPENDENCIES["project_participant"]
        assert "travel_expense" in DEPENDENCIES["travel_expense_per_diem"]

    def test_no_cycles(self):
        visited = set()
        in_stack = set()

        def has_cycle(node):
            if node in in_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for dep in DEPENDENCIES.get(node, []):
                if has_cycle(dep):
                    return True
            in_stack.remove(node)
            return False

        for entity in DEPENDENCIES:
            assert not has_cycle(entity), f"Cycle detected involving {entity}"

    def test_all_dependency_targets_exist_in_schemas(self):
        """Every dependency target should be a known entity."""
        for entity, deps in DEPENDENCIES.items():
            for dep in deps:
                assert dep in ENTITY_SCHEMAS, f"{entity} depends on unknown entity {dep}"
