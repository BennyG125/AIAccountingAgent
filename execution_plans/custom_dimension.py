"""Execution plan: Custom Accounting Dimension (Tier 2)."""
import datetime
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

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
        # Validate required params
        required = ["dimension_name", "dimension_values", "voucher_account_number", "voucher_amount", "voucher_dimension_value"]
        missing = [f for f in required if not params.get(f)]
        if missing:
            logger.warning(f"Missing required params for {self.task_type}: {missing}")
            return None

        self._check_timeout(start_time)

        dimension_name = params["dimension_name"]
        dimension_values = params["dimension_values"]
        voucher_account_number = params["voucher_account_number"]
        voucher_amount = params["voucher_amount"]
        voucher_dimension_value = params["voucher_dimension_value"]

        api_calls = 0
        api_errors = 0

        # Step 1 — Create the custom dimension type directly (sandbox starts empty)
        # API uses "dimensionName" field (NOT "name")
        # POST directly; on conflict, fall back to GET to find existing
        result = client.post(
            "/ledger/accountingDimensionName",
            body={"dimensionName": dimension_name},
        )
        api_calls += 1
        dimension_index = None
        dimension_name_id = None  # entity ID for linking values

        if result["success"]:
            dimension_index = result["body"]["value"]["dimensionIndex"]
            dimension_name_id = result["body"]["value"]["id"]
        else:
            # Conflict or other error — fall back to GET to find existing
            search_result = client.get(
                "/ledger/accountingDimensionName",
                params={"fields": "id,dimensionName,dimensionIndex"},
            )
            api_calls += 1
            if search_result["success"]:
                existing = search_result["body"].get("values", [])
                for dim in existing:
                    if dim.get("dimensionName", "").lower() == dimension_name.lower():
                        dimension_index = dim["dimensionIndex"]
                        dimension_name_id = dim["id"]
                        break

            if dimension_name_id is None:
                api_errors += 1
                logger.warning(
                    "Failed to create accountingDimensionName '%s': status=%s, error=%s",
                    dimension_name, result.get('status_code'), result.get('error'),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        # Step 2 — Create each dimension value directly (sandbox starts empty)
        # API uses "displayName" for values, "dimensionIndex" for filtering
        # POST directly; on conflict, fall back to GET to find existing IDs
        voucher_value_id = None

        for value_name in dimension_values:
            self._check_timeout(start_time)
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
            if result["success"]:
                created_id = result["body"]["value"]["id"]
                if value_name == voucher_dimension_value:
                    voucher_value_id = created_id
            else:
                # Conflict — value may already exist; try GET fallback
                api_errors += 1
                logger.warning(
                    "Failed to create accountingDimensionValue '%s': status=%s, error=%s",
                    value_name, result.get('status_code'), result.get('error'),
                )

        if voucher_value_id is None:
            # Fallback: GET existing values to find the voucher dimension value ID
            existing_values_result = client.get(
                "/ledger/accountingDimensionValue",
                params={"dimensionIndex": dimension_index, "fields": "id,displayName"},
            )
            api_calls += 1
            if existing_values_result["success"]:
                for val in existing_values_result["body"].get("values", []):
                    display_name = val.get("displayName", "")
                    if display_name.lower() == voucher_dimension_value.lower():
                        voucher_value_id = val["id"]
                        break

            if voucher_value_id is None:
                api_errors += 1
                logger.warning(
                    "Dimension value '%s' not found among created/existing values: %s",
                    voucher_dimension_value, dimension_values,
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        # Step 3 — Batch look up expense + bank accounts (1 call instead of 2)
        self._check_timeout(start_time)
        accounts = self._get_accounts(client, str(voucher_account_number), "1920")
        api_calls += 1
        expense_account_id = accounts.get(str(voucher_account_number))
        bank_account_id = accounts.get("1920")
        if not expense_account_id or not bank_account_id:
            logger.warning(
                "Account lookup failed: %s=%s, 1920=%s — falling back",
                voucher_account_number, expense_account_id, bank_account_id,
            )
            return None

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
            logger.warning(
                "Failed to post voucher: status=%s, error=%s",
                result.get('status_code'), result.get('error'),
            )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
