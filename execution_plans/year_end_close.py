"""Execution plan: Year-End Close (Tier 3).

Flow:
  1. Look up all referenced account IDs (8–9 GET calls)
  2. For each asset: POST /ledger/voucher — straight-line depreciation
       debit depreciation expense account, credit accumulated depreciation account
       Annual depreciation = round(cost / years, 2)
  3. POST /ledger/voucher — prepaid expense reversal
       debit operating expense account, credit 1700
  4. GET /balanceSheet to compute taxable profit
  5. POST /ledger/voucher — tax provision at 22% (debit 8700, credit 2920)
       Skip entirely if taxable profit <= 0

NEVER use /asset endpoint — all operations are POST /ledger/voucher only.
amountCurrency must always equal amount for NOK postings.
Each voucher must balance (sum of amounts == 0).
"""
from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "fiscal_year": {
            "type": "integer",
            "description": "Fiscal year being closed, e.g. 2025. Voucher date: YYYY-12-31.",
        },
        "assets": {
            "type": "array",
            "description": "List of fixed assets to depreciate (one voucher each).",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Asset name used in voucher description, e.g. 'Kontormaskiner'.",
                    },
                    "cost": {
                        "type": "number",
                        "description": "Original acquisition cost in NOK.",
                    },
                    "years": {
                        "type": "number",
                        "description": "Useful life in years (for straight-line depreciation).",
                    },
                    "asset_account": {
                        "type": "integer",
                        "description": "Balance sheet account for the asset, e.g. 1200.",
                    },
                    "depreciation_account": {
                        "type": "integer",
                        "description": (
                            "Accumulated depreciation account (credit side), e.g. 1209. "
                            "Defaults to asset_account + 9 if not specified."
                        ),
                    },
                    "expense_account": {
                        "type": "integer",
                        "description": (
                            "Depreciation expense account (debit side), e.g. 6010. "
                            "Defaults to 6010 if not specified."
                        ),
                    },
                },
                "required": ["name", "cost", "years", "asset_account"],
            },
        },
        "prepaid_amount": {
            "type": "number",
            "description": "Total prepaid expense amount on account 1700 to reverse in NOK.",
        },
        "prepaid_expense_account": {
            "type": "integer",
            "description": (
                "Operating expense account to debit when releasing prepaid (1700 is credited). "
                "Defaults to 6000 if not specified."
            ),
        },
        "depreciation_expense_account": {
            "type": "integer",
            "description": "Shared depreciation expense account number (debit), e.g. 6010.",
        },
        "accumulated_depreciation_account": {
            "type": "integer",
            "description": "Shared accumulated depreciation account number (credit), e.g. 1209.",
        },
        "tax_expense_account": {
            "type": "integer",
            "description": "Tax expense account, e.g. 8700.",
        },
        "tax_provision_account": {
            "type": "integer",
            "description": "Tax provision (payable) account, e.g. 2920.",
        },
    },
    "required": ["fiscal_year", "assets"],
}


def _lookup_account(client, number: str) -> int | None:
    """Look up a ledger account by number. Returns id or None if not found."""
    result = client.get(
        "/ledger/account",
        params={"number": str(number), "fields": "id,number,name"},
    )
    if result["success"]:
        values = result["body"].get("values", [])
        if values:
            return values[0]["id"]
    return None


def _require_account(client, number: str, api_calls: list, api_errors: list) -> int:
    """Look up account; raise RuntimeError if not found. Mutates api_calls/api_errors counts."""
    account_id = _lookup_account(client, number)
    api_calls[0] += 1
    if account_id is None:
        api_errors[0] += 1
        raise RuntimeError(
            f"Account {number} not found in this sandbox. "
            "Ensure the chart of accounts contains this account number."
        )
    return account_id


@register
class YearEndClosePlan(ExecutionPlan):
    task_type = "year_end_close"
    description = (
        "Post year-end close vouchers: straight-line depreciation for each asset, "
        "prepaid expense reversal, and 22% tax provision based on balance sheet profit"
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        fiscal_year = int(params.get("fiscal_year") or 2025)
        voucher_date = f"{fiscal_year}-12-31"
        assets = params.get("assets") or []

        # Shared account number defaults
        default_depr_expense = str(params.get("depreciation_expense_account") or 6010)
        default_acc_depr = str(params.get("accumulated_depreciation_account") or 1209)
        prepaid_amount = float(params.get("prepaid_amount") or 0)
        prepaid_expense_account_number = str(
            params.get("prepaid_expense_account") or 6000
        )
        tax_expense_account_number = str(params.get("tax_expense_account") or 8700)
        tax_provision_account_number = str(params.get("tax_provision_account") or 2920)

        # Mutable counters passed by reference via single-element lists
        api_calls = [0]
        api_errors = [0]

        # ------------------------------------------------------------------
        # Phase 1: Batch look up ALL account IDs in 1 call
        # ------------------------------------------------------------------
        self._check_timeout(start_time)

        # Collect all unique account numbers we need
        all_account_numbers = set()
        all_account_numbers.add(default_depr_expense)
        all_account_numbers.add(default_acc_depr)
        all_account_numbers.add("1700")
        all_account_numbers.add(prepaid_expense_account_number)
        all_account_numbers.add(tax_expense_account_number)
        all_account_numbers.add(tax_provision_account_number)
        for asset in assets:
            for key in ["asset_account", "depreciation_account", "expense_account"]:
                val = asset.get(key)
                if val:
                    all_account_numbers.add(str(val))

        # Remove empty strings
        all_account_numbers.discard("")

        # Single batch lookup
        try:
            all_accounts = self._get_accounts(client, *all_account_numbers)
            api_calls[0] += 1
        except RuntimeError:
            # Some accounts may not exist — fall back to individual lookups
            all_accounts = {}
            for num in all_account_numbers:
                acc_id = _lookup_account(client, num)
                api_calls[0] += 1
                if acc_id is not None:
                    all_accounts[str(num)] = acc_id

        shared_depr_expense_id = all_accounts.get(default_depr_expense)
        shared_acc_depr_id = all_accounts.get(default_acc_depr)
        asset_account_ids = all_accounts  # all accounts in one dict

        prepaid_account_id = all_accounts.get("1700")
        prepaid_expense_id = all_accounts.get(prepaid_expense_account_number)
        tax_expense_id = all_accounts.get(tax_expense_account_number)
        tax_provision_id = all_accounts.get(tax_provision_account_number)

        # Create missing critical accounts if needed
        if shared_depr_expense_id is None:
            cr = client.post("/ledger/account", body={"number": int(default_depr_expense), "name": f"Konto {default_depr_expense}"})
            api_calls[0] += 1
            if cr["success"]:
                shared_depr_expense_id = cr["body"]["value"]["id"]
                all_accounts[default_depr_expense] = shared_depr_expense_id
        if prepaid_account_id is None and prepaid_amount > 0:
            cr = client.post("/ledger/account", body={"number": 1700, "name": "Forskuddsbetalte kostnader"})
            api_calls[0] += 1
            if cr["success"]:
                prepaid_account_id = cr["body"]["value"]["id"]
                prepaid_expense_id = all_accounts.get(prepaid_expense_account_number)
        if prepaid_expense_id is None and prepaid_amount > 0:
            cr = client.post("/ledger/account", body={"number": int(prepaid_expense_account_number), "name": f"Konto {prepaid_expense_account_number}"})
            api_calls[0] += 1
            if cr["success"]:
                prepaid_expense_id = cr["body"]["value"]["id"]

        # ------------------------------------------------------------------
        # Phase 2: Post one depreciation voucher per asset
        # ------------------------------------------------------------------
        for asset in assets:
            self._check_timeout(start_time)

            name = asset.get("name", "Unknown asset")
            cost = float(asset.get("cost", 0))
            years = float(asset.get("years", 1))
            annual_depr = round(cost / years, 2)

            # Resolve account IDs for this asset
            depr_expense_id = asset_account_ids.get(
                str(asset.get("expense_account", "")), shared_depr_expense_id
            )
            acc_depr_id = asset_account_ids.get(
                str(asset.get("depreciation_account", "")), shared_acc_depr_id
            )

            voucher_body = {
                "date": voucher_date,
                "description": f"Avskrivning {name} {fiscal_year}",
                "postings": [
                    {
                        "row": 1,
                        "account": {"id": depr_expense_id},
                        "amount": annual_depr,
                        "amountCurrency": annual_depr,
                        "currency": {"id": 1},
                        "description": f"Avskrivning {name}",
                    },
                    {
                        "row": 2,
                        "account": {"id": acc_depr_id},
                        "amount": -annual_depr,
                        "amountCurrency": -annual_depr,
                        "currency": {"id": 1},
                        "description": f"Akkumulert avskrivning {name}",
                    },
                ],
            }

            # Skip if we couldn't resolve accounts for this asset
            if depr_expense_id is None or acc_depr_id is None:
                api_errors[0] += 1
                continue

            result = client.post("/ledger/voucher", body=voucher_body)
            api_calls[0] += 1
            if not result["success"]:
                api_errors[0] += 1

        # ------------------------------------------------------------------
        # Phase 3: Prepaid expense reversal (only if amount > 0)
        # ------------------------------------------------------------------
        if prepaid_amount > 0:
            self._check_timeout(start_time)

            reversal_body = {
                "date": voucher_date,
                "description": f"Oppløsning forskuddsbetalte kostnader {fiscal_year}",
                "postings": [
                    {
                        "row": 1,
                        "account": {"id": prepaid_expense_id},
                        "amount": prepaid_amount,
                        "amountCurrency": prepaid_amount,
                        "currency": {"id": 1},
                        "description": "Forskuddsbetalte kostnader oppløst",
                    },
                    {
                        "row": 2,
                        "account": {"id": prepaid_account_id},
                        "amount": -prepaid_amount,
                        "amountCurrency": -prepaid_amount,
                        "currency": {"id": 1},
                        "description": "Konto 1700 reversering",
                    },
                ],
            }

            if prepaid_expense_id is None or prepaid_account_id is None:
                api_errors[0] += 1
            else:
                result = client.post("/ledger/voucher", body=reversal_body)
                api_calls[0] += 1
                if not result["success"]:
                    api_errors[0] += 1

        # ------------------------------------------------------------------
        # Phase 4: Compute taxable profit from balance sheet
        # ------------------------------------------------------------------
        self._check_timeout(start_time)

        # Use /ledger/posting to compute taxable profit (/balanceSheet and
        # /resultSheet do NOT exist — they return 404).
        posting_result = client.get(
            "/ledger/posting",
            params={
                "dateFrom": f"{fiscal_year}-01-01",
                "dateTo": f"{fiscal_year}-12-31",
                "count": 10000,
            },
        )
        api_calls[0] += 1

        tax_provision_amount = 0.0
        if posting_result["success"]:
            postings = posting_result["body"].get("values", [])
            # Aggregate amounts by account number range
            revenue = 0.0    # accounts 3000–3999
            expenses = 0.0   # accounts 4000–8699

            for posting in postings:
                account = posting.get("account", {})
                acc_number = account.get("number", 0)
                try:
                    acc_num = int(str(acc_number).strip())
                except (ValueError, TypeError):
                    continue

                amount = float(posting.get("amount", 0))

                if 3000 <= acc_num <= 3999:
                    # Revenue: credit entries are negative, accumulate absolute
                    revenue += abs(amount)
                elif 4000 <= acc_num <= 8699:
                    # Expenses: debit entries are positive
                    expenses += max(amount, 0)

            net_profit = revenue - expenses
            if net_profit > 0:
                tax_provision_amount = round(net_profit * 0.22, 2)

        # ------------------------------------------------------------------
        # Phase 5: Post tax provision (skip if profit <= 0)
        # ------------------------------------------------------------------
        if tax_provision_amount > 0:
            self._check_timeout(start_time)

            tax_body = {
                "date": voucher_date,
                "description": f"Skattekostnad {fiscal_year} (22%)",
                "postings": [
                    {
                        "row": 1,
                        "account": {"id": tax_expense_id},
                        "amount": tax_provision_amount,
                        "amountCurrency": tax_provision_amount,
                        "currency": {"id": 1},
                        "description": "Skattekostnad 22%",
                    },
                    {
                        "row": 2,
                        "account": {"id": tax_provision_id},
                        "amount": -tax_provision_amount,
                        "amountCurrency": -tax_provision_amount,
                        "currency": {"id": 1},
                        "description": f"Betalbar skatt {fiscal_year}",
                    },
                ],
            }

            if tax_expense_id is None or tax_provision_id is None:
                # Create missing tax accounts
                if tax_expense_id is None:
                    cr = client.post("/ledger/account", body={"number": int(tax_expense_account_number), "name": "Skattekostnad"})
                    api_calls[0] += 1
                    if cr["success"]:
                        tax_expense_id = cr["body"]["value"]["id"]
                if tax_provision_id is None:
                    cr = client.post("/ledger/account", body={"number": int(tax_provision_account_number), "name": "Betalbar skatt"})
                    api_calls[0] += 1
                    if cr["success"]:
                        tax_provision_id = cr["body"]["value"]["id"]

            if tax_expense_id is not None and tax_provision_id is not None:
                # Re-build body with resolved IDs
                tax_body["postings"][0]["account"] = {"id": tax_expense_id}
                tax_body["postings"][1]["account"] = {"id": tax_provision_id}
                result = client.post("/ledger/voucher", body=tax_body)
                api_calls[0] += 1
                if not result["success"]:
                    api_errors[0] += 1
            else:
                api_errors[0] += 1

        return self._make_result(
            api_calls=api_calls[0], api_errors=api_errors[0]
        )
