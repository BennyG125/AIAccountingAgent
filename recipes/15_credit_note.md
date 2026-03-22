# Credit Note (Tier 2)
Full flow: create invoice → SEND invoice → create credit note.

1. Follow Invoice recipe (#6) → capture invoice_id
2. SEND the invoice first (REQUIRED — credit notes only work on sent/paid invoices):
   PUT /invoice/{invoice_id}/:send?sendType=EMAIL
   - Customer must have email set (see recipe #6 step 5 for details)
3. PUT /invoice/{invoice_id}/:createCreditNote — QUERY PARAMS (not body):
   ?date={today}&comment=Credit%20note
   - date is optional (defaults to today)
   - comment is optional

IMPORTANT: If the invoice is NOT yet sent, step 3 will fail with 422.
The correct sequence is ALWAYS: create invoice → send invoice → create credit note.
If the task says "create a credit note for invoice X" and invoice X exists but hasn't been sent,
you must send it first before creating the credit note.
