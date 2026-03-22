# Monthly Closing (Tier 3)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

Monthly closing = post three adjusting journal entries as separate vouchers:
1. **Accrual / periodification** — release prepaid expense from balance sheet to P&L
2. **Depreciation** — monthly straight-line depreciation of a fixed asset
3. **Salary provision** — accrue unpaid wages

There is NO "close the month" API endpoint. "Close the month" means all adjusting entries are posted.
The "verify balance is zero" instruction means each voucher must balance — Tripletex enforces this automatically (422 if not). Do NOT call GET /balanceSheet to verify.

## CRITICAL: Extract ALL account numbers and amounts from the PROMPT
**NEVER use default or example account numbers. The prompt ALWAYS specifies the exact accounts to use.**
Before any API call, parse the prompt and extract EVERY number:
- **Closing month/year** → voucher date = last day of that month (e.g. March 2026 → 2026-03-31)
- **Accrual amount** — the per-month amount stated in the prompt
- **Accrual source account** — the account number stated in the prompt (could be 1700, 1710, or any 4-digit number)
- **Accrual target expense account** — if stated, use it; if "til kostnadskonto" without a number, use 7700
- **Asset acquisition cost** and **useful life in years**
- **Depreciation expense account** — the account number stated in the prompt (could be 6010, 6020, 6030, etc.)
- **Accumulated depreciation account** — if stated, use it; if not stated, use 1209
- **Salary expense account** and **salary amount** — from the prompt
- **Accrued wages liability account** — from the prompt

## Calculate Depreciation NOW (before any API call)
`monthly_depreciation = acquisition_cost / (lifetime_years * 12)` → round to 2 decimals
Example: 107950 / (6 * 12) = 107950 / 72 = 1499.31

## Step 1: Look up ALL account IDs (up to 6 GET calls)
**API call:** `GET /ledger/account?number=XXXX&fields=id,number,name` for each unique account
Capture `values[0].id` from each response.

Look up EACH account number extracted from the prompt:
```
GET /ledger/account?number=<accrual_source_from_prompt>   → accrual_source_id
GET /ledger/account?number=<accrual_expense_from_prompt>  → accrual_expense_id
GET /ledger/account?number=<depr_expense_from_prompt>     → depr_expense_id
GET /ledger/account?number=<acc_depr_from_prompt_or_1209> → acc_depr_id
GET /ledger/account?number=<salary_expense_from_prompt>   → salary_expense_id
GET /ledger/account?number=<accrued_wages_from_prompt>    → accrued_wages_id
```
**Use the EXACT account numbers from the prompt. Do NOT substitute with example numbers.**
Deduplicate — if same account number appears in multiple roles, look it up once.
**On error (empty values[]):** Create the account: `POST /ledger/account {"number": XXXX, "name": "Account name"}`.

## Step 2: Post accrual / periodification voucher (1 POST)
**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "<last_day_of_month>",
  "description": "Periodisering <month> <year>",
  "postings": [
    {
      "account": {"id": <accrual_expense_id>},
      "amount": <accrual_amount>,
      "amountCurrency": <accrual_amount>,
      "amountGross": <accrual_amount>,
      "amountGrossCurrency": <accrual_amount>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Periodisert kostnad"
    },
    {
      "account": {"id": <accrual_source_id>},
      "amount": <negative_accrual_amount>,
      "amountCurrency": <negative_accrual_amount>,
      "amountGross": <negative_accrual_amount>,
      "amountGrossCurrency": <negative_accrual_amount>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Reduksjon forskuddsbetalt"
    }
  ]
}
```
Row 1 = debit (positive). Row 2 = credit (negative). MUST sum to 0.

## Step 3: Post depreciation voucher (1 POST)
**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "<last_day_of_month>",
  "description": "Månedlig avskrivning <month> <year>",
  "postings": [
    {
      "account": {"id": <depr_expense_id>},
      "amount": <monthly_depreciation>,
      "amountCurrency": <monthly_depreciation>,
      "amountGross": <monthly_depreciation>,
      "amountGrossCurrency": <monthly_depreciation>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Avskrivning driftsmidler"
    },
    {
      "account": {"id": <acc_depr_id>},
      "amount": <negative_monthly_depreciation>,
      "amountCurrency": <negative_monthly_depreciation>,
      "amountGross": <negative_monthly_depreciation>,
      "amountGrossCurrency": <negative_monthly_depreciation>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Akkumulert avskrivning"
    }
  ]
}
```

## Step 4: Post salary provision voucher (1 POST)
**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "<last_day_of_month>",
  "description": "Lønnsavsetning <month> <year>",
  "postings": [
    {
      "account": {"id": <salary_expense_id>},
      "amount": <salary_amount>,
      "amountCurrency": <salary_amount>,
      "amountGross": <salary_amount>,
      "amountGrossCurrency": <salary_amount>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Lønnskostnad"
    },
    {
      "account": {"id": <accrued_wages_id>},
      "amount": <negative_salary_amount>,
      "amountCurrency": <negative_salary_amount>,
      "amountGross": <negative_salary_amount>,
      "amountGrossCurrency": <negative_salary_amount>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Skyldig lønn"
    }
  ]
}
```

## STOP — You are done. Do NOT make any more API calls.

## IMPORTANT
- Do NOT call GET /balanceSheet to verify — wastes an API call. Tripletex enforces balance via 422.
- Do NOT explore alternative approaches — this sequence is proven optimal.
- All amounts in NOK: always set BOTH `amount` and `amountCurrency` to the same value.
- Rows start at 1. Row 0 is reserved by the system.
- Each voucher's postings MUST sum to exactly 0.
- Round monthly depreciation to 2 decimal places. Use the SAME rounded value for both rows.
- If the prompt says "verify balance" — that means each voucher is balanced, which Tripletex enforces. You do NOT need to call any verification endpoint.
- The prompt may be in Spanish (cierre mensual, periodificación, depreciación, provisión salarial), Norwegian, English, German, French, or Portuguese. The structure is always the same three vouchers.
- Account number inference when not stated: 1700=prepaid, 7700=other operating expense, 6010=depreciation expense, 1209=accumulated depreciation, 5000=salary expense, 2900=accrued wages.
- Target: 9 API calls total (6 GETs + 3 POSTs). Do NOT exceed 12 calls.
