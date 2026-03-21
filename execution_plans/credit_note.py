"""Execution plan: Credit Note (Tier 2).

Sequence:
  1. GET /customer?organizationNumber=X  → find customer ID
  2. GET /invoice?customerId=X           → find matching invoice by description/amount
  3. PUT /invoice/{id}/:createCreditNote?date=YYYY-MM-DD  → issue credit note

CRITICAL: The ?date=YYYY-MM-DD query param is REQUIRED on the PUT call.
Omitting it causes a 422 "date: Kan ikke vaere null" error.
"""
import datetime

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "org_number": "string — organization number of the customer (required)",
    "description": "string|null — invoice description/product name to match (e.g. 'Training Session')",
    "amount": "number|null — invoice amount excluding VAT in NOK, used to disambiguate if multiple invoices match",
}


@register
class CreditNotePlan(ExecutionPlan):
    task_type = "credit_note"
    description = "Issue a credit note that reverses a customer invoice"

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0
        today = datetime.date.today().isoformat()  # YYYY-MM-DD
        # invoiceDateTo is EXCLUSIVE in the Tripletex API — add 1 day to include today
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

        # Step 1: Find customer by organizationNumber
        org_number = params.get("org_number")
        if not org_number:
            raise RuntimeError("Missing required param: org_number")

        result = client.get("/customer", params={"organizationNumber": org_number, "fields": "id,name"})
        api_calls += 1
        if not result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up customer by org_number={org_number}: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )

        customers = result["body"].get("values", [])
        if not customers:
            raise RuntimeError(f"No customer found with organizationNumber={org_number}")
        customer_id = customers[0]["id"]

        self._check_timeout(start_time)

        # Step 2: Find invoices for this customer
        # The /invoice endpoint REQUIRES invoiceDateFrom and invoiceDateTo.
        # Use a wide date range to find all invoices.
        result = client.get(
            "/invoice",
            params={
                "customerId": customer_id,
                "invoiceDateFrom": "2020-01-01",
                "invoiceDateTo": tomorrow,
                "fields": "id,invoiceDate,amountExcludingVatCurrency,orders",
            },
        )
        api_calls += 1
        if not result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to fetch invoices for customerId={customer_id}: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )

        invoices = result["body"].get("values", [])
        if not invoices:
            raise RuntimeError(f"No invoices found for customerId={customer_id}")

        # Select the matching invoice — prefer matching by description/amount;
        # fall back to most recent (last in list or highest id).
        invoice_id = self._pick_invoice(invoices, params)

        self._check_timeout(start_time)

        # Step 3: Create credit note — date query param is REQUIRED
        result = client.put(
            f"/invoice/{invoice_id}/:createCreditNote",
            body=None,
            params={"date": today},
        )
        api_calls += 1
        if not result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to create credit note for invoice {invoice_id}: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_invoice(self, invoices: list, params: dict) -> int:
        """Pick the best matching invoice from the list.

        Matching strategy (in priority order):
          1. If amount provided, find invoice whose amountExcludingVatCurrency matches.
          2. Fall back to the most recent invoice (highest id).
        """
        amount = params.get("amount")

        if amount is not None:
            for inv in invoices:
                if inv.get("amountExcludingVatCurrency") == amount:
                    return inv["id"]

        # Fall back: most recent = highest id
        return max(invoices, key=lambda i: i["id"])["id"]
