"""Execution plan: Register Payment (Tier 2).

Full flow: find/create customer → create product → create order → create invoice
→ register payment via PUT /invoice/{id}/:payment with query params.
"""
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

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)
        api_calls = 0

        # --- Step 1: Find or create customer ---
        customer_name = params["customer_name"]
        org_number = params.get("org_number")

        create_body = {"name": customer_name}
        if org_number:
            create_body["organizationNumber"] = org_number

        customer_id = self._find_or_create(
            client,
            search_path="/customer",
            search_params={"name": customer_name, "count": 1},
            create_path="/customer",
            create_body=create_body,
        )
        api_calls += 2  # search + create (or just search if found)

        self._check_timeout(start_time)

        # --- Step 2: Create product (NEVER include vatType) ---
        product_body = {
            "name": params["product_name"],
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

        # --- Step 3: Create order with embedded order lines ---
        quantity = params.get("quantity", 1)
        order_body = {
            "customer": {"id": customer_id},
            "orderDate": params["payment_date"],
            "orderLines": [
                {
                    "product": {"id": product_id},
                    "count": quantity,
                    "unitPriceExcludingVatCurrency": params["price"],
                }
            ],
        }
        order_result = client.post("/order", body=order_body)
        api_calls += 1
        if not order_result["success"]:
            raise RuntimeError(
                f"Failed to create order: "
                f"status={order_result.get('status_code')}, "
                f"error={order_result.get('error')}"
            )
        order_id = order_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 4: Create invoice from order ---
        invoice_result = client.put(
            f"/order/{order_id}/:invoice",
            params={"invoiceDate": params["payment_date"]},
        )
        api_calls += 1
        if not invoice_result["success"]:
            raise RuntimeError(
                f"Failed to create invoice from order {order_id}: "
                f"status={invoice_result.get('status_code')}, "
                f"error={invoice_result.get('error')}"
            )
        invoice_id = invoice_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 5: Register payment via query params (NOT body) ---
        # paymentTypeId=1 is bank transfer — reliable, no lookup needed
        payment_result = client.put(
            f"/invoice/{invoice_id}/:payment",
            params={
                "paymentDate": params["payment_date"],
                "paymentTypeId": 1,
                "paidAmount": params["paid_amount"],
                "paidAmountCurrency": params["paid_amount"],
            },
        )
        api_calls += 1
        if not payment_result["success"]:
            raise RuntimeError(
                f"Failed to register payment for invoice {invoice_id}: "
                f"status={payment_result.get('status_code')}, "
                f"error={payment_result.get('error')}"
            )

        return self._make_result(api_calls=api_calls, api_errors=0)
