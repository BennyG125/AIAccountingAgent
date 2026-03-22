# Overdue Invoice Reminder (Tier 3)

STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## Task Pattern
Find an overdue (unpaid, past-due) invoice in the sandbox. Book a reminder fee voucher (debit 1500, credit 3400). Create a new invoice for the reminder fee and send it. Register a partial payment on the original overdue invoice. Prompts appear in DE, ES, PT, NO, EN, FR.

Typical prompt (translated): "One of your customers has an overdue invoice. Find it and book a reminder fee of X NOK (debit 1500, credit 3400). Create an invoice for the reminder fee and send it. Register a partial payment of 5000 NOK on the overdue invoice."

## Parameters to extract
- `reminder_fee_amount`: 35, 40, or 70 NOK (from the prompt)
- `partial_payment_amount`: 5000 NOK (always so far)
- Debit account: 1500 (from the prompt)
- Credit account: 3400 (from the prompt)
- Customer: NOT given by name — must be discovered from the overdue invoice

## Step 1: Find the overdue invoice
**API call:** `GET /invoice?invoiceDateFrom=<one_year_ago>&invoiceDateTo={today}&fields=id,invoiceNumber,invoiceDueDate,amountOutstanding,customer`
**Capture:** Pick the invoice with the earliest `invoiceDueDate` in the past AND non-zero `amountOutstanding`. Capture `overdue_invoice_id` and `customer_id` (from `customer.id`).
**CRITICAL:** Do NOT use `invoiceDateFrom=2000-01-01` — this causes 422. Use a 1-year lookback: `invoiceDateFrom=<today minus 365 days>`.
**On error 422:** Try a narrower date window, e.g. 6 months back.

## Step 2: Look up ledger account IDs (2 parallel GETs)
**API calls (run both in parallel):**
```
GET /ledger/account?number=1500&fields=id,number,name   → debit_account_id
GET /ledger/account?number=3400&fields=id,number,name   → credit_account_id
```
**On 404 for account 3400:** `POST /ledger/account {"number": 3400, "name": "Purregebyr"}` to create it.

## Step 3: Post reminder fee voucher
**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "{today}",
  "description": "Reminder fee <reminder_fee_amount> NOK",
  "postings": [
    {
      "account": {"id": <debit_account_id>},
      "amount": <reminder_fee_amount>,
      "amountCurrency": <reminder_fee_amount>,
      "amountGross": <reminder_fee_amount>,
      "amountGrossCurrency": <reminder_fee_amount>,
      "currency": {"id": 1},
      "customer": {"id": <customer_id>},
      "description": "Reminder fee — accounts receivable",
      "row": 1
    },
    {
      "account": {"id": <credit_account_id>},
      "amount": <negative_reminder_fee>,
      "amountCurrency": <negative_reminder_fee>,
      "amountGross": <negative_reminder_fee>,
      "amountGrossCurrency": <negative_reminder_fee>,
      "currency": {"id": 1},
      "description": "Reminder fee income",
      "row": 2
    }
  ]
}
```
**CRITICAL rules:**
- Both `amount` AND `amountCurrency` MUST be set (same value) — omitting `amountCurrency` silently results in 0.0.
- Do NOT include `vatType` on either row — reminder fees have no VAT here.
- Postings must balance: row 1 = +fee, row 2 = -fee.
- Rows start at 1 (row 0 is system-reserved).

## Step 4: Get payment type
**API call:** `GET /invoice/paymentType?fields=*`
**Capture:** `payment_type_id` (first result, typically id=1 for bank transfer)

## Step 5: Create order for the reminder fee invoice
**API call:** `POST /order`
**Payload:**
```json
{
  "customer": {"id": <customer_id>},
  "orderDate": "{today}",
  "deliveryDate": "{today}",
  "orderLines": [
    {
      "description": "Reminder fee",
      "count": 1,
      "unitPriceExcludingVatCurrency": <reminder_fee_amount>
    }
  ]
}
```
**Capture:** `order_id`
**NOTE:** No product creation needed — description-only orderLine saves a call.

## Step 6: Create the reminder fee invoice
**API call:** `POST /invoice`
**Payload:**
```json
{
  "invoiceDate": "{today}",
  "invoiceDueDate": "<today + 30 days>",
  "orders": [{"id": <order_id>}]
}
```
**Capture:** `reminder_invoice_id`

## Step 7: Send the reminder fee invoice
**API call:** `PUT /invoice/<reminder_invoice_id>/:send`
**Body:** `{"sendType": "EMAIL"}`
**On error 422** (customer has no email): Retry ONCE with `{"sendType": "MANUAL"}`.
**On second 422:** Skip sending — the invoice was created and will be scored on creation fields. Do NOT waste more calls.

## Step 8: Register partial payment on the overdue invoice
**API call:** `PUT /invoice/<overdue_invoice_id>/:payment` with QUERY PARAMS (NO body)
**Query params:** `?paymentDate={today}&paymentTypeId=<payment_type_id>&paidAmount=<partial_payment_amount>&paidAmountCurrency=1`
**CRITICAL:** All parameters are QUERY PARAMS, NOT a request body.

## IMPORTANT
- The sandbox contains exactly ONE overdue invoice — find it by looking for past `invoiceDueDate` with non-zero `amountOutstanding`.
- Do NOT use `PUT /invoice/{id}/:createReminder` — that is a different action (send reminder on existing invoice). This task requires creating a NEW standalone invoice for the fee.
- The voucher (Step 3) records the accounting entry. The invoice (Steps 5-7) sends a formal bill. Both are required.
- Do NOT verify with GET calls after successful creates.
- The send step (Step 7) will likely fail with EMAIL — this is expected. One retry with MANUAL, then move on.
- Target: 8-9 calls, 0-1 errors (the send 422 is expected).
