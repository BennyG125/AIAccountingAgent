# tests/test_generate_tools.py
"""Tests for the OpenAPI tool generator."""
import json
import pytest

# Minimal OpenAPI fragment for testing
MINI_SPEC = {
    "paths": {
        "/employee": {
            "post": {
                "tags": ["employee"],
                "summary": "Create employee",
                "operationId": "Employee_post",
                "parameters": [],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "firstName": {"type": "string", "description": "First name"},
                                    "lastName": {"type": "string", "description": "Last name"},
                                    "userType": {
                                        "type": "string",
                                        "enum": ["STANDARD", "EXTENDED", "NO_ACCESS"],
                                    },
                                    "id": {"type": "integer", "readOnly": True},
                                },
                                "required": ["firstName", "lastName"],
                            }
                        }
                    }
                },
            }
        },
        "/employee/entitlement/:grantEntitlementsByTemplate": {
            "put": {
                "tags": ["employee/entitlement"],
                "summary": "Grant entitlements by template",
                "operationId": "EmployeeEntitlement_grant",
                "parameters": [
                    {"name": "employeeId", "in": "query", "required": True,
                     "schema": {"type": "integer"}},
                    {"name": "template", "in": "query", "required": True,
                     "schema": {"type": "string", "enum": ["ALL_PRIVILEGES", "NONE_PRIVILEGES"]}},
                ],
            }
        },
        "/invoice/{id}/:payment": {
            "put": {
                "tags": ["invoice"],
                "summary": "Register payment",
                "operationId": "Invoice_payment",
                "parameters": [
                    {"name": "id", "in": "path", "required": True,
                     "schema": {"type": "integer"}},
                    {"name": "paymentDate", "in": "query", "required": True,
                     "schema": {"type": "string"}},
                    {"name": "paidAmount", "in": "query", "required": True,
                     "schema": {"type": "number"}},
                ],
            }
        },
        "/unrelated/endpoint": {
            "get": {
                "tags": ["unrelated_tag"],
                "summary": "Should be filtered out",
                "operationId": "Unrelated_get",
                "parameters": [],
            }
        },
    },
    "components": {"schemas": {}},
}

ACCOUNTING_TAGS = {"employee", "employee/entitlement", "invoice"}


def test_generate_tools_from_spec():
    from scripts.generate_tools import generate_tools_from_spec
    tools, meta = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    assert len(tools) == 3
    names = {t["name"] for t in tools}
    assert "employee_post" in names
    assert "employee_entitlement_grant" in names
    assert "invoice_payment" in names
    assert not any("unrelated" in t["name"] for t in tools)


def test_readonly_fields_stripped():
    from scripts.generate_tools import generate_tools_from_spec
    tools, _ = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    emp = next(t for t in tools if t["name"] == "employee_post")
    props = emp["input_schema"]["properties"]
    assert "firstName" in props
    assert "id" not in props


def test_enums_preserved():
    from scripts.generate_tools import generate_tools_from_spec
    tools, _ = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    emp = next(t for t in tools if t["name"] == "employee_post")
    assert emp["input_schema"]["properties"]["userType"]["enum"] == ["STANDARD", "EXTENDED", "NO_ACCESS"]


def test_query_params_become_input_properties():
    from scripts.generate_tools import generate_tools_from_spec
    tools, meta = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    ent = next(t for t in tools if t["name"] == "employee_entitlement_grant")
    props = ent["input_schema"]["properties"]
    assert "employeeId" in props
    assert "template" in props
    assert ent["input_schema"]["required"] == ["employeeId", "template"]
    assert meta["employee_entitlement_grant"]["query_params"] == ["employeeId", "template"]
    assert meta["employee_entitlement_grant"]["method"] == "PUT"


def test_path_params_in_meta():
    from scripts.generate_tools import generate_tools_from_spec
    tools, meta = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    assert meta["invoice_payment"]["path_params"] == ["id"]
    assert "paymentDate" in meta["invoice_payment"]["query_params"]


def test_all_tools_have_defer_loading():
    from scripts.generate_tools import generate_tools_from_spec
    tools, _ = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    for t in tools:
        assert t.get("defer_loading") is True


def test_no_duplicate_names():
    from scripts.generate_tools import generate_tools_from_spec
    tools, _ = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    names = [t["name"] for t in tools]
    assert len(names) == len(set(names)), f"Duplicate tool names: {[n for n in names if names.count(n) > 1]}"
