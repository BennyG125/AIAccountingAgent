"""Execution plan: Cost Analysis → Create Projects (Tier 3).

Full flow:
  1. GET /ledger/posting for Jan 2026 (accounts 4000-8999) — expense postings
  2. GET /ledger/posting for Feb 2026 (accounts 4000-8999) — expense postings
  3. In-Python: group by account number, sum amounts per month, compute delta,
     sort descending, take top 3 accounts with largest increase
  4. GET /ledger/account?number=X for each top-3 account — to obtain account name
  5. GET /employee to find a project manager (use first available employee)
  6. POST /project for each top-3 account (internal project named after account)
  7. POST /activity for each project (if required)
"""
from collections import defaultdict
from datetime import date

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

# Minimal extraction schema — date ranges are always Jan/Feb 2026 for this task type
EXTRACTION_SCHEMA = {
    "date_from_jan": "string — January start date, always '2026-01-01'",
    "date_to_jan": "string — January end date, always '2026-01-31'",
    "date_from_feb": "string — February start date, always '2026-02-01'",
    "date_to_feb": "string — February end date, always '2026-02-28'",
    "create_activities": "boolean — true if the task requests creating activities for the projects (default false)",
}

# Account range covering all expense/cost accounts
_ACCOUNT_FROM = 4000
_ACCOUNT_TO = 8999

# Fixed date ranges
_JAN_FROM = "2026-01-01"
_JAN_TO = "2026-01-31"
_FEB_FROM = "2026-02-01"
_FEB_TO = "2026-02-28"


@register
class CostAnalysisProjectsPlan(ExecutionPlan):
    task_type = "cost_analysis_projects"
    description = (
        "Analyse Jan/Feb expense postings, find top-3 accounts by cost increase, "
        "then create an internal project (and optionally activity) for each"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0
        today = date.today().isoformat()

        create_activities = params.get("create_activities", False)

        # ---------------------------------------------------------------
        # Step 1: Fetch January expense postings (accounts 4000–8999)
        # ---------------------------------------------------------------
        jan_result = client.get(
            "/ledger/posting",
            params={
                "dateFrom": _JAN_FROM,
                "dateTo": _JAN_TO,
                "accountNumberFrom": _ACCOUNT_FROM,
                "accountNumberTo": _ACCOUNT_TO,
                "fields": "account(number),amount",
                "count": 1000,
            },
        )
        api_calls += 1
        if not jan_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to fetch January postings: "
                f"status={jan_result.get('status_code')}, error={jan_result.get('error')}"
            )

        self._check_timeout(start_time)

        # ---------------------------------------------------------------
        # Step 2: Fetch February expense postings (accounts 4000–8999)
        # ---------------------------------------------------------------
        feb_result = client.get(
            "/ledger/posting",
            params={
                "dateFrom": _FEB_FROM,
                "dateTo": _FEB_TO,
                "accountNumberFrom": _ACCOUNT_FROM,
                "accountNumberTo": _ACCOUNT_TO,
                "fields": "account(number),amount",
                "count": 1000,
            },
        )
        api_calls += 1
        if not feb_result["success"]:
            api_errors += 1
            raise RuntimeError(
                f"Failed to fetch February postings: "
                f"status={feb_result.get('status_code')}, error={feb_result.get('error')}"
            )

        self._check_timeout(start_time)

        # ---------------------------------------------------------------
        # Step 3: In-agent analysis — sum, compare, rank (pure Python)
        # ---------------------------------------------------------------
        jan_totals: dict[int, float] = defaultdict(float)
        for posting in jan_result["body"].get("values", []):
            account = posting.get("account") or {}
            acct_num = account.get("number")
            amount = posting.get("amount", 0) or 0
            if acct_num is not None:
                jan_totals[int(acct_num)] += float(amount)

        feb_totals: dict[int, float] = defaultdict(float)
        for posting in feb_result["body"].get("values", []):
            account = posting.get("account") or {}
            acct_num = account.get("number")
            amount = posting.get("amount", 0) or 0
            if acct_num is not None:
                feb_totals[int(acct_num)] += float(amount)

        # Compute increase: delta = feb_total - jan_total (positive = cost went up)
        all_account_numbers = set(jan_totals.keys()) | set(feb_totals.keys())
        deltas: list[tuple[float, int]] = []
        for acct_num in all_account_numbers:
            delta = feb_totals.get(acct_num, 0.0) - jan_totals.get(acct_num, 0.0)
            deltas.append((delta, acct_num))

        # Sort descending by delta — largest increase first
        deltas.sort(key=lambda x: x[0], reverse=True)
        top3_account_numbers = [acct_num for _, acct_num in deltas[:3]]

        if not top3_account_numbers:
            # No postings found — nothing to create
            return self._make_result(api_calls=api_calls, api_errors=api_errors)

        self._check_timeout(start_time)

        # ---------------------------------------------------------------
        # Step 4: Fetch account names for top-3 accounts
        # ---------------------------------------------------------------
        account_names: dict[int, str] = {}
        for acct_num in top3_account_numbers:
            self._check_timeout(start_time)
            r = client.get(
                "/ledger/account",
                params={"number": str(acct_num), "fields": "id,number,name"},
            )
            api_calls += 1
            if r["success"]:
                values = r["body"].get("values", [])
                if values:
                    account_names[acct_num] = values[0].get("name", f"Konto {acct_num}")
            else:
                # Non-fatal: fall back to account number as name
                account_names[acct_num] = f"Konto {acct_num}"

        self._check_timeout(start_time)

        # ---------------------------------------------------------------
        # Step 5: Get a project manager (first available employee)
        # ---------------------------------------------------------------
        emp_result = client.get("/employee", params={"fields": "id", "count": 1})
        api_calls += 1
        project_manager_id: int | None = None
        if emp_result["success"]:
            values = emp_result["body"].get("values", [])
            if values:
                project_manager_id = values[0]["id"]

        if project_manager_id is None:
            raise RuntimeError(
                "No employees found — cannot set projectManager for internal projects"
            )

        self._check_timeout(start_time)

        # ---------------------------------------------------------------
        # Step 6: Create an internal project for each top-3 account
        # ---------------------------------------------------------------
        project_ids: list[int] = []
        for acct_num in top3_account_numbers:
            self._check_timeout(start_time)
            account_name = account_names.get(acct_num, f"Konto {acct_num}")
            project_name = account_name

            result = client.post(
                "/project",
                body={
                    "name": project_name,
                    "projectManager": {"id": project_manager_id},
                    "startDate": today,
                    "isInternal": True,
                },
            )
            api_calls += 1
            if not result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to create project '{project_name}': "
                    f"status={result.get('status_code')}, error={result.get('error')}"
                )
            project_ids.append(result["body"]["value"]["id"])

        self._check_timeout(start_time)

        # ---------------------------------------------------------------
        # Step 7: Create an activity for each project (if requested)
        # ---------------------------------------------------------------
        if create_activities:
            for i, project_id in enumerate(project_ids):
                self._check_timeout(start_time)
                acct_num = top3_account_numbers[i]
                account_name = account_names.get(acct_num, f"Konto {acct_num}")
                activity_name = account_name

                # Search for existing activity first
                search = client.get("/activity", params={"name": activity_name})
                api_calls += 1
                existing = search.get("body", {}).get("values", []) if search["success"] else []
                if not existing:
                    result = client.post(
                        "/activity",
                        body={
                            "name": activity_name,
                            "activityType": "GENERAL_ACTIVITY",
                            "isChargeable": False,
                        },
                    )
                    api_calls += 1
                    if not result["success"]:
                        # Non-fatal — project creation is the important part
                        api_errors += 1

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
