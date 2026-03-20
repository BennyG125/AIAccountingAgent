# task_registry.py
"""Static entity registry for deterministic execution.

Contains all knowledge needed to validate and execute Tripletex API calls
without LLM involvement: entity schemas, known constants, and dependency graph.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Entity Schemas
# ---------------------------------------------------------------------------

ENTITY_SCHEMAS = {
    "department": {
        "endpoint": "/department",
        "method": "POST",
        "required": ["name", "departmentNumber"],
        "defaults": {},
        "auto_generate": ["departmentNumber"],
    },
    "employee": {
        "endpoint": "/employee",
        "method": "POST",
        "required": ["firstName", "lastName", "userType", "department"],
        "defaults": {"userType": "STANDARD"},
        "lookup_defaults": {"department": "/department"},
    },
    "customer": {
        "endpoint": "/customer",
        "method": "POST",
        "required": ["name"],
        "defaults": {},
    },
    "product": {
        "endpoint": "/product",
        "method": "POST",
        "required": ["name"],
        "defaults": {},
    },
    "order": {
        "endpoint": "/order",
        "method": "POST",
        "required": ["customer", "orderDate", "deliveryDate"],
        "defaults": {},
        "auto_generate": ["orderDate", "deliveryDate"],
        "embed": ["orderLines"],
    },
    "invoice": {
        "endpoint": "/invoice",
        "method": "POST",
        "required": ["invoiceDate", "invoiceDueDate", "orders"],
        "defaults": {},
        "auto_generate": ["invoiceDate", "invoiceDueDate"],
    },
    "register_payment": {
        "endpoint": "/invoice/{id}/:payment",
        "method": "PUT",
        "use_query_params": True,
        "required": ["paymentDate", "paidAmount", "paidAmountCurrency"],
        "defaults": {"paidAmountCurrency": 1, "paymentTypeId": 0},
        "auto_generate": ["paymentDate"],
    },
    "travel_expense": {
        "endpoint": "/travelExpense",
        "method": "POST",
        "required": ["employee", "title"],
        "defaults": {},
    },
    "travel_expense_cost": {
        "endpoint": "/travelExpense/cost",
        "method": "POST",
        "required": ["travelExpense", "date", "amountCurrencyIncVat", "costCategory", "paymentType"],
        "defaults": {"currency": {"id": 1}},
        "auto_generate": ["date"],
        "lookup_constants_inject": {
            "costCategory": "/travelExpense/costCategory",
            "paymentType": "/travelExpense/paymentType",
        },
    },
    "project": {
        "endpoint": "/project",
        "method": "POST",
        "required": ["name", "projectManager", "startDate"],
        "defaults": {},
        "auto_generate": ["startDate"],
    },
    "contact": {
        "endpoint": "/contact",
        "method": "POST",
        "required": ["firstName", "lastName", "customer"],
        "defaults": {},
    },
    "voucher": {
        "endpoint": "/ledger/voucher",
        "method": "POST",
        "required": ["date", "description", "postings"],
        "defaults": {},
        "auto_generate": ["date"],
    },
}

# ---------------------------------------------------------------------------
# Known Constants — injected automatically, never looked up via API
# ---------------------------------------------------------------------------

KNOWN_CONSTANTS = {
    "vat_25": {"id": 3},
    "vat_15": {"id": 5},
    "vat_0": {"id": 6},
    "nok": {"id": 1},
    "norway": {"id": 162},
    "paymentTypeId_default": 0,
}

# ---------------------------------------------------------------------------
# Lookup Constants — GET once per session, cache the result
# ---------------------------------------------------------------------------

LOOKUP_CONSTANTS = {
    "costCategory": "/travelExpense/costCategory",
    "paymentType_travel": "/travelExpense/paymentType",
    "rateCategory": "/travelExpense/rateCategory",
}

# ---------------------------------------------------------------------------
# Dependency Graph — directed, acyclic
# ---------------------------------------------------------------------------

DEPENDENCIES = {
    "department": [],
    "employee": ["department"],
    "customer": [],
    "product": [],
    "contact": ["customer"],
    "order": ["customer", "product"],
    "invoice": ["order"],
    "register_payment": ["invoice"],
    "travel_expense": ["employee"],
    "travel_expense_cost": ["travel_expense"],
    "project": ["employee"],
    "voucher": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_dept_counter = 100


def generate_auto_value(field: str) -> str | dict:
    """Generate a default value for auto_generate fields."""
    global _dept_counter
    if field in ("orderDate", "deliveryDate", "invoiceDate", "invoiceDueDate",
                 "startDate", "date", "paymentDate"):
        return date.today().isoformat()
    if field == "departmentNumber":
        val = str(_dept_counter)
        _dept_counter += 1
        return val
    return ""
