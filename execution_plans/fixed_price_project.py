"""Execution plan: Fixed Price Project (Tier 2).

Full flow:
  1. Find or create customer by org number
  2. Find or create employee (project manager) by email
  3. PUT /employee/entitlement/:grantEntitlementsByTemplate  <- MUST happen before project
  4. POST /project {isFixedPrice: true, fixedprice: amount, customer, projectManager, name}
  5. (Optional) If invoice_percentage provided:
       POST /product -> POST /order (unitPrice = fixedprice * pct/100, project linked) -> POST /invoice

This plan NEVER raises RuntimeError — it always returns a result dict.
"""
import datetime
import logging

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "project_name": "string — project name (required)",
    "fixed_price": "number — fixed price amount in NOK (required)",
    "customer_name": "string — customer/company name (required)",
    "org_number": "string|null — organisation number if mentioned",
    "pm_first_name": "string — project manager first name (required)",
    "pm_last_name": "string — project manager last name (required)",
    "pm_email": "string — project manager email (required)",
    "start_date": "string — project start date in YYYY-MM-DD format, default today if not mentioned",
    "invoice_percentage": "number|null — percentage of fixed price to invoice immediately (e.g. 30 for 30%), null if not mentioned",
}


@register
class FixedPriceProjectPlan(ExecutionPlan):
    task_type = "fixed_price_project"
    description = (
        "Create a fixed-price project: find/create customer + PM employee, "
        "grant PM entitlements, POST /project with isFixedPrice=true, "
        "optionally invoice a percentage of the fixed price"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0
        error_details = []

        today = datetime.date.today().isoformat()

        # --- Step 1: Find or create customer ---
        customer_name = params["customer_name"]
        org_number = params.get("org_number")

        customer_create_body = {"name": customer_name}
        if org_number:
            customer_create_body["organizationNumber"] = org_number

        search_params = {"name": customer_name, "count": 1}
        if org_number:
            search_params = {"organizationNumber": org_number, "count": 1}

        customer_id = None

        # Try search first
        search_result = client.get("/customer", params=search_params)
        api_calls += 1
        if search_result["success"] and search_result["body"].get("values"):
            customer_id = search_result["body"]["values"][0]["id"]
        else:
            # Not found — try to create
            create_result = client.post("/customer", body=customer_create_body)
            api_calls += 1
            if create_result["success"]:
                customer_id = create_result["body"]["value"]["id"]
            else:
                # Creation failed — try fallback searches
                # Maybe customer already exists; try by name if we searched by org, or vice versa
                fallback_params_list = []
                if org_number:
                    # We searched by org number, try by name
                    fallback_params_list.append({"name": customer_name, "count": 1})
                else:
                    # We searched by name, try broader search
                    fallback_params_list.append({"name": customer_name, "count": 5})

                for fb_params in fallback_params_list:
                    fb_result = client.get("/customer", params=fb_params)
                    api_calls += 1
                    if fb_result["success"] and fb_result["body"].get("values"):
                        customer_id = fb_result["body"]["values"][0]["id"]
                        break

                if customer_id is None:
                    err_msg = (
                        f"Failed to find or create customer '{customer_name}': "
                        f"status={create_result.get('status_code')}, "
                        f"error={create_result.get('error')}"
                    )
                    logger.warning(err_msg)
                    api_errors += 1
                    error_details.append(err_msg)
                    # Customer is critical for project — return early
                    return self._make_result(
                        api_calls=api_calls,
                        api_errors=api_errors,
                        error_details=error_details,
                    )

        self._check_timeout(start_time)

        # --- Step 2: Find or create employee (project manager) ---
        pm_email = params["pm_email"]
        pm_first_name = params["pm_first_name"]
        pm_last_name = params["pm_last_name"]
        employee_id = None

        # Try to find existing employee by email first
        employee_result = client.get("/employee", params={"email": pm_email, "count": 1})
        api_calls += 1
        if employee_result["success"] and employee_result["body"].get("values"):
            employee_id = employee_result["body"]["values"][0]["id"]
        else:
            # Employee not found — need a department to create one
            dept_result = client.get("/department", params={"count": 1})
            api_calls += 1
            dept_id = None
            if dept_result["success"] and dept_result["body"].get("values"):
                dept_id = dept_result["body"]["values"][0]["id"]
            else:
                err_msg = (
                    f"Failed to find any department for employee creation: "
                    f"status={dept_result.get('status_code')}, error={dept_result.get('error')}"
                )
                logger.warning(err_msg)
                api_errors += 1
                error_details.append(err_msg)
                # Without a department we cannot create an employee, which is critical
                return self._make_result(
                    api_calls=api_calls,
                    api_errors=api_errors,
                    error_details=error_details,
                )

            create_emp_result = client.post(
                "/employee",
                body={
                    "firstName": pm_first_name,
                    "lastName": pm_last_name,
                    "email": pm_email,
                    "dateOfBirth": "1990-01-01",
                    "userType": "STANDARD",
                    "department": {"id": dept_id},
                },
            )
            api_calls += 1
            if create_emp_result["success"]:
                employee_id = create_emp_result["body"]["value"]["id"]
            else:
                # Creation failed — try to find by email again (maybe race condition or already exists)
                retry = client.get("/employee", params={"email": pm_email, "count": 1})
                api_calls += 1
                if retry["success"] and retry["body"].get("values"):
                    employee_id = retry["body"]["values"][0]["id"]
                else:
                    # Try searching by name as last resort
                    name_search = client.get(
                        "/employee",
                        params={"firstName": pm_first_name, "lastName": pm_last_name, "count": 1},
                    )
                    api_calls += 1
                    if name_search["success"] and name_search["body"].get("values"):
                        employee_id = name_search["body"]["values"][0]["id"]
                    else:
                        err_msg = (
                            f"Failed to create or find employee '{pm_email}': "
                            f"status={create_emp_result.get('status_code')}, "
                            f"error={create_emp_result.get('error')}"
                        )
                        logger.warning(err_msg)
                        api_errors += 1
                        error_details.append(err_msg)
                        # Employee is critical for project — return early
                        return self._make_result(
                            api_calls=api_calls,
                            api_errors=api_errors,
                            error_details=error_details,
                        )

        self._check_timeout(start_time)

        # --- Step 3: Grant ALL_PRIVILEGES entitlements to project manager ---
        # MUST happen before POST /project — PM needs AUTH_PROJECT_MANAGER entitlement
        entitlement_result = client.put(
            "/employee/entitlement/:grantEntitlementsByTemplate",
            params={"employeeId": employee_id, "template": "ALL_PRIVILEGES"},
        )
        api_calls += 1
        if not entitlement_result["success"]:
            # Non-critical: the employee may already have entitlements; log and continue
            err_msg = (
                f"Failed to grant entitlements to employee {employee_id}: "
                f"status={entitlement_result.get('status_code')}, "
                f"error={entitlement_result.get('error')}"
            )
            logger.warning(err_msg)
            api_errors += 1
            error_details.append(err_msg)
            # Continue — project creation may still succeed if PM already has entitlements

        self._check_timeout(start_time)

        # --- Step 4: Create fixed-price project ---
        fixed_price = params["fixed_price"]
        start_date = params.get("start_date") or today

        project_body = {
            "name": params["project_name"],
            "projectManager": {"id": employee_id},
            "customer": {"id": customer_id},
            "startDate": start_date,
            "isFixedPrice": True,
            "fixedprice": fixed_price,
        }

        project_result = client.post("/project", body=project_body)
        api_calls += 1
        if not project_result["success"]:
            err_msg = (
                f"Failed to create project '{params['project_name']}': "
                f"status={project_result.get('status_code')}, "
                f"error={project_result.get('error')}"
            )
            logger.warning(err_msg)
            api_errors += 1
            error_details.append(err_msg)
            # Project creation is the core goal — return what we have
            return self._make_result(
                api_calls=api_calls,
                api_errors=api_errors,
                error_details=error_details,
            )
        project_id = project_result["body"]["value"]["id"]

        self._check_timeout(start_time)

        # --- Step 5 (optional): Invoice a percentage of the fixed price ---
        invoice_percentage = params.get("invoice_percentage")
        if invoice_percentage is not None:
            unit_price = fixed_price * invoice_percentage / 100

            # 5a: Create a product for the invoice line
            product_name = f"{params['project_name']} — {invoice_percentage}%"
            product_result = client.post(
                "/product",
                body={
                    "name": product_name,
                    "priceExcludingVatCurrency": unit_price,
                },
            )
            api_calls += 1
            if not product_result["success"]:
                err_msg = (
                    f"Failed to create product for invoice: "
                    f"status={product_result.get('status_code')}, "
                    f"error={product_result.get('error')}"
                )
                logger.warning(err_msg)
                api_errors += 1
                error_details.append(err_msg)
                # Cannot invoice without a product — return what we have (project was created)
                return self._make_result(
                    api_calls=api_calls,
                    api_errors=api_errors,
                    error_details=error_details,
                )
            product_id = product_result["body"]["value"]["id"]

            self._check_timeout(start_time)

            # 5b: Create invoice with inline order (1 call instead of 2)
            invoice_result = client.post(
                "/invoice",
                body={
                    "invoiceDate": today,
                    "invoiceDueDate": today,
                    "orders": [{
                        "customer": {"id": customer_id},
                        "orderDate": today,
                        "deliveryDate": today,
                        "orderLines": [{
                            "product": {"id": product_id},
                            "count": 1,
                            "unitPriceExcludingVatCurrency": unit_price,
                        }],
                    }],
                },
            )
            api_calls += 1
            if not invoice_result["success"]:
                err_msg = (
                    f"Failed to create invoice: "
                    f"status={invoice_result.get('status_code')}, "
                    f"error={invoice_result.get('error')}"
                )
                logger.warning(err_msg)
                api_errors += 1
                error_details.append(err_msg)
                # Invoice failed but project was created — return what we have
                return self._make_result(
                    api_calls=api_calls,
                    api_errors=api_errors,
                    error_details=error_details,
                )

        return self._make_result(
            api_calls=api_calls,
            api_errors=api_errors,
            error_details=error_details if error_details else None,
        )
