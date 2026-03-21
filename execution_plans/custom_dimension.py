"""Execution plan: Custom Accounting Dimension (Tier 2)."""
import datetime

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "dimension_name": {
            "type": "string",
            "description": "Name of the custom dimension to create, e.g. 'Prosjekttype'",
        },
        "dimension_values": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of values to create for the dimension, e.g. ['Forskning', 'Utvikling']",
        },
        "voucher_account_number": {
            "type": "integer",
            "description": "Account number for the expense posting, e.g. 6590",
        },
        "voucher_amount": {
            "type": "number",
            "description": "Amount in NOK for the voucher posting (positive)",
        },
        "voucher_dimension_value": {
            "type": "string",
            "description": "Which dimension value to attach to the voucher posting, e.g. 'Forskning'",
        },
    },
    "required": [
        "dimension_name",
        "dimension_values",
        "voucher_account_number",
        "voucher_amount",
        "voucher_dimension_value",
    ],
}


@register
class CustomDimensionPlan(ExecutionPlan):
    task_type = "custom_dimension"
    description = (
        "Create a custom accounting dimension with values, then post a balanced voucher "
        "referencing one of those values"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        dimension_name = params["dimension_name"]
        dimension_values = params["dimension_values"]
        voucher_account_number = params["voucher_account_number"]
        voucher_amount = params["voucher_amount"]
        voucher_dimension_value = params["voucher_dimension_value"]

        api_calls = 0
        api_errors = 0

        # Step 1 — Find or create the custom dimension type
        # First, search if it already exists
        search_result = client.get(
            "/ledger/accountingDimensionName",
            params={"dimensionName": dimension_name},
        )
        api_calls += 1
        dimension_index = None

        if search_result["success"]:
            existing = search_result["body"].get("values", [])
            for dim in existing:
                if dim.get("dimensionName", "").lower() == dimension_name.lower():
                    dimension_index = dim["dimensionIndex"]
                    break

        if dimension_index is None:
            # Not found — create it
            result = client.post(
                "/ledger/accountingDimensionName",
                body={"dimensionName": dimension_name, "active": True},
            )
            api_calls += 1
            if not result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to create accountingDimensionName '{dimension_name}': "
                    f"status={result.get('status_code')}, error={result.get('error')}"
                )
            dimension_index = result["body"]["value"]["dimensionIndex"]

        # Step 2 — Find or create each dimension value; capture the ID for the voucher value
        voucher_value_id = None

        # Search existing values for this dimension
        existing_values_result = client.get(
            "/ledger/accountingDimensionValue",
            params={"dimensionIndex": dimension_index},
        )
        api_calls += 1
        existing_values_map: dict[str, int] = {}
        if existing_values_result["success"]:
            for val in existing_values_result["body"].get("values", []):
                name = val.get("displayName", "")
                existing_values_map[name.lower()] = val["id"]

        for value_name in dimension_values:
            self._check_timeout(start_time)
            # Check if value already exists (case-insensitive)
            existing_id = existing_values_map.get(value_name.lower())
            if existing_id is not None:
                if value_name == voucher_dimension_value:
                    voucher_value_id = existing_id
                continue

            result = client.post(
                "/ledger/accountingDimensionValue",
                body={
                    "displayName": value_name,
                    "dimensionIndex": dimension_index,
                    "active": True,
                    "showInVoucherRegistration": True,
                },
            )
            api_calls += 1
            if not result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to create accountingDimensionValue '{value_name}': "
                    f"status={result.get('status_code')}, error={result.get('error')}"
                )
            created_id = result["body"]["value"]["id"]
            if value_name == voucher_dimension_value:
                voucher_value_id = created_id

        if voucher_value_id is None:
            # Fallback: check case-insensitive match for the voucher dimension value
            voucher_value_id = existing_values_map.get(voucher_dimension_value.lower())
            if voucher_value_id is None:
                raise RuntimeError(
                    f"Dimension value '{voucher_dimension_value}' not found among "
                    f"created/existing values: {dimension_values}"
                )

        # Step 3 — Look up expense account ID
        self._check_timeout(start_time)
        result = client.get(
            "/ledger/account", params={"number": str(voucher_account_number)}
        )
        api_calls += 1
        if not result["success"] or not result["body"].get("values"):
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up account {voucher_account_number}: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )
        expense_account_id = result["body"]["values"][0]["id"]

        # Step 4 — Look up bank/offset account ID (1920)
        self._check_timeout(start_time)
        result = client.get("/ledger/account", params={"number": "1920"})
        api_calls += 1
        if not result["success"] or not result["body"].get("values"):
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up account 1920: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )
        bank_account_id = result["body"]["values"][0]["id"]

        # Step 5 — Post balanced voucher with freeAccountingDimensionN on the expense row
        today = datetime.date.today().isoformat()
        dim_field = f"freeAccountingDimension{dimension_index}"
        voucher_body = {
            "date": today,
            "description": voucher_dimension_value,
            "postings": [
                {
                    "account": {"id": expense_account_id},
                    "amount": voucher_amount,
                    "amountCurrency": voucher_amount,
                    "amountGross": voucher_amount,
                    "amountGrossCurrency": voucher_amount,
                    "row": 1,
                    dim_field: {"id": voucher_value_id},
                },
                {
                    "account": {"id": bank_account_id},
                    "amount": -voucher_amount,
                    "amountCurrency": -voucher_amount,
                    "amountGross": -voucher_amount,
                    "amountGrossCurrency": -voucher_amount,
                    "row": 2,
                },
            ],
        }
        self._check_timeout(start_time)
        result = client.post("/ledger/voucher", body=voucher_body)
        api_calls += 1
        if not result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to post voucher: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
