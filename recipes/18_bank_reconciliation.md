# Bank Reconciliation from CSV (Tier 3)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## CRITICAL — Time Budget
This task has MANY API calls. You MUST minimize LLM iterations (each costs ~10s).
**Target: 4 iterations max.** Batch as many parallel tool calls per iteration as possible.

## Task Pattern
Reconcile a bank statement CSV. Parse it FIRST, then execute in exactly 4 iterations:
- Incoming payments (Inn column) → customer + order + invoice + payment
- Outgoing payments (Ut column) → supplier + voucher (2400/1920)
- Bank fees (Bankgebyr) → voucher (7770/1920)

## CSV Parsing Rules
- Delimiter: semicolon (`;`)
- Header: `Dato;Forklaring;Inn;Ut;Saldo`
- `Inn` = inflow (positive) — customer payments OR bank fee credits
- `Ut` = outflow (negative) — supplier payments OR bank fee debits
- `Saldo` = running balance — NEVER use this as a payment amount
- Dates are already YYYY-MM-DD
- Amounts use `.` as decimal separator. European format `28 812,50` → remove spaces, replace `,` with `.` → `28812.50`

**Transaction classification from `Forklaring` column:**
| Pattern | Type | Action |
|---------|------|--------|
| `Innbetaling fra <Name> / Faktura <N>` | Customer payment | customer → order → invoice → payment |
| `Betaling <Name>` or `Betaling Fournisseur/Lieferant <Name>` | Supplier payment | supplier → voucher (2400/1920) |
| `Bankgebyr` | Bank fee | voucher (7770/1920) — check which column for sign |

**Pre-processing:** Group by unique customer name and unique supplier name. One entity per unique name, but one order/invoice per CSV row.

## Iteration 1: Setup + All Entities (7-12 parallel calls)
Issue ALL of these in ONE tool_use response:
```
GET /ledger/account?number=1920&fields=id,number    → bank_account_id
GET /ledger/account?number=2400&fields=id,number    → supplier_account_id
GET /ledger/account?number=7770&fields=id,number    → fee_account_id
GET /invoice/paymentType?fields=*             → payment_type_id (use values[0].id)
POST /customer {name: "<name1>"}                    → customer_id_1
POST /customer {name: "<name2>"}                    → customer_id_2
... (one per UNIQUE customer)
POST /supplier {name: "<name1>"}                    → supplier_id_1
... (one per UNIQUE supplier)
POST /product {name: "Service", priceExcludingVatCurrency: 1}  → product_id
```

## Iteration 2: All Orders (parallel)
One order per incoming CSV row (NOT per unique customer). If "Robert SARL" has 3 payment rows → 3 separate orders.
```json
POST /order {
  "customer": {"id": "<customer_id_for_this_row>"},
  "orderDate": "<payment_date>",
  "deliveryDate": "<payment_date>",
  "orderLines": [{"product": {"id": "<product_id>"}, "count": 1,
                  "unitPriceExcludingVatCurrency": "<inn_amount>"}]
}
```
Issue ALL order POSTs in parallel. Capture each order_id.

## Iteration 3: All Invoices + All Vouchers (parallel)
Issue ALL of these in ONE tool_use response:

**For each order → create invoice:**
```json
POST /invoice {
  "invoiceDate": "<payment_date>",
  "invoiceDueDate": "<payment_date>",
  "orders": [{"id": "<order_id>"}]
}
```

**For each supplier payment → create voucher:**
```json
POST /ledger/voucher {
  "date": "<supplier_date>",
  "description": "Betaling til <supplier_name>",
  "postings": [
    {"account": {"id": "<account_2400>"}, "supplier": {"id": "<supplier_id>"},
     "amount": -<abs_amount>, "amountCurrency": -<abs_amount>, "currency": {"id": 1}, "row": 1},
    {"account": {"id": "<account_1920>"},
     "amount": <abs_amount>, "amountCurrency": <abs_amount>, "currency": {"id": 1}, "row": 2}
  ]
}
```

**For each bank fee in `Ut` column (standard debit):**
```json
POST /ledger/voucher {
  "date": "<fee_date>",
  "description": "Bankgebyr",
  "postings": [
    {"account": {"id": "<account_7770>"},
     "amount": <abs_fee>, "amountCurrency": <abs_fee>, "currency": {"id": 1}, "row": 1},
    {"account": {"id": "<account_1920>"},
     "amount": -<abs_fee>, "amountCurrency": -<abs_fee>, "currency": {"id": 1}, "row": 2}
  ]
}
```

**For each bank fee in `Inn` column (bank credit/refund — REVERSE postings):**
```json
POST /ledger/voucher {
  "date": "<fee_date>",
  "description": "Bankgebyr",
  "postings": [
    {"account": {"id": "<account_1920>"},
     "amount": <abs_fee>, "amountCurrency": <abs_fee>, "currency": {"id": 1}, "row": 1},
    {"account": {"id": "<account_7770>"},
     "amount": -<abs_fee>, "amountCurrency": -<abs_fee>, "currency": {"id": 1}, "row": 2}
  ]
}
```

## Iteration 4: Register All Payments (parallel)
For each invoice from iteration 3:
```
PUT /invoice/<invoice_id>/:payment
  ?paymentDate=<payment_date>&paymentTypeId=<payment_type_id>
  &paidAmount=<inn_amount>&paidAmountCurrency=<inn_amount>
```
**CRITICAL**: Endpoint is `/:payment`, NOT `/:createPayment`. Uses QUERY PARAMS, NOT body.

Then STOP. Do NOT verify.

## IMPORTANT
- Supplier voucher 2400 posting REQUIRES `"supplier": {"id": ...}` — without it → 422 "Leverandor mangler"
- Voucher postings MUST balance (sum of amounts = 0)
- `amountCurrency` MUST always equal `amount` — omitting defaults to 0.0
- Row numbers start at 1
- Bank fees CAN appear in Inn column (positive = bank credit) — reverse the posting direction
- `Saldo` column is informational ONLY — never use as payment amount
- One order per CSV row, not per unique customer
- Do NOT use /incomingInvoice — returns 403
- Do NOT verify after creates — no GET calls after iteration 4
- Target: 20-25 calls in 4 iterations. 0 errors.
