# Create Invoice — Multi-Product (Tier 2, HIGHEST PRIORITY — 16% of competition)
1. POST /customer {name, organizationNumber} → capture customer_id
2. For EACH product: POST /product with ONLY {name, priceExcludingVatCurrency} → capture product_id
   - **NEVER include `vatType`** — causes 422 "Ugyldig mva-kode". Tripletex assigns default automatically.
   - **NEVER include `number`** — causes "Produktnummeret X er i bruk". Let Tripletex auto-assign.
   - If POST fails with "Produktnummeret X er i bruk": GET /product?number=X to find existing product ID.
3. POST /order {customer: {id: customer_id}, orderDate: "{today}", deliveryDate: "{today}",
   orderLines: [
     {product: {id: p1_id}, count: 1, unitPriceExcludingVatCurrency: price1},
     {product: {id: p2_id}, count: 1, unitPriceExcludingVatCurrency: price2},
     ...
   ]} → capture order_id
4. POST /invoice {invoiceDate: "{today}", invoiceDueDate: "30 days later",
   orders: [{id: order_id}]} → capture invoice_id
5. If prompt says "send": PUT /invoice/{invoice_id}/:send?sendType=EMAIL — QUERY PARAM, not body.
   Customer must have email set. If 422, check customer has email/invoiceEmail.
NOTE: orderLines do NOT need vatType — it's optional and Tripletex uses the product's default.
