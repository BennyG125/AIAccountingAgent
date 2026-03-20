# api_knowledge/cheat_sheet.py

TRIPLETEX_API_CHEAT_SHEET = """
## Tripletex v2 API — Quick Reference

### Authentication
- Basic Auth: username = "0", password = session_token
- All requests go through the provided base_url (proxy)

### Response Formats
- POST/PUT single entity: {"value": {"id": <int>, ...}}
- GET list: {"fullResultSize": <int>, "values": [{...}, ...]}
- Use ?fields=id,name,email to select specific fields
- Use ?fields=* to discover all fields on an entity
- Pagination: ?from=0&count=100

### Date Format
- Always YYYY-MM-DD (e.g., "2026-03-19")

### Important: Fresh Account
The account starts EMPTY every submission. If a task requires an invoice, you must first:
1. Create the customer
2. Create the product (if order lines are needed)
3. Create the order (links customer + products)
4. Create the invoice (from the order)

Do NOT assume any entities exist unless the task says to find/modify existing ones.

---

### Endpoints

#### POST /employee
Create an employee.
Required: firstName (string), lastName (string)
Optional: email (string), phoneNumberMobile (string),
          isAdministrator (boolean — set true for admin/"kontoadministrator" role),
          department (object: {"id": <int>}),
          employments (array)
Returns: {"value": {"id": <int>, "firstName": ..., "lastName": ..., ...}}

#### PUT /employee/{id}
Update an employee. Send the full object with changes applied.
Required: id (in URL), firstName, lastName

#### GET /employee
Search employees.
Params: firstName, lastName, email, fields, from, count
Returns: {"fullResultSize": <int>, "values": [...]}

---

#### POST /customer
Create a customer.
Required: name (string)
Optional: email (string), phoneNumber (string),
          isCustomer (boolean, default true), isSupplier (boolean),
          organizationNumber (string), accountManager (object: {"id": <int>})
Returns: {"value": {"id": <int>, "name": ..., ...}}

#### PUT /customer/{id}
Update a customer.
Required: id (in URL), name

#### GET /customer
Search customers.
Params: name, email, isCustomer, fields, from, count

---

#### POST /product
Create a product.
Required: name (string)
Optional: number (string), priceExcludingVat (number), priceIncludingVat (number),
          vatType (object: {"id": <int>}), productUnit (object: {"id": <int>}),
          account (object: {"id": <int>}), department (object: {"id": <int>})
Returns: {"value": {"id": <int>, "name": ..., ...}}

#### GET /product
Search products.
Params: name, number, fields, from, count

---

#### POST /order
Create an order. Required before creating an invoice.
Required: customer (object: {"id": <int>}),
          deliveryDate (string YYYY-MM-DD),
          orderDate (string YYYY-MM-DD)
Optional: orderLines (array of {"product": {"id": <int>}, "count": <number>,
          "unitPriceExcludingVat": <number>}),
          receiver (string)
Returns: {"value": {"id": <int>, ...}}

#### GET /order
Search orders.
Params: customerId, fields, from, count

---

#### POST /invoice
Create an invoice from one or more orders.
Required: invoiceDate (string YYYY-MM-DD),
          invoiceDueDate (string YYYY-MM-DD),
          orders (array of {"id": <int>})
Optional: comment (string)
Returns: {"value": {"id": <int>, "invoiceNumber": <int>, ...}}

#### GET /invoice
Search invoices.
Params: invoiceNumber, customerId, fields, from, count

---

#### POST /travelExpense
Create a travel expense report.
Required: employee (object: {"id": <int>}), title (string)
Optional: date (string YYYY-MM-DD), description (string),
          project (object: {"id": <int>})
Returns: {"value": {"id": <int>, ...}}

#### DELETE /travelExpense/{id}
Delete a travel expense report.

#### GET /travelExpense
Search travel expenses.
Params: employeeId, fields, from, count

---

#### POST /project
Create a project.
Required: name (string), projectManager (object: {"id": <int>})
Optional: customer (object: {"id": <int>}), number (string),
          description (string), startDate (string), endDate (string)
Returns: {"value": {"id": <int>, "name": ..., ...}}

#### GET /project
Search projects.
Params: name, fields, from, count

---

#### POST /department
Create a department.
Required: name (string), departmentNumber (int)
Optional: departmentManager (object: {"id": <int>})
Returns: {"value": {"id": <int>, "name": ..., ...}}

#### GET /department
Search departments.
Params: name, fields, from, count

---

#### GET /ledger/account
Query chart of accounts.
Params: number, from, count, fields

#### POST /ledger/voucher
Create a voucher (for journal entries, corrections).
Required: date (string YYYY-MM-DD), description (string),
          postings (array of {"account": {"id": <int>}, "amount": <number>})

#### DELETE /ledger/voucher/{id}
Delete a voucher.

#### GET /ledger/voucher
Query vouchers.
Params: dateFrom, dateTo, fields, from, count

#### GET /ledger/posting
Query ledger postings.
Params: dateFrom, dateTo, accountId, fields, from, count

---

### Common Patterns

**Create single entity:**
Task: "Create employee Ola Nordmann, ola@example.com, admin"
-> POST /employee {"firstName":"Ola","lastName":"Nordmann","email":"ola@example.com","isAdministrator":true}

**Create entity chain for invoicing:**
1. POST /customer {"name":"Acme AS"} -> get customer id from response
2. POST /product {"name":"Widget","priceExcludingVat":100} -> get product id
3. POST /order {"customer":{"id":<customer_id>},"deliveryDate":"2026-03-19","orderDate":"2026-03-19","orderLines":[{"product":{"id":<product_id>},"count":1,"unitPriceExcludingVat":100}]}
4. POST /invoice {"invoiceDate":"2026-03-19","invoiceDueDate":"2026-04-19","orders":[{"id":<order_id>}]}

**Find then modify:**
1. GET /customer?name=Acme&fields=id,name,email -> get id from values[0]
2. PUT /customer/{id} {"id":<id>,"name":"Acme AS","email":"new@acme.no"}

**Find then delete:**
1. GET /travelExpense?employeeId=1&fields=id -> get id from values[0]
2. DELETE /travelExpense/{id}

### Tips
- Norwegian characters (ae, oe, aa) work fine — send as UTF-8
- All IDs are integers
- "kontoadministrator" = isAdministrator: true on employee
- Invoice REQUIRES at least one order. Order REQUIRES a customer and delivery date.
- When the prompt says "slett" (Norwegian) = delete, "opprett" = create, "endre" = modify
- For "faktura" (invoice), always create the full chain: customer -> product -> order -> invoice
- POST returns the created entity with its ID — use it directly, don't make a GET
"""
