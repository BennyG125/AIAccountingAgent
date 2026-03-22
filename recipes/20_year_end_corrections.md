# Year-End Closing & Ledger Corrections (Tier 3)

## Task Pattern
Prompts asking to:
- Correct accounting errors, post adjustment vouchers, reverse incorrect entries
- Perform simplified year-end closing ("forenklet årsoppgjør" / "vereinfachten Jahresabschluss")
- Post depreciation, closing entries, result allocation
Languages observed: NO, FR, EN, DE

## DO NOT USE these endpoints — they do NOT exist and return 404:
- GET /resultSheet
- GET /result
- GET /profitAndLoss

Use GET /ledger/account and GET /ledger/posting (with REQUIRED dateFrom + dateTo) instead.

---

## A. Ledger Corrections (Adjustment Vouchers)

**For correction vouchers (new postings):**
1. GET /ledger/account?number=XXXX for each account mentioned → capture account IDs
2. If VAT is involved: GET /ledger/vatType?fields=id,number,percentage → find correct VAT type
3. POST /ledger/voucher with balanced postings (see Field Reference below)

**For reversals of existing vouchers:**
1. GET /ledger/voucher?dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD → find the voucher to reverse
   - Filter by description, amount, or date to find the right one
   - You need the voucher ID from the response
2. PUT /ledger/voucher/{voucher_id}/:reverse?date=YYYY-MM-DD — date is a REQUIRED query param (no body)
   - If this returns 422, the voucher may already be reversed or is in a closed period
   - In that case, create a NEW voucher with opposite amounts instead

**For combined (reverse old + post new):**
1. Find and reverse the old voucher (steps above)
2. Create new correction voucher with correct amounts

---

## B. Simplified Year-End Closing ("Forenklet Årsoppgjør")

### Step 1: Look up all required account IDs
```
GET /ledger/account?number=1200  → asset account (machinery)
GET /ledger/account?number=6010  → depreciation expense
GET /ledger/account?number=8800  → year-end closing (årsoppgjør)
GET /ledger/account?number=2050  → equity / retained earnings (annen egenkapital)
GET /ledger/account?number=8960  → tax expense (if applicable)
GET /ledger/account?number=2510  → tax payable (if applicable)
```

### Step 2: Calculate year's profit/loss
To find the result for the year, query all postings:
```
GET /ledger/posting?dateFrom=<year>-01-01&dateTo=<year>-12-31&accountNumberFrom=3000&accountNumberTo=9999&fields=*
```
Sum all amounts. Revenue accounts (3xxx) will be negative (credit), expense accounts (4xxx-8xxx) positive (debit). The net sum = result (negative = profit, positive = loss).

Alternatively, if the task gives you the profit/loss amount directly, use that.

### Step 3: Post depreciation (if required)
```
POST /ledger/voucher
{
  "date": "<year>-12-31",
  "description": "Årsavskrivning <year>",
  "postings": [
    {
      "account": {"id": <depreciation_expense_6010_id>},
      "amount": <annual_depreciation>,
      "amountCurrency": <annual_depreciation>,
      "currency": {"id": 1},
      "description": "Årsavskrivning",
      "row": 1
    },
    {
      "account": {"id": <asset_account_1200_id>},
      "amount": <negative_annual_depreciation>,
      "amountCurrency": <negative_annual_depreciation>,
      "currency": {"id": 1},
      "description": "Akkumulert avskrivning",
      "row": 2
    }
  ]
}
```

### Step 4: Post tax provision (if required)
```
POST /ledger/voucher
{
  "date": "<year>-12-31",
  "description": "Skattekostnad <year>",
  "postings": [
    {
      "account": {"id": <tax_expense_8960_id>},
      "amount": <tax_amount>,
      "amountCurrency": <tax_amount>,
      "currency": {"id": 1},
      "description": "Beregnet skatt",
      "row": 1
    },
    {
      "account": {"id": <tax_payable_2510_id>},
      "amount": <negative_tax_amount>,
      "amountCurrency": <negative_tax_amount>,
      "currency": {"id": 1},
      "description": "Betalbar skatt",
      "row": 2
    }
  ]
}
```

### Step 5: Post result allocation (transfer profit/loss to equity)
After depreciation and tax are posted, allocate the net result:
- If profit: credit 8800 (debit side = positive amount), debit 2050 (credit side = negative)
- If loss: opposite signs

```
POST /ledger/voucher
{
  "date": "<year>-12-31",
  "description": "Årsoppgjør <year> - overføring til egenkapital",
  "postings": [
    {
      "account": {"id": <year_end_8800_id>},
      "amount": <result_amount>,
      "amountCurrency": <result_amount>,
      "currency": {"id": 1},
      "description": "Årsresultat",
      "row": 1
    },
    {
      "account": {"id": <equity_2050_id>},
      "amount": <negative_result_amount>,
      "amountCurrency": <negative_result_amount>,
      "currency": {"id": 1},
      "description": "Overført til annen egenkapital",
      "row": 2
    }
  ]
}
```

**Profit example**: If profit is 100,000 → 8800 amount = 100000, 2050 amount = -100000
**Loss example**: If loss is 50,000 → 8800 amount = -50000, 2050 amount = 50000

---

## Field Reference
```json
{
  "date": "YYYY-MM-DD",
  "description": "Korreksjon: <description of what is being corrected>",
  "postings": [
    {
      "account": {"id": "<account_id>"},
      "amount": <positive_or_negative>,
      "amountCurrency": <same_as_amount>,
      "currency": {"id": 1},
      "description": "Debit/credit description",
      "row": 1
    },
    {
      "account": {"id": "<other_account_id>"},
      "amount": <opposite_sign>,
      "amountCurrency": <same_as_amount>,
      "currency": {"id": 1},
      "description": "Balancing entry",
      "row": 2
    }
  ]
}
```

If VAT is involved, add to the VAT-bearing row:
```json
{
  "vatType": {"id": <vat_type_id>},
  "amountGross": <gross_amount>,
  "amountGrossCurrency": <gross_amount>
}
```

## Common Account Numbers for Year-End
- 1200: Maskiner og anlegg (machinery/equipment)
- 2050: Annen egenkapital (other equity / retained earnings)
- 2510: Betalbar skatt (tax payable)
- 6010: Avskrivning (depreciation expense)
- 8800: Årsoppgjør (year-end closing)
- 8801: Overføring til/fra egenkapital (transfer to/from equity)
- 8960: Skattekostnad (tax expense)

## Known Gotchas
- **Postings MUST balance**: Sum of all amounts must equal 0. If they don't, you get 422.
- **amountCurrency**: ALWAYS set equal to amount for NOK transactions. Omitting it silently results in 0.0.
- **Row numbers**: Start at 1 (row 0 is reserved for system-generated VAT postings).
- **Reversals need date**: PUT /:reverse?date=YYYY-MM-DD — omitting date → 422 "Kan ikke være null"
- **Reversals may fail**: If PUT /:reverse returns 422 (not the date issue), create a new voucher with opposite amounts instead.
- **Date matters**: Use 12-31 of the fiscal year for year-end entries, not today's date.
- **Multiple corrections**: If correcting multiple errors, each voucher must balance independently.
- **DO NOT call** GET /resultSheet — it returns 404. Use GET /ledger/posting with date filters to calculate results.
- **DO NOT call** GET /balanceSheet to verify — it wastes an API call.
- **GET /ledger/posting requires dateFrom and dateTo** — omitting them causes 422 "Validation failed".
