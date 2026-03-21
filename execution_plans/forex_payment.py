"""Execution plan: Forex Payment (Tier 3).

Full flow: find/create customer → create product → create order → create invoice (EUR)
→ look up ledger accounts → register payment at invoice rate
→ post forex difference voucher (agio/disagio) to account 8060 or 8070.
"""
from datetime import date, timedelta

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

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

        # --- Step 1: Find or create customer ---
        create_body = {"name": customer_name}
        if org_number:
            create_body["organizationNumber"] = org_number

        customer_id = self._find_or_create(
            client,
            search_path="/customer",
            search_params={"organizationNumber": org_number} if org_number else {"name": customer_name, "count": 1},
            create_path="/customer",
            create_body=create_body,
        )
        api_calls += 2  # search + create (or search only if found)

        self._check_timeout(start_time)

        # --- Step 2: Look up EUR currency ID ---
        currency_result = client.get("/currency", params={"code": "EUR"})
        api_calls += 1
        if not currency_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up EUR currency: "
                f"status={currency_result.get('status_code')}, error={currency_result.get('error')}"
            )
        eur_values = currency_result["body"].get("values", [])
        if not eur_values:
            raise RuntimeError("EUR currency not found in /currency response")
        eur_currency_id = eur_values[0]["id"]

        self._check_timeout(start_time)

        # --- Step 3: Look up ledger account IDs (1500, 1920, 8060 or 8070) ---
        # Always look up 1500 (AR) and the relevant forex account
        ar_result = client.get("/ledger/account", params={"number": 1500, "count": 1})
        api_calls += 1
        if not ar_result["success"] or not ar_result["body"].get("values"):
            api_errors += 1
            raise RuntimeError("Failed to look up account 1500 (Kundefordringer)")
        ar_account_id = ar_result["body"]["values"][0]["id"]

        self._check_timeout(start_time)

        forex_account_number = 8070 if is_gain else 8060
        forex_result = client.get("/ledger/account", params={"number": forex_account_number, "count": 1})
        api_calls += 1
        if not forex_result["success"] or not forex_result["body"].get("values"):
            # Account may not exist — create it
            create_account_name = "Valutagevinst" if is_gain else "Valutatap"
            create_acct_result = client.post(
                "/ledger/account",
                body={"number": forex_account_number, "name": create_account_name},
            )
            api_calls += 1
            if not create_acct_result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to find or create account {forex_account_number}: "
                    f"status={create_acct_result.get('status_code')}, error={create_acct_result.get('error')}"
                )
            forex_account_id = create_acct_result["body"]["value"]["id"]
        else:
            forex_account_id = forex_result["body"]["values"][0]["id"]

        self._check_timeout(start_time)

        # --- Step 4: Find or create product (minimal — no vatType) ---
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
                raise RuntimeError(
                    f"Failed to create product: "
                    f"status={product_result.get('status_code')}, error={product_result.get('error')}"
                )
            product_id = product_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 5: Create order in EUR ---
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
            raise RuntimeError(
                f"Failed to create order: "
                f"status={order_result.get('status_code')}, error={order_result.get('error')}"
            )
        order_id = order_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 6: Create invoice in EUR ---
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
            raise RuntimeError(
                f"Failed to create invoice: "
                f"status={invoice_result.get('status_code')}, error={invoice_result.get('error')}"
            )
        invoice_id = invoice_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 7: Register payment at invoice rate (NOK) ---
        # Look up payment type
        pt_result = client.get("/invoice/paymentType")
        api_calls += 1
        payment_type_id = 1  # fallback
        if pt_result["success"]:
            types = pt_result["body"].get("values", [])
            if types:
                payment_type_id = types[0]["id"]

        # paidAmount = NOK equivalent at invoice_rate
        # paidAmountCurrency = EUR amount (currency of the invoice)
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
            raise RuntimeError(
                f"Failed to register payment for invoice {invoice_id}: "
                f"status={payment_result.get('status_code')}, error={payment_result.get('error')}"
            )

        self._check_timeout(start_time)

        # --- Step 8: Post forex difference voucher ---
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
                    "row": 1,
                    "description": "Agio valutagevinst",
                },
                {
                    "account": {"id": forex_account_id},
                    "amount": -abs_diff,
                    "amountCurrency": -abs_diff,
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
                    "row": 1,
                    "description": "Disagio valutatap",
                },
                {
                    "account": {"id": ar_account_id},
                    "customer": {"id": customer_id},
                    "amount": -abs_diff,
                    "amountCurrency": -abs_diff,
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
            raise RuntimeError(
                f"Failed to post forex voucher: "
                f"status={voucher_result.get('status_code')}, error={voucher_result.get('error')}"
            )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
