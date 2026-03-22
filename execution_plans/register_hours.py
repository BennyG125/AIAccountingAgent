"""Execution plan: Register Hours (Tier 2).

Full flow:
  find/create customer → find/create department → find/create employee
  → grant entitlements (new employees only) → find/create project
  → find/create activity → check/set hourly rate → register timesheet entry
  → (optionally) create order + invoice.
"""
import logging
from datetime import date, timedelta

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "hours": "number — number of hours to register (required, decimals allowed e.g. 7.5)",
    "employee_first_name": "string — employee first name (required)",
    "employee_last_name": "string — employee last name (required)",
    "employee_email": "string — employee email address (required)",
    "activity_name": "string — activity name, usually quoted in prompt (required)",
    "project_name": "string — project name, usually quoted in prompt (required)",
    "customer_name": "string — customer/company name (required)",
    "org_number": "string|null — organisation number for customer lookup/creation",
    "hourly_rate": "number — hourly rate in NOK (required)",
    "generate_invoice": "boolean — true if prompt requests invoice generation (default false)",
}


@register
class RegisterHoursPlan(ExecutionPlan):
    task_type = "register_hours"
    description = (
        "Find/create customer, employee, project, activity; set hourly rate; "
        "register timesheet entry; optionally generate project invoice"
    )

    def execute(self, client, params, start_time):
        # Validate required params
        required = ["hours", "employee_email", "employee_first_name", "employee_last_name", "activity_name", "project_name", "customer_name", "hourly_rate"]
        missing = [f for f in required if not params.get(f)]
        if missing:
            logger.warning(f"Missing required params for {self.task_type}: {missing}")
            return None

        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0
        today = date.today().isoformat()
        due_date = (date.today() + timedelta(days=30)).isoformat()

        customer_name = params["customer_name"]
        org_number = params.get("org_number")
        employee_email = params["employee_email"]
        employee_first = params["employee_first_name"]
        employee_last = params["employee_last_name"]
        activity_name = params["activity_name"]
        project_name = params["project_name"]
        hourly_rate = params["hourly_rate"]
        hours = params["hours"]
        generate_invoice = params.get("generate_invoice", False)

        # --- Step 1: Find or create customer (POST-first) ---
        customer_id = None
        create_body = {"name": customer_name}
        if org_number:
            create_body["organizationNumber"] = org_number

        r = client.post("/customer", body=create_body)
        api_calls += 1
        if r["success"]:
            customer_id = r["body"]["value"]["id"]
        else:
            # Conflict — customer already exists, search for it
            if r.get("status_code") not in (409, 422):
                api_errors += 1
            search_params = {"fields": "id,name"}
            if org_number:
                search_params["organizationNumber"] = org_number
            else:
                search_params["name"] = customer_name
            r2 = client.get("/customer", params=search_params)
            api_calls += 1
            if r2["success"] and r2["body"].get("values"):
                customer_id = r2["body"]["values"][0]["id"]
            elif org_number:
                # Fallback: search by name if org_number search failed
                r3 = client.get("/customer", params={"name": customer_name, "fields": "id,name"})
                api_calls += 1
                if r3["success"] and r3["body"].get("values"):
                    customer_id = r3["body"]["values"][0]["id"]
            if customer_id is None:
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 2: Find or create department (POST-first) ---
        r = client.post("/department", body={"name": "Avdeling", "departmentNumber": "1"})
        api_calls += 1
        if r["success"]:
            dept_id = r["body"]["value"]["id"]
        else:
            # Conflict — department already exists, search for it
            if r.get("status_code") not in (409, 422):
                api_errors += 1
            search_result = client.get("/department", params={"fields": "id,name"})
            api_calls += 1
            dept_id = None
            if search_result["success"] and search_result["body"].get("values"):
                dept_id = search_result["body"]["values"][0]["id"]
            if dept_id is None:
                logger.warning(
                    "Failed to create or find department: status=%s, error=%s",
                    r.get("status_code"), r.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 3: Find or create employee (POST-first) ---
        employee_id = None
        employee_created = False
        r = client.post(
            "/employee",
            body={
                "firstName": employee_first,
                "lastName": employee_last,
                "email": employee_email,
                "dateOfBirth": "1990-01-01",
                "userType": "STANDARD",
                "department": {"id": dept_id},
            },
        )
        api_calls += 1
        if r["success"]:
            employee_id = r["body"]["value"]["id"]
            employee_created = True
        else:
            # Conflict — employee already exists, search for it
            if r.get("status_code") not in (409, 422):
                api_errors += 1
            r2 = client.get("/employee", params={"email": employee_email, "fields": "id,firstName,lastName"})
            api_calls += 1
            if r2["success"] and r2["body"].get("values"):
                employee_id = r2["body"]["values"][0]["id"]
            else:
                # Fallback: search by name
                r3 = client.get(
                    "/employee",
                    params={"firstName": employee_first, "lastName": employee_last, "fields": "id"},
                )
                api_calls += 1
                if r3["success"] and r3["body"].get("values"):
                    employee_id = r3["body"]["values"][0]["id"]
            if employee_id is None:
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 4: Grant entitlements (only for newly created employees) ---
        if employee_created:
            r = client.put(
                "/employee/entitlement/:grantEntitlementsByTemplate",
                params={"employeeId": employee_id, "template": "ALL_PRIVILEGES"},
            )
            api_calls += 1
            if not r["success"]:
                api_errors += 1
                logger.warning(
                    "Failed to grant entitlements for employee %s: status=%s, error=%s",
                    employee_id, r.get("status_code"), r.get("error"),
                )
                # Non-fatal — continue without entitlements

        self._check_timeout(start_time)

        # --- Step 5: Find or create project (POST-first) ---
        r = client.post(
            "/project",
            body={
                "name": project_name,
                "projectManager": {"id": employee_id},
                "startDate": today,
                "customer": {"id": customer_id},
            },
        )
        api_calls += 1
        if r["success"]:
            project_id = r["body"]["value"]["id"]
        else:
            # Conflict — project already exists, search for it
            if r.get("status_code") not in (409, 422):
                api_errors += 1
                logger.warning(
                    "Failed to create project: status=%s, error=%s",
                    r.get("status_code"), r.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            r2 = client.get(
                "/project",
                params={"name": project_name, "customerId": customer_id, "fields": "id,name"},
            )
            api_calls += 1
            if r2["success"] and r2["body"].get("values"):
                project_id = r2["body"]["values"][0]["id"]
            else:
                api_errors += 1
                logger.warning("Failed to find existing project '%s'", project_name)
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 6: Find or create activity (POST-first) ---
        r = client.post(
            "/activity",
            body={
                "name": activity_name,
                "activityType": "GENERAL_ACTIVITY",
                "isChargeable": True,
            },
        )
        api_calls += 1
        if r["success"]:
            activity_id = r["body"]["value"]["id"]
        else:
            # Conflict — activity already exists, search for it
            if r.get("status_code") not in (409, 422):
                api_errors += 1
                logger.warning(
                    "Failed to create activity: status=%s, error=%s",
                    r.get("status_code"), r.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            r2 = client.get("/activity", params={"name": activity_name, "fields": "id,name"})
            api_calls += 1
            if r2["success"] and r2["body"].get("values"):
                activity_id = r2["body"]["values"][0]["id"]
            else:
                api_errors += 1
                logger.warning("Failed to find existing activity '%s'", activity_name)
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 7: Set hourly rate on project (POST-first, skip GET check) ---
        # Just POST the rate directly — if the project already has a rate, it will
        # return 409/422 which we can safely ignore (non-fatal).
        r = client.post(
            "/project/hourlyRates",
            body={
                "project": {"id": project_id},
                "startDate": today,
                "hourlyRateModel": "TYPE_FIXED_HOURLY_RATE",
                "fixedRate": hourly_rate,
            },
        )
        api_calls += 1
        if not r["success"] and r.get("status_code") not in (409, 422):
            api_errors += 1
            logger.warning(
                "Failed to set hourly rate for project %s: status=%s, error=%s",
                project_id, r.get("status_code"), r.get("error"),
            )
            # Non-fatal — continue, timesheet entry may still work

        self._check_timeout(start_time)

        # --- Step 8: Register timesheet entry ---
        r = client.post(
            "/timesheet/entry",
            body={
                "activity": {"id": activity_id},
                "employee": {"id": employee_id},
                "project": {"id": project_id},
                "date": today,
                "hours": hours,
            },
        )
        api_calls += 1
        if not r["success"]:
            # Duplicate entry — look up existing
            if r.get("status_code") in (400, 409, 422):
                lookup = client.get(
                    "/timesheet/entry",
                    params={
                        "employeeId": employee_id,
                        "projectId": project_id,
                        "activityId": activity_id,
                        "dateFrom": today,
                        "dateTo": today,
                        "fields": "id,hours",
                    },
                )
                api_calls += 1
                if not (lookup["success"] and lookup["body"].get("values")):
                    api_errors += 1
                    logger.warning(
                        "Failed to register timesheet entry and could not retrieve existing: "
                        "status=%s, error=%s",
                        r.get("status_code"), r.get("error"),
                    )
                    return self._make_result(api_calls=api_calls, api_errors=api_errors)
            else:
                api_errors += 1
                logger.warning(
                    "Failed to register timesheet entry: status=%s, error=%s",
                    r.get("status_code"), r.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 9: Generate invoice (conditional) ---
        if generate_invoice:
            # Step 9a: Create order
            r = client.post(
                "/order",
                body={
                    "customer": {"id": customer_id},
                    "orderDate": today,
                    "deliveryDate": today,
                    "orderLines": [
                        {
                            "description": f"{activity_name} - {project_name}",
                            "count": hours,
                            "unitPriceExcludingVatCurrency": hourly_rate,
                        }
                    ],
                },
            )
            api_calls += 1
            if not r["success"]:
                api_errors += 1
                logger.warning(
                    "Failed to create order: status=%s, error=%s",
                    r.get("status_code"), r.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)
            order_id = r["body"]["value"]["id"]

            self._check_timeout(start_time)

            # Step 9b: Create invoice from order
            r = client.post(
                "/invoice",
                body={
                    "invoiceDate": today,
                    "invoiceDueDate": due_date,
                    "orders": [{"id": order_id}],
                },
            )
            api_calls += 1
            if not r["success"]:
                api_errors += 1
                logger.warning(
                    "Failed to create invoice for order %s: status=%s, error=%s",
                    order_id, r.get("status_code"), r.get("error"),
                )
                return self._make_result(api_calls=api_calls, api_errors=api_errors)

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
