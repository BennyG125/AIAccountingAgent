"""Execution plan: Forex Payment (Tier 3).

Full flow: find/create customer → create product → create order → create invoice (EUR)
→ look up ledger accounts → register payment at invoice rate
→ post forex difference voucher (agio/disagio) to account 8060 or 8070.

Optimisation: if the evaluator pre-created the invoice we find it by customer +
EUR amount and skip straight to payment + forex voucher.
"""
import logging
from datetime import date, timedelta

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "customer_name": "string — customer/company name (required)",
    "customer_org": "string|null — Norwegian organisation number if mentioned",
    "eur_amount": "number — invoice amount in EUR (required)",
    "invoice_rate": "number — NOK/EUR exchange rate when invoice was issued (required)",
    "payment_rate": "number — NOK/EUR exchange rate when customer paid (required)",
    "description": "string|null — product/service description, default 'EUR Invoice' if not specified",
}


@register
class ForexPaymentPlan(ExecutionPlan):
    task_type = "forex_payment"
    description = (
        "Create EUR invoice, register payment at invoice rate, "
        "post forex difference voucher (agio/disagio) to account 8060 or 8070"
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_customer_by_org(self, client, org_number):
        """Search customer by organisation number. Returns (id, api_calls) or (None, api_calls)."""
        result = client.get("/customer", params={"organizationNumber": org_number, "count": 1})
        if result["success"] and result["body"].get("values"):
            return result["body"]["values"][0]["id"], 1
        return None, 1

    def _find_matching_invoice(self, client, customer_id, invoice_nok):
        """Search invoices for *customer_id* and match by NOK amount.

        The expected NOK amount on the invoice is eur_amount * invoice_rate.
        Returns (invoice_id, api_calls) if a match is found, else (None, api_calls).
        """
        date_from = (date.today() - timedelta(days=365)).isoformat()
        date_to = (date.today() + timedelta(days=1)).isoformat()

        result = client.get(
            "/invoice",
            params={
                "customerId": customer_id,
                "invoiceDateFrom": date_from,
                "invoiceDateTo": date_to,
                "count": 50,
            },
        )
        if not result["success"]:
            return None, 1

        invoices = result["body"].get("values", [])
        if not invoices:
            return None, 1

        # Match by amountExcludingVat (NOK) — the invoice was booked at invoice_rate
        for inv in invoices:
            inv_amount = inv.get("amountExcludingVat") or inv.get("amount") or 0
            if abs(float(inv_amount) - float(invoice_nok)) < 0.50:
                return inv["id"], 1

        return None, 1

    # ------------------------------------------------------------------
    # Main execute
    # ------------------------------------------------------------------

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        today = date.today().isoformat()
        due_date = (date.today() + timedelta(days=30)).isoformat()

        api_calls = 0
        api_errors = 0

        eur_amount = float(params["eur_amount"])
        invoice_rate = float(params["invoice_rate"])
        payment_rate = float(params["payment_rate"])
        customer_name = params["customer_name"]
        org_number = params.get("customer_org")
        description = params.get("description") or f"EUR Invoice {eur_amount}"

        # Pre-compute NOK amounts
        invoice_nok = round(eur_amount * invoice_rate, 2)
        payment_nok = round(eur_amount * payment_rate, 2)
        diff_nok = round(payment_nok - invoice_nok, 2)  # positive = gain, negative = loss
        abs_diff = abs(diff_nok)
        is_gain = diff_nok > 0

        # ==============================================================
        # FAST PATH: find existing customer + invoice → pay + forex voucher
        # ==============================================================
        found_invoice_id = None
        found_customer_id = None

        if org_number:
            cust_id, calls = self._find_customer_by_org(client, org_number)
            api_calls += calls

            if cust_id is not None:
                found_customer_id = cust_id
                self._check_timeout(start_time)

                inv_id, calls = self._find_matching_invoice(
                    client, cust_id, invoice_nok,
                )
                api_calls += calls

                if inv_id is not None:
                    found_invoice_id = inv_id

        # ==============================================================
        # If fast path found both, skip creation steps entirely
        # ==============================================================
        customer_id = None
        invoice_id = None

        if found_invoice_id is not None and found_customer_id is not None:
            customer_id = found_customer_id
            invoice_id = found_invoice_id
        else:
            # ==============================================================
            # FULL PATH: create everything from scratch
            # ==============================================================

            # --- Step 1: Find or create customer ---
            create_body = {"name": customer_name}
            if org_number:
                create_body["organizationNumber"] = org_number

            try:
                customer_id = self._find_or_create(
                    client,
                    search_path="/customer",
                    search_params=(
                        {"organizationNumber": org_number}
                        if org_number
                        else {"name": customer_name, "count": 1}
                    ),
                    create_path="/customer",
                    create_body=create_body,
                )
            except RuntimeError as e:
                api_errors += 1
                logger.warning("Failed to find or create customer: %s", e)
                return self._make_result(api_calls=api_calls + 2, api_errors=api_errors)
            api_calls += 2  # search + create (or search only if found)

            self._check_timeout(start_time)

            # --- Step 2: Look up EUR currency ID ---
            eur_currency_id = None
            currency_result = client.get("/currency", params={"code": "EUR"})
            api_calls += 1
            if not currency_result["success"]:
                api_errors += 1
                logger.warning(
                    "Failed to look up EUR currency: status=%s, error=%s",
                    currency_result.get("status_code"), currency_result.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            eur_values = currency_result["body"].get("values", [])
            if not eur_values:
                api_errors += 1
                logger.warning("EUR currency not found in /currency response")
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            eur_currency_id = eur_values[0]["id"]

            self._check_timeout(start_time)

            # --- Step 3: Find or create product (minimal — no vatType) ---
            product_id = None
            product_search = client.get(
                "/product", params={"name": description, "count": 1}
            )
            api_calls += 1
            if product_search["success"] and product_search["body"].get("values"):
                product_id = product_search["body"]["values"][0]["id"]
            else:
                product_result = client.post(
                    "/product",
                    body={
                        "name": description,
                        "priceExcludingVatCurrency": eur_amount,
                    },
                )
                api_calls += 1
                if not product_result["success"]:
                    api_errors += 1
                    logger.warning(
                        "Failed to create product: status=%s, error=%s",
                        product_result.get("status_code"), product_result.get("error"),
                    )
                    return self._make_result(api_calls=api_calls, api_errors=api_errors)
                product_id = product_result["body"]["value"]["id"]

            self._check_timeout(start_time)

            # --- Step 4: Create order in EUR ---
            order_result = client.post(
                "/order",
                body={
                    "customer": {"id": customer_id},
                    "orderDate": today,
                    "deliveryDate": today,
                    "currency": {"id": eur_currency_id},
                    "orderLines": [
                        {
                            "product": {"id": product_id},
                            "count": 1,
                            "unitPriceExcludingVatCurrency": eur_amount,
                        }
                    ],
                },
            )
            api_calls += 1
            if not order_result["success"]:
                api_errors += 1
                logger.warning(
                    "Failed to create order: status=%s, error=%s",
                    order_result.get("status_code"), order_result.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            order_id = order_result["body"]["value"]["id"]

            self._check_timeout(start_time)

            # --- Step 5: Create invoice in EUR ---
            invoice_result = client.post(
                "/invoice",
                body={
                    "invoiceDate": today,
                    "invoiceDueDate": due_date,
                    "orders": [{"id": order_id}],
                    "currency": {"id": eur_currency_id},
                },
            )
            api_calls += 1
            if not invoice_result["success"]:
                api_errors += 1
                logger.warning(
                    "Failed to create invoice: status=%s, error=%s",
                    invoice_result.get("status_code"), invoice_result.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            invoice_id = invoice_result["body"]["value"]["id"]

            self._check_timeout(start_time)

        # ==============================================================
        # SHARED: register payment + forex voucher (both paths converge)
        # ==============================================================

        # If we don't have customer_id or invoice_id at this point, bail out
        if customer_id is None or invoice_id is None:
            api_errors += 1
            logger.warning(
                "Missing customer_id=%s or invoice_id=%s — cannot proceed with payment",
                customer_id, invoice_id,
            )
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        # --- Batch look up ledger accounts (1500 + forex account) ---
        forex_account_number = str(8070 if is_gain else 8060)
        ar_account_id = None
        forex_account_id = None
        try:
            accounts = self._get_accounts(client, "1500", forex_account_number)
            api_calls += 1
            ar_account_id = accounts["1500"]
            forex_account_id = accounts[forex_account_number]
        except RuntimeError:
            # Forex account may not exist — look up 1500 individually, create forex
            api_calls += 1
            ar_result = client.get("/ledger/account", params={"number": "1500"})
            api_calls += 1
            if not ar_result["success"] or not ar_result["body"].get("values"):
                api_errors += 1
                logger.warning("Failed to look up account 1500")
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            ar_account_id = ar_result["body"]["values"][0]["id"]

            create_name = "Valutagevinst" if is_gain else "Valutatap"
            create_result = client.post(
                "/ledger/account",
                body={"number": int(forex_account_number), "name": create_name},
            )
            api_calls += 1
            if not create_result["success"]:
                api_errors += 1
                logger.warning("Failed to create account %s", forex_account_number)
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            forex_account_id = create_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Register payment at invoice rate (NOK) ---
        pt_result = client.get("/invoice/paymentType", params={"fields": "*"})
        api_calls += 1
        payment_type_id = 1  # fallback
        if pt_result["success"]:
            types = pt_result["body"].get("values", [])
            if types:
                payment_type_id = types[0]["id"]

        payment_result = client.put(
            f"/invoice/{invoice_id}/:payment",
            params={
                "paymentDate": today,
                "paymentTypeId": payment_type_id,
                "paidAmount": invoice_nok,
                "paidAmountCurrency": eur_amount,
            },
        )
        api_calls += 1
        if not payment_result["success"]:
            api_errors += 1
            logger.warning(
                "Failed to register payment for invoice %s: status=%s, error=%s",
                invoice_id, payment_result.get("status_code"), payment_result.get("error"),
            )
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Post forex difference voucher ---
        # Skip voucher if rates are identical (no difference)
        if abs_diff == 0.0:
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        if is_gain:
            # Agio (gain): debit 1500 (AR), credit 8070 (Valutagevinst)
            voucher_description = f"Valutagevinst (agio) - {customer_name} EUR {eur_amount}"
            postings = [
                {
                    "account": {"id": ar_account_id},
                    "customer": {"id": customer_id},
                    "amount": abs_diff,
                    "amountCurrency": abs_diff,
                    "amountGross": abs_diff,
                    "amountGrossCurrency": abs_diff,
                    "row": 1,
                    "description": "Agio valutagevinst",
                },
                {
                    "account": {"id": forex_account_id},
                    "amount": -abs_diff,
                    "amountCurrency": -abs_diff,
                    "amountGross": -abs_diff,
                    "amountGrossCurrency": -abs_diff,
                    "row": 2,
                    "description": "Agio valutagevinst",
                },
            ]
        else:
            # Disagio (loss): debit 8060 (Valutatap), credit 1500 (AR)
            voucher_description = f"Valutatap (disagio) - {customer_name} EUR {eur_amount}"
            postings = [
                {
                    "account": {"id": forex_account_id},
                    "amount": abs_diff,
                    "amountCurrency": abs_diff,
                    "amountGross": abs_diff,
                    "amountGrossCurrency": abs_diff,
                    "row": 1,
                    "description": "Disagio valutatap",
                },
                {
                    "account": {"id": ar_account_id},
                    "customer": {"id": customer_id},
                    "amount": -abs_diff,
                    "amountCurrency": -abs_diff,
                    "amountGross": -abs_diff,
                    "amountGrossCurrency": -abs_diff,
                    "row": 2,
                    "description": "Disagio valutatap",
                },
            ]

        voucher_result = client.post(
            "/ledger/voucher",
            body={
                "date": today,
                "description": voucher_description,
                "postings": postings,
            },
        )
        api_calls += 1
        if not voucher_result["success"]:
            api_errors += 1
            logger.warning(
                "Failed to post forex voucher: status=%s, error=%s",
                voucher_result.get("status_code"), voucher_result.get("error"),
            )
            # Non-fatal at this point — payment was registered, voucher failed

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
