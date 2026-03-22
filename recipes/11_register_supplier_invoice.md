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
      "amountGross": <NEGATIVE_GROSS_AMOUNT>,
      "amountGrossCurrency": <NEGATIVE_GROSS_AMOUNT>,
      "currency": {"id": 1},
      "supplier": {"id": <supplier_id>},
      "description": "Supplier debt",
      "row": 2
    }
  ]
}
```

## Amount Calculations (with worked example)
Given: Invoice total (GROSS) = 12,500 NOK including 25% VAT

Step 1 — Calculate NET and VAT:
  NET = GROSS / 1.25 = 12500 / 1.25 = 10000
  VAT = GROSS - NET = 12500 - 10000 = 2500

Step 2 — Assign to rows:
  Row 1 (Expense, e.g. 7000):
    amount = 10000 (NET — positive = debit)
    amountCurrency = 10000 (MUST equal amount)
    amountGross = 12500 (GROSS — required because vatType is set)
    amountGrossCurrency = 12500 (MUST equal amountGross)
    vatType = {id: <looked_up_vat_id>}

  Row 2 (Supplier debt, 2400):
    amount = -12500 (negative GROSS — credit)
    amountCurrency = -12500 (MUST equal amount)
    amountGross = -12500 (MUST include — omitting silently zeroes the amount!)
    amountGrossCurrency = -12500 (MUST equal amountGross)
    supplier = {id: <supplier_id>} (REQUIRED on 2400 postings)
    NO vatType on this row

  System auto-creates Row 0 (VAT account 2710):
    The system adds +2500 on the VAT account automatically.
    Do NOT create this row yourself.

Step 3 — Self-check balance:
  Row 1 amount (10000) + Row 2 amount (-12500) + System Row 0 (2500) = 0  BALANCED
  You only send rows 1 and 2. The system adds row 0.
  Your submitted rows: 10000 + (-12500) = -2500 (the system fills +2500 to balance)

## General Formulas
- GROSS = total amount including VAT (the invoice total)
- NET = GROSS / 1.25 (for 25% VAT), or GROSS / 1.15 (for 15% VAT), or GROSS / 1.12 (for 12% VAT)
- VAT = GROSS - NET
- Row 1 amount = +NET (debit expense)
- Row 1 amountGross = +GROSS
- Row 2 amount = -GROSS (credit supplier debt)

## Critical Rules
- The system auto-creates a row 0 posting for the VAT account (2710) — do NOT create it yourself
- amountGross MUST equal amountGrossCurrency — omitting either causes 422
- amount MUST equal amountCurrency — omitting amountCurrency silently results in 0.0
- Row 2 does NOT get vatType but MUST have amountGross/amountGrossCurrency (equal to amount)
- Rows start at 1 (row 0 is reserved for the system-generated VAT posting)
- ALWAYS look up account IDs with GET /ledger/account?number=XXXX — NEVER guess
- ALWAYS look up vatType ID with GET /ledger/vatType — do not hardcode
