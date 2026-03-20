# task_registry.py
"""Static entity registry for deterministic execution.

Contains all knowledge needed to validate and execute Tripletex API calls
without LLM involvement: entity schemas, known constants, dependency graph,
action schemas, bulk endpoints, and search parameter mappings.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Entity Schemas (27 entities)
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
        "pre_lookups": {"department": "/department"},
        "object_ref_fields": ["department"],
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
        "object_ref_fields": ["vatType"],
    },
    "order": {
        "endpoint": "/order",
        "method": "POST",
        "required": ["customer", "orderDate", "deliveryDate"],
        "defaults": {},
        "auto_generate": ["orderDate", "deliveryDate"],
        "embed": ["orderLines"],
        "object_ref_fields": ["customer"],
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
        "object_ref_fields": ["employee"],
    },
    "travel_expense_cost": {
        "endpoint": "/travelExpense/cost",
        "method": "POST",
        "required": ["travelExpense", "date", "amountCurrencyIncVat", "costCategory", "paymentType"],
        "defaults": {"currency": {"id": 1}},
        "auto_generate": ["date"],
        "pre_lookups": {
            "costCategory": "/travelExpense/costCategory",
            "paymentType": "/travelExpense/paymentType",
        },
        "object_ref_fields": ["travelExpense", "currency", "costCategory", "paymentType"],
    },
    "project": {
        "endpoint": "/project",
        "method": "POST",
        "required": ["name", "projectManager", "startDate"],
        "defaults": {},
        "auto_generate": ["startDate"],
        "object_ref_fields": ["projectManager", "customer"],
    },
    "contact": {
        "endpoint": "/contact",
        "method": "POST",
        "required": ["firstName", "lastName", "customer"],
        "defaults": {},
        "object_ref_fields": ["customer"],
    },
    "voucher": {
        "endpoint": "/ledger/voucher",
        "method": "POST",
        "required": ["date", "description", "postings"],
        "defaults": {},
        "auto_generate": ["date"],
    },
    # --- Employee ---
    "employee_employment": {
        "endpoint": "/employee/employment",
        "method": "POST",
        "required": ["employee", "startDate"],
        "defaults": {"isMainEmployer": True},
        "auto_generate": ["startDate"],
        "object_ref_fields": ["employee"],
    },
    "employee_employment_details": {
        "endpoint": "/employee/employment/details",
        "method": "POST",
        "required": ["employment", "date"],
        "defaults": {},
        "auto_generate": ["date"],
        "object_ref_fields": ["employment"],
    },
    # --- Customer/Supplier ---
    "supplier": {
        "endpoint": "/supplier",
        "method": "POST",
        "required": ["name"],
        "defaults": {},
    },
    "supplier_invoice": {
        "endpoint": "/supplierInvoice",
        "method": "GET",
        "required": [],
        "defaults": {},
    },
    "customer_category": {
        "endpoint": "/customer/category",
        "method": "POST",
        "required": ["name", "number", "type"],
        "defaults": {},
    },
    # --- Product ---
    "product_unit": {
        "endpoint": "/product/unit",
        "method": "POST",
        "required": ["name", "nameShort", "commonCode"],
        "defaults": {},
    },
    # --- Order ---
    "order_line": {
        "endpoint": "/order/orderline",
        "method": "POST",
        "required": ["order", "product"],
        "defaults": {},
        "object_ref_fields": ["product", "vatType", "order"],
    },
    # --- Project ---
    "project_participant": {
        "endpoint": "/project/participant",
        "method": "POST",
        "required": ["project", "employee"],
        "defaults": {},
        "object_ref_fields": ["project", "employee"],
    },
    # --- Travel Expense sub-types ---
    "travel_expense_per_diem": {
        "endpoint": "/travelExpense/perDiemCompensation",
        "method": "POST",
        "required": ["travelExpense", "rateCategory"],
        "defaults": {},
        "pre_lookups": {
            "rateCategory": "/travelExpense/rateCategory",
            "rateType": "/travelExpense/rate",
        },
        "object_ref_fields": ["travelExpense", "rateCategory", "rateType"],
    },
    "travel_expense_mileage": {
        "endpoint": "/travelExpense/mileageAllowance",
        "method": "POST",
        "required": ["travelExpense", "rateCategory", "date"],
        "defaults": {},
        "auto_generate": ["date"],
        "pre_lookups": {
            "rateCategory": "/travelExpense/rateCategory",
            "rateType": "/travelExpense/rate",
        },
        "object_ref_fields": ["travelExpense", "rateCategory", "rateType"],
    },
    "travel_expense_accommodation": {
        "endpoint": "/travelExpense/accommodationAllowance",
        "method": "POST",
        "required": ["travelExpense", "rateCategory"],
        "defaults": {},
        "pre_lookups": {
            "rateCategory": "/travelExpense/rateCategory",
        },
        "object_ref_fields": ["travelExpense", "rateCategory"],
    },
    # --- Ledger ---
    "ledger_account": {
        "endpoint": "/ledger/account",
        "method": "POST",
        "required": ["number", "name"],
        "defaults": {},
    },
    # --- Salary ---
    "salary_transaction": {
        "endpoint": "/salary/transaction",
        "method": "POST",
        "required": ["date", "month", "year"],
        "defaults": {},
        "auto_generate": ["date"],
    },
    # --- Delivery Address ---
    "delivery_address": {
        "endpoint": "/deliveryAddress",
        "method": "PUT",
        "required": [],
        "defaults": {},
    },
    # --- Company ---
    "company": {
        "endpoint": "/company",
        "method": "PUT",
        "required": [],
        "defaults": {},
        "singleton": True,
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

# NOTE: LOOKUP_CONSTANTS removed — migrated to pre_lookups on individual schemas

# ---------------------------------------------------------------------------
# Action Schemas — for update/delete/named action patterns
# ---------------------------------------------------------------------------

ACTION_SCHEMAS = {
    # --- Generic actions (work on any entity in ENTITY_SCHEMAS) ---
    "update": {
        "flow": "search_put",
        "description": "Search for entity by search_fields, then PUT with merged fields",
    },
    "delete": {
        "flow": "search_delete",
        "description": "Search for entity by search_fields, then DELETE",
    },
    # --- Invoice actions ---
    "send_invoice": {
        "entity": "invoice",
        "flow": "search_action",
        "action_endpoint": "/invoice/{id}/:send",
        "action_method": "PUT",
    },
    "create_credit_note": {
        "entity": "invoice",
        "flow": "search_action",
        "action_endpoint": "/invoice/{id}/:createCreditNote",
        "action_method": "PUT",
    },
    "create_reminder": {
        "entity": "invoice",
        "flow": "search_action",
        "action_endpoint": "/invoice/{id}/:createReminder",
        "action_method": "PUT",
    },
    # --- Voucher actions ---
    "reverse_voucher": {
        "entity": "voucher",
        "flow": "search_action",
        "action_endpoint": "/ledger/voucher/{id}/:reverse",
        "action_method": "PUT",
    },
    # --- Employee actions ---
    "grant_entitlements": {
        "entity": "employee",
        "flow": "search_action",
        "action_endpoint": "/employee/entitlement/:grantEntitlementsByTemplate",
        "action_method": "PUT",
        "action_params_from_search": {"employeeId": "id"},
    },
    # --- Travel expense workflow actions ---
    "approve_travel_expense": {
        "entity": "travel_expense",
        "flow": "search_action",
        "action_endpoint": "/travelExpense/:approve",
        "action_method": "PUT",
        "body_from_search": True,
    },
    "deliver_travel_expense": {
        "entity": "travel_expense",
        "flow": "search_action",
        "action_endpoint": "/travelExpense/:deliver",
        "action_method": "PUT",
        "body_from_search": True,
    },
    "unapprove_travel_expense": {
        "entity": "travel_expense",
        "flow": "search_action",
        "action_endpoint": "/travelExpense/:unapprove",
        "action_method": "PUT",
        "body_from_search": True,
    },
    # --- Supplier invoice actions ---
    "approve_supplier_invoice": {
        "entity": "supplier_invoice",
        "flow": "search_action",
        "action_endpoint": "/supplierInvoice/{id}/:approve",
        "action_method": "PUT",
    },
    "reject_supplier_invoice": {
        "entity": "supplier_invoice",
        "flow": "search_action",
        "action_endpoint": "/supplierInvoice/{id}/:reject",
        "action_method": "PUT",
    },
    "pay_supplier_invoice": {
        "entity": "supplier_invoice",
        "flow": "search_action",
        "action_endpoint": "/supplierInvoice/{id}/:addPayment",
        "action_method": "POST",
    },
}

# ---------------------------------------------------------------------------
# Bulk Endpoints — POST /*/list for batch creation
# ---------------------------------------------------------------------------

BULK_ENDPOINTS = {
    "employee": "/employee/list",
    "customer": "/customer/list",
    "contact": "/contact/list",
    "product": "/product/list",
    "order_line": "/order/orderline/list",
    "project_participant": "/project/participant/list",
}

# ---------------------------------------------------------------------------
# Search Parameters — field name → query param mapping per entity
# ---------------------------------------------------------------------------

SEARCH_PARAMS = {
    "department": {"name": "name", "departmentNumber": "departmentNumber"},
    "employee": {"firstName": "firstName", "lastName": "lastName", "email": "email"},
    "customer": {"name": "name", "email": "email", "organizationNumber": "organizationNumber"},
    "product": {"name": "name", "number": "number"},
    "order": {"customerName": "customerName", "number": "number"},
    "invoice": {"customerId": "customerId", "invoiceNumber": "invoiceNumber"},
    "supplier": {"name": "name", "organizationNumber": "organizationNumber"},
    "contact": {"firstName": "firstName", "lastName": "lastName", "email": "email"},
    "project": {"name": "name", "number": "number"},
    "voucher": {"number": "number", "dateFrom": "dateFrom", "dateTo": "dateTo"},
    "travel_expense": {"employeeId": "employeeId"},
    "customer_category": {"name": "name", "number": "number"},
    "product_unit": {"name": "name", "nameShort": "nameShort"},
    "supplier_invoice": {},
    "ledger_account": {"number": "number", "name": "name"},
    "salary_transaction": {},
    "delivery_address": {},
    "employee_employment": {"employeeId": "employeeId"},
    "company": {},
}

# ---------------------------------------------------------------------------
# Dependency Graph — directed, acyclic (27 entities)
# ---------------------------------------------------------------------------

DEPENDENCIES = {
    # --- Core entities (no deps) ---
    "department": [],
    "customer": [],
    "product": [],
    "supplier": [],
    "customer_category": [],
    "product_unit": [],
    "ledger_account": [],
    "voucher": [],
    "company": [],
    "delivery_address": [],
    # --- Employee chain ---
    "employee": ["department"],
    "employee_employment": ["employee"],
    "employee_employment_details": ["employee_employment"],
    # --- Customer chain ---
    "contact": ["customer"],
    # --- Order → Invoice → Payment chain ---
    "order": ["customer", "product"],
    "order_line": ["order", "product"],
    "invoice": ["order"],
    "register_payment": ["invoice"],
    # --- Travel expense chain ---
    "travel_expense": ["employee"],
    "travel_expense_cost": ["travel_expense"],
    "travel_expense_per_diem": ["travel_expense"],
    "travel_expense_mileage": ["travel_expense"],
    "travel_expense_accommodation": ["travel_expense"],
    # --- Project chain ---
    "project": ["employee"],
    "project_participant": ["project", "employee"],
    # --- Salary ---
    "salary_transaction": [],
    # --- Supplier invoice ---
    "supplier_invoice": [],
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
