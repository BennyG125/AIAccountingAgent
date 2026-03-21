"""Execution plan: Register Supplier Invoice (Tier 2).

Flow:
  1. Find or create supplier by org number (GET /supplier, POST /supplier)
  2. Look up supplier payable account 2400
  3. Look up expense account (from params, e.g. 7000)
  4. Look up incoming VAT type via GET /ledger/vatType
  5. POST /ledger/voucher with two manual postings:
       row 1 — expense debit with VAT type (net amount)
       row 2 — supplier payable credit, negative gross, no vatType
     Tripletex auto-creates row 0 (VAT posting to 2710).

NEVER use /incomingInvoice — it always returns 403.
"""
import datetime

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "supplier_name": {
            "type": "string",
            "description": "Supplier / vendor company name (required)",
        },
        "org_number": {
            "type": "string",
            "description": "Supplier organisation number, e.g. '803273723' (required if available)",
        },
        "invoice_number": {
            "type": "string",
            "description": "Invoice reference number, e.g. 'INV-2026-8172'",
        },
        "invoice_date": {
            "type": "string",
            "description": "Invoice date in YYYY-MM-DD format (required)",
        },
        "gross_amount": {
            "type": "number",
            "description": "Total invoice amount including VAT in NOK (required)",
        },
        "vat_rate": {
            "type": "number",
            "description": "VAT rate as a decimal fraction, e.g. 0.25 for 25% (default 0.25 if not mentioned)",
        },
        "expense_account": {
            "type": "integer",
            "description": "Expense account number to debit, e.g. 7000 (default 7000 if not specified)",
        },
    },
    "required": ["supplier_name", "invoice_date", "gross_amount"],
}


@register
class RegisterSupplierInvoicePlan(ExecutionPlan):
    task_type = "register_supplier_invoice"
    description = (
        "Find or create supplier, look up accounts and VAT type, "
        "then post a balanced voucher to /ledger/voucher (never /incomingInvoice)"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        supplier_name = params["supplier_name"]
        org_number = params.get("org_number")
        invoice_number = params.get("invoice_number", "")
        invoice_date = params.get("invoice_date") or datetime.date.today().isoformat()
        gross_amount = float(params["gross_amount"])
        vat_rate = float(params.get("vat_rate") or 0.25)
        expense_account_number = str(params.get("expense_account") or 7000)

        # Derived amounts
        net_amount = round(gross_amount / (1 + vat_rate), 2)

        api_calls = 0
        api_errors = 0

        # --- Step 1: Find or create supplier ---
        self._check_timeout(start_time)
        search_params = {"count": 1}
        if org_number:
            search_params["organizationNumber"] = org_number
        else:
            search_params["name"] = supplier_name

        supplier_result = client.get("/supplier", params=search_params)
        api_calls += 1

        supplier_id = None
        if supplier_result["success"]:
            values = supplier_result["body"].get("values", [])
            if values:
                supplier_id = values[0]["id"]

        if supplier_id is None:
            create_body = {"name": supplier_name}
            if org_number:
                create_body["organizationNumber"] = org_number

            create_result = client.post("/supplier", body=create_body)
            api_calls += 1
            if not create_result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to create supplier '{supplier_name}': "
                    f"status={create_result.get('status_code')}, "
                    f"error={create_result.get('error')}"
                )
            supplier_id = create_result["body"]["value"]["id"]

        # --- Step 2: Look up supplier payable account (2400) ---
        self._check_timeout(start_time)
        acc2400_result = client.get("/ledger/account", params={"number": "2400"})
        api_calls += 1
        if not acc2400_result["success"] or not acc2400_result["body"].get("values"):
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up account 2400: "
                f"status={acc2400_result.get('status_code')}, "
                f"error={acc2400_result.get('error')}"
            )
        supplier_payable_account_id = acc2400_result["body"]["values"][0]["id"]

        # --- Step 3: Look up expense account ---
        self._check_timeout(start_time)
        exp_result = client.get(
            "/ledger/account", params={"number": expense_account_number}
        )
        api_calls += 1
        if not exp_result["success"] or not exp_result["body"].get("values"):
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up expense account {expense_account_number}: "
                f"status={exp_result.get('status_code')}, "
                f"error={exp_result.get('error')}"
            )
        expense_account_id = exp_result["body"]["values"][0]["id"]

        # --- Step 4: Look up incoming VAT type ---
        # Prefer percentage matching vat_rate; fall back to first entry (id=1 is usually 25%)
        self._check_timeout(start_time)
        vat_result = client.get(
            "/ledger/vatType", params={"fields": "id,number,percentage"}
        )
        api_calls += 1
        vat_type_id = None
        if vat_result["success"]:
            target_pct = round(vat_rate * 100)
            for vt in vat_result["body"].get("values", []):
                pct = vt.get("percentage")
                if pct is not None and round(float(pct)) == target_pct:
                    vat_type_id = vt["id"]
                    break
            if vat_type_id is None:
                # Fallback: use first available VAT type
                values = vat_result["body"].get("values", [])
                if values:
                    vat_type_id = values[0]["id"]

        if vat_type_id is None:
            api_errors += 1
            raise RuntimeError("No VAT types available in this sandbox")

        # --- Step 5: POST /ledger/voucher ---
        self._check_timeout(start_time)

        description = (
            f"Leverandørfaktura {invoice_number} - {supplier_name}"
            if invoice_number
            else f"Leverandørfaktura - {supplier_name}"
        )

        voucher_body = {
            "date": invoice_date,
            "description": description,
            "postings": [
                # Row 1: expense debit (net) with vatType — Tripletex will auto-create row 0 (VAT)
                {
                    "row": 1,
                    "account": {"id": expense_account_id},
                    "amount": net_amount,
                    "amountCurrency": net_amount,
                    "amountGross": gross_amount,
                    "amountGrossCurrency": gross_amount,
                    "currency": {"id": 1},
                    "vatType": {"id": vat_type_id},
                    "supplier": {"id": supplier_id},
                    "description": description,
                },
                # Row 2: supplier payable credit (negative gross) — no vatType, no amountGross
                {
                    "row": 2,
                    "account": {"id": supplier_payable_account_id},
                    "amount": -gross_amount,
                    "amountCurrency": -gross_amount,
                    "amountGross": -gross_amount,
                    "amountGrossCurrency": -gross_amount,
                    "currency": {"id": 1},
                    "description": description,
                },
            ],
        }

        voucher_result = self._safe_post(
            client,
            "/ledger/voucher",
            body=voucher_body,
            retry_without=["vatType"],
        )
        api_calls += 1
        if not voucher_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to post supplier invoice voucher: "
                f"status={voucher_result.get('status_code')}, "
                f"error={voucher_result.get('error')}"
            )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
