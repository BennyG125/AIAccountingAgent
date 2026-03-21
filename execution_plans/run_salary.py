"""Execution plan: Run Salary (Tier 2).

Full flow:
  1. GET /employee?email=X — find employee by email
  2. If not found: POST /employee, POST /employee/employment,
     POST /employee/employment/details
  3. GET /salary/type — discover IDs for base salary type and bonus type
  4. POST /salary/transaction with payslips structure
"""
import datetime

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "employee_email": "string — employee email address (required)",
    "employee_first_name": "string — employee first name (required)",
    "employee_last_name": "string — employee last name (required)",
    "base_salary": "number — base/monthly salary amount in NOK (required)",
    "bonus_amount": "number|null — one-time bonus amount in NOK, or null if not mentioned",
}


@register
class RunSalaryPlan(ExecutionPlan):
    task_type = "run_salary"
    description = (
        "Find or create employee, discover salary type IDs, "
        "then POST /salary/transaction with payslips"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)
        api_calls = 0

        today = datetime.date.today()
        current_month = today.month
        current_year = today.year
        date_str = today.isoformat()

        # --- Step 1: Find employee by email ---
        email = params["employee_email"]
        emp_result = client.get("/employee", params={"email": email, "fields": "id,firstName,lastName"})
        api_calls += 1

        emp_id = None
        if emp_result["success"]:
            values = emp_result["body"].get("values", [])
            if values:
                emp_id = values[0]["id"]

        # --- Step 2: Create employee if not found ---
        if emp_id is None:
            self._check_timeout(start_time)

            # Need a department — find first available
            dept_result = client.get("/department", params={"fields": "id", "count": 1})
            api_calls += 1
            dept_id = None
            if dept_result["success"]:
                dept_values = dept_result["body"].get("values", [])
                if dept_values:
                    dept_id = dept_values[0]["id"]

            if dept_id is None:
                # Create a default department
                dept_create = client.post("/department", body={"name": "General", "departmentNumber": "100"})
                api_calls += 1
                if not dept_create["success"]:
                    raise RuntimeError(
                        f"Failed to create default department: "
                        f"status={dept_create.get('status_code')}, error={dept_create.get('error')}"
                    )
                dept_id = dept_create["body"]["value"]["id"]

            emp_body = {
                "firstName": params["employee_first_name"],
                "lastName": params["employee_last_name"],
                "email": email,
                "dateOfBirth": params.get("dateOfBirth", "1990-01-01"),
                "userType": "STANDARD",
                "department": {"id": dept_id},
            }
            emp_create = client.post("/employee", body=emp_body)
            api_calls += 1
            if not emp_create["success"]:
                raise RuntimeError(
                    f"Failed to create employee: "
                    f"status={emp_create.get('status_code')}, error={emp_create.get('error')}"
                )
            emp_id = emp_create["body"]["value"]["id"]

            self._check_timeout(start_time)

            # Look up division for employment
            div_result = client.get("/company/divisions", params={"fields": "id", "count": 1})
            api_calls += 1
            division_id = None
            if div_result["success"]:
                div_values = div_result["body"].get("values", [])
                if div_values:
                    division_id = div_values[0]["id"]

            # Create employment
            employment_body = {
                "employee": {"id": emp_id},
                "startDate": date_str,
                "isMainEmployer": True,
            }
            if division_id is not None:
                employment_body["division"] = {"id": division_id}
            employment_result = client.post("/employee/employment", body=employment_body)
            api_calls += 1
            if not employment_result["success"]:
                raise RuntimeError(
                    f"Failed to create employment: "
                    f"status={employment_result.get('status_code')}, "
                    f"error={employment_result.get('error')}"
                )
            employment_id = employment_result["body"]["value"]["id"]

            self._check_timeout(start_time)

            # Create employment details
            details_body = {
                "employment": {"id": employment_id},
                "date": date_str,
                "employmentType": "ORDINARY",
                "salaryType": "MONTHLY",
                "scheduleType": "SHIFT",
                "percentageOfFullTimeEquivalent": 100.0,
            }
            details_result = client.post("/employee/employment/details", body=details_body)
            api_calls += 1
            # Non-fatal if details fail — salary transaction can still proceed
            if not details_result["success"]:
                pass

        self._check_timeout(start_time)

        # --- Step 3: Find salary type IDs ---
        # Fetch all salary types and match by name/number
        types_result = client.get("/salary/type", params={"fields": "id,name,number"})
        api_calls += 1

        base_type_id = None
        bonus_type_id = None

        if types_result["success"]:
            salary_types = types_result["body"].get("values", [])
            for st in salary_types:
                name_lower = (st.get("name") or "").lower()
                number = str(st.get("number") or "")
                # Match base salary: "Fastlønn", "Fastlonn", number "1000", or generic "base"
                if base_type_id is None and (
                    "fastl" in name_lower
                    or number == "1000"
                    or "base" in name_lower
                    or "grunn" in name_lower
                    or "grunnl" in name_lower
                    or "monthly" in name_lower
                    or "fast" in name_lower
                ):
                    base_type_id = st["id"]
                # Match bonus
                if bonus_type_id is None and (
                    "bonus" in name_lower
                    or "tillegg" in name_lower
                ):
                    bonus_type_id = st["id"]

        # Fallback: if still not found, try targeted searches
        if base_type_id is None:
            base_search = client.get("/salary/type", params={"name": "Fastlønn", "fields": "id,name,number"})
            api_calls += 1
            if base_search["success"]:
                values = base_search["body"].get("values", [])
                if values:
                    base_type_id = values[0]["id"]

        if base_type_id is None:
            base_search2 = client.get("/salary/type", params={"number": "1000", "fields": "id,name,number"})
            api_calls += 1
            if base_search2["success"]:
                values = base_search2["body"].get("values", [])
                if values:
                    base_type_id = values[0]["id"]

        if base_type_id is None:
            raise RuntimeError("Could not find a base salary type (Fastlønn/number 1000)")

        if bonus_type_id is None and params.get("bonus_amount"):
            bonus_search = client.get("/salary/type", params={"name": "Bonus", "fields": "id,name,number"})
            api_calls += 1
            if bonus_search["success"]:
                values = bonus_search["body"].get("values", [])
                if values:
                    bonus_type_id = values[0]["id"]

        self._check_timeout(start_time)

        # --- Step 4: POST /salary/transaction ---
        specifications = [
            {
                "salaryType": {"id": base_type_id},
                "rate": params["base_salary"],
                "count": 1,
            }
        ]

        bonus_amount = params.get("bonus_amount")
        if bonus_amount and bonus_type_id:
            specifications.append(
                {
                    "salaryType": {"id": bonus_type_id},
                    "rate": bonus_amount,
                    "count": 1,
                }
            )
        elif bonus_amount and not bonus_type_id:
            # Bonus requested but no bonus type found — skip rather than fail
            pass

        transaction_body = {
            "date": date_str,
            "month": current_month,
            "year": current_year,
            "payslips": [
                {
                    "employee": {"id": emp_id},
                    "date": date_str,
                    "specifications": specifications,
                }
            ],
        }

        tx_result = client.post("/salary/transaction", body=transaction_body)
        api_calls += 1
        if not tx_result["success"]:
            raise RuntimeError(
                f"Failed to create salary transaction: "
                f"status={tx_result.get('status_code')}, error={tx_result.get('error')}"
            )

        return self._make_result(api_calls=api_calls, api_errors=0)
