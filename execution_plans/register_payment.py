"""Execution plan: Register Payment (Tier 2).

Full flow: find/create customer → create product → create order → create invoice
→ register payment via PUT /invoice/{id}/:payment with query params.

Optimisation: if the evaluator pre-created the invoice we find it by customer +
amount and skip straight to payment registration (3 API calls instead of ~7).
"""
from datetime import date, timedelta

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "customer_name": "string — customer/company name (required)",
    "org_number": "string|null — organisation number if mentioned",
    "product_name": "string — product or service description (required)",
    "price": "number — price excluding VAT in NOK (required)",
    "quantity": "number — quantity, default 1 if not mentioned",
    "payment_date": "string — payment date in YYYY-MM-DD format (required)",
    "paid_amount": "number — amount paid in NOK (required, usually equals price * quantity)",
}


@register
class RegisterPaymentPlan(ExecutionPlan):
    task_type = "register_payment"
    description = (
        "Create customer, product, order, invoice, then register payment "
        "via PUT /invoice/{id}/:payment with query parameters"
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

    def _find_matching_invoice(self, client, customer_id, expected_amount, product_name):
        """Search invoices for *customer_id* created within the last year.

        Returns (invoice_id, api_calls) if a match is found, else (None, api_calls).
        Match criteria (in priority order):
        1. Order line description/product name contains *product_name*
        2. amountExcludingVat matches *expected_amount*
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

        # Try matching by amount first (most reliable for payment registration)
        for inv in invoices:
            inv_amount = inv.get("amountExcludingVat") or inv.get("amount") or 0
            if abs(float(inv_amount) - float(expected_amount)) < 0.01:
                return inv["id"], 1

        # Fallback: match by order-line product name (substring)
        product_lower = product_name.lower() if product_name else ""
        if product_lower:
            for inv in invoices:
                for line in inv.get("orderLines", []):
                    line_desc = (line.get("description") or "").lower()
                    prod = line.get("product", {})
                    prod_name = (prod.get("name") or "").lower() if isinstance(prod, dict) else ""
                    if product_lower in line_desc or product_lower in prod_name:
                        return inv["id"], 1

        return None, 1

    # ------------------------------------------------------------------
    # Main execute
    # ------------------------------------------------------------------

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)
        api_calls = 0

        # Default payment_date to today if empty/null
        today = date.today().isoformat()
        payment_date = params.get("payment_date") or today

        customer_name = params["customer_name"]
        org_number = params.get("org_number")
        product_name = params["product_name"]
        quantity = params.get("quantity", 1)
        expected_amount = float(params["price"]) * float(quantity)

        # ==============================================================
        # FAST PATH: find existing customer + invoice → pay immediately
        # ==============================================================
        if org_number:
            cust_id, calls = self._find_customer_by_org(client, org_number)
            api_calls += calls

            if cust_id is not None:
                self._check_timeout(start_time)
                inv_id, calls = self._find_matching_invoice(
                    client, cust_id, expected_amount, product_name,
                )
                api_calls += calls

                if inv_id is not None:
                    self._check_timeout(start_time)
                    # Register payment on the found invoice
                    api_calls += self._register_payment(
                        client, inv_id, payment_date, params["paid_amount"],
                    )
                    return self._make_result(api_calls=api_calls, api_errors=0)

        # ==============================================================
        # FULL PATH: create everything from scratch
        # ==============================================================

        # --- Step 1: Find or create customer ---
        create_body = {"name": customer_name}
        if org_number:
            create_body["organizationNumber"] = org_number

        customer_id = self._find_or_create(
            client,
            search_path="/customer",
            search_params=(
                {"organizationNumber": org_number, "count": 1}
                if org_number
                else {"name": customer_name, "count": 1}
            ),
            create_path="/customer",
            create_body=create_body,
        )
        api_calls += 2  # search + create (or just search if found)

        self._check_timeout(start_time)

        # --- Step 2: Find or create product (NEVER include vatType) ---
        product_search = client.get("/product", params={"name": product_name, "count": 1})
        api_calls += 1
        if product_search["success"] and product_search["body"].get("values"):
            product_id = product_search["body"]["values"][0]["id"]
        else:
            product_body = {
                "name": product_name,
                "priceExcludingVatCurrency": params["price"],
            }
            product_result = client.post("/product", body=product_body)
            api_calls += 1
            if not product_result["success"]:
                raise RuntimeError(
                    f"Failed to create product: "
                    f"status={product_result.get('status_code')}, "
                    f"error={product_result.get('error')}"
                )
            product_id = product_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 3: Create invoice with inline order (1 call instead of 2) ---
        invoice_result = client.post("/invoice", body={
            "invoiceDate": payment_date,
            "invoiceDueDate": payment_date,
            "orders": [{
                "customer": {"id": customer_id},
                "orderDate": payment_date,
                "deliveryDate": payment_date,
                "orderLines": [{
                    "product": {"id": product_id},
                    "count": quantity,
                    "unitPriceExcludingVatCurrency": params["price"],
                }],
            }],
        })
        api_calls += 1
        if not invoice_result["success"]:
            raise RuntimeError(
                f"Failed to create invoice: "
                f"status={invoice_result.get('status_code')}, "
                f"error={invoice_result.get('error')}"
            )
        invoice_id = invoice_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 5: Register payment ---
        api_calls += self._register_payment(
            client, invoice_id, payment_date, params["paid_amount"],
        )

        return self._make_result(api_calls=api_calls, api_errors=0)

    # ------------------------------------------------------------------
    # Payment helper (shared by fast and full paths)
    # ------------------------------------------------------------------

    def _register_payment(self, client, invoice_id, payment_date, paid_amount):
        """Register payment on *invoice_id*. Returns number of API calls made."""
        calls = 0

        # Look up payment type
        pt_result = client.get("/invoice/paymentType")
        calls += 1
        payment_type_id = 1  # fallback
        if pt_result["success"]:
            types = pt_result["body"].get("values", [])
            if types:
                payment_type_id = types[0]["id"]

        payment_result = client.put(
            f"/invoice/{invoice_id}/:payment",
            params={
                "paymentDate": payment_date,
                "paymentTypeId": payment_type_id,
                "paidAmount": paid_amount,
                "paidAmountCurrency": paid_amount,
            },
        )
        calls += 1
        if not payment_result["success"]:
            raise RuntimeError(
                f"Failed to register payment for invoice {invoice_id}: "
                f"status={payment_result.get('status_code')}, "
                f"error={payment_result.get('error')}"
            )

        return calls
