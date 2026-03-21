# Reverse Payment Voucher (Tier 2)
Full flow: create invoice → register payment → find voucher → reverse it.
1. Follow Register Payment recipe (#7) → capture invoice_id
2. GET /invoice/{invoice_id}?fields=* → find the voucher ID from the payment
3. PUT /ledger/voucher/{voucher_id}/:reverse
If the task specifies which voucher to reverse, use GET /ledger/voucher to find it.
