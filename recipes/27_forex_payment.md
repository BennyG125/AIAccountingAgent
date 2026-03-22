# Forex Payment — Currency Exchange Rate Difference (Tier 3)

STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## Task Pattern
A foreign-currency invoice (EUR) was sent to a customer. The customer paid at a different exchange rate. You must: create the customer, create the EUR invoice, register the payment at the invoice rate, and post an exchange rate difference voucher (agio = gain, disagio = loss).

Typical prompt: "Customer X was invoiced EUR Y at rate Z. They paid at rate W. Register the payment and book the exchange rate difference."

## Parameters to extract
- `eur_amount`: Invoice amount in EUR
- `invoice_rate`: NOK/EUR rate when invoice was issued
- `payment_rate`: NOK/EUR rate when customer paid
- `customer_name`: Customer name
- `org_number`: Organization number

## Compute amounts BEFORE making any API calls
```
invoice_nok = eur_amount * invoice_rate      # NOK value at invoice time
payment_nok = eur_amount * payment_rate      # NOK value at payment time
diff_nok    = payment_nok - invoice_nok      # positive = agio (gain), negative = disagio (loss)
```
- If `payment_rate > invoice_rate`: **agio** (currency gain) → use account 8070
- If `payment_rate < invoice_rate`: **disagio** (currency loss) → use account 8060

## Step 1: Look up account IDs and EUR currency (run ALL in parallel)
**API calls (4-5 parallel GETs):**
```
GET /ledger/account?number=1500&fields=id   → ar_account_id      (Kundefordringer)
GET /ledger/account?number=1920&fields=id   → bank_account_id    (Bankkonto)
GET /ledger/account?number=8060&fields=id   → disagio_account_id (only if disagio)
GET /ledger/account?number=8070&fields=id   → agio_account_id    (only if agio)
GET /currency?code=EUR&fields=id            → eur_currency_id
```
**On 404 for account 8060/8070:** Create it: `POST /ledger/account {"number": 8060, "name": "Valutatap"}` or `{"number": 8070, "name": "Valutagevinst"}`.

## Step 2: Create customer
**API call:** `POST /customer`
**Payload:**
```json
{"name": "<customer_name>", "organizationNumber": "<org_number>"}
```
**Capture:** `customer_id`
**On error 422:** `GET /customer?organizationNumber=<org_number>` to find existing ID.

## Step 3: Create order with inline orderLine in EUR
**API call:** `POST /order`
**Payload:**
```json
{
  "customer": {"id": <customer_id>},
  "orderDate": "{today}",
  "deliveryDate": "{today}",
  "currency": {"id": <eur_currency_id>},
  "orderLines": [
    {
      "description": "EUR Invoice <eur_amount>",
      "count": 1,
      "unitPriceExcludingVatCurrency": <eur_amount>
    }
  ]
}
```
**Capture:** `order_id`
**NOTE:** Use description-only orderLine — no product needed. This saves one POST /product call.

## Step 4: Create invoice in EUR
**API call:** `POST /invoice`
**Payload:**
```json
{
  "invoiceDate": "{today}",
  "invoiceDueDate": "<today + 30 days>",
  "orders": [{"id": <order_id>}],
  "currency": {"id": <eur_currency_id>}
}
```
**Capture:** `invoice_id`

## Step 5: Get payment type
**API call:** `GET /invoice/paymentType?fields=*`
**Capture:** `payment_type_id` (first result, typically id=1)
**NOTE:** If you are confident paymentTypeId=1 works, skip this call to save time.

## Step 6: Register payment at the INVOICE exchange rate
**API call:** `PUT /invoice/<invoice_id>/:payment` with QUERY PARAMS (NO body)
**Query params:** `?paymentDate={today}&paymentTypeId=<payment_type_id>&paidAmount=<invoice_nok>&paidAmountCurrency=1`
**CRITICAL:**
- `paidAmount` = `invoice_nok` (= eur_amount * invoice_rate) — NOT payment_nok
- `paidAmountCurrency` = 1 (NOK currency ID)
- All parameters are QUERY PARAMS, NOT a request body.

## Step 7: Post exchange rate difference voucher
**API call:** `POST /ledger/voucher`

**If AGIO (gain, payment_rate > invoice_rate, diff_nok > 0):**
```json
{
  "date": "{today}",
  "description": "Valutagevinst (agio) - <customer_name> EUR <eur_amount>",
  "postings": [
    {
      "account": {"id": <ar_account_id>},
      "amount": <diff_nok>,
      "amountCurrency": <diff_nok>,
      "amountGross": <diff_nok>,
      "amountGrossCurrency": <diff_nok>,
      "currency": {"id": 1},
      "description": "Agio valutagevinst",
      "row": 1
    },
    {
      "account": {"id": <agio_account_id>},
      "amount": <negative_diff_nok>,
      "amountCurrency": <negative_diff_nok>,
      "amountGross": <negative_diff_nok>,
      "amountGrossCurrency": <negative_diff_nok>,
      "currency": {"id": 1},
      "description": "Agio valutagevinst",
      "row": 2
    }
  ]
}
```

**If DISAGIO (loss, payment_rate < invoice_rate, diff_nok < 0):**
```json
{
  "date": "{today}",
  "description": "Valutatap (disagio) - <customer_name> EUR <eur_amount>",
  "postings": [
    {
      "account": {"id": <disagio_account_id>},
      "amount": <abs_diff_nok>,
      "amountCurrency": <abs_diff_nok>,
      "amountGross": <abs_diff_nok>,
      "amountGrossCurrency": <abs_diff_nok>,
      "currency": {"id": 1},
      "description": "Disagio valutatap",
      "row": 1
    },
    {
      "account": {"id": <ar_account_id>},
      "amount": <negative_abs_diff_nok>,
      "amountCurrency": <negative_abs_diff_nok>,
      "amountGross": <negative_abs_diff_nok>,
      "amountGrossCurrency": <negative_abs_diff_nok>,
      "currency": {"id": 1},
      "description": "Disagio valutatap",
      "row": 2
    }
  ]
}
```

**CRITICAL rules:**
- Postings MUST balance (sum of amounts = 0).
- ALWAYS set ALL FOUR amount fields: `amount`, `amountCurrency`, `amountGross`, `amountGrossCurrency` — omitting amountGross silently stores 0.0.
- For non-VAT rows: amountGross = amount, amountGrossCurrency = amountCurrency.
- Do NOT include `vatType` on exchange rate difference postings.
- Rows start at 1.

## IMPORTANT
- Compute all NOK amounts locally BEFORE making API calls — do NOT call any currency exchange rate endpoint.
- Do NOT attempt to delete payment vouchers — they are immutable. If you need to correct a mistake, create a NEW corrective voucher.
- Do NOT verify with GET calls after successful creates.
- The EUR currency ID varies per sandbox — ALWAYS look it up with `GET /currency?code=EUR`.
- Account 8060 = Valutatap (loss/disagio), Account 8070 = Valutagevinst (gain/agio).
- Target: 7-8 calls, 0 errors. All computations are local — the only API calls are lookups, creates, payment, and the voucher.
