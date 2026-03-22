"""Execution plan: Employee Onboarding (Tier 3).

Full flow:
  1. GET /department — find or create the department
  2. POST /employee — create employee with all available fields
  3. GET /company/divisions — get division id (NEVER POST /division)
  4. POST /employee/employment — create employment record
  5. POST /employee/employment/details — set salary, percentage, etc.
"""
from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

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
        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0

        # --- Step 1: Find or create department ---
        department_name = params["department_name"]
        dept_id = self._find_or_create(
            client,
            search_path="/department",
            search_params={"name": department_name, "count": 1},
            create_path="/department",
            create_body={"name": department_name, "departmentNumber": "10"},
        )
        api_calls += 2  # search + possible create

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

        # --- Step 3: Get division (NEVER create a division) ---
        division_result = client.get("/company/divisions")
        api_calls += 1
        division_id = None
        if division_result["success"]:
            values = division_result["body"].get("values", [])
            if values:
                division_id = values[0]["id"]

        self._check_timeout(start_time)

        # --- Step 4: Create employment ---
        employment_body = {
            "employee": {"id": employee_id},
            "startDate": params["startDate"],
        }
        if division_id:
            employment_body["division"] = {"id": division_id}
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
