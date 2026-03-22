# Custom Dimension + Voucher (Tier 2)
STOP. Follow these steps IN ORDER.

## Step 1: Create the dimension name
**API call:** `POST /ledger/accountingDimensionName`
**Payload:**
```json
{"dimensionName": "<name from prompt>", "active": true}
```
The `dimensionIndex` (1, 2, or 3) is assigned automatically. Capture it from the response.

## Step 2: Create dimension values
For EACH value mentioned in the prompt:
**API call:** `POST /ledger/accountingDimensionValue`
**Payload:**
```json
{
  "displayName": "<value name>",
  "dimensionIndex": <index from step 1>,
  "active": true,
  "showInVoucherRegistration": true
}
```
Capture each value's `id` from the response.

## Step 3: Look up accounts for the voucher
**API call:** `GET /ledger/account?number=<XXXX>&fields=id,number` for each account in the prompt.

## Step 4: Post voucher with dimension reference
**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "<date from prompt or today>",
  "description": "<description>",
  "postings": [
    {
      "account": {"id": <debit_account_id>},
      "amount": <amount>,
      "amountCurrency": <amount>,
      "amountGross": <amount>,
      "amountGrossCurrency": <amount>,
      "currency": {"id": 1},
      "freeAccountingDimension<N>": {"id": <value_id>},
      "row": 1,
      "description": "<line description>"
    },
    {
      "account": {"id": <credit_account_id>},
      "amount": <negative_amount>,
      "amountCurrency": <negative_amount>,
      "amountGross": <negative_amount>,
      "amountGrossCurrency": <negative_amount>,
      "currency": {"id": 1},
      "freeAccountingDimension<N>": {"id": <value_id>},
      "row": 2,
      "description": "<line description>"
    }
  ]
}
```
Replace `<N>` with the dimensionIndex (1, 2, or 3) from Step 1.

## IMPORTANT
- Use `/ledger/accountingDimensionName` NOT `/dimension` — the `/dimension` endpoint does NOT exist
- Use `/ledger/accountingDimensionValue` to create values, NOT to search (use `/ledger/accountingDimensionValue/search` for searching)
- Dimension fields on postings are `freeAccountingDimension1`, `freeAccountingDimension2`, or `freeAccountingDimension3` — use the index from step 1
- Max 3 dimensions per company
- Do NOT try to enable modules — dimensions are available by default
