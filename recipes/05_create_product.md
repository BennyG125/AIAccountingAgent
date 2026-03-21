# Create Product (Tier 1)
POST /product {name, priceExcludingVatCurrency}
Do NOT include `number` unless the prompt explicitly requires a specific number — Tripletex auto-assigns.
Do NOT include `vatType` — setting vatType on products is not supported (returns "Ugyldig mva-kode").
Tripletex assigns a default. Even if the prompt asks for a specific VAT rate,
do NOT try to set it — just create the product without vatType and STOP. Do NOT attempt to update
the product's vatType after creation either.
