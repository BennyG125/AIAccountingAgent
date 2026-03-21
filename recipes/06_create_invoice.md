# Create Invoice — Multi-Product (Tier 2, HIGHEST PRIORITY — 16% of competition)
1. POST /customer {name, organizationNumber} → capture customer_id
2. For EACH product: POST /product {name, priceExcludingVatCurrency} → capture product_id
   - Do NOT include `number` field — let Tripletex auto-assign to avoid "number in use" errors.
   - Do NOT include `vatType` — let Tripletex assign default. Avoids "Ugyldig mva-kode" errors.
   - If product already exists ("Produktnummeret X er i bruk"), GET /product?number=X to find it.
3. POST /order {customer: {id: customer_id}, orderDate: "{today}", deliveryDate: "{today}",
   orderLines: [
     {product: {id: p1_id}, count: 1, unitPriceExcludingVatCurrency: price1},
     {product: {id: p2_id}, count: 1, unitPriceExcludingVatCurrency: price2},
     ...
   ]} → capture order_id
4. POST /invoice {invoiceDate: "{today}", invoiceDueDate: "30 days later",
   orders: [{id: order_id}]} → capture invoice_id
5. If prompt says "send": PUT /invoice/{invoice_id}/:send — Body: {"sendType": "EMAIL"}
NOTE: orderLines do NOT need vatType — it's optional and Tripletex uses the product's default.
