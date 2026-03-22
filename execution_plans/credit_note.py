"""Execution plan: Credit Note (Tier 2).

Sequence:
  1. GET /customer?organizationNumber=X  → find customer ID
  2. GET /invoice?customerId=X           → find matching invoice by description/amount
  3. PUT /invoice/{id}/:createCreditNote?date=YYYY-MM-DD  → issue credit note

CRITICAL: The ?date=YYYY-MM-DD query param is REQUIRED on the PUT call.
Omitting it causes a 422 "date: Kan ikke vaere null" error.
"""
import datetime
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "org_number": "string — organization number of the customer (required)",
    "customer_name": "string|null — customer/company name, used as fallback if org_number lookup fails",
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
        error_details = []
        today = datetime.date.today().isoformat()  # YYYY-MM-DD
        # invoiceDateTo is EXCLUSIVE in the Tripletex API — add 1 day to include today
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

        # Step 1: Find customer by organizationNumber
        org_number = params.get("org_number")
        customer_name = params.get("customer_name")
        if not org_number and not customer_name:
            error_details.append("Missing required param: org_number (and no customer_name fallback)")
            logger.warning("credit_note plan: missing org_number and customer_name")
            return self._make_result(api_calls=api_calls, api_errors=1, error_details=error_details)

        customer_id = None

        # Try by org number first
        if org_number:
            result = client.get("/customer", params={"organizationNumber": org_number, "fields": "id,name"})
            api_calls += 1
            if not result["success"]:
                api_errors += 1
                error_details.append(
                    f"Failed to look up customer by org_number={org_number}: "
                    f"status={result.get('status_code')}, error={result.get('error')}"
                )
                logger.warning("credit_note plan: customer lookup by org_number failed: %s", result.get("error"))
            else:
                customers = result["body"].get("values", [])
                if customers:
                    customer_id = customers[0]["id"]

        # Fallback: try by name if org_number lookup yielded nothing
        if customer_id is None and customer_name:
            result = client.get("/customer", params={"name": customer_name, "fields": "id,name"})
            api_calls += 1
            if not result["success"]:
                api_errors += 1
                error_details.append(
                    f"Fallback: failed to look up customer by name={customer_name}: "
                    f"status={result.get('status_code')}, error={result.get('error')}"
                )
                logger.warning("credit_note plan: customer lookup by name failed: %s", result.get("error"))
            else:
                customers = result["body"].get("values", [])
                if customers:
                    customer_id = customers[0]["id"]

        if customer_id is None:
            error_details.append(f"No customer found with org_number={org_number}, name={customer_name}")
            logger.warning("credit_note plan: no customer found")
            return self._make_result(api_calls=api_calls, api_errors=api_errors or 1, error_details=error_details)

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
            error_details.append(
                f"Failed to fetch invoices for customerId={customer_id}: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )
            logger.warning("credit_note plan: invoice fetch failed: %s", result.get("error"))
            return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        invoices = result["body"].get("values", [])
        if not invoices:
            api_errors += 1
            error_details.append(f"No invoices found for customerId={customer_id}")
            logger.warning("credit_note plan: no invoices found for customer %s", customer_id)
            return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

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
            error_details.append(
                f"Failed to create credit note for invoice {invoice_id}: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )
            logger.warning("credit_note plan: credit note creation failed: %s", result.get("error"))
            return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details or None)

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
