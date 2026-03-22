# Monthly Closing (Accruals, Prepayments, Depreciation)

## Task Pattern
Prompts asking to perform monthly closing ("månedsavslutning"), accrue prepaid expenses
("periodiser forskuddsbetalt kostnad"), post depreciation, or defer revenue for a given month.
Languages observed: NO, EN, DE

## DO NOT USE these endpoints — they do NOT exist and return 404:
- GET /resultSheet
- GET /result
- GET /profitAndLoss

Use GET /ledger/account and POST /ledger/voucher instead.

## Optimal API Sequence

### 1. Look up all required account IDs
For each account number mentioned in the task, look it up:
- GET /ledger/account?number=1700 → prepaid expenses (forskuddsbetalt kostnad)
- GET /ledger/account?number=6XXX → the target expense account (from task description)
- GET /ledger/account?number=1200 → machinery/equipment (for depreciation)
- GET /ledger/account?number=6010 → depreciation expense
- GET /ledger/account?number=3000 → revenue (if deferring revenue)
- GET /ledger/account?number=2900 → deferred revenue (if deferring revenue)

Capture the `id` from `values[0].id` for each.

### 2. Post accrual/prepayment voucher
Transfer prepaid cost from balance sheet to expense for the period:
```
POST /ledger/voucher
{
  "date": "<last day of the month, e.g. 2026-03-31>",
  "description": "Månedsavslutning <month> <year> - periodisering forskuddsbetalt kostnad",
  "postings": [
    {
      "account": {"id": <expense_account_id>},
      "amount": <monthly_amount>,
      "amountCurrency": <monthly_amount>,
      "amountGross": <monthly_amount>,
      "amountGrossCurrency": <monthly_amount>,
      "currency": {"id": 1},
      "description": "Periodisert kostnad for <month>",
      "row": 1
    },
    {
      "account": {"id": <prepaid_account_id_1700>},
      "amount": <negative_monthly_amount>,
      "amountCurrency": <negative_monthly_amount>,
      "amountGross": <negative_monthly_amount>,
      "amountGrossCurrency": <negative_monthly_amount>,
      "currency": {"id": 1},
      "description": "Reduksjon forskuddsbetalt kostnad",
      "row": 2
    }
  ]
}
```

### 3. Post depreciation voucher (if required)
```
POST /ledger/voucher
{
  "date": "<last day of the month>",
  "description": "Månedsavslutning <month> <year> - avskrivning",
  "postings": [
    {
      "account": {"id": <depreciation_expense_6010_id>},
      "amount": <monthly_depreciation>,
      "amountCurrency": <monthly_depreciation>,
      "amountGross": <monthly_depreciation>,
      "amountGrossCurrency": <monthly_depreciation>,
      "currency": {"id": 1},
      "description": "Avskrivning for <month>",
      "row": 1
    },
    {
      "account": {"id": <asset_account_1200_id>},
      "amount": <negative_monthly_depreciation>,
      "amountCurrency": <negative_monthly_depreciation>,
      "amountGross": <negative_monthly_depreciation>,
      "amountGrossCurrency": <negative_monthly_depreciation>,
      "currency": {"id": 1},
      "description": "Akkumulert avskrivning",
      "row": 2
    }
  ]
}
```

### 4. Post revenue deferral voucher (if required)
If unearned revenue needs to be deferred:
```
POST /ledger/voucher
{
  "date": "<last day of the month>",
  "description": "Månedsavslutning <month> <year> - periodisering inntekt",
  "postings": [
    {
      "account": {"id": <revenue_account_3000_id>},
      "amount": <deferral_amount>,
      "amountCurrency": <deferral_amount>,
      "amountGross": <deferral_amount>,
      "amountGrossCurrency": <deferral_amount>,
      "currency": {"id": 1},
      "description": "Utsatt inntekt",
      "row": 1
    },
    {
      "account": {"id": <deferred_revenue_2900_id>},
      "amount": <negative_deferral_amount>,
      "amountCurrency": <negative_deferral_amount>,
      "amountGross": <negative_deferral_amount>,
      "amountGrossCurrency": <negative_deferral_amount>,
      "currency": {"id": 1},
      "description": "Forskuddsbetalt inntekt",
      "row": 2
    }
  ]
}
```

## Calculating Amounts
- **Prepaid expense accrual**: If a 12-month prepayment of X was paid, monthly amount = X / 12
  (or X / number_of_remaining_months if specified in the task)
- **Depreciation**: If annual depreciation is X, monthly = X / 12.
  If asset lifetime is given in months, monthly = acquisition_cost / lifetime_months.
- **Revenue deferral**: Amount as specified in the task.

## Common Account Numbers (Norwegian Standard)
- 1200: Maskiner og anlegg (machinery/equipment)
- 1700: Forskuddsbetalt kostnad (prepaid expenses)
- 2900: Forskuddsbetalt inntekt / utsatt inntekt (deferred revenue)
- 3000: Salgsinntekt (sales revenue)
- 6010: Avskrivning (depreciation expense)
- 6300: Leiekostnad (rent expense)
- 6800: Kontorkostnad (office expense)
- 6900: Telefonkostnad (telephone expense)

## Known Gotchas
- **Postings MUST balance**: Sum of all amounts must equal 0.
- **ALL FOUR amount fields required**: amount, amountCurrency, amountGross, amountGrossCurrency. Omitting amountGross silently zeroes all amounts!
- For non-VAT rows: amountGross = amount, amountGrossCurrency = amountCurrency.
- **Row numbers**: Start at 1 (row 0 is reserved for system-generated postings).
- **Date**: Use the LAST day of the period month (e.g. 2026-03-31 for March).
- **Look up account IDs**: ALWAYS use GET /ledger/account?number=XXXX — never guess IDs.
- **One voucher per type**: Create separate vouchers for accruals, depreciation, and deferrals for clarity, but the task may allow combining them into one voucher with multiple posting pairs.
- **DO NOT call** GET /resultSheet, GET /balanceSheet, or any analytical endpoints to verify — they waste API calls or return 404.
