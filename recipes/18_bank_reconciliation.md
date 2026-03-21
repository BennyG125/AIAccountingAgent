# Bank Reconciliation from CSV
1. Parse the CSV data from the prompt/attachment
2. GET /ledger/account?number=1920 (or the bank account specified) → account_id
3. GET /bank/reconciliation/>last?accountId=ID → check for existing reconciliation
4. POST /bank/reconciliation {account: {id}, type: "MANUAL", bankAccountClosingBalanceCurrency: BALANCE}
5. For each transaction: create matching postings or reconciliation matches
6. Use POST /bank/reconciliation/match to link transactions to postings
