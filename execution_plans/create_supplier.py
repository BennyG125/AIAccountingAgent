"""Execution plan: Create Supplier (Tier 1)."""
from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

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
        if not result["success"]:
            raise RuntimeError(
                f"Failed to create supplier: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )

        return self._make_result(api_calls=1, api_errors=0)
