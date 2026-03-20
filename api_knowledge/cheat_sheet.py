# api_knowledge/cheat_sheet.py

TRIPLETEX_API_CHEAT_SHEET = """
## Tripletex v2 API — Endpoint Reference

### Authentication
- Basic Auth: username = "0", password = session_token
- All requests go through the provided base_url (which already includes /v2)

### Important: Fresh Account
The Tripletex account starts EMPTY on each competition submission. If the task says
to modify or delete something, first search for it. If it doesn't exist, create it.

### Response Format
- Single entity: {"value": {<entity>}}
- List: {"fullResultSize": N, "values": [{...}, ...]}
- POST returns the created entity with its assigned ID inside "value"
- Errors return {"status": 4xx, "message": "..."}

### Query Parameters (all GET list endpoints)
- fields: comma-separated field names, use * for all (e.g. ?fields=id,name,email or ?fields=*)
- from: pagination offset (default 0)
- count: results per page (default 1000)
- sorting: field name, prefix with - for descending (e.g. ?sorting=-id)

### Object References
When a field expects a reference to another entity (e.g. department, customer, project),
send it as an object with just the id: {"id": <int>}
Example: "department": {"id": 42}

### Date Format
All dates are strings in YYYY-MM-DD format.

---

## EMPLOYEE

### POST /employee
Create an employee.
Required body fields: firstName (string), lastName (string),
  userType ("STANDARD"|"EXTENDED"|"NO_ACCESS") — MUST be set, cannot be empty,
  department ({id}) — MUST reference an existing department
Optional: email, phoneNumberMobile, phoneNumberWork, phoneNumberHome,
          dateOfBirth (YYYY-MM-DD), nationalIdentityNumber, employeeNumber,
          bankAccountNumber, address ({addressLine1, city, postalCode, country: {id}}),
          employeeCategory ({id}),
          isContact (boolean), comments,
          employments (array — see POST /employee/employment)
IMPORTANT: If the task does not specify a department, search for existing departments
with GET /department and use the first one found.
Note: There is NO "isAdministrator" field. Admin access is controlled via entitlements.

### PUT /employee/{id}
Update employee. Send full object with version field included.

### GET /employee
Search: ?firstName=X&lastName=X&email=X&employeeNumber=X&department=X&fields=...
Returns list of employees.

### GET /employee/{id}
Get single employee by ID.

### POST /employee/list
Create multiple employees at once.

---

## EMPLOYEE EMPLOYMENT

### POST /employee/employment
Create employment for an employee.
Required: employee ({id}), startDate (YYYY-MM-DD)
Optional: endDate, division ({id}), employmentId,
          taxDeductionCode ("loennFraHovedarbeidsgiver"|"loennFraBiarbeidsgiver"|...),
          isMainEmployer (boolean, default true),
          employmentDetails (array — see POST /employee/employment/details)

### POST /employee/employment/details
Create employment details (salary, job title, etc.).
Required: employment ({id}), date (YYYY-MM-DD)
Optional: employmentType, maritimeEmploymentType, salaryType, scheduleType,
          percentOfFullTimeEquivalent, annualSalary, hourlyWage,
          occupationCode ({id})

### GET /employee/employment
Find employments. Params: employeeId, fields

### PUT /employee/employment/{id}
Update employment.

---

## EMPLOYEE ENTITLEMENTS

### GET /employee/entitlement
Find entitlements for a user. Params: employeeId, fields
Use this to check what permissions/roles an employee has.

### PUT /employee/entitlement/:grantEntitlementsByTemplate
Update employee entitlements (grant roles/permissions).

---

## CUSTOMER

### POST /customer
Create a customer.
Required: name (string)
Optional: email, phoneNumber, phoneNumberMobile, organizationNumber,
          customerNumber (int), invoiceEmail, website, description,
          isPrivateIndividual (boolean), isCustomer (boolean, read-only/auto true),
          isSupplier (boolean), language ("NO"|"EN"),
          physicalAddress ({addressLine1, city, postalCode, country: {id}}),
          postalAddress ({addressLine1, city, postalCode, country: {id}}),
          deliveryAddress ({addressLine1, city, postalCode, name}),
          accountManager ({id}), department ({id}), currency ({id}),
          invoiceSendMethod ("EMAIL"|"EHF"|"EFAKTURA"|"AVTALEGIRO"|"VIPPS"|"PAPER"|"MANUAL"),
          invoicesDueIn (int), invoicesDueInType ("DAYS"|"MONTHS"|"RECURRING_DAY_OF_MONTH"),
          category1 ({id}), category2 ({id}), category3 ({id})

### PUT /customer/{id}
Update customer. Include version field.

### GET /customer
Search: ?name=X&email=X&customerNumber=X&organizationNumber=X&isCustomer=true&fields=...

### GET /customer/{id}
Get single customer.

### DELETE /customer/{id}
Delete customer. [BETA]

### POST /customer/list
Create multiple customers. [BETA]

---

## CUSTOMER CATEGORY

### POST /customer/category
Create customer/supplier category.
Fields: name, number, description, type (int)

### GET /customer/category
Search categories.

---

## CONTACT

### POST /contact
Create a contact person (linked to a customer).
Fields: firstName, lastName, email, phoneNumberMobile, phoneNumberWork,
        customer ({id}), department ({id}), isInactive (boolean)

### PUT /contact/{id}
Update contact.

### GET /contact
Search: ?firstName=X&lastName=X&email=X&customerId=X&fields=...

### POST /contact/list
Create multiple contacts.

---

## PRODUCT

### POST /product
Create a product.
Required: name (string)
Optional: number (string), description, orderLineDescription,
          priceExcludingVatCurrency (number), priceIncludingVatCurrency (number),
          costExcludingVatCurrency (number),
          isInactive (boolean), isStockItem (boolean),
          vatType ({id}), productUnit ({id}), account ({id}),
          department ({id}), supplier ({id}), currency ({id}),
          weight (number), weightUnit ("kg"|"g"|"hg"),
          volume (number), volumeUnit ("cm3"|"dm3"|"m3"),
          ean (string), hsnCode (string)

### PUT /product/{id}
Update product. Include version.

### GET /product
Search: ?name=X&number=X&isInactive=false&fields=...

### DELETE /product/{id}
Delete product.

### POST /product/list
Create multiple products.

---

## PRODUCT UNIT

### GET /product/unit
Search product units. Params: name, nameShort, commonCode, fields
Returns units like "pieces", "kg", "hours", etc.

### POST /product/unit
Create product unit. Fields: name, nameShort, commonCode

---

## ORDER

### POST /order
Create an order (prerequisite for invoices).
Required: customer ({id}), deliveryDate (YYYY-MM-DD), orderDate (YYYY-MM-DD)
Optional: orderLines (array of OrderLine objects),
          receiverEmail, reference, invoiceComment, deliveryComment,
          ourContactEmployee ({id}), contact ({id}), department ({id}),
          project ({id}), currency ({id}), deliveryAddress ({id}),
          invoicesDueIn (int), invoicesDueInType ("DAYS"|"MONTHS"|"RECURRING_DAY_OF_MONTH"),
          isClosed (boolean), number (string)

### PUT /order/{id}
Update order.

### GET /order
Search: ?customerName=X&number=X&fields=...

### GET /order/{id}
Get single order.

### DELETE /order/{id}
Delete order.

---

## ORDER LINE

### POST /order/orderline
Create a single order line.
Fields: order ({id}), product ({id}), description (string),
        count (number), unitPriceExcludingVatCurrency (number),
        unitPriceIncludingVatCurrency (number),
        vatType ({id}), discount (number, percentage)

### POST /order/orderline/list
Create multiple order lines at once.

### PUT /order/orderline/{id}
Update order line. [BETA]

### DELETE /order/orderline/{id}
Delete order line. [BETA]

---

## INVOICE

### POST /invoice
Create an invoice from order(s).
Required: invoiceDate (YYYY-MM-DD), invoiceDueDate (YYYY-MM-DD),
          orders (array of {id: int})
Optional: invoiceNumber (int, 0 = auto-generate), comment (string),
          customer ({id}), currency ({id}), kid (string),
          paidAmount (number), paymentTypeId (int),
          voucher ({id})
Note: Order must have orderLines. Include orderLines when creating the order,
or create them separately with POST /order/orderline before invoicing.
Note: The company must have a bank account registered before invoices can be created.
If invoice creation fails with bank account error, this is a company setup issue.

### GET /invoice
Search: ?invoiceDateFrom=X&invoiceDateTo=X&customerId=X&fields=...

### GET /invoice/{id}
Get single invoice.

### PUT /invoice/{id}/:payment
Register payment on an invoice.
Body: paymentDate (YYYY-MM-DD), paymentTypeId (int), paidAmount (number),
      paidAmountCurrency (number)

### PUT /invoice/{id}/:send
Send invoice. Body: sendType ("EMAIL"|"EHF"|"EFAKTURA"|"AVTALEGIRO"|"VIPPS"),
              overrideEmailAddress (string, optional)

### PUT /invoice/{id}/:createCreditNote
Create credit note for an invoice.

### PUT /invoice/{id}/:createReminder
Create and send invoice reminder.

### GET /invoice/paymentType
Get available payment types.

---

## SUPPLIER

### POST /supplier
Create a supplier.
Required: name (string)
Optional: email, phoneNumber, phoneNumberMobile, organizationNumber,
          supplierNumber (int), invoiceEmail, website, description,
          isPrivateIndividual (boolean), language ("NO"|"EN"),
          physicalAddress, postalAddress, deliveryAddress,
          accountManager ({id}), currency ({id}),
          category1 ({id}), category2 ({id}), category3 ({id})

### PUT /supplier/{id}
Update supplier. Include version.

### GET /supplier
Search: ?name=X&organizationNumber=X&supplierNumber=X&fields=...

### DELETE /supplier/{id}
Delete supplier.

---

## SUPPLIER INVOICE

### GET /supplierInvoice
Search supplier invoices.

### GET /supplierInvoice/{id}
Get supplier invoice.

### POST /supplierInvoice/{invoiceId}/:addPayment
Register payment on supplier invoice.
Body: paymentType (int), amount (number), paymentDate (YYYY-MM-DD),
      basisPercentage (number)

### PUT /supplierInvoice/{invoiceId}/:approve
Approve a supplier invoice.

### PUT /supplierInvoice/{invoiceId}/:reject
Reject a supplier invoice.

---

## PROJECT

### POST /project
Create a project.
Required: name (string), projectManager ({id}), startDate (YYYY-MM-DD)
Optional: number (string, auto if null), description, reference,
          endDate (YYYY-MM-DD),
          customer ({id}), department ({id}), currency ({id}),
          projectCategory ({id}), mainProject ({id}),
          contact ({id}), deliveryAddress ({...}),
          isInternal (boolean), isClosed (boolean),
          isFixedPrice (boolean), fixedprice (number),
          isPriceCeiling (boolean), priceCeilingAmount (number),
          isOffer (boolean), isReadyForInvoicing (boolean),
          accessType ("NONE"|"READ"|"WRITE"),
          invoiceComment, invoiceDueDate (int),
          invoiceDueDateType ("DAYS"|"MONTHS"|"RECURRING_DAY_OF_MONTH"),
          participants (array of ProjectParticipant),
          projectActivities (array of ProjectActivity),
          projectHourlyRates (array of ProjectHourlyRate)

### PUT /project/{id}
Update project. [BETA] Include version.

### GET /project
Search: ?name=X&number=X&projectManagerId=X&customerId=X&isClosed=false&fields=...

### GET /project/{id}
Get single project.

### DELETE /project/{id}
Delete project. [BETA]

---

## PROJECT PARTICIPANTS

### POST /project/participant
Add participant to a project. [BETA]
Fields: project ({id}), employee ({id}), adminAccess (boolean)

### POST /project/participant/list
Add multiple participants. [BETA]

---

## DEPARTMENT

### POST /department
Create a department.
Required: name (string), departmentNumber (string)
Optional: departmentManager ({id}), isInactive (boolean)

### PUT /department/{id}
Update department. Include version.

### GET /department
Search: ?name=X&departmentNumber=X&fields=...

### DELETE /department/{id}
Delete department.

---

## TRAVEL EXPENSE

### POST /travelExpense
Create a travel expense report.
Required: employee ({id}), title (string)
Optional: project ({id}), department ({id}),
          travelAdvance (number), isChargeable (boolean),
          travelDetails ({...}),
          costs (array of Cost — can be embedded in POST body),
          perDiemCompensations (array — can be embedded in POST body)
Note: mileageAllowances and accommodationAllowances are READ-ONLY on this object.
      You MUST create them separately via their own POST endpoints (see below).

### GET /travelExpense
Search: ?employeeId=X&departmentId=X&projectId=X&fields=...

### GET /travelExpense/{id}
Get single travel expense.

### DELETE /travelExpense/{id}
Delete travel expense.

### PUT /travelExpense/:approve
Approve travel expenses. Body: list of travel expense IDs.

### PUT /travelExpense/:deliver
Deliver travel expenses.

### PUT /travelExpense/:unapprove
Unapprove travel expenses.

---

## TRAVEL EXPENSE — COSTS

### POST /travelExpense/cost
Create a cost entry on a travel expense.
Fields: travelExpense ({id}), date (YYYY-MM-DD),
        costCategory ({id}), paymentType ({id}),
        currency ({id}), amountCurrencyIncVat (number),
        rate (number), vatType ({id}),
        comments (string), isChargeable (boolean),
        participants (array of {employeeName, isEmployee})

### GET /travelExpense/cost
Search costs. Params: travelExpenseId, fields

### GET /travelExpense/costCategory
Get available cost categories.

### GET /travelExpense/paymentType
Get available payment types for travel expenses.

---

## TRAVEL EXPENSE — PER DIEM

### POST /travelExpense/perDiemCompensation
Create per diem compensation.
Fields: travelExpense ({id}), rateCategory ({id}), rateType ({id}),
        countryCode (string), location (string), address (string),
        count (int), amount (number), rate (number),
        overnightAccommodation ("NONE"|"HOTEL"|"BOARDING_HOUSE_WITHOUT_COOKING"|"BOARDING_HOUSE_WITH_COOKING"),
        isDeductionForBreakfast (boolean),
        isDeductionForLunch (boolean),
        isDeductionForDinner (boolean)

### GET /travelExpense/perDiemCompensation
Search. Params: travelExpenseId, fields

### GET /travelExpense/rateCategory
Get rate categories for per diem / mileage.

### GET /travelExpense/rate
Get rates.

---

## TRAVEL EXPENSE — MILEAGE

### POST /travelExpense/mileageAllowance
Create mileage allowance.
Fields: travelExpense ({id}), rateCategory ({id}), rateType ({id}),
        date (YYYY-MM-DD), departureLocation (string), destination (string),
        km (number), rate (number), amount (number),
        isCompanyCar (boolean), vehicleType (int),
        passengers (array), tollCost ({...})

### GET /travelExpense/mileageAllowance
Search. Params: travelExpenseId, fields

---

## TRAVEL EXPENSE — ACCOMMODATION

### POST /travelExpense/accommodationAllowance
Create accommodation allowance.
Fields: travelExpense ({id}), rateCategory ({id}), rateType ({id}),
        location (string), address (string), zone (string),
        count (int), rate (number), amount (number)

### GET /travelExpense/accommodationAllowance
Search. Params: travelExpenseId, fields

---

## LEDGER / VOUCHER

### POST /ledger/voucher
Create a voucher (journal entry).
Required: date (YYYY-MM-DD), description (string),
          postings (array of Posting objects)
Each Posting needs: account ({id}), amount (number), row (integer, MUST be >= 1)
  Row 0 is reserved for system-generated postings and will be rejected.
  Number rows sequentially starting from 1.
Optional posting fields: amountCurrency, currency ({id}), description,
          customer ({id}), supplier ({id}), employee ({id}),
          project ({id}), department ({id}), product ({id}),
          vatType ({id}), date (YYYY-MM-DD)
IMPORTANT: Postings must balance (sum of amounts = 0). Only gross amounts needed.
IMPORTANT: Look up real account IDs with GET /ledger/account?number=XXXX — do NOT guess IDs.

### GET /ledger/voucher
Search: ?dateFrom=X&dateTo=X&number=X&fields=...

### GET /ledger/voucher/{id}
Get voucher by ID.

### DELETE /ledger/voucher/{id}
Delete voucher.

### PUT /ledger/voucher/{id}/:reverse
Reverse a voucher.

### POST /ledger/voucher/{voucherId}/attachment
Upload attachment to voucher (multipart form data).

---

## LEDGER / ACCOUNT

### GET /ledger/account
Search chart of accounts.
Params: number (string), name, from, count, fields

### POST /ledger/account
Create account. Fields: number (int), name (string)

### PUT /ledger/account/{id}
Update account.

---

## LEDGER / POSTING

### GET /ledger/posting
Search postings.
Params: dateFrom, dateTo, accountNumberFrom, accountNumberTo, fields

---

## LEDGER / VAT TYPE

### GET /ledger/vatType
Search VAT types. Returns VAT codes with rates.
Params: number, name, fields
Common types: id 3 = 25% MVA, id 5 = 15% MVA, id 6 = 0% MVA (check actual IDs via GET)

---

## COMPANY

### GET /company/{id}
Get company info (name, org number, address, etc.).

### PUT /company
Update company information.

### GET /company/salesmodules
Get active sales modules. [BETA]

### POST /company/salesmodules
Activate a new sales module. [BETA]

---

## SALARY

### GET /salary/type
Get salary types. Params: number, name, fields

### POST /salary/transaction
Create salary transaction.
Fields: date (YYYY-MM-DD), month (int), year (int),
        payslips (array of Payslip objects),
        isHistorical (boolean), paySlipsAvailableDate (YYYY-MM-DD)

### GET /salary/payslip
Search payslips. Params: employeeId, yearFrom, yearTo, fields

---

## COUNTRY

### GET /country
Search countries.
Params: id, code (string, e.g. "NO", "SE"), fields

---

## CURRENCY

### GET /currency
Search currencies.
Params: code (e.g. "NOK", "EUR", "USD"), fields

---

## MUNICIPALITY

### GET /municipality
Get Norwegian municipalities.

---

## DELIVERY ADDRESS

### GET /deliveryAddress
Search delivery addresses.

### PUT /deliveryAddress/{id}
Update delivery address.

---

## COMMON PATTERNS

### Create Employee
1. GET /department → capture dept_id from values.0.id (need an existing department)
2. POST /employee {firstName, lastName, email, userType: "STANDARD", department: {id: dept_id}}

### Create Customer + Invoice
1. POST /customer {name} → capture customer_id
2. POST /product {name} → capture product_id (if needed)
3. POST /order {customer: {id: customer_id}, orderDate, deliveryDate,
                orderLines: [{product: {id: product_id}, count, unitPriceExcludingVatCurrency}]}
   → capture order_id
4. POST /invoice {invoiceDate, invoiceDueDate, orders: [{id: order_id}]}

### Register Payment on Invoice
PUT /invoice/{id}/:payment {paymentDate, paymentTypeId, paidAmount}

### Create Travel Expense with Costs
1. POST /travelExpense {employee: {id}, title} → capture expense_id
2. POST /travelExpense/cost {travelExpense: {id: expense_id}, date, paymentType: {id},
   amountCurrencyIncVat: amount}

### Create Project with Participants
1. POST /project {name, projectManager: {id}, startDate} → capture project_id
2. POST /project/participant {project: {id: project_id}, employee: {id}}

### Create Department
POST /department {name, departmentNumber}

### Create Voucher (Journal Entry)
1. GET /ledger/account?number=1000 → capture debit_account_id from values.0.id
2. GET /ledger/account?number=3000 → capture credit_account_id from values.0.id
3. POST /ledger/voucher {date, description, postings: [
     {account: {id: debit_account_id}, amount: 1000, row: 1},
     {account: {id: credit_account_id}, amount: -1000, row: 2}
   ]}

### Tips
- Norwegian chars (æ, ø, å) work fine — send as UTF-8
- All IDs are integers
- Always include "version" field when doing PUT updates
- Use GET with ?fields=* first if unsure about an entity's structure
- Object references are always {id: int}, never just the int
- departmentNumber is a STRING, not int
- When creating orders, you can embed orderLines directly in the POST body
- Invoice requires at least one order with at least one order line
- For voucher postings, row must be >= 1 (row 0 is system-reserved)
- Look up account IDs with GET /ledger/account?number=XXXX, never guess them
"""
