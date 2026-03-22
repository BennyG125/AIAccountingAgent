"""Execution plan: Project Lifecycle (Tier 3, 3x).

Full flow:
  1.  Find or create customer
  2.  Find or create department
  3.  Find or create project manager employee + grant ALL_PRIVILEGES (BEFORE project creation)
  4.  Find or create other (consultant) employees + grant ALL_PRIVILEGES
  5.  POST /project with budget (isFixedPrice=true, fixedprice=budget_amount)
  6.  Find or create activity
  7.  POST /timesheet/entry for each employee's hours
  8.  (If supplier cost) Find or create supplier, look up accounts 7000 + 2400,
      GET /ledger/vatType, POST /ledger/voucher with project link
  9.  POST /order + POST /invoice for customer billing
  10. GET /project (for version), PUT /project/{id} with isClosed=true

CRITICAL: Employee entitlements MUST be granted before POST /project.
CRITICAL: On employee 422 "e-postadressen er i bruk" fallback to GET /employee?email=X.
CRITICAL: Voucher rows must start at 1, all 4 amount fields required.
          Row 1 = expense debit (net, with vatType + project link).
          Row 2 = supplier payable credit (-gross, NO vatType, NO amountGross).
NEVER use /incomingInvoice — always 403. Use /ledger/voucher.
"""
import copy
import datetime

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {
            "type": "string",
            "description": "Project name (required)",
        },
        "customer_name": {
            "type": "string",
            "description": "Customer / company name (required)",
        },
        "customer_org_number": {
            "type": ["string", "null"],
            "description": "Customer organisation number (e.g. '909990343'), if provided",
        },
        "budget_amount": {
            "type": "number",
            "description": (
                "Project budget in NOK. Used as fixedprice when isFixedPrice=true. "
                "Required."
            ),
        },
        "project_manager_first_name": {
            "type": "string",
            "description": "Project manager first name (required)",
        },
        "project_manager_last_name": {
            "type": "string",
            "description": "Project manager last name (required)",
        },
        "project_manager_email": {
            "type": "string",
            "description": (
                "Project manager email. Generate as "
                "firstname.lastname@example.org if not given."
            ),
        },
        "project_manager_hours": {
            "type": "number",
            "description": "Hours to register for the project manager (required)",
        },
        "other_employees": {
            "type": "array",
            "description": "Other employees to register hours for (consultants, etc.)",
            "items": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "email": {"type": "string"},
                    "hours": {"type": "number"},
                },
                "required": ["first_name", "last_name", "email", "hours"],
            },
        },
        "supplier_name": {
            "type": ["string", "null"],
            "description": "Supplier name if there is a supplier cost, else null",
        },
        "supplier_org_number": {
            "type": ["string", "null"],
            "description": "Supplier organisation number, if provided",
        },
        "supplier_cost_amount": {
            "type": ["number", "null"],
            "description": "Gross supplier cost amount in NOK (including 25% VAT), or null",
        },
        "activity_name": {
            "type": "string",
            "description": "Activity name for timesheet entries. Default: 'Consulting'",
        },
        "start_date": {
            "type": ["string", "null"],
            "description": "Project start date YYYY-MM-DD. Defaults to today.",
        },
    },
    "required": [
        "project_name",
        "customer_name",
        "budget_amount",
        "project_manager_first_name",
        "project_manager_last_name",
        "project_manager_email",
        "project_manager_hours",
        "activity_name",
    ],
}


@register
class ProjectLifecyclePlan(ExecutionPlan):
    task_type = "project_lifecycle"
    description = (
        "Full project lifecycle: find/create customer + department + employees, "
        "grant entitlements, create fixed-price project, register hours, "
        "optionally post supplier cost voucher, create order+invoice, close project"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        today = datetime.date.today().isoformat()
        due_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        start_date = params.get("start_date") or today

        project_name = params["project_name"]
        customer_name = params["customer_name"]
        customer_org = params.get("customer_org_number")
        budget_amount = float(params["budget_amount"])

        pm_first = params["project_manager_first_name"]
        pm_last = params["project_manager_last_name"]
        pm_email = params["project_manager_email"]
        pm_hours = float(params["project_manager_hours"])

        other_employees = params.get("other_employees") or []
        activity_name = params.get("activity_name") or "Consulting"

        supplier_name = params.get("supplier_name")
        supplier_org = params.get("supplier_org_number")
        supplier_cost = params.get("supplier_cost_amount")
        has_supplier_cost = bool(supplier_name and supplier_cost)

        api_calls = 0
        api_errors = 0

        # ------------------------------------------------------------------
        # Step 1: Find or create customer
        # ------------------------------------------------------------------
        self._check_timeout(start_time)
        search_params = {"count": 1, "fields": "id,name"}
        if customer_org:
            search_params["organizationNumber"] = customer_org
        else:
            search_params["name"] = customer_name

        r = client.get("/customer", params=search_params)
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            customer_id = r["body"]["values"][0]["id"]
        else:
            create_body = {"name": customer_name}
            if customer_org:
                create_body["organizationNumber"] = customer_org
            r = client.post("/customer", body=create_body)
            api_calls += 1
            if not r["success"]:
                # Fallback: org number conflict — search again
                if customer_org and r.get("status_code") == 422:
                    r2 = client.get(
                        "/customer",
                        params={"organizationNumber": customer_org, "fields": "id,name"},
                    )
                    api_calls += 1
                    if r2["success"] and r2["body"].get("values"):
                        customer_id = r2["body"]["values"][0]["id"]
                    else:
                        api_errors += 1
                        raise RuntimeError(
                            f"Failed to find/create customer '{customer_name}': "
                            f"status={r.get('status_code')}, error={r.get('error')}"
                        )
                else:
                    api_errors += 1
                    raise RuntimeError(
                        f"Failed to create customer '{customer_name}': "
                        f"status={r.get('status_code')}, error={r.get('error')}"
                    )
            else:
                customer_id = r["body"]["value"]["id"]

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 2: Find or create department (required for employee creation)
        # ------------------------------------------------------------------
        r = client.get("/department", params={"fields": "id,name", "count": 1})
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            dept_id = r["body"]["values"][0]["id"]
        else:
            r = client.post(
                "/department",
                body={"name": "Avdeling", "departmentNumber": "100"},
            )
            api_calls += 1
            if not r["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to find/create department: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
            dept_id = r["body"]["value"]["id"]

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 3: Find or create project manager employee
        # ------------------------------------------------------------------
        pm_id = self._find_or_create_employee(
            client, pm_first, pm_last, pm_email, dept_id
        )
        api_calls += 2  # search + possible create

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 4: Grant ALL_PRIVILEGES to project manager (CRITICAL — BEFORE project)
        # ------------------------------------------------------------------
        r = client.put(
            "/employee/entitlement/:grantEntitlementsByTemplate",
            params={"employeeId": pm_id, "template": "ALL_PRIVILEGES"},
        )
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to grant entitlements to project manager {pm_id}: "
                f"status={r.get('status_code')}, error={r.get('error')}"
            )

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 4b: Find or create other employees + grant entitlements
        # ------------------------------------------------------------------
        other_employee_ids = []
        for emp in other_employees:
            self._check_timeout(start_time)
            emp_id = self._find_or_create_employee(
                client,
                emp["first_name"],
                emp["last_name"],
                emp["email"],
                dept_id,
            )
            api_calls += 2  # search + possible create

            # Grant entitlements to all employees so they can log hours
            r = client.put(
                "/employee/entitlement/:grantEntitlementsByTemplate",
                params={"employeeId": emp_id, "template": "ALL_PRIVILEGES"},
            )
            api_calls += 1
            # Non-fatal if this fails — continue
            if not r["success"]:
                api_errors += 1

            other_employee_ids.append(emp_id)

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 5: Create project with fixed-price budget
        # ------------------------------------------------------------------
        r = client.get(
            "/project",
            params={
                "name": project_name,
                "customerId": customer_id,
                "fields": "id,name",
                "count": 1,
            },
        )
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            project_id = r["body"]["values"][0]["id"]
        else:
            project_body = {
                "name": project_name,
                "projectManager": {"id": pm_id},
                "customer": {"id": customer_id},
                "startDate": start_date,
                "isFixedPrice": True,
                "fixedprice": budget_amount,
            }
            r = client.post("/project", body=project_body)
            api_calls += 1
            if not r["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to create project '{project_name}': "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
            project_id = r["body"]["value"]["id"]

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 6: Find or create activity
        # ------------------------------------------------------------------
        r = client.get(
            "/activity",
            params={"name": activity_name, "isGeneral": True, "fields": "id,name", "count": 1},
        )
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
                # Name conflict — retrieve existing
                if r.get("status_code") == 422:
                    r2 = client.get(
                        "/activity",
                        params={"name": activity_name, "fields": "id,name", "count": 1},
                    )
                    api_calls += 1
                    if r2["success"] and r2["body"].get("values"):
                        activity_id = r2["body"]["values"][0]["id"]
                    else:
                        api_errors += 1
                        raise RuntimeError(
                            f"Failed to find/create activity '{activity_name}': "
                            f"status={r.get('status_code')}, error={r.get('error')}"
                        )
                else:
                    api_errors += 1
                    raise RuntimeError(
                        f"Failed to create activity '{activity_name}': "
                        f"status={r.get('status_code')}, error={r.get('error')}"
                    )
            else:
                activity_id = r["body"]["value"]["id"]

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 7: Register hours for all employees (bulk)
        # ------------------------------------------------------------------
        timesheet_entries = [
            {
                "activity": {"id": activity_id},
                "employee": {"id": pm_id},
                "project": {"id": project_id},
                "date": today,
                "hours": pm_hours,
            }
        ]
        for i, emp_id in enumerate(other_employee_ids):
            timesheet_entries.append({
                "activity": {"id": activity_id},
                "employee": {"id": emp_id},
                "project": {"id": project_id},
                "date": today,
                "hours": float(other_employees[i]["hours"]),
            })

        bulk_ts = client.post("/timesheet/entry/list", body=timesheet_entries)
        api_calls += 1
        if not bulk_ts["success"]:
            # Fallback: register individually
            api_calls, api_errors = self._register_hours(
                client, pm_id, project_id, activity_id, pm_hours, today,
                api_calls, api_errors,
            )
            for i, emp_id in enumerate(other_employee_ids):
                self._check_timeout(start_time)
                emp_hours = float(other_employees[i]["hours"])
                api_calls, api_errors = self._register_hours(
                    client, emp_id, project_id, activity_id, emp_hours, today,
                    api_calls, api_errors,
                )

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 8: Register supplier cost (conditional)
        # ------------------------------------------------------------------
        if has_supplier_cost:
            api_calls, api_errors = self._register_supplier_cost(
                client, supplier_name, supplier_org, float(supplier_cost),
                project_id, today, api_calls, api_errors, start_time,
            )

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 9: Create order + invoice for customer
        # ------------------------------------------------------------------
        # NOTE: Do NOT link order to project — Tripletex treats linked orders as
        # "underordre" that must be closed before the project can close, and there
        # is no order-close endpoint.
        # Create invoice with inline order (1 call instead of 2)
        # NOTE: Do NOT link to project — causes "underordre" issues
        r = client.post(
            "/invoice",
            body={
                "invoiceDate": today,
                "invoiceDueDate": due_date,
                "orders": [{
                    "customer": {"id": customer_id},
                    "orderDate": today,
                    "deliveryDate": today,
                    "orderLines": [{
                        "description": f"Prosjektleveranse {project_name}",
                        "count": 1,
                        "unitPriceExcludingVatCurrency": budget_amount,
                    }],
                }],
            },
        )
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to create invoice (inline order): "
                f"status={r.get('status_code')}, error={r.get('error')}"
            )

        self._check_timeout(start_time)

        # ------------------------------------------------------------------
        # Step 10: Close sub-projects, then close main project
        # ------------------------------------------------------------------
        # Close any open sub-projects first (Tripletex requires this)
        sub_r = client.get(
            "/project",
            params={
                "parentProjectId": project_id,
                "isClosed": False,
                "fields": "id,version,name",
            },
        )
        api_calls += 1
        if sub_r["success"]:
            for sub in sub_r["body"].get("values", []):
                self._check_timeout(start_time)
                sub_close = client.put(
                    f"/project/{sub['id']}",
                    body={
                        "id": sub["id"],
                        "version": sub["version"],
                        "isClosed": True,
                        "endDate": today,
                    },
                )
                api_calls += 1
                if not sub_close["success"]:
                    api_errors += 1
                    # Non-fatal: continue closing others

        # Get main project version (may have changed after sub-project closes)
        r = client.get(f"/project/{project_id}", params={"fields": "id,version"})
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to get project {project_id} for version: "
                f"status={r.get('status_code')}, error={r.get('error')}"
            )
        project_version = r["body"]["value"]["version"]

        r = client.put(
            f"/project/{project_id}",
            body={
                "id": project_id,
                "version": project_version,
                "isClosed": True,
                "endDate": today,
            },
        )
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to close project {project_id}: "
                f"status={r.get('status_code')}, error={r.get('error')}"
            )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_or_create_employee(
        self, client, first_name, last_name, email, dept_id
    ) -> int:
        """Find employee by email; create if not found.

        On 422 'e-postadressen er i bruk', falls back to GET /employee?email=X.
        Returns employee ID.
        """
        r = client.get(
            "/employee",
            params={"email": email, "fields": "id,firstName,lastName", "count": 1},
        )
        if r["success"] and r["body"].get("values"):
            return r["body"]["values"][0]["id"]

        # Not found — create
        r = client.post(
            "/employee",
            body={
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "userType": "STANDARD",
                "department": {"id": dept_id},
            },
        )
        if r["success"]:
            return r["body"]["value"]["id"]

        # Email already in use (422) — fetch the existing employee
        if r.get("status_code") == 422:
            r2 = client.get(
                "/employee",
                params={"email": email, "fields": "id,firstName,lastName", "count": 1},
            )
            if r2["success"] and r2["body"].get("values"):
                return r2["body"]["values"][0]["id"]

        raise RuntimeError(
            f"Failed to find or create employee {first_name} {last_name} ({email}): "
            f"status={r.get('status_code')}, error={r.get('error')}"
        )

    def _register_hours(
        self, client, employee_id, project_id, activity_id, hours, date_str,
        api_calls, api_errors,
    ):
        """POST a timesheet entry; handles duplicate gracefully.

        Returns updated (api_calls, api_errors).
        """
        r = client.post(
            "/timesheet/entry",
            body={
                "activity": {"id": activity_id},
                "employee": {"id": employee_id},
                "project": {"id": project_id},
                "date": date_str,
                "hours": hours,
            },
        )
        api_calls += 1
        if not r["success"]:
            if r.get("status_code") in (400, 409, 422):
                # Possible duplicate — try to look up
                lookup = client.get(
                    "/timesheet/entry",
                    params={
                        "employeeId": employee_id,
                        "projectId": project_id,
                        "activityId": activity_id,
                        "dateFrom": date_str,
                        "dateTo": date_str,
                        "fields": "id,hours",
                    },
                )
                api_calls += 1
                if not (lookup["success"] and lookup["body"].get("values")):
                    api_errors += 1
                    raise RuntimeError(
                        f"Failed to register timesheet entry for employee {employee_id} "
                        f"and could not find existing: "
                        f"status={r.get('status_code')}, error={r.get('error')}"
                    )
            else:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to register timesheet entry for employee {employee_id}: "
                    f"status={r.get('status_code')}, error={r.get('error')}"
                )
        return api_calls, api_errors

    def _register_supplier_cost(
        self, client, supplier_name, supplier_org, gross_amount,
        project_id, date_str, api_calls, api_errors, start_time,
    ):
        """Find/create supplier, look up accounts + VAT type, post ledger voucher.

        Returns updated (api_calls, api_errors).
        """
        vat_rate = 0.25
        net_amount = round(gross_amount / (1 + vat_rate), 2)

        # Find or create supplier
        self._check_timeout(start_time)
        search_p = {"count": 1, "fields": "id,name"}
        if supplier_org:
            search_p["organizationNumber"] = supplier_org
        else:
            search_p["name"] = supplier_name

        r = client.get("/supplier", params=search_p)
        api_calls += 1
        supplier_id = None
        if r["success"] and r["body"].get("values"):
            supplier_id = r["body"]["values"][0]["id"]

        if supplier_id is None:
            create_body = {"name": supplier_name}
            if supplier_org:
                create_body["organizationNumber"] = supplier_org
            r = client.post("/supplier", body=create_body)
            api_calls += 1
            if not r["success"]:
                if supplier_org and r.get("status_code") == 422:
                    r2 = client.get(
                        "/supplier",
                        params={"organizationNumber": supplier_org, "fields": "id,name"},
                    )
                    api_calls += 1
                    if r2["success"] and r2["body"].get("values"):
                        supplier_id = r2["body"]["values"][0]["id"]
                    else:
                        api_errors += 1
                        raise RuntimeError(
                            f"Failed to find/create supplier '{supplier_name}': "
                            f"status={r.get('status_code')}, error={r.get('error')}"
                        )
                else:
                    api_errors += 1
                    raise RuntimeError(
                        f"Failed to create supplier '{supplier_name}': "
                        f"status={r.get('status_code')}, error={r.get('error')}"
                    )
            else:
                supplier_id = r["body"]["value"]["id"]

        # Look up expense account 7000
        self._check_timeout(start_time)
        r = client.get("/ledger/account", params={"number": "7000", "fields": "id,number"})
        api_calls += 1
        if not r["success"] or not r["body"].get("values"):
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up account 7000: "
                f"status={r.get('status_code')}, error={r.get('error')}"
            )
        expense_account_id = r["body"]["values"][0]["id"]

        # Look up supplier payable account 2400
        r = client.get("/ledger/account", params={"number": "2400", "fields": "id,number"})
        api_calls += 1
        if not r["success"] or not r["body"].get("values"):
            api_errors += 1
            raise RuntimeError(
                f"Failed to look up account 2400: "
                f"status={r.get('status_code')}, error={r.get('error')}"
            )
        supplier_payable_id = r["body"]["values"][0]["id"]

        # Look up incoming VAT type
        self._check_timeout(start_time)
        r = client.get("/ledger/vatType", params={"fields": "id,number,percentage"})
        api_calls += 1
        vat_type_id = None
        if r["success"]:
            target_pct = round(vat_rate * 100)
            for vt in r["body"].get("values", []):
                pct = vt.get("percentage")
                if pct is not None and round(float(pct)) == target_pct:
                    vat_type_id = vt["id"]
                    break
            if vat_type_id is None:
                values = r["body"].get("values", [])
                if values:
                    vat_type_id = values[0]["id"]

        if vat_type_id is None:
            api_errors += 1
            raise RuntimeError("No VAT types available in this sandbox")

        # Post supplier cost voucher with project link on expense row
        self._check_timeout(start_time)
        description_voucher = f"Leverandørkostnad - {supplier_name}"

        voucher_body = {
            "date": date_str,
            "description": description_voucher,
            "postings": [
                {
                    "row": 1,
                    "account": {"id": expense_account_id},
                    "amount": net_amount,
                    "amountCurrency": net_amount,
                    "amountGross": gross_amount,
                    "amountGrossCurrency": gross_amount,
                    "currency": {"id": 1},
                    "vatType": {"id": vat_type_id},
                    "supplier": {"id": supplier_id},
                    "project": {"id": project_id},
                    "description": description_voucher,
                },
                {
                    "row": 2,
                    "account": {"id": supplier_payable_id},
                    "supplier": {"id": supplier_id},
                    "amount": -gross_amount,
                    "amountCurrency": -gross_amount,
                    "currency": {"id": 1},
                    "description": description_voucher,
                },
            ],
        }

        r = client.post("/ledger/voucher", body=voucher_body)
        api_calls += 1
        if not r["success"] and r.get("status_code") == 422:
            # vatType may be invalid in this sandbox — retry without it
            cleaned_body = copy.deepcopy(voucher_body)
            for posting in cleaned_body.get("postings", []):
                posting.pop("vatType", None)
            r = client.post("/ledger/voucher", body=cleaned_body)
            api_calls += 1
        if not r["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to post supplier cost voucher: "
                f"status={r.get('status_code')}, error={r.get('error')}"
            )

        return api_calls, api_errors
