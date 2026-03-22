"""Execution plan: Create Project (Tier 2).

Sequence: customer → department → employee (PM) → entitlements → project.
The PM must have ALL_PRIVILEGES entitlements BEFORE project creation.
"""
import logging
from datetime import date

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    "project_name": "string (project name)",
    "customer_name": "string (customer/client name)",
    "customer_org_number": "string (organization number)",
    "pm_first_name": "string (project manager first name)",
    "pm_last_name": "string (project manager last name)",
    "pm_email": "string (project manager email address)",
}


@register
class CreateProjectPlan(ExecutionPlan):
    task_type = "create_project"
    description = "Create a project with customer and project manager"

    def execute(self, client, params, start_time):
        # Validate required params
        required = ["project_name", "customer_name", "pm_first_name", "pm_last_name", "pm_email"]
        missing = [f for f in required if not params.get(f)]
        if missing:
            logger.warning(f"Missing required params for {self.task_type}: {missing}")
            return None

        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0
        today = date.today().isoformat()

        # 1. Create customer
        customer_id = None
        r = client.post("/customer", body={
            "name": params["customer_name"],
            "organizationNumber": params.get("customer_org_number"),
        })
        api_calls += 1
        if r["success"]:
            customer_id = r["body"]["value"]["id"]
        elif r.get("status_code") == 422:
            api_errors += 1
            r2 = client.get("/customer", params={
                "organizationNumber": params.get("customer_org_number"),
                "fields": "id", "count": 1,
            })
            api_calls += 1
            if r2["success"] and r2["body"].get("values"):
                customer_id = r2["body"]["values"][0]["id"]
            else:
                # Try searching by name as fallback
                r3 = client.get("/customer", params={
                    "name": params["customer_name"],
                    "fields": "id", "count": 1,
                })
                api_calls += 1
                if r3["success"] and r3["body"].get("values"):
                    customer_id = r3["body"]["values"][0]["id"]
                else:
                    logger.warning("Failed to create/find customer: %s", r.get('error'))
        else:
            api_errors += 1
            logger.warning("Failed to create customer: %s", r.get('error'))

        if customer_id is None:
            api_errors += 1
            logger.warning("customer_id is None — cannot create project")
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # 2. Find or create department
        dept_id = None
        r = client.get("/department", params={"fields": "id,name"})
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            dept_id = r["body"]["values"][0]["id"]
        else:
            r = client.post("/department", body={
                "name": "Avdeling", "departmentNumber": "1",
            })
            api_calls += 1
            if r["success"]:
                dept_id = r["body"]["value"]["id"]
            else:
                api_errors += 1
                logger.warning("Failed to create department: %s", r.get('error'))
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # 3. Create employee (PM)
        pm_id = None
        r = client.post("/employee", body={
            "firstName": params["pm_first_name"],
            "lastName": params["pm_last_name"],
            "email": params["pm_email"],
            "dateOfBirth": "1990-01-01",
            "userType": "STANDARD",
            "department": {"id": dept_id},
        })
        api_calls += 1
        if r["success"]:
            pm_id = r["body"]["value"]["id"]
        elif r.get("status_code") == 422:
            api_errors += 1
            r2 = client.get("/employee", params={
                "email": params["pm_email"], "fields": "id", "count": 1,
            })
            api_calls += 1
            if r2["success"] and r2["body"].get("values"):
                pm_id = r2["body"]["values"][0]["id"]
            else:
                logger.warning("Failed to create/find employee: %s", r.get('error'))
        else:
            api_errors += 1
            logger.warning("Failed to create employee: %s", r.get('error'))

        if pm_id is None:
            api_errors += 1
            logger.warning("pm_id is None — cannot create project")
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # 4. Grant entitlements (MUST be before project creation)
        r = client.put(
            "/employee/entitlement/:grantEntitlementsByTemplate",
            params={"employeeId": pm_id, "template": "ALL_PRIVILEGES"},
        )
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            logger.warning(
                "Failed to grant entitlements for PM %s: status=%s, error=%s",
                pm_id, r.get('status_code'), r.get('error'),
            )
            # Non-fatal — continue, project creation might still work

        self._check_timeout(start_time)

        # 5. Create project
        r = client.post("/project", body={
            "name": params["project_name"],
            "projectManager": {"id": pm_id},
            "startDate": today,
            "customer": {"id": customer_id},
        })
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            logger.warning("Failed to create project: %s", r.get('error'))

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
