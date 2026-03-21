# Create Order (Tier 2)
1. POST /customer {name, organizationNumber} → capture customer_id
2. For each product: POST /product {name, priceExcludingVatCurrency} → capture product_ids
3. POST /order {customer: {id}, orderDate: "{today}", deliveryDate: "{today}",
   orderLines: [{product: {id}, count, unitPriceExcludingVatCurrency}]}
