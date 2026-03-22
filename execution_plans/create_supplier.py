"""Execution plan: Create Supplier (Tier 1)."""
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    "name": "string (supplier name)",
    "org_number": "string (organization number)",
    "email": "string or null",
    "phone": "string or null",
    "address": {
        "street": "string (street address) or null",
        "postal_code": "string or null",
        "city": "string or null",
    },
}


@register
class CreateSupplierPlan(ExecutionPlan):
    task_type = "create_supplier"
    description = "Create a supplier with all provided fields"

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        body = {"name": params["name"]}

        if params.get("org_number"):
            body["organizationNumber"] = params["org_number"]
        if params.get("email"):
            body["email"] = params["email"]
        if params.get("phone"):
            body["phoneNumber"] = params["phone"]

        if params.get("address"):
            addr = params["address"]
            body["physicalAddress"] = {
                "addressLine1": addr.get("street"),
                "postalCode": addr.get("postal_code"),
                "city": addr.get("city"),
                "country": {"id": 162},  # Norway
            }

        result = client.post("/supplier", body=body)
        api_calls = 1
        api_errors = 0
        if not result["success"]:
            api_errors += 1
            logger.warning(
                "Failed to create supplier: status=%s, error=%s",
                result.get('status_code'), result.get('error'),
            )
            # Try to find existing supplier by org number or name
            search_params = {}
            if params.get("org_number"):
                search_params["organizationNumber"] = params["org_number"]
            else:
                search_params["name"] = params["name"]
            find_result = client.get("/supplier", params=search_params)
            api_calls += 1
            if find_result["success"] and find_result["body"].get("values"):
                logger.warning("Found existing supplier, continuing")
            # Either way, return gracefully

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
