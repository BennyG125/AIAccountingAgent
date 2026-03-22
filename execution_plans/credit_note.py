"""Execution plan: Credit Note (Tier 2).

Sequence:
  1. GET /customer?organizationNumber=X  -> find customer ID
  2. GET /invoice?customerId=X           -> find matching invoice by description/amount
  3. PUT /invoice/{id}/:createCreditNote?date=YYYY-MM-DD  -> issue credit note

CRITICAL: The ?date=YYYY-MM-DD query param is REQUIRED on the PUT call.
Omitting it causes a 422 "date: Kan ikke vaere null" error.

CRITICAL: Filter out invoices that are already credit notes (isCreditNote=true).
Trying to create a credit note on a credit note causes 422 "Validering feilet."
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
        # invoiceDateTo is EXCLUSIVE in the Tripletex API -- add 1 day to include today
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
        # CRITICAL: Request isCreditNote to filter out credit notes.
        result = client.get(
            "/invoice",
            params={
                "customerId": customer_id,
                "invoiceDateFrom": "2020-01-01",
                "invoiceDateTo": tomorrow,
                "fields": "id,invoiceDate,invoiceNumber,amountExcludingVatCurrency,isCreditNote,orders",
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

        all_invoices = result["body"].get("values", [])

        # Filter out credit notes -- you cannot create a credit note on a credit note
        invoices = [inv for inv in all_invoices if not inv.get("isCreditNote", False)]

        if not invoices:
            api_errors += 1
            if all_invoices:
                error_details.append(
                    f"All {len(all_invoices)} invoices for customerId={customer_id} are credit notes"
                )
                logger.warning("credit_note plan: all invoices are credit notes for customer %s", customer_id)
            else:
                error_details.append(f"No invoices found for customerId={customer_id}")
                logger.warning("credit_note plan: no invoices found for customer %s", customer_id)
            return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        # Select the matching invoice(s) -- ranked by best match
        ranked_invoices = self._rank_invoices(invoices, params)

        self._check_timeout(start_time)

        # Step 3: Create credit note -- try the best match first, then fallback
        # The date query param is REQUIRED.
        for invoice_id in ranked_invoices:
            result = client.put(
                f"/invoice/{invoice_id}/:createCreditNote",
                body={},
                params={"date": today},
            )
            api_calls += 1
            if result["success"]:
                logger.info("credit_note plan: credit note created for invoice %s", invoice_id)
                return self._make_result(
                    api_calls=api_calls,
                    api_errors=api_errors,
                    error_details=error_details or None,
                )

            # Failed -- log and try next candidate
            api_errors += 1
            error_msg = (
                f"Failed to create credit note for invoice {invoice_id}: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )
            error_details.append(error_msg)
            logger.warning("credit_note plan: %s", error_msg)

            # If there are more candidates, try them
            self._check_timeout(start_time)

        # All candidates failed
        return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _rank_invoices(self, invoices: list, params: dict) -> list[int]:
        """Rank invoices by match quality, return list of invoice IDs (best first).

        Matching strategy (in priority order):
          1. If amount provided, invoices whose amountExcludingVatCurrency matches
             (within tolerance) come first.
          2. Remaining invoices sorted by ID descending (most recent first).

        Returns at most 3 candidates to avoid excessive API calls.
        """
        amount = params.get("amount")
        amount_matched = []
        others = []

        for inv in invoices:
            inv_amount = inv.get("amountExcludingVatCurrency")
            if amount is not None and inv_amount is not None:
                # Use tolerance for float comparison (handles 35700 vs 35700.0 etc.)
                try:
                    if abs(float(inv_amount) - float(amount)) < 0.01:
                        amount_matched.append(inv)
                        continue
                except (ValueError, TypeError):
                    pass
            others.append(inv)

        # Sort both lists by id descending (most recent first)
        amount_matched.sort(key=lambda i: i["id"], reverse=True)
        others.sort(key=lambda i: i["id"], reverse=True)

        # Combine: amount-matched first, then others
        ranked = amount_matched + others

        # Return at most 3 invoice IDs to limit retries
        return [inv["id"] for inv in ranked[:3]]
