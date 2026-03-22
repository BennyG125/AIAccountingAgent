# Register Supplier Invoice (Tier 2)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

**CRITICAL: NEVER call /incomingInvoice — it ALWAYS returns 403. Go directly to /ledger/voucher.**

## Task Pattern
Register a supplier invoice as a manual journal entry (voucher). Extract from prompt (or PDF via OCR): supplier name, org number, invoice number, gross amount (incl. VAT), VAT rate, expense account number, invoice date.

If a PDF is attached: run `gemini_ocr` FIRST to extract all fields before any API calls.

## Step 1: Find or Create Supplier
**API call:** `GET /supplier?organizationNumber=<org_nr>&fields=id,name,organizationNumber`
- If found → capture `supplier_id = values[0].id`. Skip POST.
- If empty or no org number → `POST /supplier {name: "<name>", organizationNumber: "<org_nr>"}` → capture `id`

## Step 2: Look Up Accounts + VAT Type (3 parallel calls)
Issue ALL three simultaneously:
- `GET /ledger/account?number=<expense_account>&fields=id,number,name` → `expense_account_id`
- `GET /ledger/account?number=2400&fields=id,number,name` → `debt_account_id`
- `GET /ledger/vatType?fields=id,number,name,percentage` → find `vat_type_id` where `percentage == 25` (for 25% VAT)

## Step 3: Post Voucher (single call)
**Calculate amounts:**
- `gross` = total invoice amount incl. VAT (e.g. 62850)
- `net` = gross / 1.25 (for 25% VAT) — e.g. 62850 / 1.25 = 50280
- For 15% VAT: net = gross / 1.15
- For 0% VAT: net = gross, omit vatType and amountGross fields

**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "YYYY-MM-DD",
  "description": "Leverandorfaktura INV-XXX - Supplier Name",
  "postings": [
    {
      "row": 1,
      "account": {"id": "<expense_account_id>"},
      "amount": "<net>",
      "amountCurrency": "<net>",
      "amountGross": "<gross>",
      "amountGrossCurrency": "<gross>",
      "currency": {"id": 1},
      "vatType": {"id": "<vat_type_id>"},
      "supplier": {"id": "<supplier_id>"},
      "description": "INV-XXX - Supplier Name"
    },
    {
      "row": 2,
      "account": {"id": "<debt_account_id>"},
      "amount": "<negative_gross>",
      "amountCurrency": "<negative_gross>",
      "currency": {"id": 1},
      "description": "Leverandorgjeld - Supplier Name"
    }
  ]
}
```

Then STOP. Do NOT verify.

## IMPORTANT
- **Row 1 (expense + VAT):** ALL FOUR amount fields required: `amount` (net), `amountCurrency` (net), `amountGross` (gross), `amountGrossCurrency` (gross). Missing any → 422.
- **Row 2 (supplier liability 2400):** Only `amount` and `amountCurrency` (both = -gross). Do NOT add vatType, amountGross, or amountGrossCurrency on row 2.
- **System auto-creates row 0** for the VAT account posting. Do NOT manually create a VAT posting row. The manual postings do NOT need to balance — the system VAT row closes the balance.
- **amountCurrency MUST equal amount** — omitting amountCurrency silently results in 0.0.
- **amountGrossCurrency MUST equal amountGross** — mismatch causes 422.
- Row numbers start at 1 (row 0 is system-reserved).
- vatType IDs vary per sandbox — always look up dynamically by `percentage` field, never hardcode.
- Target: 4-5 calls (4 if supplier exists). 0 errors.
