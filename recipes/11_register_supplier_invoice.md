# Register Supplier Invoice (Tier 2)

**CRITICAL: NEVER call /incomingInvoice — it ALWAYS returns 403. Go directly to /ledger/voucher.**

1. POST /supplier {name, organizationNumber} → capture supplier_id
2. Look up account IDs (3 parallel GETs):
   - GET /ledger/account?number=7000 (or the expense account from the prompt) → expense_account_id
   - GET /ledger/account?number=2400 → supplier_debt_account_id
   - GET /ledger/vatType?fields=id,number,percentage → find incoming VAT type
     (Usually id=1: "Fradrag inngående avgift, høy sats" for 25% incoming VAT)
3. POST /ledger/voucher with this EXACT structure:
```json
{
  "date": "YYYY-MM-DD",
  "description": "Leverandørfaktura INV-XXX - Supplier Name",
  "postings": [
    {
      "account": {"id": "<expense_account_id>"},
      "amount": <NET_AMOUNT>,
      "amountCurrency": <NET_AMOUNT>,
      "amountGross": <GROSS_AMOUNT>,
      "amountGrossCurrency": <GROSS_AMOUNT>,
      "currency": {"id": 1},
      "vatType": {"id": <vat_type_id>},
      "supplier": {"id": <supplier_id>},
      "description": "Expense description",
      "row": 1
    },
    {
      "account": {"id": "<supplier_debt_account_id>"},
      "amount": <NEGATIVE_GROSS_AMOUNT>,
      "amountCurrency": <NEGATIVE_GROSS_AMOUNT>,
      "currency": {"id": 1},
      "description": "Supplier debt",
      "row": 2
    }
  ]
}
```

## Amount Calculations
- GROSS = total amount including VAT (the invoice total)
- NET = GROSS / 1.25 (for 25% VAT)
- Row 2 amount = negative GROSS (e.g., if GROSS is 10000, row 2 amount is -10000)

## Critical Rules
- The system auto-creates a row 0 posting for the VAT account (2710) — do NOT create it yourself
- amountGross MUST equal amountGrossCurrency — omitting either causes 422
- amount MUST equal amountCurrency — omitting amountCurrency silently results in 0.0
- Row 2 does NOT get vatType or amountGross fields
- Rows start at 1 (row 0 is reserved for the system-generated VAT posting)
