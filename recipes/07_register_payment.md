# Register Payment (Tier 2)
Full flow: create customer → products → order → invoice → payment.
1. Follow Invoice recipe above → capture invoice_id and total amount
2. GET /invoice/paymentType → find appropriate payment type ID
3. PUT /invoice/{invoice_id}/:payment?paymentDate={today}&paymentTypeId=N&paidAmount=TOTAL&paidAmountCurrency=1
CRITICAL: Payment uses QUERY PARAMS on PUT, NOT a request body.
