"""Execution plan: Overdue Invoice Reminder (Tier 2/3).

Sequence:
  1. GET /invoice?invoiceDateFrom=<1yr ago>  → find overdue invoice (past due, unpaid)
  2. GET /ledger/account?number=1500         → accounts receivable account ID
  3. GET /ledger/account?number=3400         → reminder fee income account ID
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

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "customer_name": "string|null — customer name to narrow invoice search",
    "org_number": "string|null — organisation number of the customer",
    "reminder_fee": "number — reminder fee amount in NOK (e.g. 100.0)",
    "debit_account": "number — ledger account to debit (always 1500 for accounts receivable)",
    "credit_account": "number — ledger account to credit (always 3400 for reminder fee income)",
    "register_payment": "boolean — true if the prompt also asks to register payment on the overdue invoice",
    "payment_date": "string|null — YYYY-MM-DD payment date (required if register_payment is true)",
    "paid_amount": "number|null — amount paid in NOK (required if register_payment is true)",
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
        one_year_ago = (today - datetime.timedelta(days=365)).isoformat()

        api_calls = 0
        api_errors = 0

        reminder_fee = params["reminder_fee"]
        debit_account_number = params.get("debit_account", 1500)
        credit_account_number = params.get("credit_account", 3400)

        # ------------------------------------------------------------------
        # Step 1: Find the overdue invoice
        # ------------------------------------------------------------------
        search_params: dict = {
            "invoiceDateFrom": one_year_ago,
            "invoiceDateTo": today_str,
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
            raise RuntimeError(
                f"Failed to search invoices: "
                f"status={invoice_result.get('status_code')}, error={invoice_result.get('error')}"
            )

        invoices = invoice_result["body"].get("values", [])
        if not invoices:
            raise RuntimeError(
                f"No invoices found in the past year"
                + (f" for customerId={customer_id}" if customer_id else "")
            )

        # Identify overdue invoice: past due date and not paid (pick most overdue)
        overdue_invoice = self._pick_overdue_invoice(invoices, today)
        overdue_invoice_id: int = overdue_invoice["id"]

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 2: Look up ledger account IDs
        # ------------------------------------------------------------------
        acct_1500_result = client.get(
            "/ledger/account", params={"number": str(debit_account_number)}
        )
        api_calls += 1
        if not acct_1500_result["success"] or not acct_1500_result["body"].get("values"):
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up account {debit_account_number}: "
                f"status={acct_1500_result.get('status_code')}, "
                f"error={acct_1500_result.get('error')}"
            )
        debit_account_id: int = acct_1500_result["body"]["values"][0]["id"]

        acct_3400_result = client.get(
            "/ledger/account", params={"number": str(credit_account_number)}
        )
        api_calls += 1
        if not acct_3400_result["success"] or not acct_3400_result["body"].get("values"):
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up account {credit_account_number}: "
                f"status={acct_3400_result.get('status_code')}, "
                f"error={acct_3400_result.get('error')}"
            )
        credit_account_id: int = acct_3400_result["body"]["values"][0]["id"]

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
            raise RuntimeError(
                f"Failed to post reminder fee voucher: "
                f"status={voucher_result.get('status_code')}, "
                f"error={voucher_result.get('error')}"
            )

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
                raise RuntimeError(
                    "Cannot create reminder invoice: unable to determine customer ID"
                )

        # Create a reminder product on the fly
        product_result = client.post(
            "/product",
            body={
                "name": "Purregebyr",
                "priceExcludingVatCurrency": reminder_fee,
            },
        )
        api_calls += 1
        if not product_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to create reminder fee product: "
                f"status={product_result.get('status_code')}, "
                f"error={product_result.get('error')}"
            )
        product_id: int = product_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # Create order with the reminder fee as an order line
        order_result = client.post(
            "/order",
            body={
                "customer": {"id": customer_id},
                "orderDate": today_str,
                "orderLines": [
                    {
                        "product": {"id": product_id},
                        "count": 1,
                        "unitPriceExcludingVatCurrency": reminder_fee,
                    }
                ],
            },
        )
        api_calls += 1
        if not order_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to create reminder order: "
                f"status={order_result.get('status_code')}, "
                f"error={order_result.get('error')}"
            )
        order_id: int = order_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # Create the invoice from the order
        invoice_due_date = (today + datetime.timedelta(days=14)).isoformat()
        reminder_invoice_result = client.post(
            "/invoice",
            body={
                "invoiceDate": today_str,
                "invoiceDueDate": invoice_due_date,
                "orders": [{"id": order_id}],
            },
        )
        api_calls += 1
        if not reminder_invoice_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to create reminder invoice: "
                f"status={reminder_invoice_result.get('status_code')}, "
                f"error={reminder_invoice_result.get('error')}"
            )
        reminder_invoice_id: int = reminder_invoice_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 5: Send the reminder invoice — EMAIL with fallback to MANUAL
        # ------------------------------------------------------------------
        send_result = client.put(
            f"/invoice/{reminder_invoice_id}/:send",
            body={"sendType": "EMAIL"},
        )
        api_calls += 1
        if not send_result["success"] and send_result.get("status_code") == 422:
            # Fallback: send as MANUAL
            send_result = client.put(
                f"/invoice/{reminder_invoice_id}/:send",
                body={"sendType": "MANUAL"},
            )
            api_calls += 1
        if not send_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to send reminder invoice {reminder_invoice_id}: "
                f"status={send_result.get('status_code')}, "
                f"error={send_result.get('error')}"
            )

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 6 (optional): Register payment on the original overdue invoice
        # ------------------------------------------------------------------
        if params.get("register_payment"):
            payment_date = params.get("payment_date") or today_str
            paid_amount = params.get("paid_amount") or overdue_invoice.get(
                "amountExcludingVatCurrency", 0
            )
            payment_result = client.put(
                f"/invoice/{overdue_invoice_id}/:payment",
                params={
                    "paymentDate": payment_date,
                    "paymentTypeId": 1,  # bank transfer
                    "paidAmount": paid_amount,
                    "paidAmountCurrency": paid_amount,
                },
            )
            api_calls += 1
            if not payment_result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to register payment for overdue invoice {overdue_invoice_id}: "
                    f"status={payment_result.get('status_code')}, "
                    f"error={payment_result.get('error')}"
                )

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
