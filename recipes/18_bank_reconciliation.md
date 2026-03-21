# Bank Reconciliation from CSV (Tier 3)

## CRITICAL — Time Budget
This task has MANY API calls. You MUST minimize LLM iterations (each costs ~10s).
**Target: 4 iterations max.** Batch as many parallel tool calls per iteration as possible.

## Task Pattern
Reconcile a bank statement CSV. Incoming payments → customer invoices. Outgoing payments → supplier vouchers. Bank fees → expense vouchers.

## Iteration Plan (FOLLOW THIS EXACTLY)

### Iteration 1: Setup + all entities (7-10 parallel calls)
Issue ALL of these in ONE tool_use response:
- GET /ledger/account?number=1920 → bank_account_id
- GET /ledger/account?number=2400 → supplier_account_id
- GET /ledger/account?number=7770 → fee_account_id
- GET /invoice/paymentType → payment_type_id
- POST /customer for EACH unique customer in CSV
- POST /supplier for EACH unique supplier in CSV
- POST /product {name: "Service", priceExcludingVatCurrency: 1}

### Iteration 2: All orders (parallel)
Using customer_ids and product_id from iteration 1:
- POST /order for EACH incoming payment (one order per customer payment line)
  Each order has ONE orderLine with the payment amount as unitPriceExcludingVatCurrency

### Iteration 3: All invoices + all vouchers (parallel)
Using order_ids from iteration 2 and account_ids from iteration 1:
- POST /invoice for EACH order (one invoice per order)
- POST /ledger/voucher for EACH outgoing supplier payment
- POST /ledger/voucher for EACH bank fee

### Iteration 4: All payments (parallel)
Using invoice_ids from iteration 3:
- PUT /invoice/{id}/:createPayment for EACH invoice

Then STOP. Do NOT verify.

## Field Reference

### POST /order
```json
{
  "customer": {"id": "<customer_id>"},
  "deliveryDate": "<payment_date>",
  "orderDate": "<payment_date>",
  "orderLines": [{"product": {"id": "<product_id>"}, "count": 1, "unitPriceExcludingVatCurrency": 28812.50}]
}
```

### POST /invoice
```json
{
  "invoiceDate": "<payment_date>",
  "invoiceDueDate": "<payment_date>",
  "orders": [{"id": "<order_id>"}]
}
```

### PUT /invoice/{id}/:createPayment
Query params ONLY (NO body): `paymentDate=YYYY-MM-DD&paymentTypeId=<id>&paidAmount=28812.50&paidAmountCurrency=28812.50`

### POST /ledger/voucher (supplier payment)
```json
{
  "date": "<payment_date>",
  "description": "Betaling til <supplier> / <ref>",
  "postings": [
    {"account": {"id": "<account_2400>"}, "supplier": {"id": "<supplier_id>"}, "amount": -28812.50, "amountCurrency": -28812.50, "currency": {"id": 1}, "row": 1},
    {"account": {"id": "<account_1920>"}, "amount": 28812.50, "amountCurrency": 28812.50, "currency": {"id": 1}, "row": 2}
  ]
}
```

### POST /ledger/voucher (bank fee)
```json
{
  "date": "<fee_date>",
  "description": "Bankgebyr",
  "postings": [
    {"account": {"id": "<account_7770>"}, "amount": 350.00, "amountCurrency": 350.00, "currency": {"id": 1}, "row": 1},
    {"account": {"id": "<account_1920>"}, "amount": -350.00, "amountCurrency": -350.00, "currency": {"id": 1}, "row": 2}
  ]
}
```

## Known Gotchas
- **Supplier voucher postings REQUIRE supplier ID**: On the 2400 posting, include `"supplier": {"id": "<supplier_id>"}`. Without it → 422 "Leverandør mangler".
- **Voucher postings MUST balance**: Sum of all amounts = 0.
- **amountCurrency**: ALWAYS set equal to amount. Omitting it = 0.0.
- **Row numbers**: Start at 1.
- **European decimals**: `28 812,50` = 28812.50. Remove spaces, replace comma with dot.
- **Multiple payments from same customer**: Each CSV line = separate order + invoice + payment.
- **Do NOT use /incomingInvoice** — returns 403.
- **Do NOT verify** — no GET after creates.

## Expected Performance
- Calls: 20-30 (depends on CSV transaction count)
- Errors: 0
- Iterations: 4
- Time: <120s
