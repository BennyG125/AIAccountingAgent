# Year-End / Ledger Corrections
1. Identify the accounts involved (GET /ledger/account?number=XXXX)
2. POST /ledger/voucher with balanced postings
3. For reversals: PUT /ledger/voucher/{id}/:reverse
4. Use GET /balanceSheet?dateFrom=X&dateTo=X to verify account balances
