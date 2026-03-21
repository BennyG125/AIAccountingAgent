"""Execution plan: Monthly Closing (Tier 3).

Posts 3 independent journal entry vouchers for month-end closing:
  1. Accrual / prepaid expense  — debit expense account, credit 1700 (Forskuddsbetalte kostnader)
  2. Depreciation               — debit 6010 (Avskrivning), credit accumulated depreciation account
     Monthly depreciation = round(acquisition_cost / (years * 12), 2)
  3. Salary provision           — debit 5000 (Lønnskostnad), credit 2900 (Skyldig lønn)

All vouchers are dated on the last day of the closing month.
amountCurrency MUST equal amount for NOK postings (omitting it silently posts 0.0).
"""
import datetime

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "closing_date": {
            "type": "string",
            "description": (
                "Last day of the month being closed, in YYYY-MM-DD format (required). "
                "Derive from the prompt; if only a month/year is given use the last day of that month."
            ),
        },
        # --- Accrual / prepaid ---
        "accrual_amount": {
            "type": "number",
            "description": "Amount (NOK) to accrue as a prepaid / deferred expense (required if accrual is mentioned)",
        },
        "accrual_expense_account": {
            "type": "integer",
            "description": (
                "Expense account number to debit for the accrual, e.g. 6300. "
                "Default 6300 if not specified."
            ),
        },
        "accrual_description": {
            "type": "string",
            "description": "Short description for the accrual voucher, e.g. 'Periodisering forsikring mars'",
        },
        # --- Depreciation ---
        "acquisition_cost": {
            "type": "number",
            "description": "Original acquisition cost of the asset in NOK (required if depreciation is mentioned)",
        },
        "asset_lifetime_years": {
            "type": "number",
            "description": "Asset lifetime in years used to compute monthly depreciation (required if depreciation is mentioned)",
        },
        "depreciation_asset_account": {
            "type": "integer",
            "description": (
                "Balance-sheet asset account number to credit for accumulated depreciation, "
                "e.g. 1230. Default 1230 if not specified."
            ),
        },
        "depreciation_description": {
            "type": "string",
            "description": "Short description for the depreciation voucher, e.g. 'Avskrivning inventar mars'",
        },
        # --- Salary provision ---
        "salary_provision_amount": {
            "type": "number",
            "description": "Salary provision amount in NOK (required if salary provision is mentioned)",
        },
        "salary_description": {
            "type": "string",
            "description": "Short description for the salary provision voucher, e.g. 'Lønnsavsetning mars'",
        },
    },
    "required": ["closing_date"],
}


@register
class MonthlyClosingPlan(ExecutionPlan):
    task_type = "monthly_closing"
    description = (
        "Post 3 month-end journal entries: accrual (expense / 1700), "
        "depreciation (6010 / accumulated dep.), and salary provision (5000 / 2900)"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        closing_date = params["closing_date"]

        # Determine which vouchers to post
        accrual_amount = params.get("accrual_amount")
        acquisition_cost = params.get("acquisition_cost")
        asset_lifetime_years = params.get("asset_lifetime_years")
        salary_provision_amount = params.get("salary_provision_amount")

        api_calls = 0
        api_errors = 0

        # ------------------------------------------------------------------
        # Step 1: Look up all needed account IDs in parallel-style GET calls
        # ------------------------------------------------------------------

        # Accounts needed depending on which vouchers are active:
        #   Accrual:      expense account (e.g. 6300) + 1700
        #   Depreciation: 6010 + asset balance-sheet account (e.g. 1230)
        #   Salary:       5000 + 2900

        account_numbers_needed = set()
        if accrual_amount is not None:
            accrual_expense_acc = str(params.get("accrual_expense_account") or 6300)
            account_numbers_needed.add(accrual_expense_acc)
            account_numbers_needed.add("1700")
        if acquisition_cost is not None and asset_lifetime_years is not None:
            account_numbers_needed.add("6010")
            dep_asset_acc = str(params.get("depreciation_asset_account") or 1230)
            account_numbers_needed.add(dep_asset_acc)
        if salary_provision_amount is not None:
            account_numbers_needed.add("5000")
            account_numbers_needed.add("2900")

        account_ids: dict[str, int] = {}
        for acc_number in account_numbers_needed:
            self._check_timeout(start_time)
            result = client.get("/ledger/account", params={"number": acc_number, "count": 1})
            api_calls += 1
            if not result["success"] or not result["body"].get("values"):
                api_errors += 1
                raise RuntimeError(
                    f"Failed to look up account {acc_number}: "
                    f"status={result.get('status_code')}, error={result.get('error')}"
                )
            account_ids[acc_number] = result["body"]["values"][0]["id"]

        # ------------------------------------------------------------------
        # Voucher 1: Accrual — debit expense account, credit 1700 (prepaid)
        # ------------------------------------------------------------------
        if accrual_amount is not None:
            self._check_timeout(start_time)
            amount = float(accrual_amount)
            description = (
                params.get("accrual_description")
                or f"Periodisering kostnad {closing_date[:7]}"
            )
            expense_acc_id = account_ids[accrual_expense_acc]
            prepaid_acc_id = account_ids["1700"]

            accrual_body = {
                "date": closing_date,
                "description": description,
                "postings": [
                    {
                        "row": 1,
                        "account": {"id": expense_acc_id},
                        "amount": amount,
                        "amountCurrency": amount,
                        "description": description,
                    },
                    {
                        "row": 2,
                        "account": {"id": prepaid_acc_id},
                        "amount": -amount,
                        "amountCurrency": -amount,
                        "description": description,
                    },
                ],
            }
            accrual_result = client.post("/ledger/voucher", body=accrual_body)
            api_calls += 1
            if not accrual_result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to post accrual voucher: "
                    f"status={accrual_result.get('status_code')}, "
                    f"error={accrual_result.get('error')}"
                )

        # ------------------------------------------------------------------
        # Voucher 2: Depreciation — debit 6010, credit accumulated dep. account
        # Monthly amount = round(acquisition_cost / (years * 12), 2)
        # Both rows use the SAME rounded value.
        # ------------------------------------------------------------------
        if acquisition_cost is not None and asset_lifetime_years is not None:
            self._check_timeout(start_time)
            monthly_dep = round(
                float(acquisition_cost) / (float(asset_lifetime_years) * 12), 2
            )
            description = (
                params.get("depreciation_description")
                or f"Avskrivning {closing_date[:7]}"
            )
            dep_expense_id = account_ids["6010"]
            dep_asset_id = account_ids[dep_asset_acc]

            dep_body = {
                "date": closing_date,
                "description": description,
                "postings": [
                    {
                        "row": 1,
                        "account": {"id": dep_expense_id},
                        "amount": monthly_dep,
                        "amountCurrency": monthly_dep,
                        "description": description,
                    },
                    {
                        "row": 2,
                        "account": {"id": dep_asset_id},
                        "amount": -monthly_dep,
                        "amountCurrency": -monthly_dep,
                        "description": description,
                    },
                ],
            }
            dep_result = client.post("/ledger/voucher", body=dep_body)
            api_calls += 1
            if not dep_result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to post depreciation voucher: "
                    f"status={dep_result.get('status_code')}, "
                    f"error={dep_result.get('error')}"
                )

        # ------------------------------------------------------------------
        # Voucher 3: Salary provision — debit 5000, credit 2900
        # ------------------------------------------------------------------
        if salary_provision_amount is not None:
            self._check_timeout(start_time)
            amount = float(salary_provision_amount)
            description = (
                params.get("salary_description")
                or f"Lønnsavsetning {closing_date[:7]}"
            )
            salary_acc_id = account_ids["5000"]
            payable_acc_id = account_ids["2900"]

            salary_body = {
                "date": closing_date,
                "description": description,
                "postings": [
                    {
                        "row": 1,
                        "account": {"id": salary_acc_id},
                        "amount": amount,
                        "amountCurrency": amount,
                        "description": description,
                    },
                    {
                        "row": 2,
                        "account": {"id": payable_acc_id},
                        "amount": -amount,
                        "amountCurrency": -amount,
                        "description": description,
                    },
                ],
            }
            salary_result = client.post("/ledger/voucher", body=salary_body)
            api_calls += 1
            if not salary_result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to post salary provision voucher: "
                    f"status={salary_result.get('status_code')}, "
                    f"error={salary_result.get('error')}"
                )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
