"""Execution plan: Register Hours (Tier 2).

Full flow:
  find/create customer → find/create department → find/create employee
  → grant entitlements (new employees only) → find/create project
  → find/create activity → check/set hourly rate → register timesheet entry
  → (optionally) create order + invoice.
"""
from datetime import date, timedelta

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

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
        self._check_timeout(start_time)
        api_calls = 0
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

        # --- Step 1: Find or create customer ---
        search_params = {"fields": "id,name"}
        if org_number:
            search_params["organizationNumber"] = org_number
        else:
            search_params["name"] = customer_name

        r = client.get("/customer", params=search_params)
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            customer_id = r["body"]["values"][0]["id"]
        else:
            create_body = {"name": customer_name}
            if org_number:
                create_body["organizationNumber"] = org_number
            r = client.post("/customer", body=create_body)
            api_calls += 1
            if not r["success"]:
                raise RuntimeError(
                    f"Failed to create customer: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
            customer_id = r["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 2: Find or create department ---
        r = client.get("/department", params={"fields": "id,name"})
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            dept_id = r["body"]["values"][0]["id"]
        else:
            r = client.post("/department", body={"name": "Avdeling", "departmentNumber": "1"})
            api_calls += 1
            if not r["success"]:
                raise RuntimeError(
                    f"Failed to create department: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
            dept_id = r["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 3: Find or create employee ---
        r = client.get("/employee", params={"email": employee_email, "fields": "id,firstName,lastName"})
        api_calls += 1
        employee_created = False
        if r["success"] and r["body"].get("values"):
            employee_id = r["body"]["values"][0]["id"]
        else:
            r = client.post(
                "/employee",
                body={
                    "firstName": employee_first,
                    "lastName": employee_last,
                    "email": employee_email,
                    "userType": "STANDARD",
                    "department": {"id": dept_id},
                },
            )
            api_calls += 1
            if not r["success"]:
                raise RuntimeError(
                    f"Failed to create employee: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
            employee_id = r["body"]["value"]["id"]
            employee_created = True

        self._check_timeout(start_time)

        # --- Step 4: Grant entitlements (only for newly created employees) ---
        if employee_created:
            r = client.put(
                "/employee/entitlement/:grantEntitlementsByTemplate",
                params={"employeeId": employee_id, "template": "ALL_PRIVILEGES"},
            )
            api_calls += 1
            if not r["success"]:
                raise RuntimeError(
                    f"Failed to grant entitlements for employee {employee_id}: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )

        self._check_timeout(start_time)

        # --- Step 5: Find or create project ---
        r = client.get(
            "/project",
            params={"name": project_name, "customerId": customer_id, "fields": "id,name"},
        )
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            project_id = r["body"]["values"][0]["id"]
        else:
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
            if not r["success"]:
                raise RuntimeError(
                    f"Failed to create project: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
            project_id = r["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 6: Find or create activity ---
        r = client.get("/activity", params={"name": activity_name, "fields": "id,name"})
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            activity_id = r["body"]["values"][0]["id"]
        else:
            r = client.post(
                "/activity",
                body={
                    "name": activity_name,
                    "activityType": "PROJECT_GENERAL_ACTIVITY",
                    "isChargeable": True,
                },
            )
            api_calls += 1
            if not r["success"]:
                raise RuntimeError(
                    f"Failed to create activity: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
            activity_id = r["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 7: Check/set hourly rate on project ---
        # Always GET first to avoid 409 duplicate if project was reused
        r = client.get(
            "/project/hourlyRates",
            params={"projectId": project_id, "fields": "id,hourlyRateModel,fixedRate"},
        )
        api_calls += 1
        if not (r["success"] and r["body"].get("values")):
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
            if not r["success"]:
                raise RuntimeError(
                    f"Failed to set hourly rate for project {project_id}: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )

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
                    raise RuntimeError(
                        f"Failed to register timesheet entry and could not retrieve existing: "
                        f"status={r.get('status_code')}, error={r.get('error')}"
                    )
            else:
                raise RuntimeError(
                    f"Failed to register timesheet entry: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )

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
                raise RuntimeError(
                    f"Failed to create order: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
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
                raise RuntimeError(
                    f"Failed to create invoice for order {order_id}: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )

        return self._make_result(api_calls=api_calls, api_errors=0)
