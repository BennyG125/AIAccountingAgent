# Year-End / Ledger Corrections (Tier 3)

## Task Pattern
Prompts asking to correct accounting errors, post adjustment vouchers, reverse incorrect entries,
or make year-end journal entries. May involve multiple accounts and specific periods.
Languages observed: NO, FR, EN

## Optimal API Sequence

**For correction vouchers (new postings):**
1. GET /ledger/account?number=XXXX for each account mentioned → capture account IDs
2. If VAT is involved: GET /ledger/vatType?fields=id,number,percentage → find correct VAT type
3. POST /ledger/voucher with balanced postings (see Field Reference below)

**For reversals of existing vouchers:**
1. GET /ledger/voucher?dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD → find the voucher to reverse
   - Filter by description, amount, or date to find the right one
   - You need the voucher ID from the response
2. PUT /ledger/voucher/{voucher_id}/:reverse — NO body needed
   - If this returns 422, the voucher may already be reversed or is in a closed period
   - In that case, create a NEW voucher with opposite amounts instead

**For combined (reverse old + post new):**
1. Find and reverse the old voucher (steps above)
2. Create new correction voucher with correct amounts

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

## Known Gotchas
- **Postings MUST balance**: Sum of all amounts must equal 0. If they don't, you get 422.
- **amountCurrency**: ALWAYS set equal to amount for NOK transactions. Omitting it silently results in 0.0.
- **Row numbers**: Start at 1 (row 0 is reserved for system-generated VAT postings).
- **Reversals may fail**: If PUT /:reverse returns 422, create a new voucher with opposite amounts instead.
- **Date matters**: Use the correct accounting period date, not today's date, for corrections.
- **Multiple corrections**: If correcting multiple errors, you can use one voucher with multiple posting pairs, or separate vouchers. Each voucher must balance independently.
- **Do NOT verify**: Do NOT call GET /balanceSheet to verify — it wastes an API call.
