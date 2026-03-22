"""Execution plan: Create Product (Tier 1)."""
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "name": "string — product name (required)",
    "price": "number — price excluding VAT in NOK (required)",
    "number": "string|null — product number, ONLY if prompt explicitly states one",
}


@register
class CreateProductPlan(ExecutionPlan):
    task_type = "create_product"
    description = "Create a product with name and price; never include vatType"

    def execute(self, client, params, start_time):
        # Validate required params
        required = ["name", "price"]
        missing = [f for f in required if not params.get(f)]
        if missing:
            logger.warning(f"Missing required params for {self.task_type}: {missing}")
            return None

        self._check_timeout(start_time)

        body = {
            "name": params["name"],
            "priceExcludingVatCurrency": params["price"],
        }

        product_number = params.get("number")

        # Only include number if explicitly provided in the prompt
        if product_number is not None:
            body["number"] = product_number

        # Use _safe_post: if number causes 422 "already in use", retry without it
        api_calls = 0
        result = self._safe_post(
            client,
            "/product",
            body=body,
            retry_without=["number"],
        )
        api_calls += 1

        if result["success"]:
            return self._make_result(api_calls=api_calls, api_errors=0)

        # POST failed — try to find existing product instead of raising
        logger.warning(
            "Product creation failed (status=%s), attempting lookup fallback",
            result.get("status_code"),
        )

        # 1. Try to find by product number if we have one
        if product_number is not None:
            self._check_timeout(start_time)
            search = client.get("/product", params={"number": str(product_number)})
            api_calls += 1
            if search["success"]:
                values = search["body"].get("values", [])
                if values:
                    logger.info(
                        "Found existing product by number=%s (id=%s)",
                        product_number,
                        values[0]["id"],
                    )
                    return self._make_result(api_calls=api_calls, api_errors=0)

        # 2. Try to find by name
        self._check_timeout(start_time)
        search = client.get("/product", params={"name": params["name"]})
        api_calls += 1
        if search["success"]:
            values = search["body"].get("values", [])
            if values:
                logger.info(
                    "Found existing product by name='%s' (id=%s)",
                    params["name"],
                    values[0]["id"],
                )
                return self._make_result(api_calls=api_calls, api_errors=0)

        # 3. Nothing found — return error result instead of raising
        logger.error(
            "Product creation failed and no existing product found: status=%s, error=%s",
            result.get("status_code"),
            result.get("error"),
        )
        return self._make_result(
            api_calls=api_calls,
            api_errors=1,
            error_details=[
                f"Failed to create product: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            ],
        )
