"""Execution plan: Create Employee (Tier 1)."""
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    "first_name": "string (first name)",
    "last_name": "string (last name)",
    "email": "string (email address)",
    "date_of_birth": "string (YYYY-MM-DD) or null",
    "department_name": "string (department name) or null",
}


@register
class CreateEmployeePlan(ExecutionPlan):
    task_type = "create_employee"
    description = "Create an employee with department"

    def execute(self, client, params, start_time):
        # Validate required params
        required = ["first_name", "last_name", "email"]
        missing = [f for f in required if not params.get(f)]
        if missing:
            logger.warning(f"Missing required params for {self.task_type}: {missing}")
            return None

        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0

        # 1. Find or create department
        dept_id = None
        dept_name = params.get("department_name")

        r = client.get("/department", params={"fields": "id,name"})
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            if dept_name:
                # Try to find matching department
                for d in r["body"]["values"]:
                    if d.get("name", "").lower() == dept_name.lower():
                        dept_id = d["id"]
                        break
            if dept_id is None:
                dept_id = r["body"]["values"][0]["id"]
        else:
            # Create a department
            r = client.post(
                "/department",
                body={
                    "name": dept_name or "Avdeling",
                    "departmentNumber": "1",
                },
            )
            api_calls += 1
            if r["success"]:
                dept_id = r["body"]["value"]["id"]
            else:
                api_errors += 1
                logger.warning(
                    "Failed to create department: status=%s, error=%s",
                    r.get('status_code'), r.get('error'),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        # 2. Create employee
        body = {
            "firstName": params["first_name"],
            "lastName": params["last_name"],
            "email": params["email"],
            "dateOfBirth": params.get("date_of_birth") or "1990-01-01",
            "userType": "STANDARD",
            "department": {"id": dept_id},
        }

        r = client.post("/employee", body=body)
        api_calls += 1
        if r["success"]:
            emp_id = r["body"]["value"]["id"]
        elif r.get("status_code") == 422:
            # Email already in use — find existing
            api_errors += 1
            r2 = client.get(
                "/employee",
                params={"email": params["email"], "fields": "id", "count": 1},
            )
            api_calls += 1
            if r2["success"] and r2["body"].get("values"):
                emp_id = r2["body"]["values"][0]["id"]
            else:
                api_errors += 1
                logger.warning(
                    "Failed to create or find employee: status=%s, error=%s",
                    r.get('status_code'), r.get('error'),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
        else:
            api_errors += 1
            logger.warning(
                "Failed to create employee: status=%s, error=%s",
                r.get('status_code'), r.get('error'),
            )
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        # 3. Grant entitlements
        r = client.put(
            f"/employee/entitlement/:grantEntitlementsByTemplate",
            params={"employeeId": emp_id, "template": "ALL_PRIVILEGES"},
        )
        api_calls += 1
        # Don't fail on entitlement errors — some sandboxes may not support it

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
