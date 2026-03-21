# Create Product (Tier 1)
POST /product with ONLY these fields:
```json
{
  "name": "<from prompt>",
  "priceExcludingVatCurrency": <number>
}
```

**FORBIDDEN FIELDS — including ANY of these causes 422:**
- `vatType` — NEVER include. Returns "Ugyldig mva-kode". Tripletex assigns a default automatically.
- `number` — NEVER include unless the prompt explicitly requires a specific product number. Tripletex auto-assigns. Including it risks "Produktnummeret X er i bruk" errors.

Even if the prompt specifies a VAT rate (25%, 15%, etc.), do NOT include vatType. Just create the product without it. The VAT rate cannot be set via the API.

**Error recovery — product number already in use:**
If the prompt specifies a product number and POST /product returns 422 "Produktnummeret X er i bruk":
1. GET /product?number=X → check if the existing product matches (same name/price)
2. If it matches: use its ID directly — no need to create
3. If it doesn't match: retry POST /product WITHOUT the `number` field. Let Tripletex auto-assign.
