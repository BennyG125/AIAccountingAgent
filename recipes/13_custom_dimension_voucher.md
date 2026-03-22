# Custom Dimension + Voucher (Tier 2)

## CORRECT ENDPOINTS — Use these EXACTLY
- POST /ledger/accountingDimensionName — Create a custom dimension
- POST /ledger/accountingDimensionValue — Create values for a dimension
- GET /ledger/accountingDimensionName — List existing dimensions
- GET /ledger/accountingDimensionValue/search — Search dimension values

## WARNING: These endpoints DO NOT EXIST — never try them
- /dimension — 404
- /ledger/dimension — 404
- /ledger/customDimension — 404
- /dimension/v2 — 404
- /customDimension — 404
- /ledger/freeDimension — 404
- /freeDimension — 404
- /freeAccountingDimension — 404
- /ledger/freeAccountingDimension — 404
- /ledger/freeAccountingDimensionType — 404

## Step-by-step flow

### 1. Create the custom dimension name
```
POST /ledger/accountingDimensionName
{
  "dimensionName": "<name from task, e.g. Region>",
  "dimensionIndex": 1,
  "active": true
}
```
Required fields:
- dimensionName (string) — the name of the dimension
- dimensionIndex (int) — must be 1, 2, or 3. Use 1 for the first custom dimension, 2 for second, 3 for third.
- active (boolean) — set to true

### 2. Create dimension values
```
POST /ledger/accountingDimensionValue
{
  "displayName": "<value name, e.g. Vestlandet>",
  "dimensionIndex": 1,
  "number": "1",
  "active": true
}
```
Required fields:
- displayName (string) — the name of the value
- dimensionIndex (int) — MUST match the dimension's index from step 1
- number (string) — a unique number/code for this value
- active (boolean) — set to true

Repeat for each dimension value the task requires. Capture the returned ID for each value you need to reference in voucher postings.

### 3. Look up account IDs (if task includes a voucher)
```
GET /ledger/account?number=<account_number>
```
Capture the account ID from values[0].id. Do this for each account number mentioned in the task.

### 4. Create the voucher with dimension references
```
POST /ledger/voucher
{
  "date": "YYYY-MM-DD",
  "description": "<description from task>",
  "postings": [
    {
      "account": {"id": <expense_account_id>},
      "amountGross": <amount>,
      "amountGrossCurrency": <amount>,
      "row": 1,
      "freeAccountingDimension1": {"id": <dimension_value_id>}
    },
    {
      "account": {"id": <bank_account_id>},
      "amountGross": <negative_amount>,
      "amountGrossCurrency": <negative_amount>,
      "row": 2
    }
  ]
}
```

### Linking dimensions to voucher postings
The posting object has three optional dimension fields:
- **freeAccountingDimension1** ({id}) — links to a value from dimension with index 1
- **freeAccountingDimension2** ({id}) — links to a value from dimension with index 2
- **freeAccountingDimension3** ({id}) — links to a value from dimension with index 3

Use the field that matches your dimension's index. Reference the dimension VALUE id (not the dimension name id).

## Complete example
Task: Create dimension "Region" with values "Vestlandet" and "Nord-Norge", then post a voucher for 19550 NOK to account 6540 (debit) / 1920 (credit) tagged with "Vestlandet".

1. `POST /ledger/accountingDimensionName` with `{"dimensionName": "Region", "dimensionIndex": 1, "active": true}`
2. `POST /ledger/accountingDimensionValue` with `{"displayName": "Vestlandet", "dimensionIndex": 1, "number": "1", "active": true}` → capture value_id
3. `POST /ledger/accountingDimensionValue` with `{"displayName": "Nord-Norge", "dimensionIndex": 1, "number": "2", "active": true}`
4. `GET /ledger/account?number=6540` → capture expense_account_id
5. `GET /ledger/account?number=1920` → capture bank_account_id
6. `POST /ledger/voucher` with postings:
   - Row 1: account expense_account_id, amountGross 19550, freeAccountingDimension1: {id: value_id}
   - Row 2: account bank_account_id, amountGross -19550
