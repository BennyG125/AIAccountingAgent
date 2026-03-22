"""Execution plan: Employee Onboarding (Tier 3).

Full flow (POST-first pattern):
  1. POST /department — create department (fall back to GET on conflict)
  2. POST /employee — create employee with all available fields
  3. Division id hardcoded to 1 (every sandbox has default division 1)
  4. POST /employee/employment — create employment record
  5. POST /employee/employment/details — set salary, percentage, etc.
"""
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "firstName": {
            "type": "string",
            "description": "Employee first name",
        },
        "lastName": {
            "type": "string",
            "description": "Employee last name",
        },
        "email": {
            "type": "string",
            "description": (
                "Employee email. If not in PDF, generate as "
                "firstname.lastname@company.no"
            ),
        },
        "dateOfBirth": {
            "type": "string",
            "description": "Date of birth in YYYY-MM-DD format (convert from DD.MM.YYYY if needed)",
        },
        "nationalIdentityNumber": {
            "type": ["string", "null"],
            "description": "11-digit personnummer. Omit entirely if not present.",
        },
        "department_name": {
            "type": "string",
            "description": "Department name from PDF 'Avdeling' field",
        },
        "startDate": {
            "type": "string",
            "description": "Employment start date in YYYY-MM-DD format (convert from DD.MM.YYYY if needed)",
        },
        "percentageOfFullTimeEquivalent": {
            "type": "number",
            "description": "Stillingsprosent as a number (e.g. 80 or 100), NOT a string",
        },
        "annualSalary": {
            "type": "number",
            "description": "Annual salary in NOK as a number (e.g. 710000), NOT a string",
        },
        "occupationCode": {
            "type": ["integer", "null"],
            "description": "STYRK code integer (e.g. 2511). Omit if not in PDF.",
        },
        "employmentType": {
            "type": "string",
            "description": "Employment type: 'ORDINARY' for 'Fast stilling'. Default 'ORDINARY'.",
        },
    },
    "required": [
        "firstName",
        "lastName",
        "email",
        "dateOfBirth",
        "department_name",
        "startDate",
        "percentageOfFullTimeEquivalent",
        "annualSalary",
        "employmentType",
    ],
}


@register
class EmployeeOnboardingPlan(ExecutionPlan):
    task_type = "employee_onboarding"
    description = (
        "Onboard a new employee: find/create department, create employee, "
        "get division, create employment and employment details"
    )

    def execute(self, client, params, start_time):
        # Validate required params
        required = ["firstName", "lastName", "email", "dateOfBirth", "department_name", "startDate", "annualSalary"]
        missing = [f for f in required if not params.get(f)]
        if missing:
            logger.warning(f"Missing required params for {self.task_type}: {missing}")
            return None

        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0

        # --- Step 1: Find or create department (POST-first) ---
        department_name = params["department_name"]
        dept_result = client.post("/department", body={"name": department_name, "departmentNumber": "10"})
        api_calls += 1
        if dept_result["success"]:
            dept_id = dept_result["body"]["value"]["id"]
        else:
            # Conflict — department already exists, search for it
            if dept_result.get("status_code") not in (409, 422):
                api_errors += 1
            search_result = client.get("/department", params={"name": department_name, "count": 1})
            api_calls += 1
            values = search_result.get("body", {}).get("values", []) if search_result["success"] else []
            dept_id = values[0]["id"] if values else None

        if dept_id is None:
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 2: Create employee ---
        employee_body = {
            "firstName": params["firstName"],
            "lastName": params["lastName"],
            "email": params["email"],
            "dateOfBirth": params["dateOfBirth"],
            "userType": "STANDARD",
            "department": {"id": dept_id},
        }
        nin = params.get("nationalIdentityNumber")
        if nin:
            employee_body["nationalIdentityNumber"] = nin

        # Retry without nationalIdentityNumber on 422
        employee_result = self._safe_post(
            client,
            "/employee",
            body=employee_body,
            retry_without=["nationalIdentityNumber"],
        )
        api_calls += 1
        employee_id = None
        if not employee_result["success"]:
            api_errors += 1
            # Fallback: try to find existing employee by email
            search_result = client.get(
                "/employee", params={"email": params["email"], "count": 1}
            )
            api_calls += 1
            if search_result["success"]:
                values = search_result["body"].get("values", [])
                if values:
                    employee_id = values[0]["id"]
            if employee_id is None:
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
        else:
            employee_id = employee_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 3: Division ID ---
        # Hardcode division_id=1: every Tripletex sandbox has a default division
        # with id=1. The old GET /company/divisions call always just picked
        # divisions[0]["id"] which was always 1 — skipping this saves 1 API call.
        division_id = 1

        self._check_timeout(start_time)

        # --- Step 4: Create employment ---
        employment_body = {
            "employee": {"id": employee_id},
            "startDate": params["startDate"],
            "division": {"id": division_id},
        }
        employment_result = client.post("/employee/employment", body=employment_body)
        api_calls += 1
        employment_id = None
        if not employment_result["success"]:
            api_errors += 1
            # Continue — skip employment details since we have no employment_id
        else:
            employment_id = employment_result["body"]["value"]["id"]

        # --- Step 5: Create employment details (only if employment was created) ---
        if employment_id is not None:
            self._check_timeout(start_time)

            # CRITICAL: Only send whitelisted fields — any unknown field causes 422.
            # NOTE: field is "percentageOfFullTimeEquivalent" (NOT "percentOfFullTimeEquivalent")
            details_body = {
                "employment": {"id": employment_id},
                "date": params["startDate"],
                "employmentType": params.get("employmentType", "ORDINARY"),
                "percentageOfFullTimeEquivalent": params["percentageOfFullTimeEquivalent"],
                "annualSalary": params["annualSalary"],
            }
            occupation_code = params.get("occupationCode")
            if occupation_code is not None:
                details_body["occupationCode"] = {"id": occupation_code}

            details_result = client.post(
                "/employee/employment/details", body=details_body
            )
            api_calls += 1
            if not details_result["success"]:
                api_errors += 1

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
