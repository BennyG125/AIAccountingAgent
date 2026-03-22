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

## Step 2: Look Up Accounts + VAT Type + Voucher Type (4 parallel calls)
Issue ALL four simultaneously:
- `GET /ledger/account?number=<expense_account>&fields=id,number,name` → `expense_account_id`
- `GET /ledger/account?number=2400&fields=id,number,name` → `debt_account_id`
- `GET /ledger/vatType?fields=id,number,name,percentage` → find `vat_type_id` where `percentage == 25` (for 25% VAT)
- `GET /ledger/voucherType?fields=id,name` → find the entry with name containing "Leverandør" (e.g. "Leverandørfaktura") → `voucher_type_id`

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
  "voucherType": {"id": "<voucher_type_id>"},
  "vendorInvoiceNumber": "<invoice_number_from_prompt>",
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
      "supplier": {"id": "<supplier_id>"},
      "amount": "<negative_gross>",
      "amountCurrency": "<negative_gross>",
      "amountGross": "<negative_gross>",
      "amountGrossCurrency": "<negative_gross>",
      "currency": {"id": 1},
      "description": "Leverandorgjeld - Supplier Name"
    }
  ]
}
```

Then STOP. Do NOT verify.

## Error Recovery: VAT-Locked Account ("låst til mva-kode 0")
If POST /ledger/voucher fails with 422 mentioning "låst til mva-kode 0" (account is locked to VAT code 0),
the expense account does NOT allow vatType. Switch to a **3-row manual posting** without vatType on the expense row:

```json
{
  "date": "YYYY-MM-DD",
  "description": "Leverandorfaktura INV-XXX - Supplier Name",
  "voucherType": {"id": "<voucher_type_id>"},
  "vendorInvoiceNumber": "<invoice_number_from_prompt>",
  "postings": [
    {
      "row": 1,
      "account": {"id": "<expense_account_id>"},
      "amount": "<net>",
      "amountCurrency": "<net>",
      "amountGross": "<net>",
      "amountGrossCurrency": "<net>",
      "currency": {"id": 1},
      "supplier": {"id": "<supplier_id>"},
      "description": "INV-XXX - Supplier Name"
    },
    {
      "row": 2,
      "account": {"id": "<vat_account_id>"},
      "amount": "<vat_amount>",
      "amountCurrency": "<vat_amount>",
      "amountGross": "<vat_amount>",
      "amountGrossCurrency": "<vat_amount>",
      "currency": {"id": 1},
      "description": "Inngående mva"
    },
    {
      "row": 3,
      "account": {"id": "<debt_account_id>"},
      "supplier": {"id": "<supplier_id>"},
      "amount": "<negative_gross>",
      "amountCurrency": "<negative_gross>",
      "amountGross": "<negative_gross>",
      "amountGrossCurrency": "<negative_gross>",
      "currency": {"id": 1},
      "description": "Leverandorgjeld - Supplier Name"
    }
  ]
}
```

**Key differences from standard posting:**
- **Row 1 (expense):** NO vatType. amountGross = amountGrossCurrency = **net** (NOT gross, since no VAT on this row).
- **Row 2 (VAT account 2710 or 2711):** Look up with `GET /ledger/account?number=2710`. amount = amountGross = VAT amount (gross - net). NO vatType.
- **Row 3 (supplier liability 2400):** Same as before, negative gross amount.
- All three rows must balance: net + vat_amount + (-gross) = 0.

## IMPORTANT
- **voucherType is REQUIRED**: ALWAYS include `"voucherType": {"id": <voucher_type_id>}` on the voucher. Look up from GET /ledger/voucherType — use the one with name containing "Leverandør". Without this, the voucher scores 0.
- **vendorInvoiceNumber is REQUIRED**: ALWAYS include `"vendorInvoiceNumber": "<invoice_number>"` on the voucher. This is the invoice reference number from the prompt (e.g. "INV-2025-042", "Faktura 1234"). Without this, the voucher scores 0.
- **Row 1 (expense + VAT):** ALL FOUR amount fields required: `amount` (net), `amountCurrency` (net), `amountGross` (gross), `amountGrossCurrency` (gross). Missing any → 422.
- **Row 2 (supplier liability 2400):** ALL FOUR amount fields required: `amount` (-gross), `amountCurrency` (-gross), `amountGross` (-gross), `amountGrossCurrency` (-gross). Do NOT add vatType on row 2. Include `"supplier": {"id": "<supplier_id>"}` on this row.
- **System auto-creates row 0** for the VAT account posting. Do NOT manually create a VAT posting row. The manual postings do NOT need to balance — the system VAT row closes the balance.
- **amountCurrency MUST equal amount** — omitting amountCurrency silently results in 0.0.
- **amountGrossCurrency MUST equal amountGross** — mismatch causes 422.
- Row numbers start at 1 (row 0 is system-reserved).
- vatType IDs vary per sandbox — always look up dynamically by `percentage` field, never hardcode.
- Target: 5-6 calls (5 if supplier exists). 0 errors.
