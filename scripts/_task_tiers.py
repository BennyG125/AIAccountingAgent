"""Shared constants for pipeline coverage tools."""

TASK_TIERS: dict[str, int] = {
    # Tier 1
    "create_product": 1, "create_invoice": 1, "create_customer": 1,
    "create_supplier": 1, "create_departments": 1, "create_employee": 1,
    "create_order": 1, "create_project": 1,
    # Tier 2
    "register_payment": 2, "credit_note": 2, "register_supplier_invoice": 2,
    "register_hours": 2, "run_salary": 2, "custom_dimension": 2,
    "employee_onboarding": 2, "travel_expense": 2, "fixed_price_project": 2,
    "reverse_payment": 2, "overdue_invoice_reminder": 2, "forex_payment": 2,
    # Tier 3
    "bank_reconciliation": 3, "year_end_close": 3, "year_end_corrections": 3,
    "monthly_closing": 3, "project_lifecycle": 3, "cost_analysis_projects": 3,
}

# Recipe/guard filenames that don't match task_type names.
# None = orphan recipe with no corresponding task type.
RECIPE_NAME_OVERRIDES: dict[str, str | None] = {
    "custom_dimension_voucher": "custom_dimension",
    "reverse_payment_voucher": "reverse_payment",
    "asset_registration": None,
}
