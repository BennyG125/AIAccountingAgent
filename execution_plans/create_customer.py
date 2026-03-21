"""Execution plan: Create Customer (Tier 1)."""
from execution_plans._base import ExecutionPlan
from execution_plans._registry import register


@register
class CreateCustomerPlan(ExecutionPlan):
    task_type = "create_customer"
    description = "Create a customer with all provided fields"

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

        result = client.post("/customer", body=body)
        if not result["success"]:
            raise RuntimeError(
                f"Failed to create customer: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )

        return self._make_result(api_calls=1, api_errors=0)
