"""Execution plan: Overdue Invoice Reminder (Tier 2/3).

Sequence:
  1. GET /invoice?invoiceDateFrom=<1yr ago>  → find overdue invoice (past due, unpaid)
  2. GET /ledger/account?number=1500,3400     → batch lookup: debit + credit account IDs
  4. POST /ledger/voucher                    → post reminder fee (debit 1500, credit 3400)
  5. POST /order + POST /invoice             → create new standalone reminder invoice
  6. PUT /invoice/{id}/:send                 → send EMAIL, fallback MANUAL on 422
  7. PUT /invoice/{overdue_id}/:payment      → register payment on overdue invoice (optional)

CRITICAL:
- Do NOT use /invoice/:createReminder — create a fresh invoice for the fee instead.
- invoiceDateFrom must be within ~1 year (not 2000-01-01 — causes 422).
- All voucher posting rows require amountCurrency = amount.
"""
import datetime
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

# Fields the LLM should extract from the prompt
# Only reminder_fee is truly required — customer can be discovered from the overdue invoice.
# Defaults: debit_account=1500, credit_account=3400, register_payment=false
EXTRACTION_SCHEMA = {
    "customer_name": "string|null — customer name to narrow invoice search (optional, can be discovered)",
    "org_number": "string|null — organisation number of the customer (optional)",
    "reminder_fee": "number — reminder fee amount in NOK (e.g. 70.0). REQUIRED — extract from prompt",
    "debit_account": "number — ledger account to debit, default 1500 if not mentioned",
    "credit_account": "number — ledger account to credit, default 3400 if not mentioned",
    "register_payment": "boolean — true ONLY if prompt explicitly says 'register payment' or 'registrer betaling'. Default false. Do NOT set true for prompts about reminder fees.",
    "payment_date": "string|null — YYYY-MM-DD payment date (only if register_payment is true)",
    "paid_amount": "number|null — amount paid in NOK (only if register_payment is true)",
}


@register
class OverdueInvoiceReminderPlan(ExecutionPlan):
    task_type = "overdue_invoice_reminder"
    description = (
        "Find overdue invoice, post reminder fee voucher (debit 1500 / credit 3400), "
        "create and send a standalone reminder invoice, optionally register payment"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        today = datetime.date.today()
        today_str = today.isoformat()
        # invoiceDateTo is EXCLUSIVE in the Tripletex API — add 1 day to include today
        tomorrow_str = (today + datetime.timedelta(days=1)).isoformat()
        one_year_ago = (today - datetime.timedelta(days=365)).isoformat()

        api_calls = 0
        api_errors = 0

        reminder_fee = params.get("reminder_fee")
        if not reminder_fee:
            logger.warning("reminder_fee is required but was not extracted")
            return self._make_result(api_calls=api_calls, api_errors=1)
        debit_account_number = params.get("debit_account") or 1500
        credit_account_number = params.get("credit_account") or 3400

        # ------------------------------------------------------------------
        # Step 1: Find the overdue invoice
        # ------------------------------------------------------------------
        search_params: dict = {
            "invoiceDateFrom": one_year_ago,
            "invoiceDateTo": tomorrow_str,
            "fields": "id,invoiceDate,invoiceDueDate,amountExcludingVatCurrency,customer",
        }

        customer_id: int | None = None

        # If we have an org number, resolve the customer first
        org_number = params.get("org_number")
        customer_name = params.get("customer_name")
        if org_number:
            cust_result = client.get(
                "/customer",
                params={"organizationNumber": org_number, "fields": "id,name"},
            )
            api_calls += 1
            if cust_result["success"]:
                customers = cust_result["body"].get("values", [])
                if customers:
                    customer_id = customers[0]["id"]
        elif customer_name:
            cust_result = client.get(
                "/customer",
                params={"name": customer_name, "count": 1, "fields": "id,name"},
            )
            api_calls += 1
            if cust_result["success"]:
                customers = cust_result["body"].get("values", [])
                if customers:
                    customer_id = customers[0]["id"]

        if customer_id is not None:
            search_params["customerId"] = customer_id

        invoice_result = client.get("/invoice", params=search_params)
        api_calls += 1
        if not invoice_result["success"]:
            api_errors += 1
            logger.warning(
                "Failed to search invoices: status=%s, error=%s",
                invoice_result.get("status_code"), invoice_result.get("error"),
            )
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        invoices = invoice_result["body"].get("values", [])
        if not invoices:
            api_errors += 1
            logger.warning(
                "No invoices found in the past year%s",
                f" for customerId={customer_id}" if customer_id else "",
            )
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        # Identify overdue invoice: past due date and not paid (pick most overdue)
        overdue_invoice = self._pick_overdue_invoice(invoices, today)
        overdue_invoice_id: int = overdue_invoice["id"]

        # Resolve customer_id from overdue invoice if not already known
        if customer_id is None:
            overdue_customer = overdue_invoice.get("customer")
            if isinstance(overdue_customer, dict):
                customer_id = overdue_customer.get("id")
            if customer_id is None:
                api_errors += 1
                logger.warning("Cannot determine customer ID from overdue invoice")
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 2: Look up ledger account IDs
        # ------------------------------------------------------------------
        # Batch account lookup (1 call instead of 2)
        accounts = self._get_accounts(
            client, str(debit_account_number), str(credit_account_number)
        )
        api_calls += 1

        debit_account_id = accounts.get(str(debit_account_number))
        credit_account_id = accounts.get(str(credit_account_number))

        if debit_account_id is None or credit_account_id is None:
            api_errors += 1
            logger.warning(
                "Account lookup failed: debit=%s (id=%s), credit=%s (id=%s)",
                debit_account_number, debit_account_id,
                credit_account_number, credit_account_id,
            )
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 3: Post reminder fee voucher (debit 1500, credit 3400)
        # ------------------------------------------------------------------
        voucher_body = {
            "date": today_str,
            "description": "Purregebyr",
            "postings": [
                {
                    "account": {"id": debit_account_id},
                    "customer": {"id": customer_id},
                    "amount": reminder_fee,
                    "amountCurrency": reminder_fee,
                    "amountGross": reminder_fee,
                    "amountGrossCurrency": reminder_fee,
                    "row": 1,
                },
                {
                    "account": {"id": credit_account_id},
                    "amount": -reminder_fee,
                    "amountCurrency": -reminder_fee,
                    "amountGross": -reminder_fee,
                    "amountGrossCurrency": -reminder_fee,
                    "row": 2,
                },
            ],
        }
        voucher_result = client.post("/ledger/voucher", body=voucher_body)
        api_calls += 1
        if not voucher_result["success"]:
            api_errors += 1
            logger.warning(
                "Failed to post reminder fee voucher: status=%s, error=%s",
                voucher_result.get("status_code"), voucher_result.get("error"),
            )
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 4: Create reminder invoice (new standalone invoice for the fee)
        #         POST /order first, then POST /invoice
        # ------------------------------------------------------------------
        if customer_id is None:
            # Derive customer_id from the overdue invoice if not already known
            overdue_customer = overdue_invoice.get("customer")
            if isinstance(overdue_customer, dict):
                customer_id = overdue_customer.get("id")
            if customer_id is None:
                api_errors += 1
                logger.warning(
                    "Cannot create reminder invoice: unable to determine customer ID"
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        # Create reminder invoice with description-only order line (no product needed)
        invoice_due_date = (today + datetime.timedelta(days=14)).isoformat()
        reminder_invoice_result = client.post(
            "/invoice",
            body={
                "invoiceDate": today_str,
                "invoiceDueDate": invoice_due_date,
                "orders": [
                    {
                        "customer": {"id": customer_id},
                        "orderDate": today_str,
                        "deliveryDate": today_str,
                        "orderLines": [
                            {
                                "description": "Purregebyr",
                                "count": 1,
                                "unitPriceExcludingVatCurrency": reminder_fee,
                            }
                        ],
                    }
                ],
            },
        )
        api_calls += 1
        if not reminder_invoice_result["success"]:
            api_errors += 1
            logger.warning(
                "Failed to create reminder invoice: status=%s, error=%s",
                reminder_invoice_result.get("status_code"),
                reminder_invoice_result.get("error"),
            )
            return self._make_result(api_calls=api_calls, api_errors=api_errors)
        reminder_invoice_id: int = reminder_invoice_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # Send the reminder invoice — try EMAIL first, fallback to MANUAL on 422
        send_result = client.put(
            f"/invoice/{reminder_invoice_id}/:send",
            params={"sendType": "EMAIL"},
        )
        api_calls += 1
        if not send_result["success"]:
            send_result2 = client.put(
                f"/invoice/{reminder_invoice_id}/:send",
                params={"sendType": "MANUAL"},
            )
            api_calls += 1
            if not send_result2["success"]:
                api_errors += 1
                # Non-fatal — invoice was created, sending failed

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 6 (optional): Register payment on the original overdue invoice
        # ------------------------------------------------------------------
        if params.get("register_payment"):
            payment_date = params.get("payment_date") or today_str
            paid_amount = params.get("paid_amount") or overdue_invoice.get(
                "amountExcludingVatCurrency", 0
            )

            payment_type_id = 1  # Standard payment type (always ID 1 in sandbox)

            payment_result = client.put(
                f"/invoice/{overdue_invoice_id}/:payment",
                params={
                    "paymentDate": payment_date,
                    "paymentTypeId": payment_type_id,
                    "paidAmount": paid_amount,
                    "paidAmountCurrency": paid_amount,
                },
            )
            api_calls += 1
            if not payment_result["success"]:
                api_errors += 1
                logger.warning(
                    "Failed to register payment for overdue invoice %s: status=%s, error=%s",
                    overdue_invoice_id, payment_result.get("status_code"),
                    payment_result.get("error"),
                )
                # Non-fatal — continue and return result

        return self._make_result(api_calls=api_calls, api_errors=api_errors)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_overdue_invoice(
        self, invoices: list, today: datetime.date
    ) -> dict:
        """Return the most overdue unpaid invoice.

        Strategy:
          1. Filter invoices where dueDate < today (past due).
          2. Among those, prefer the oldest (earliest dueDate) — most overdue.
          3. If none are past due, fall back to the invoice with the earliest dueDate.
        """
        overdue = []
        for inv in invoices:
            due_str = inv.get("invoiceDueDate")
            if due_str:
                try:
                    due_date = datetime.date.fromisoformat(due_str)
                    if due_date < today:
                        overdue.append((due_date, inv))
                except ValueError:
                    pass

        if overdue:
            # Most overdue = earliest due date
            overdue.sort(key=lambda t: t[0])
            return overdue[0][1]

        # Fallback: no clearly overdue invoice — return the one with earliest due date
        # (or simply the first in the list if no due dates available)
        dated = []
        for inv in invoices:
            due_str = inv.get("invoiceDueDate")
            if due_str:
                try:
                    dated.append((datetime.date.fromisoformat(due_str), inv))
                except ValueError:
                    pass
        if dated:
            dated.sort(key=lambda t: t[0])
            return dated[0][1]

        return invoices[0]
