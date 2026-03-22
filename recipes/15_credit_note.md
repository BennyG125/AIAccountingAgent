# Credit Note (Tier 2)
STOP. Follow these steps IN ORDER.

## Step 1: Find the original invoice
**API call:** `GET /invoice?customerName=<customer>&fields=id,invoiceNumber,amount,amountCurrency`
Find the invoice matching the description in the prompt.

## Step 2: Create the credit note
**API call:** `PUT /invoice/{invoice_id}/:createCreditNote?date=<today_YYYY-MM-DD>`
**The `date` query parameter is REQUIRED.** Without it you get 422.
No body required. The credit note reverses the original invoice.
Optional params: `comment`, `sendType` (EMAIL, EHF, MANUAL).

## IMPORTANT
- The `date` parameter MUST be provided as a query parameter, e.g. `?date=2026-03-22`
- If you need to send the credit note: `PUT /invoice/{credit_note_id}/:send?sendType=EMAIL`
- Do NOT create a new invoice — use `:createCreditNote` on the existing one
