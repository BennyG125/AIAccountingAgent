"""Execution plan: Create Product (Tier 1)."""
from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

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
        self._check_timeout(start_time)

        body = {
            "name": params["name"],
            "priceExcludingVatCurrency": params["price"],
        }

        # Only include number if explicitly provided in the prompt
        if params.get("number") is not None:
            body["number"] = params["number"]

        # Use _safe_post: if number causes 422 "already in use", retry without it
        result = self._safe_post(
            client,
            "/product",
            body=body,
            retry_without=["number"],
        )

        if not result["success"]:
            raise RuntimeError(
                f"Failed to create product: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )

        return self._make_result(api_calls=1, api_errors=0)
