# Overdue Invoice + Reminder Fee (Tier 2)
Handles: find overdue invoices, send reminders, add reminder fees.

## Flow A: Send a reminder on an overdue invoice
1. GET /invoice?invoiceDateTo={today}&fields=* → find invoices
   - Filter results to find overdue ones: where invoiceDueDate < today and amountOutstanding > 0
   - NOTE: Do NOT use amountRemaining or amountRemainingCurrency — neither exists. The correct field is amountOutstanding.
   - GET /invoice REQUIRES invoiceDateFrom and invoiceDateTo query params (422 without them).
2. PUT /invoice/{invoice_id}/:createReminder — QUERY PARAMS (not body):
   ?type=REMINDER&date={today}&dispatchType=EMAIL&includeCharge=true
   - type REQUIRED: "SOFT_REMINDER", "REMINDER", "NOTICE_OF_DEBT_COLLECTION", "DEBT_COLLECTION"
   - date REQUIRED: YYYY-MM-DD
   - dispatchType REQUIRED: "EMAIL" | "OWN_PRINTER" | "NETS_PRINT" | "SMS"
     (without dispatchType you get 422 "Minst én sendetype må oppgis")
   - includeCharge: boolean (true to add reminder fee)
   - includeInterest: boolean (true to add interest)
   - IMPORTANT: Invoice must already be SENT before you can create a reminder.
     If not sent yet, send it first: PUT /invoice/{id}/:send?sendType=EMAIL

## Flow B: Add a reminder fee as a separate invoice
If the task says to add a "purregebyr" (reminder fee) as a separate charge:
1. Find the overdue invoice (see Flow A step 1) → capture customer_id from the invoice
2. POST /product {name: "Purregebyr", priceExcludingVatCurrency: 50} → capture product_id
3. POST /order {customer: {id: customer_id}, orderDate: "{today}", deliveryDate: "{today}",
   orderLines: [{product: {id: product_id}, count: 1, unitPriceExcludingVatCurrency: 50}]}
   → capture order_id
4. POST /invoice {invoiceDate: "{today}", invoiceDueDate: "14 days later",
   orders: [{id: order_id}]} → capture fee_invoice_id
5. PUT /invoice/{fee_invoice_id}/:send?sendType=EMAIL

## Flow C: Re-send an updated invoice
You CANNOT re-send an already-sent invoice. If the task asks to "send the updated invoice":
- The original sent invoice cannot be modified or re-sent
- Instead: create a credit note on the original, then create a new invoice with updated amounts
- See recipe #15 (Credit Note) for the credit note flow

## Common mistakes
- Trying to PUT body {"sendType": "EMAIL"} on /:send — sendType is a QUERY PARAM
- Trying to /:send an invoice that was already sent — use /:createReminder instead
- Trying to modify a sent invoice — sent invoices are locked, use credit note + new invoice
- Forgetting that customer needs email set before /:send works
