# Year-End / Ledger Corrections (Tier 3)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

This task asks you to find and correct exactly 4 accounting errors in the Jan+Feb ledger. The 4 error types are ALWAYS:
1. **Wrong account** — amount posted to account X instead of correct account Y
2. **Duplicate voucher** — a voucher was entered twice
3. **Missing VAT line** — net amount posted without VAT counterpart on account 2710
4. **Incorrect amount** — voucher posted with wrong amount

All corrections are NEW vouchers with opposite/corrective amounts. Do NOT use PUT /:reverse (it fails with 422 for closed periods).

## Extract from Prompt FIRST
Before any API call, parse the prompt for all 4 errors:

| Error type | What to extract | French keywords |
|---|---|---|
| Wrong account | wrong_account, correct_account, amount | "mauvais compte", "utilisé au lieu de" |
| Duplicate | duplicate_account, duplicate_amount | "pièce en double" |
| Missing VAT | net_account, net_amount (HT = ex-VAT) | "ligne de TVA manquante", "montant HT" |
| Incorrect amount | account, posted_amount, correct_amount | "montant incorrect", "comptabilisé au lieu de" |

Calculate now:
- VAT amount = net_amount * 0.25
- Gross amount = net_amount * 1.25
- Amount difference = posted_amount - correct_amount

## Step 1: Look up ALL account IDs (3-6 GET calls)
**API call:** `GET /ledger/account?number=XXXX&fields=id,number,name` for each unique account number
Deduplicate — if the same account appears in multiple errors, look it up ONCE.
Capture `values[0].id` from each response.

Typical accounts to look up:
```
GET /ledger/account?number=<wrong_account>     → wrong_account_id
GET /ledger/account?number=<correct_account>   → correct_account_id
GET /ledger/account?number=<duplicate_account> → dup_account_id
GET /ledger/account?number=<net_account>       → net_account_id
GET /ledger/account?number=2710                → vat_account_id
GET /ledger/account?number=<incorrect_account> → incorrect_account_id
```
**On error (empty values[]):** Create the account: `POST /ledger/account {"number": XXXX, "name": "Account name"}`.

## Step 2: Look up VAT type (1 GET call)
**API call:** `GET /ledger/vatType?fields=id,number,percentage`
Find the entry with percentage=25 (standard Norwegian MVA). Capture its `id` as `vat_type_id`.
NEVER hardcode the vatType ID — it varies per sandbox.

## Step 3: Get ledger postings to find voucher structure (1 GET call)
**API call:** `GET /ledger/posting?dateFrom=2026-01-01&dateTo=2026-02-28&fields=id,account,amount,description,voucher`
**CRITICAL:** Both `dateFrom` AND `dateTo` are REQUIRED. Omitting either causes 422.

From the response, identify:
- The duplicate posting (two identical amounts on the same account)
- The wrong-account posting (amount on wrong_account)
- The incorrect-amount posting (the wrong amount on the account)

You need the account IDs from Step 1 — you do NOT need voucher IDs for the correction approach below.

## Step 4: Post ALL 4 correction vouchers (4 POST calls)
Use date = last day of the period being corrected (e.g. 2026-02-28).

### Correction 1: Wrong account
**API call:** `POST /ledger/voucher`
```json
{
  "date": "2026-02-28",
  "description": "Korreksjon: feil konto - <wrong_account> til <correct_account>",
  "postings": [
    {
      "account": {"id": <wrong_account_id>},
      "amount": <negative_amount>,
      "amountCurrency": <negative_amount>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Reversering feilpostering"
    },
    {
      "account": {"id": <correct_account_id>},
      "amount": <positive_amount>,
      "amountCurrency": <positive_amount>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Korrekt konto"
    }
  ]
}
```

### Correction 2: Duplicate voucher
**API call:** `POST /ledger/voucher`
```json
{
  "date": "2026-02-28",
  "description": "Korreksjon: dobbeltpostering reversert - konto <dup_account>",
  "postings": [
    {
      "account": {"id": <dup_account_id>},
      "amount": <negative_dup_amount>,
      "amountCurrency": <negative_dup_amount>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Reversering dobbeltpostering"
    },
    {
      "account": {"id": <dup_counterpart_id>},
      "amount": <positive_dup_amount>,
      "amountCurrency": <positive_dup_amount>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Motkonto dobbeltpostering"
    }
  ]
}
```
Note: Find the counterpart account from the ledger postings in Step 3 (the other row in the same voucher). If unclear, use the same account for both rows (net-zero on that account).

### Correction 3: Missing VAT line
VAT amount = net_amount * 0.25. This is a simple 2-row voucher adding the missing VAT posting.

**API call:** `POST /ledger/voucher`
```json
{
  "date": "2026-02-28",
  "description": "Korreksjon: manglende mva-linje - konto <net_account>",
  "postings": [
    {
      "account": {"id": <net_account_id>},
      "amount": <vat_amount>,
      "amountCurrency": <vat_amount>,
      "amountGross": <gross_amount>,
      "amountGrossCurrency": <gross_amount>,
      "currency": {"id": 1},
      "vatType": {"id": <vat_type_id>},
      "row": 1,
      "description": "MVA-korreksjon"
    },
    {
      "account": {"id": <vat_account_id>},
      "amount": <negative_vat_amount>,
      "amountCurrency": <negative_vat_amount>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Manglende MVA-linje"
    }
  ]
}
```
**If this 422s due to vatType:** Remove vatType, amountGross, and amountGrossCurrency from row 1. Post a simple 2-row voucher: debit net_account for vat_amount, credit 2710 for negative vat_amount. No vatType needed.

### Correction 4: Incorrect amount
Difference = posted_amount - correct_amount (the over-posted portion to reverse).

**API call:** `POST /ledger/voucher`
```json
{
  "date": "2026-02-28",
  "description": "Korreksjon: feil beløp konto <account> (<posted_amount> -> <correct_amount>)",
  "postings": [
    {
      "account": {"id": <incorrect_account_id>},
      "amount": <negative_difference>,
      "amountCurrency": <negative_difference>,
      "currency": {"id": 1},
      "row": 1,
      "description": "Reversering feil beløp"
    },
    {
      "account": {"id": <counterpart_account_id>},
      "amount": <positive_difference>,
      "amountCurrency": <positive_difference>,
      "currency": {"id": 1},
      "row": 2,
      "description": "Motkonto korreksjon"
    }
  ]
}
```
Find the counterpart account from the ledger postings in Step 3. If the original posting debited account X, the counterpart is the credit account in the same voucher.

## STOP — You are done. Do NOT make any more API calls.

## IMPORTANT
- Do NOT use PUT /ledger/voucher/{id}/:reverse — it ALWAYS fails with 422 for Jan/Feb (closed period). Always post new correction vouchers instead.
- Do NOT call GET /balanceSheet to verify — wastes an API call.
- Do NOT explore alternative approaches — this sequence is proven optimal.
- GET /ledger/posting REQUIRES both dateFrom AND dateTo — omitting either causes 422.
- All amounts in NOK: always set BOTH `amount` and `amountCurrency` to the same value.
- Rows start at 1. Row 0 is reserved by the system.
- Each voucher's postings MUST sum to exactly 0.
- When using vatType on a row, you MUST also set amountGross and amountGrossCurrency (both = gross amount). The system auto-generates a row 0 for VAT — do NOT manually duplicate it.
- The prompt is typically in French but may be in any language. Error types are always the same 4.
- Target: 9-12 API calls total (5-6 GETs + 1 vatType GET + 1 posting GET + 4 POSTs). Do NOT exceed 15 calls.
