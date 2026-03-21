# Credit Note (Tier 2)
1. Follow Invoice recipe (#6) → capture invoice_id
2. PUT /invoice/{invoice_id}/:createCreditNote
No body required. The credit note reverses the original invoice.
