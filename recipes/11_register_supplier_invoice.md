# Register Supplier Invoice (Tier 2)
**Do NOT use /incomingInvoice (403 in sandbox). Use /ledger/voucher instead.**
1. POST /supplier {name, organizationNumber} → capture supplier_id
2. Look up account IDs (3 parallel GETs):
   - GET /ledger/account?number=7000 (or the expense account from the prompt) → expense_account_id
   - GET /ledger/account?number=2400 → supplier_debt_account_id
   - GET /ledger/vatType?fields=id,number,name,percentage → find incoming VAT type
     (Usually id=1: "Fradrag inngående avgift, høy sats" for 25% incoming VAT)
3. POST /ledger/voucher — use BOTH amount and amountCurrency (they must match for NOK),
   and BOTH amountGross and amountGrossCurrency on the expense row:
   {
     date: "YYYY-MM-DD",
     description: "Leverandørfaktura INV-XXX - Supplier Name",
     postings: [
       {account: {id: expense_account_id},
        amount: NET_AMOUNT, amountCurrency: NET_AMOUNT,
        amountGross: GROSS_AMOUNT, amountGrossCurrency: GROSS_AMOUNT,
        currency: {id: 1}, vatType: {id: vat_type_id},
        supplier: {id: supplier_id}, description: "...", row: 1},
       {account: {id: supplier_debt_account_id},
        amount: -GROSS_AMOUNT, amountCurrency: -GROSS_AMOUNT,
        currency: {id: 1}, description: "...", row: 2}
     ]
   }
   The system auto-creates a row 0 posting for the VAT account (2710).
   Amounts: GROSS = total incl VAT, NET = GROSS / 1.25 (for 25% VAT).
   **CRITICAL**: amountGross MUST equal amountGrossCurrency — omitting either causes 422.
