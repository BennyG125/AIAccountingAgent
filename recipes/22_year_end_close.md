# Year-End Close (Tier 3)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

This task has three sub-tasks: (A) depreciation vouchers for fixed assets, (B) prepaid expense reversal, (C) tax provision.
All are pure journal entries via POST /ledger/voucher. Do NOT use /asset endpoints.

## CRITICAL: Extract ALL account numbers and amounts from the PROMPT
**NEVER use default or example account numbers. The prompt ALWAYS specifies the exact accounts to use.**
Before any API call, parse the prompt and extract EVERY number:
- **Fiscal year** → voucher date = {fiscal_year}-12-31
- **For each asset:** name, acquisition cost, useful life in years, asset account number (from prompt)
- **Depreciation expense account** — the exact account number from the prompt
- **Accumulated depreciation account** — the exact account number from the prompt (if not stated, use 1209)
- **Prepaid expense account** — the exact account number from the prompt, and **prepaid amount**
- **Prepaid expense target account** — if stated use it; if not stated, use 6000
- **Tax rate**, **tax expense account**, **tax provision account** — all from the prompt

## Calculate Depreciation NOW (before any API call)
For each asset: `annual_depreciation = acquisition_cost / lifetime_years` (round to 2 decimals).
Example: 221300 / 9 = 24588.89, 420600 / 4 = 105150.00, 450650 / 4 = 112662.50

## Step 1: Look up ALL account IDs (6-9 GET calls)
Look up every unique account number mentioned. Deduplicate — if the same number appears twice, look it up once.
**API call:** `GET /ledger/account?number=XXXX&fields=id,number,name` for each unique account
Capture `values[0].id` from each response.

Look up EACH account number extracted from the prompt. Use the EXACT numbers from the prompt:
```
GET /ledger/account?number=<depr_expense_from_prompt>     → depr_expense_id
GET /ledger/account?number=<acc_depr_from_prompt_or_1209> → acc_depr_id
GET /ledger/account?number=<asset_account_1_from_prompt>  → asset_1_id (if needed)
GET /ledger/account?number=<asset_account_2_from_prompt>  → asset_2_id (if needed)
GET /ledger/account?number=<asset_account_3_from_prompt>  → asset_3_id (if needed)
GET /ledger/account?number=<prepaid_from_prompt>          → prepaid_id
GET /ledger/account?number=<prepaid_target_or_6000>       → operating_expense_id
GET /ledger/account?number=<tax_expense_from_prompt>      → tax_expense_id
GET /ledger/account?number=<tax_provision_from_prompt>    → tax_provision_id
```
**Do NOT substitute with example numbers. Use the EXACT account numbers from the prompt.**
**On error (empty values[]):** Account does not exist. Create it: `POST /ledger/account {"number": XXXX, "name": "Account name"}`, then use the returned ID.

## Step 2: Post depreciation vouchers (1 POST per asset — usually 3)
The task typically says "post each depreciation as a separate voucher." Create ONE voucher per asset.

**API call:** `POST /ledger/voucher`
**Payload (per asset):**
```json
{
  "date": "<fiscal_year>-12-31",
  "description": "Avskrivning <asset_name> <fiscal_year>",
  "postings": [
    {
      "account": {"id": <depr_expense_id>},
      "amount": <annual_depreciation>,
      "amountCurrency": <annual_depreciation>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Avskrivning <asset_name>"
    },
    {
      "account": {"id": <acc_depr_id>},
      "amount": <negative_annual_depreciation>,
      "amountCurrency": <negative_annual_depreciation>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Akkumulert avskrivning <asset_name>"
    }
  ]
}
```
Row 1 amount is POSITIVE (debit expense). Row 2 amount is NEGATIVE (credit contra-asset). They MUST sum to 0.
**On 422 error:** Check that amounts sum to exactly 0 (rounding). Ensure amountCurrency = amount on every row. Rows start at 1.

## Step 3: Post prepaid expense reversal (1 POST)
Reverses the prepaid balance from account 1700 (or stated account) to an expense account.

**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "<fiscal_year>-12-31",
  "description": "Oppløsning forskuddsbetalte kostnader <fiscal_year>",
  "postings": [
    {
      "account": {"id": <expense_account_id>},
      "amount": <prepaid_amount>,
      "amountCurrency": <prepaid_amount>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Forskuddsbetalte kostnader oppløst"
    },
    {
      "account": {"id": <prepaid_id>},
      "amount": <negative_prepaid_amount>,
      "amountCurrency": <negative_prepaid_amount>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Konto 1700 reversering"
    }
  ]
}
```
If the prompt does NOT specify which expense account to debit, use account 6000 (Avskrivning/generic operating expense). If the prompt specifies an expense account, look it up in Step 1 and use that ID.

## Step 4: Get balance sheet for tax calculation (1 GET)
**API call:** `GET /resultSheet?dateFrom=<fiscal_year>-01-01&dateTo=<fiscal_year>-12-31&fields=*`
From the response, compute taxable profit:
- Revenue = sum of `closingBalance` for accounts 3000–3999 (these are typically negative = credit = revenue, so use abs value)
- Expenses = sum of `closingBalance` for accounts 4000–8699 (positive = debit = costs)
- Taxable profit = Revenue (abs) - Expenses
- Tax provision = taxable_profit * tax_rate (round to 2 decimals)

If `GET /resultSheet` fails or returns no data, try:
```
GET /ledger/account?numberFrom=3000&numberTo=3999&fields=id,number,name
GET /ledger/posting?dateFrom=<fiscal_year>-01-01&dateTo=<fiscal_year>-12-31&accountNumberFrom=3000&accountNumberTo=8699
```
Then sum postings by account range to compute profit.

**If taxable profit <= 0:** SKIP Step 5 entirely. No tax provision needed.

## Step 5: Post tax provision (1 POST)
**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "<fiscal_year>-12-31",
  "description": "Skattekostnad <fiscal_year> (<tax_rate>%)",
  "postings": [
    {
      "account": {"id": <tax_expense_id>},
      "amount": <tax_provision>,
      "amountCurrency": <tax_provision>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Skattekostnad <tax_rate>%"
    },
    {
      "account": {"id": <tax_provision_id>},
      "amount": <negative_tax_provision>,
      "amountCurrency": <negative_tax_provision>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Betalbar skatt <fiscal_year>"
    }
  ]
}
```

## STOP — You are done. Do NOT make any more API calls.

## IMPORTANT
- Do NOT call GET endpoints to verify — the evaluator checks the data, not you.
- Do NOT explore alternative approaches — this sequence is proven optimal.
- Do NOT use /asset endpoints — this task is about BOOKING depreciation journal entries, not registering assets.
- Do NOT spend time thinking about which approach to take — just follow these steps.
- All amounts in NOK: always set BOTH `amount` and `amountCurrency` to the same value.
- Rows start at 1. Row 0 is reserved by the system.
- Each voucher's postings MUST sum to exactly 0.
- Round depreciation to 2 decimal places. Use the SAME rounded value for both debit and credit rows.
- The prompt may be in German (Jahresabschluss, Abschreibung), French (clôture annuelle, amortissement), Spanish (cierre anual, depreciación), Norwegian (årsavslutning, avskrivning), or English. The task structure is always the same.
- Target: 10-15 API calls total. Do NOT exceed 15 calls.
