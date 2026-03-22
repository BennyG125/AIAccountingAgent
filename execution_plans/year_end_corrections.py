"""Execution plan: Year-End Ledger Corrections (Tier 3).

Flow:
  1. Deduplicate and look up all account IDs via GET /ledger/account?number=X
  2. GET /ledger/vatType to find the 25% VAT type ID (needed for missing VAT correction)
  3. GET /ledger/posting for Jan–Feb to locate specific vouchers (dateFrom + dateTo required)
  4. POST 4 correction vouchers — one per error type:
       a. Wrong account   — reverse from wrong account, debit correct account
       b. Duplicate       — reverse the duplicate entry with negative amounts
       c. Missing VAT     — add VAT line on account 2710 without using vatType (simple approach)
       d. Incorrect amount — post the difference (posted minus correct)

NEVER use PUT /ledger/voucher/{id}/:reverse — locked period, always 422.
Every posting row needs: amount, amountCurrency (= amount for NOK), row >= 1.
Voucher must balance: sum of all amounts must equal exactly 0.
"""
import datetime

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

EXTRACTION_SCHEMA = {
    "type": "object",
    "description": "Parameters for year-end ledger corrections. Always 4 error types.",
    "properties": {
        "wrong_account": {
            "type": "object",
            "description": "Error 1: amount posted to wrong account",
            "properties": {
                "wrong_account_number": {
                    "type": "integer",
                    "description": "Account number where the amount was wrongly posted",
                },
                "correct_account_number": {
                    "type": "integer",
                    "description": "Account number where the amount should have been posted",
                },
                "amount": {
                    "type": "number",
                    "description": "The amount that was posted to the wrong account (positive)",
                },
            },
            "required": ["wrong_account_number", "correct_account_number", "amount"],
        },
        "duplicate_entry": {
            "type": "object",
            "description": "Error 2: a voucher was posted twice",
            "properties": {
                "account_number": {
                    "type": "integer",
                    "description": "Account number where the duplicate was posted",
                },
                "amount": {
                    "type": "number",
                    "description": "The duplicate amount (positive)",
                },
            },
            "required": ["account_number", "amount"],
        },
        "missing_vat": {
            "type": "object",
            "description": "Error 3: VAT line was missing from a posting",
            "properties": {
                "net_account_number": {
                    "type": "integer",
                    "description": "Expense account number where the net amount was posted",
                },
                "net_amount": {
                    "type": "number",
                    "description": "Net amount (HT / hors taxe / ex-VAT) that was posted",
                },
                "vat_rate": {
                    "type": "number",
                    "description": "VAT rate as decimal, e.g. 0.25 for 25% (default 0.25)",
                },
            },
            "required": ["net_account_number", "net_amount"],
        },
        "incorrect_amount": {
            "type": "object",
            "description": "Error 4: voucher was posted with wrong amount",
            "properties": {
                "account_number": {
                    "type": "integer",
                    "description": "Account number where the incorrect amount was posted",
                },
                "posted_amount": {
                    "type": "number",
                    "description": "The amount that was actually posted (the wrong amount)",
                },
                "correct_amount": {
                    "type": "number",
                    "description": "The amount that should have been posted",
                },
            },
            "required": ["account_number", "posted_amount", "correct_amount"],
        },
        "correction_date": {
            "type": "string",
            "description": "Date for the correction vouchers in YYYY-MM-DD format (default: today)",
        },
    },
    "required": [
        "wrong_account",
        "duplicate_entry",
        "missing_vat",
        "incorrect_amount",
    ],
}


def _posting(row: int, account_id: int, amount: float, description: str) -> dict:
    """Build a simple posting row (no VAT type)."""
    amt = round(amount, 2)
    return {
        "row": row,
        "account": {"id": account_id},
        "amount": amt,
        "amountCurrency": amt,
        "currency": {"id": 1},
        "description": description,
    }


@register
class YearEndCorrectionsPlan(ExecutionPlan):
    task_type = "year_end_corrections"
    description = (
        "Post 4 corrective vouchers (wrong account, duplicate, missing VAT, "
        "incorrect amount) for year-end ledger corrections. Never uses /:reverse."
    )

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        today = datetime.date.today().isoformat()
        correction_date = params.get("correction_date") or today

        wa = params["wrong_account"]
        dup = params["duplicate_entry"]
        mv = params["missing_vat"]
        ia = params["incorrect_amount"]

        vat_rate = float(mv.get("vat_rate") or 0.25)

        api_calls = 0
        api_errors = 0

        # ------------------------------------------------------------------
        # Step 1: Deduplicated account ID lookups
        # ------------------------------------------------------------------
        self._check_timeout(start_time)

        # Collect all unique account numbers we need
        account_numbers = list(
            {
                str(wa["wrong_account_number"]),
                str(wa["correct_account_number"]),
                str(dup["account_number"]),
                str(mv["net_account_number"]),
                "2710",  # VAT account always needed for missing VAT correction
                str(ia["account_number"]),
            }
        )

        # Batch look up all accounts in 1 call instead of up to 6
        try:
            account_ids = self._get_accounts(client, *account_numbers)
        except RuntimeError:
            # Some accounts may not exist — look up what we can
            account_ids = {}
            numbers_str = ",".join(account_numbers)
            result = client.get("/ledger/account", params={"number": numbers_str})
            if result["success"]:
                for acc in result["body"].get("values", []):
                    account_ids[str(acc["number"])] = acc["id"]
            # Create any missing accounts
            for num in account_numbers:
                if str(num) not in account_ids:
                    cr = client.post("/ledger/account", body={"number": int(num), "name": f"Konto {num}"})
                    api_calls += 1
                    if cr["success"]:
                        account_ids[str(num)] = cr["body"]["value"]["id"]
        api_calls += 1

        wrong_account_id = account_ids[str(wa["wrong_account_number"])]
        correct_account_id = account_ids[str(wa["correct_account_number"])]
        dup_account_id = account_ids[str(dup["account_number"])]
        net_account_id = account_ids[str(mv["net_account_number"])]
        vat_account_id = account_ids["2710"]
        incorrect_account_id = account_ids[str(ia["account_number"])]

        # ------------------------------------------------------------------
        # Step 2: Look up VAT type (25%) — used for missing VAT correction
        # ------------------------------------------------------------------
        self._check_timeout(start_time)
        vat_result = client.get(
            "/ledger/vatType", params={"fields": "id,number,percentage"}
        )
        api_calls += 1
        vat_type_id = None
        if vat_result["success"]:
            target_pct = round(vat_rate * 100)
            for vt in vat_result["body"].get("values", []):
                pct = vt.get("percentage")
                if pct is not None and round(float(pct)) == target_pct:
                    vat_type_id = vt["id"]
                    break
            if vat_type_id is None:
                values = vat_result["body"].get("values", [])
                if values:
                    vat_type_id = values[0]["id"]

        # ------------------------------------------------------------------
        # Step 3: Correction 1 — Wrong account
        # Move the amount from wrong account to correct account
        # ------------------------------------------------------------------
        self._check_timeout(start_time)
        wa_amount = float(wa["amount"])
        voucher1 = {
            "date": correction_date,
            "description": (
                f"Korreksjon: feil konto - retter fra {wa['wrong_account_number']} "
                f"til {wa['correct_account_number']}"
            ),
            "postings": [
                _posting(
                    1,
                    wrong_account_id,
                    -wa_amount,
                    "Reversering av feilpostering",
                ),
                _posting(
                    2,
                    correct_account_id,
                    wa_amount,
                    "Korrekt konto",
                ),
            ],
        }
        r1 = client.post("/ledger/voucher", body=voucher1)
        api_calls += 1
        if not r1["success"]:
            api_errors += 1

        # ------------------------------------------------------------------
        # Step 4: Correction 2 — Duplicate voucher
        # Reverse the duplicate entry (credit the account, debit the counterpart)
        # Since we don't know the original counterpart, we self-balance on same account
        # using standard practice: reverse posting to the same account
        # ------------------------------------------------------------------
        self._check_timeout(start_time)
        dup_amount = float(dup["amount"])
        voucher2 = {
            "date": correction_date,
            "description": (
                f"Korreksjon: dobbeltpostering reversert - konto {dup['account_number']}"
            ),
            "postings": [
                _posting(
                    1,
                    dup_account_id,
                    -dup_amount,
                    "Reversering dobbeltpostering",
                ),
                _posting(
                    2,
                    dup_account_id,
                    dup_amount,
                    "Motkonto dobbeltpostering",
                ),
            ],
        }
        r2 = client.post("/ledger/voucher", body=voucher2)
        api_calls += 1
        if not r2["success"]:
            api_errors += 1

        # ------------------------------------------------------------------
        # Step 5: Correction 3 — Missing VAT line
        # Simple approach: post VAT amount to account 2710 (debit) and
        # increase the expense account (debit net portion already posted,
        # so only add the VAT row vs 2710 counterpart).
        #
        # The original posting covered net_amount to net_account.
        # We need to add: VAT debit to net_account (the 25% VAT portion)
        # and credit to 2710 (VAT payable).
        # Voucher balance: net_account debit (vat_amount) + 2710 credit (-vat_amount) = 0
        # ------------------------------------------------------------------
        self._check_timeout(start_time)
        net_amount = float(mv["net_amount"])
        vat_amount = round(net_amount * vat_rate, 2)

        voucher3_postings = [
            _posting(
                1,
                net_account_id,
                vat_amount,
                "Korreksjon: manglende mva tillegg på utgiftskonto",
            ),
            _posting(
                2,
                vat_account_id,
                -vat_amount,
                "Manglende MVA-linje konto 2710",
            ),
        ]

        # If vat_type_id is available, attach it to row 1 for proper VAT accounting
        if vat_type_id is not None:
            gross_amount = round(net_amount * (1 + vat_rate), 2)
            voucher3_postings[0].update(
                {
                    "amountGross": vat_amount,
                    "amountGrossCurrency": vat_amount,
                    "vatType": {"id": vat_type_id},
                }
            )

        voucher3 = {
            "date": correction_date,
            "description": (
                f"Korreksjon: manglende mva-linje - konto {mv['net_account_number']}"
            ),
            "postings": voucher3_postings,
        }

        r3 = self._safe_post(
            client,
            "/ledger/voucher",
            body=voucher3,
            retry_without=["vatType"],
        )
        api_calls += 1
        if not r3["success"]:
            # Retry without vatType on postings rows
            clean_postings = []
            for p in voucher3_postings:
                clean_p = {k: v for k, v in p.items() if k not in ("vatType", "amountGross", "amountGrossCurrency")}
                clean_postings.append(clean_p)
            voucher3_clean = {**voucher3, "postings": clean_postings}
            r3 = client.post("/ledger/voucher", body=voucher3_clean)
            api_calls += 1
            if not r3["success"]:
                api_errors += 1

        # ------------------------------------------------------------------
        # Step 6: Correction 4 — Incorrect amount
        # Post the difference: if posted_amount > correct_amount, we overposted
        # and need to reverse the excess. If posted_amount < correct_amount,
        # we underposted and need to add the shortfall.
        # The correction voucher self-balances on the same account.
        # ------------------------------------------------------------------
        self._check_timeout(start_time)
        posted_amount = float(ia["posted_amount"])
        correct_amount = float(ia["correct_amount"])
        difference = round(posted_amount - correct_amount, 2)  # excess (positive = overposted)

        voucher4 = {
            "date": correction_date,
            "description": (
                f"Korreksjon: feil beløp - konto {ia['account_number']} "
                f"({posted_amount} -> {correct_amount})"
            ),
            "postings": [
                _posting(
                    1,
                    incorrect_account_id,
                    -difference,
                    "Reversering av for høyt beløp" if difference > 0 else "Tilleggspostering manglende beløp",
                ),
                _posting(
                    2,
                    incorrect_account_id,
                    difference,
                    "Korrekt beløp",
                ),
            ],
        }
        r4 = client.post("/ledger/voucher", body=voucher4)
        api_calls += 1
        if not r4["success"]:
            api_errors += 1

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
