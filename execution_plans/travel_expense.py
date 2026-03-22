"""Execution plan: Travel Expense (Tier 2).

Full flow:
  find/create employee → grant entitlements (new employees only)
  → GET paymentType → GET costCategories → GET rateCategories
  → POST /travelExpense with embedded costs + perDiemCompensations
"""
import logging
from datetime import date

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

# Fields the LLM should extract from the prompt
EXTRACTION_SCHEMA = {
    "employee_first_name": "string — employee first name (required)",
    "employee_last_name": "string — employee last name (required)",
    "employee_email": "string — employee email address (required)",
    "title": "string — travel expense report title / trip description (required)",
    "departure_date": "string|null — YYYY-MM-DD departure date (use today if not specified)",
    "return_date": "string|null — YYYY-MM-DD return date (use today if not specified)",
    "departure_from": "string|null — departure city/location",
    "destination": "string|null — destination city/location",
    "per_diem_days": "number|null — number of days for per diem / daily allowance (diett/Tagegeld)",
    "per_diem_rate": "number|null — daily allowance rate in NOK (if specified)",
    "costs": (
        "array of {description: string, amount: number, date: string|null} — "
        "individual out-of-pocket expenses (flights, taxi, hotel, etc.)"
    ),
}


@register
class TravelExpensePlan(ExecutionPlan):
    task_type = "travel_expense"
    description = (
        "Find/create employee; fetch paymentType, costCategories, rateCategories; "
        "POST travelExpense with costs and perDiemCompensations in one call"
    )

    def execute(self, client, params, start_time):
        # Validate required params
        required = ["employee_email", "employee_first_name", "employee_last_name", "title"]
        missing = [f for f in required if not params.get(f)]
        if missing:
            logger.warning(f"Missing required params for {self.task_type}: {missing}")
            return None

        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0
        today = date.today().isoformat()

        employee_email = params["employee_email"]
        employee_first = params["employee_first_name"]
        employee_last = params["employee_last_name"]
        title = params["title"]
        departure_date = params.get("departure_date") or today
        return_date = params.get("return_date") or today
        departure_from = params.get("departure_from") or ""
        destination = params.get("destination") or ""
        per_diem_days = params.get("per_diem_days")
        costs_input = params.get("costs") or []

        # --- Step 1: Find or create employee ---
        employee_id = None
        r = client.get("/employee", params={"email": employee_email, "fields": "id,firstName,lastName"})
        api_calls += 1
        employee_created = False
        if r["success"] and r["body"].get("values"):
            employee_id = r["body"]["values"][0]["id"]
        else:
            # Need a department first
            dept_id = None
            r_dept = client.get("/department", params={"fields": "id,name"})
            api_calls += 1
            if r_dept["success"] and r_dept["body"].get("values"):
                dept_id = r_dept["body"]["values"][0]["id"]
            else:
                r_dept = client.post("/department", body={"name": "Avdeling", "departmentNumber": "1"})
                api_calls += 1
                if not r_dept["success"]:
                    api_errors += 1
                    logger.warning(
                        "Failed to create department: status=%s, error=%s",
                        r_dept.get('status_code'), r_dept.get('error'),
                    )
                    return self._make_result(api_calls=api_calls, api_errors=api_errors)
                dept_id = r_dept["body"]["value"]["id"]

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
            if not r["success"]:
                # 422 may mean email already in use — retry search
                if r.get("status_code") == 422:
                    r2 = client.get(
                        "/employee",
                        params={"email": employee_email, "fields": "id,firstName,lastName"},
                    )
                    api_calls += 1
                    if r2["success"] and r2["body"].get("values"):
                        employee_id = r2["body"]["values"][0]["id"]
                    else:
                        api_errors += 1
                        logger.warning(
                            "Failed to create employee and could not find existing: "
                            "status=%s, error=%s",
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
            else:
                employee_id = r["body"]["value"]["id"]
                employee_created = True

        if employee_id is None:
            api_errors += 1
            logger.warning("employee_id is None after find/create — cannot continue")
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 2: Grant entitlements for new employees ---
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
                    employee_id, r.get('status_code'), r.get('error'),
                )
                # Non-fatal — continue, travel expense may still work

        self._check_timeout(start_time)

        # --- Step 3: GET paymentType (use first result) ---
        r = client.get("/travelExpense/paymentType", params={"fields": "id,description"})
        api_calls += 1
        payment_type_id = None
        if r["success"] and r["body"].get("values"):
            payment_type_id = r["body"]["values"][0]["id"]
        if payment_type_id is None:
            api_errors += 1
            logger.warning("No payment types found on /travelExpense/paymentType")
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # --- Step 4: GET costCategories (field is "description", NOT "name") ---
        r = client.get(
            "/travelExpense/costCategory",
            params={"fields": "id,description", "showOnTravelExpenses": "true"},
        )
        api_calls += 1
        cost_categories = []
        if r["success"]:
            cost_categories = r["body"].get("values", [])

        self._check_timeout(start_time)

        # --- Step 5: GET rateCategories (field is "name", NOT "description") ---
        r = client.get(
            "/travelExpense/rateCategory",
            params={"fields": "id,name,type,fromDate,toDate,isValidDomestic"},
        )
        api_calls += 1
        rate_categories = []
        if r["success"]:
            rate_categories = r["body"].get("values", [])

        self._check_timeout(start_time)

        # --- Step 6: Match cost categories to expenses ---
        def find_cost_category(description: str) -> int | None:
            """Find the best matching cost category ID for a given expense description."""
            desc_lower = description.lower()
            # Keyword mappings: order matters (most specific first)
            keyword_map = [
                (["fly", "flight", "flug", "avión", "avion", "aviao"], "fly"),
                (["taxi", "cab"], "taxi"),
                (["hotell", "hotel", "accommodation", "unterkunft", "alojamiento"], "hotell"),
                (["tog", "train", "bahn", "tren", "comboio"], "tog"),
                (["buss", "bus"], "buss"),
                (["ferge", "ferry", "fähre", "ferri"], "ferge"),
                (["leiebil", "car hire", "rental", "mietwagen", "alquiler"], "leiebil"),
                (["parkering", "parking"], "parkering"),
            ]
            for keywords, cat_hint in keyword_map:
                if any(kw in desc_lower for kw in keywords):
                    # Find category whose description contains the hint
                    for cat in cost_categories:
                        cat_desc = (cat.get("description") or "").lower()
                        if cat_hint in cat_desc:
                            return cat["id"]
            # Fallback: return first available category
            if cost_categories:
                return cost_categories[0]["id"]
            return None

        # --- Step 7: Find best per diem rate category ---
        per_diem_rate_id = None
        if per_diem_days:
            # Prefer domestic overnight for multi-day trips, else dagsreise over 12 timer
            target_year = departure_date[:4] if departure_date else str(date.today().year)
            preferred_keywords = [
                "overnatting",   # overnight domestic — most common competition scenario
                "over 12",       # dagsreise over 12 timer
                "6-12",          # dagsreise 6-12 timer
                "per_diem",      # generic fallback
            ]
            for keyword in preferred_keywords:
                for cat in rate_categories:
                    cat_name = (cat.get("name") or "").lower()
                    from_date = cat.get("fromDate") or ""
                    cat_year = from_date[:4] if from_date else ""
                    if keyword in cat_name and cat_year == target_year:
                        per_diem_rate_id = cat["id"]
                        break
                if per_diem_rate_id:
                    break

            # Second pass: ignore year filter if nothing matched
            if per_diem_rate_id is None:
                for keyword in preferred_keywords:
                    for cat in rate_categories:
                        cat_name = (cat.get("name") or "").lower()
                        if keyword in cat_name:
                            per_diem_rate_id = cat["id"]
                            break
                    if per_diem_rate_id:
                        break

            # Last resort: any PER_DIEM type
            if per_diem_rate_id is None:
                for cat in rate_categories:
                    if "per_diem" in (cat.get("type") or "").lower():
                        per_diem_rate_id = cat["id"]
                        break

        self._check_timeout(start_time)

        # --- Step 8: Build costs array ---
        costs_body = []
        for expense in costs_input:
            expense_desc = expense.get("description") or ""
            expense_amount = expense.get("amount") or 0
            expense_date = expense.get("date") or departure_date or today
            cat_id = find_cost_category(expense_desc)
            cost_item = {
                "paymentType": {"id": payment_type_id},
                "date": expense_date,
                "amountCurrencyIncVat": expense_amount,
                "currency": {"id": 1},  # NOK
                "comments": expense_desc,
            }
            if cat_id is not None:
                cost_item["costCategory"] = {"id": cat_id}
            costs_body.append(cost_item)

        # --- Step 9: Build perDiemCompensations array ---
        per_diem_body = []
        if per_diem_days and per_diem_rate_id is not None:
            per_diem_body.append({
                "rateCategory": {"id": per_diem_rate_id},
                "count": int(per_diem_days),
                "location": destination or departure_from or "",
            })

        # --- Step 10: POST /travelExpense ---
        expense_body: dict = {
            "employee": {"id": employee_id},
            "title": title,
            "isChargeable": False,
        }

        if departure_date or return_date or departure_from or destination:
            travel_details: dict = {}
            if departure_date:
                travel_details["departureDate"] = departure_date
            if return_date:
                travel_details["returnDate"] = return_date
            if departure_from:
                travel_details["departureFrom"] = departure_from
            if destination:
                travel_details["destination"] = destination
            if travel_details:
                expense_body["travelDetails"] = travel_details

        if per_diem_body:
            expense_body["perDiemCompensations"] = per_diem_body

        if costs_body:
            expense_body["costs"] = costs_body

        r = client.post("/travelExpense", body=expense_body)
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            logger.warning(
                "Failed to POST /travelExpense: status=%s, error=%s",
                r.get('status_code'), r.get('error'),
            )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
