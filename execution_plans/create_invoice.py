"""Execution plan: Create Invoice (Tier 2)."""
from datetime import date, timedelta

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "customer_name": "string — customer/company name (required)",
    "org_number": "string|null — organization number if provided",
    "products": "array of {name: string, price: number} — each product with name and price excl. VAT",
    "order_date": "string|null — YYYY-MM-DD, use today if not specified",
    "delivery_date": "string|null — YYYY-MM-DD, use today if not specified",
    "invoice_date": "string|null — YYYY-MM-DD, use today if not specified",
    "send_invoice": "boolean — true if prompt requests sending the invoice",
    "vat_rates": "array|null — list of distinct VAT rate percentages (e.g. [25, 12]) if multiple rates mentioned; null if only one rate",
}


@register
class CreateInvoicePlan(ExecutionPlan):
    task_type = "create_invoice"
    description = "Create invoice: find/create customer, create products, create order, create invoice, optionally send"

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        today = date.today().isoformat()
        order_date = params.get("order_date") or today
        delivery_date = params.get("delivery_date") or today
        invoice_date = params.get("invoice_date") or today
        invoice_due_date = (date.today() + timedelta(days=30)).isoformat()

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
        api_calls += 2  # search + create (or just 1 search + 1 create at most)

        self._check_timeout(start_time)

        # --- Step 2: Discover vatType IDs if multiple VAT rates are needed ---
        vat_type_map: dict[int, int] = {}  # rate_percent -> vatType id
        vat_rates = params.get("vat_rates")
        if vat_rates and len(vat_rates) > 1:
            result = client.get("/ledger/vatType")
            api_calls += 1
            if result["success"]:
                for vt in result["body"].get("values", []):
                    pct = vt.get("percentage")
                    if pct is not None:
                        vat_type_map[int(pct)] = vt["id"]

        self._check_timeout(start_time)

        # --- Step 3: Bulk create products via POST /product/list ---
        products = params.get("products", [])
        products_body = [
            {"name": p["name"], "priceExcludingVatCurrency": p["price"]}
            for p in products
        ]

        product_ids = []
        if len(products_body) > 1:
            # Try bulk create first
            bulk_result = client.post("/product/list", body=products_body)
            api_calls += 1
            if bulk_result["success"]:
                for prod in bulk_result["body"].get("values", []):
                    product_ids.append(prod["id"])

        if not product_ids:
            # Fallback: create individually (handles duplicates gracefully)
            for product in products:
                self._check_timeout(start_time)
                product_name = product["name"]
                price = product["price"]

                result = client.post("/product", body={
                    "name": product_name,
                    "priceExcludingVatCurrency": price,
                })
                api_calls += 1

                if not result["success"]:
                    if result.get("status_code") == 422:
                        find_result = client.get("/product", params={"name": product_name})
                        api_calls += 1
                        if find_result["success"]:
                            values = find_result["body"].get("values", [])
                            if values:
                                product_ids.append(values[0]["id"])
                                continue
                    api_errors += 1
                    # Skip this product rather than aborting the whole plan
                    continue
                else:
                    product_ids.append(result["body"]["value"]["id"])

        self._check_timeout(start_time)

        # --- Step 4: Create order ---
        order_lines = []
        for i, product in enumerate(products):
            if i >= len(product_ids):
                break
            line = {
                "product": {"id": product_ids[i]},
                "count": product.get("count", 1),
                "unitPriceExcludingVatCurrency": product["price"],
            }
            # Attach vatType to order line if we have a rate mapping and the product specifies one
            if vat_type_map and product.get("vat_rate") is not None:
                rate_key = int(product["vat_rate"])
                if rate_key in vat_type_map:
                    line["vatType"] = {"id": vat_type_map[rate_key]}
            order_lines.append(line)

        # --- Step 4+5: Create invoice with inline order (1 call instead of 2) ---
        invoice_params = {}
        if params.get("send_invoice"):
            invoice_params["sendToCustomer"] = "true"

        invoice_result = client.post(
            "/invoice",
            body={
                "invoiceDate": invoice_date,
                "invoiceDueDate": invoice_due_date,
                "orders": [{
                    "customer": {"id": customer_id},
                    "orderDate": order_date,
                    "deliveryDate": delivery_date,
                    "orderLines": order_lines,
                }],
            },
            params=invoice_params or None,
        )
        api_calls += 1
        if not invoice_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to create invoice: "
                f"status={invoice_result.get('status_code')}, error={invoice_result.get('error')}"
            )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
