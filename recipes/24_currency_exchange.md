# Currency Exchange Rate Difference Voucher (Tier 2)

## Task Pattern
An invoice was sent/received in a foreign currency (e.g. EUR) at exchange rate X.
Payment was made/received at a different exchange rate Y.
The difference must be booked as exchange rate gain or loss.

## Key Accounts
- 1500 (Customer receivables) or 2400 (Supplier payables) — depends on direction
- 1920 (Bank account)
- 8060 (Valutagevinst / Exchange rate gain) — when favorable
- 8160 (Valutatap / Exchange rate loss) — when unfavorable

## Amount Calculations
- Invoice amount in NOK = EUR_amount * invoice_rate
- Payment amount in NOK = EUR_amount * payment_rate
- Exchange difference = Payment_NOK - Invoice_NOK
  - If positive on receivable (got more than expected): GAIN → credit 8060
  - If negative on receivable (got less than expected): LOSS → debit 8160
  - For payables, the logic is reversed

## Optimal API Sequence

1. Look up ALL account IDs in parallel:
   - GET /ledger/account?number=1920 → bank_account_id
   - GET /ledger/account?number=1500 (or 2400) → receivable_account_id (or payable)
   - GET /ledger/account?number=8060 → gain_account_id
   - GET /ledger/account?number=8160 → loss_account_id
   - GET /currency?code=EUR → currency_id (for foreign currency postings)

2. POST /ledger/voucher — book the payment with exchange rate difference:

### Example: Customer paid EUR 10,000. Invoice rate 11.50, payment rate 11.80.
- Invoice NOK = 115,000. Payment NOK = 118,000. Gain = 3,000.

```json
{
  "date": "YYYY-MM-DD",
  "description": "Innbetaling EUR 10 000 - valutagevinst",
  "postings": [
    {
      "account": {"id": "<bank_account_id>"},
      "amount": 118000,
      "amountCurrency": 118000,
      "amountGross": 118000,
      "amountGrossCurrency": 118000,
      "currency": {"id": 1},
      "description": "Innbetaling fra kunde",
      "row": 1
    },
    {
      "account": {"id": "<receivable_account_id>"},
      "amount": -115000,
      "amountCurrency": -115000,
      "amountGross": -115000,
      "amountGrossCurrency": -115000,
      "currency": {"id": 1},
      "description": "Motregning kundefordring",
      "row": 2
    },
    {
      "account": {"id": "<gain_account_id>"},
      "amount": -3000,
      "amountCurrency": -3000,
      "amountGross": -3000,
      "amountGrossCurrency": -3000,
      "currency": {"id": 1},
      "description": "Valutagevinst EUR",
      "row": 3
    }
  ]
}
```

### Example: Supplier paid EUR 5,000. Invoice rate 11.50, payment rate 11.80. Loss = 1,500.
```json
{
  "date": "YYYY-MM-DD",
  "description": "Betaling leverandør EUR 5 000 - valutatap",
  "postings": [
    {
      "account": {"id": "<payable_account_id>"},
      "amount": 57500,
      "amountCurrency": 57500,
      "amountGross": 57500,
      "amountGrossCurrency": 57500,
      "currency": {"id": 1},
      "description": "Motregning leverandørgjeld",
      "row": 1
    },
    {
      "account": {"id": "<bank_account_id>"},
      "amount": -59000,
      "amountCurrency": -59000,
      "amountGross": -59000,
      "amountGrossCurrency": -59000,
      "currency": {"id": 1},
      "description": "Utbetaling til leverandør",
      "row": 2
    },
    {
      "account": {"id": "<loss_account_id>"},
      "amount": 1500,
      "amountCurrency": 1500,
      "amountGross": 1500,
      "amountGrossCurrency": 1500,
      "currency": {"id": 1},
      "description": "Valutatap EUR",
      "row": 3
    }
  ]
}
```

## Self-Check: Balance Verification
Before POST, verify: sum of ALL amount fields = 0.
- Example 1: 118000 + (-115000) + (-3000) = 0  OK
- Example 2: 57500 + (-59000) + 1500 = 0  OK

## Critical Rules
- ALWAYS set ALL FOUR amount fields on every posting: amount, amountCurrency, amountGross, amountGrossCurrency
- For non-VAT rows: amountGross = amount, amountGrossCurrency = amountCurrency
- ALWAYS look up account IDs with GET /ledger/account?number=XXXX
- Row numbers start at 1, sequential, no gaps
- No vatType needed on exchange rate difference postings (8060/8160 are not VAT accounts)
- If the task involves VAT (e.g. the original invoice had VAT), the exchange difference is still posted without VAT — it only applies to the net currency difference
