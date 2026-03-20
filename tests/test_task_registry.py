# tests/test_task_registry.py
"""Tests for task_registry.py — schema completeness and DAG validation."""

from task_registry import ENTITY_SCHEMAS, KNOWN_CONSTANTS, DEPENDENCIES, LOOKUP_CONSTANTS


class TestEntitySchemas:
    def test_all_competition_entities_covered(self):
        expected = {
            "department", "employee", "customer", "product",
            "order", "invoice", "register_payment",
            "travel_expense", "travel_expense_cost",
            "project", "contact", "voucher",
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

    def test_travel_expense_cost_has_lookup_constants(self):
        tec = ENTITY_SCHEMAS["travel_expense_cost"]
        assert "costCategory" in tec.get("lookup_constants_inject", {})
        assert "paymentType" in tec.get("lookup_constants_inject", {})


class TestKnownConstants:
    def test_vat_rates(self):
        assert KNOWN_CONSTANTS["vat_25"] == {"id": 3}
        assert KNOWN_CONSTANTS["vat_15"] == {"id": 5}
        assert KNOWN_CONSTANTS["vat_0"] == {"id": 6}

    def test_nok_and_norway(self):
        assert KNOWN_CONSTANTS["nok"] == {"id": 1}
        assert KNOWN_CONSTANTS["norway"] == {"id": 162}


class TestDependencies:
    def test_employee_depends_on_department(self):
        assert "department" in DEPENDENCIES["employee"]

    def test_invoice_depends_on_order(self):
        assert "order" in DEPENDENCIES["invoice"]

    def test_no_cycles(self):
        """Verify dependency graph is a valid DAG (no cycles)."""
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
                assert dep in ENTITY_SCHEMAS or dep in DEPENDENCIES, \
                    f"{entity} depends on unknown entity {dep}"
