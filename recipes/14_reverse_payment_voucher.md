# Reverse Payment Voucher (Tier 2)

STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## Task Pattern
The customer has already paid an invoice, but the payment needs to be reversed (e.g., returned by the bank). You must: create the customer, create an invoice, register a payment, find the payment voucher, and reverse it.

Typical prompts: "Betalingen fra X ble returnert av banken. Reverser betalingen." / "The payment was received but needs to be reversed." / "Reverse the payment voucher."

## Step 1: Create the customer
**API call:** `POST /customer`
**Payload:**
```json
{"name": "<customer_name>", "organizationNumber": "<org_number>"}
```
**Capture:** `customer_id`
**On error 422 "Kundenummeret er i bruk":** `GET /customer?organizationNumber=<org_number>` to find existing ID.

## Step 2: Create a product (minimal)
**API call:** `POST /product`
**Payload:**
```json
{"name": "<product_name>", "priceExcludingVatCurrency": <amount_excl_vat>}
```
**Capture:** `product_id`
**NEVER include vatType or number fields.**

## Step 3: Create order with inline orderLine
**API call:** `POST /order`
**Payload:**
```json
{
  "customer": {"id": <customer_id>},
  "orderDate": "{today}",
  "deliveryDate": "{today}",
  "orderLines": [
    {
      "product": {"id": <product_id>},
      "count": 1,
      "unitPriceExcludingVatCurrency": <amount_excl_vat>
    }
  ]
}
```
**Capture:** `order_id`

## Step 4: Create invoice
**API call:** `POST /invoice`
**Payload:**
```json
{
  "invoiceDate": "{today}",
  "invoiceDueDate": "<today + 30 days>",
  "orders": [{"id": <order_id>}]
}
```
**Capture:** `invoice_id`

## Step 5: Get payment type
**API call:** `GET /invoice/paymentType?fields=id,name`
**Capture:** `payment_type_id` (use the first result, typically id=1 for bank transfer)

## Step 6: Register payment on the invoice
**API call:** `PUT /invoice/<invoice_id>/:payment` with QUERY PARAMS (NO body)
**Query params:** `?paymentDate={today}&paymentTypeId=<payment_type_id>&paidAmount=<total_incl_vat>&paidAmountCurrency=1`
**CRITICAL:** All parameters are QUERY PARAMS, NOT a request body. The `paidAmount` is the total INCLUDING VAT (amount_excl_vat * 1.25 for 25% VAT).

## Step 7: Find the payment voucher
**API call:** `GET /invoice/<invoice_id>?fields=id,voucher,voucherNumber`
**Purpose:** Get the invoice details to find the associated payment voucher.
Then:
**API call:** `GET /ledger/voucher?invoiceId=<invoice_id>&fields=id,number,date,description,voucherType`
If that returns empty or 422, try:
**API call:** `GET /ledger/voucher?dateFrom={today}&dateTo={today}&fields=id,number,date,description,voucherType`
**Capture:** Find the voucher with type related to payment (look for the most recent voucher). Capture `voucher_id`.

**Alternative approach:** After Step 6, the PUT /:payment response may include voucher info. Check the response for a voucher ID. If found, skip the GET calls.

## Step 8: Reverse the payment voucher
**API call:** `PUT /ledger/voucher/<voucher_id>/:reverse` with QUERY PARAM `?date={today}`
**CRITICAL:** The `date` query parameter is REQUIRED. Without it, you get 422 "Validation failed".
**This is a PUT with QUERY PARAMS ONLY — NO request body.**
**On success:** Returns the reversed voucher.

## IMPORTANT
- The `PUT /ledger/voucher/{id}/:reverse?date={today}` endpoint requires the `date` query parameter — this is the reversal date. Omitting it causes 422.
- Payment registration uses QUERY PARAMS on PUT, NOT a request body.
- `paidAmount` should be the TOTAL including VAT. If the prompt says "21450 kr ekskl. MVA", the paidAmount is 21450 * 1.25 = 26812.50.
- Do NOT verify with GET calls after the reversal — the PUT response confirms success.
- Do NOT retry the exact same reversal if it fails — read the error message and fix the issue.
- If the voucher cannot be reversed (locked/linked), do NOT delete it — create a corrective voucher instead.
- Target: 8-9 calls, 0 errors.
