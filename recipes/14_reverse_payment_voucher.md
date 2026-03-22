# Reverse Payment Voucher (Tier 2)
Full flow: create invoice → register payment → find voucher → reverse it.
1. Follow Register Payment recipe (#7) → capture invoice_id
2. GET /invoice/{invoice_id}?fields=* → find the voucher ID from the payment
3. PUT /ledger/voucher/{voucher_id}/:reverse?date={today} — date is a REQUIRED query param
If the task specifies which voucher to reverse, use GET /ledger/voucher?dateFrom=X&dateTo=X to find it.
IMPORTANT: GET /ledger/voucher REQUIRES dateFrom and dateTo params (422 without them).
IMPORTANT: dateTo must be AFTER dateFrom (not the same day). Use dateFrom=2026-01-01&dateTo=2026-12-31 for a safe range.
IMPORTANT: PUT /:reverse REQUIRES ?date=YYYY-MM-DD (422 "Kan ikke være null" without it).
