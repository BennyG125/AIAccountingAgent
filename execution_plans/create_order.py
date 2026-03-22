"""Execution plan: Create Order → Invoice → Payment (Tier 2)."""
import logging
from datetime import date, timedelta

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    "customer_name": "string — customer/company name",
    "org_number": "string|null — organization number",
    "products": "array of {name: string, number: int|null, price: number} — each product with name, product number (in parentheses), and price excl. VAT in NOK",
    "register_payment": "boolean — true if prompt says to register payment",
}


@register
class CreateOrderPlan(ExecutionPlan):
    task_type = "create_order"
    description = "Create order: customer, products, order, invoice, payment"

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        today = date.today().isoformat()
        due_date = (date.today() + timedelta(days=30)).isoformat()
        api_calls = 0
        api_errors = 0

        # --- Step 1: Find or create customer ---
        customer_name = params["customer_name"]
        org_number = params.get("org_number")

        customer_id = self._find_or_create(
            client,
            search_path="/customer",
            search_params={"organizationNumber": org_number} if org_number else {"name": customer_name},
            create_path="/customer",
            create_body={
                "name": customer_name,
                **({"organizationNumber": org_number} if org_number else {}),
            },
        )
        api_calls += 2
        if customer_id is None:
            api_errors += 1
            logger.warning("Failed to find or create customer '%s'", customer_name)
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 2: Create products ---
        products = params.get("products", [])
        product_ids = []

        # Try bulk create first
        products_body = []
        for p in products:
            body = {
                "name": p["name"],
                "priceExcludingVatCurrency": p["price"],
            }
            if p.get("number"):
                body["number"] = p["number"]
            products_body.append(body)

        if len(products_body) > 1:
            bulk_result = client.post("/product/list", body=products_body)
            api_calls += 1
            if bulk_result["success"]:
                for prod in bulk_result["body"].get("values", []):
                    product_ids.append(prod["id"])

        if not product_ids:
            # Fallback: create individually
            for i, product in enumerate(products):
                self._check_timeout(start_time)
                body = {
                    "name": product["name"],
                    "priceExcludingVatCurrency": product["price"],
                }
                if product.get("number"):
                    body["number"] = product["number"]

                result = client.post("/product", body=body)
                api_calls += 1

                if not result["success"]:
                    # Product number might be in use — find existing
                    pnum = product.get("number")
                    if pnum:
                        find_result = client.get("/product", params={"number": str(pnum)})
                        api_calls += 1
                        if find_result["success"]:
                            values = find_result["body"].get("values", [])
                            if values:
                                product_ids.append(values[0]["id"])
                                continue
                    # Try by name
                    find_result = client.get("/product", params={"name": product["name"]})
                    api_calls += 1
                    if find_result["success"]:
                        values = find_result["body"].get("values", [])
                        if values:
                            product_ids.append(values[0]["id"])
                            continue
                    api_errors += 1
                    # Skip this product rather than failing the whole plan
                    continue
                else:
                    product_ids.append(result["body"]["value"]["id"])

        self._check_timeout(start_time)

        # --- Step 3: Create order with inline orderLines ---
        order_lines = []
        for i, product in enumerate(products):
            if i >= len(product_ids):
                break
            order_lines.append({
                "product": {"id": product_ids[i]},
                "count": product.get("count", 1),
                "unitPriceExcludingVatCurrency": product["price"],
            })

        order_result = client.post("/order", body={
            "customer": {"id": customer_id},
            "orderDate": today,
            "deliveryDate": today,
            "orderLines": order_lines,
        })
        api_calls += 1
        if not order_result["success"]:
            api_errors += 1
            logger.warning("Failed to create order: %s", order_result.get('error'))
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        order_id = order_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 4: Create invoice from order ---
        invoice_result = client.post("/invoice", body={
            "invoiceDate": today,
            "invoiceDueDate": due_date,
            "orders": [{"id": order_id}],
        })
        api_calls += 1
        if not invoice_result["success"]:
            api_errors += 1
            logger.warning("Failed to create invoice: %s", invoice_result.get('error'))
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        invoice_id = invoice_result["body"]["value"]["id"]
        invoice_amount = invoice_result["body"]["value"].get("amount", 0)

        self._check_timeout(start_time)

        # --- Step 5: Register payment (if requested) ---
        if params.get("register_payment", True):
            # Get payment type
            pt_result = client.get("/invoice/paymentType", params={"fields": "*"})
            api_calls += 1
            payment_type_id = 1
            if pt_result["success"]:
                values = pt_result["body"].get("values", [])
                if values:
                    payment_type_id = values[0]["id"]

            # Register full payment
            pay_result = client.put(
                f"/invoice/{invoice_id}/:payment",
                params={
                    "paymentDate": today,
                    "paymentTypeId": str(payment_type_id),
                    "paidAmount": str(invoice_amount),
                    "paidAmountCurrency": "1",
                },
            )
            api_calls += 1
            if not pay_result["success"]:
                api_errors += 1

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
