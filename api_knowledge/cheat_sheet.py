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
          percentageOfFullTimeEquivalent, annualSalary, hourlyWage,
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
Grant entitlements to an employee. Uses QUERY PARAMS only (no body).
Required query params:
  employeeId (int) — the employee ID
  template (string) — one of these enum values:
    "ALL_PRIVILEGES", "NONE_PRIVILEGES", "INVOICING_MANAGER",
    "PERSONELL_MANAGER", "ACCOUNTANT", "AUDITOR", "DEPARTMENT_LEADER"
Example: PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=123&template=ALL_PRIVILEGES
Returns 200 with empty body on success.
IMPORTANT: Use ALL_PRIVILEGES for project managers — they need AUTH_PROJECT_MANAGER entitlement.

### PUT /employee/entitlement/:grantClientEntitlementsByTemplate
Grant entitlements in a client account. Uses QUERY PARAMS only (no body).
Required query params:
  employeeId (int), customerId (int), template (string)
  Valid templates: "ALL_PRIVILEGES", "NONE_PRIVILEGES",
    "STANDARD_PRIVILEGES_ACCOUNTANT", "STANDARD_PRIVILEGES_AUDITOR"
Optional: addToExisting (boolean, default false)

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
Register payment. Use QUERY PARAMETERS (not JSON body):
?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1
Do NOT put these fields in the request body — they MUST be query parameters.

### PUT /invoice/{id}/:send
Send invoice. Query params (NOT body): sendType ("EMAIL"|"EHF"|"EFAKTURA"|"AVTALEGIRO"|"VIPPS"),
              overrideEmailAddress (string, optional)

### PUT /invoice/{id}/:createCreditNote
Create credit note for an invoice. REQUIRED query param: ?date=YYYY-MM-DD
Optional query params: comment, creditNoteEmail, sendToCustomer, sendType
No body required (send empty {} or omit). The credit note reverses the original invoice.
NOTE: The invoice must NOT already be a credit note (isCreditNote=true).

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
REQUIRED params:
  invoiceDateFrom (YYYY-MM-DD) — from and including (MANDATORY, not optional!)
  invoiceDateTo (YYYY-MM-DD) — to and excluding (MANDATORY, not optional!)
Optional params:
  id (string) — list of IDs
  invoiceNumber (string), kid (string), voucherId (string), supplierId (string)
  fields, from, count, sorting
IMPORTANT: Both invoiceDateFrom and invoiceDateTo are REQUIRED. Without them you get 422.
Use a wide range like invoiceDateFrom=2020-01-01&invoiceDateTo=2030-01-01 when searching broadly.
Response: SupplierInvoice objects with fields: id, invoiceNumber, invoiceDate, invoiceDueDate,
  supplier ({id, name}), voucher ({id}), amount, amountCurrency, amountExcludingVat,
  amountExcludingVatCurrency, currency, isCreditNote, orderLines, payments,
  kidOrReceiverReference, outstandingAmount

### GET /supplierInvoice/{id}
Get supplier invoice by ID. Params: fields

### PUT /supplierInvoice/voucher/{id}/postings
Put debit postings on a supplier invoice. [BETA]
Path param: id (int) — the VOUCHER id (not the supplier invoice id)
Query params:
  sendToLedger (boolean, default false) — requires special setup by Tripletex
  voucherDate (YYYY-MM-DD, optional) — if set, updates date on voucher and invoice
Body: array of OrderLinePosting objects. Each has:
  posting ({account: {id}, amount, amountCurrency, currency: {id}, vatType: {id},
            department: {id}, project: {id}, product: {id}, description, row})
  orderLine (optional, {id} — reference to existing order line)
Returns: SupplierInvoice object.
Use this to set/change the debit-side account postings on a supplier invoice voucher.

### POST /supplierInvoice/{invoiceId}/:addPayment
Register payment on supplier invoice. Uses QUERY PARAMS (not JSON body):
Required: paymentType (int) — set to 0 to auto-find last payment type for this vendor
Optional: amount (number), kidOrReceiverReference (string), bban (string),
          paymentDate (YYYY-MM-DD),
          useDefaultPaymentType (boolean, default false) — auto-select payment type,
          partialPayment (boolean, default false) — set true to allow multiple payments

### PUT /supplierInvoice/{invoiceId}/:approve
Approve a supplier invoice. Query param: comment (string, optional)

### PUT /supplierInvoice/{invoiceId}/:reject
Reject a supplier invoice. Query param: comment (string, REQUIRED)

### PUT /supplierInvoice/{invoiceId}/:changeDimension
Change a dimension on debit postings of a supplier invoice. Uses QUERY PARAMS:
Required:
  debitPostingIds (string) — comma-separated list of posting IDs to change
  dimension (string) — one of: "PROJECT", "DEPARTMENT", "EMPLOYEE", "PRODUCT",
    "FREE_DIMENSION_1", "FREE_DIMENSION_2", "FREE_DIMENSION_3"
  dimensionId (int) — the ID of the new dimension value

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
Optional voucher-level fields:
  voucherType ({id}) — reference to a VoucherType. Look up with GET /ledger/voucherType.
    Must NOT be 'Utgående faktura' (Outgoing Invoice) on new vouchers; use null or Invoice endpoint.
  externalVoucherNumber (string) — external reference, max 70 characters.
  vendorInvoiceNumber (string) — the supplier's own invoice number.
  supplierVoucherType (string, READ-ONLY) — set by the system, one of:
    "TYPE_SUPPLIER_INVOICE_SIMPLE", "TYPE_SUPPLIER_INVOICE_DETAILED"
Query param: sendToLedger (boolean, default true) — set false to create without posting to ledger.

Each Posting needs: account ({id}), amount (number), row (integer, MUST be >= 1)
  Row 0 is reserved for system-generated postings and will be rejected.
  Number rows sequentially starting from 1.
Optional posting fields: amountCurrency, amountGross, amountGrossCurrency,
          currency ({id}), description, invoiceNumber (string), termOfPayment (string),
          customer ({id}), supplier ({id}), employee ({id}),
          project ({id}), department ({id}), product ({id}),
          vatType ({id}), date (YYYY-MM-DD),
          freeAccountingDimension1 ({id}), freeAccountingDimension2 ({id}),
          freeAccountingDimension3 ({id}),
          amortizationAccount ({id}), amortizationStartDate, amortizationEndDate,
          quantityAmount1 (number), quantityType1 ({id}),
          quantityAmount2 (number), quantityType2 ({id})
IMPORTANT: Postings must balance (sum of amounts = 0). Only gross amounts needed.
IMPORTANT: Look up real account IDs with GET /ledger/account?number=XXXX — do NOT guess IDs.

### PUT /ledger/voucher/{id}
Update a voucher. Send full Voucher object with version field.
Query param: sendToLedger (boolean, default true).
Note: Postings with row==0 will be deleted and regenerated by the system.

### GET /ledger/voucher
Search: ?dateFrom=X&dateTo=X&number=X&fields=...
IMPORTANT: dateFrom and dateTo are REQUIRED. dateTo must be strictly AFTER dateFrom (same date → 422).
Use a wide range like dateFrom=2026-01-01&dateTo=2026-12-31 when searching.

### GET /ledger/voucher/{id}
Get voucher by ID.

### DELETE /ledger/voucher/{id}
Delete voucher.

### PUT /ledger/voucher/{id}/:reverse
Reverse a voucher.

### PUT /ledger/voucher/{id}/:sendToLedger
Send a non-posted voucher to ledger. Query params:
  version (int) — version of the voucher
  number (int, default 0) — voucher number to use, 0 = auto-assign

### PUT /ledger/voucher/{id}/:sendToInbox
Send a voucher back to inbox (e.g. after rejection). Query params:
  version (int), comment (string, optional)

### GET /ledger/voucher/>nonPosted
Find non-posted vouchers. Params:
  dateFrom, dateTo, includeNonApproved (boolean, REQUIRED, default false)

### GET /ledger/voucher/>externalVoucherNumber
Find vouchers by external voucher number.
  Params: externalVoucherNumber (string), fields

### POST /ledger/voucher/{voucherId}/attachment
Upload attachment to voucher (multipart form data).

### POST /ledger/voucher/importDocument
Upload a document (PDF, PNG, JPEG, TIFF) to create voucher(s). Multipart form.
  Query param: split (boolean, default false) — split multi-page into one voucher per page.
  Form fields: file (binary, required), description (string, optional).

---

## LEDGER / VOUCHER TYPE

### GET /ledger/voucherType
Search voucher types. Params: name (string, containing match), fields
Returns: list of VoucherType objects with id, name, displayName.
Use this to look up the correct voucherType ID before creating vouchers.

### GET /ledger/voucherType/{id}
Get single voucher type by ID.

---

## LEDGER / VOUCHER — OPENING BALANCE

### GET /ledger/voucher/openingBalance
Get the opening balance voucher. [BETA]
Params: fields

### POST /ledger/voucher/openingBalance
Create an opening balance on a given date. [BETA]
All movements before this date will be zeroed out in a correction voucher.
The date must be the first day of a month (first day of year recommended).
If postings don't balance, the difference is auto-posted to a help account.
Body (OpeningBalance):
  voucherDate (YYYY-MM-DD),
  balancePostings (array): each has account ({id}), amount, amountCurrency,
    project ({id}), department ({id}), product ({id}), employee ({id})
  customerPostings (array): each has customer ({id}), amount, description
  supplierPostings (array): each has supplier ({id}), amount, description
  employeePostings (array): each has employee ({id}), amount, description

### DELETE /ledger/voucher/openingBalance
Delete the opening balance.

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

## LEDGER / ACCOUNTING DIMENSION (Custom/Free Dimensions)

### POST /ledger/accountingDimensionName
Create a custom accounting dimension. Returns the created dimension with its dimensionIndex.
Body: {"dimensionName": "Prosjekttype"}
Response includes: id, dimensionName, dimensionIndex (auto-assigned, e.g. 1, 2, 3)

### GET /ledger/accountingDimensionName
List existing custom dimension names.
Params: fields, count
Response field: dimensionName (NOT "name")

### POST /ledger/accountingDimensionValue
Create a value under a custom dimension.
Body: {"displayName": "Forskning", "dimensionIndex": 1, "active": true, "showInVoucherRegistration": true}

### GET /ledger/accountingDimensionValue
List existing custom dimension values.
Params: dimensionIndex, fields, count
Response field: displayName (NOT "name")

### Using custom dimensions in vouchers
When posting a voucher with a custom dimension, add the dimension as a field on each
posting row: "freeAccountingDimension{N}": {"id": <dimension_value_id>}
where N is the dimensionIndex from the dimensionName (e.g. freeAccountingDimension1).

IMPORTANT: Do NOT use /dimension, /customDimension, /freeDimension, or any other path.
Only /ledger/accountingDimensionName and /ledger/accountingDimensionValue exist.

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
PUT /invoice/{id}/:payment — uses QUERY PARAMS, NOT body:
?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1

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

---

## ACTIVITY

### POST /activity
Create an activity (for timesheets/projects).
Fields: name (string), number (string), description,
  activityType ("GENERAL_ACTIVITY"|"PROJECT_GENERAL_ACTIVITY"|"PROJECT_SPECIFIC_ACTIVITY"|"TASK"),
  isChargeable (boolean), rate (number)
Note: PROJECT_SPECIFIC_ACTIVITY must be created via project/projectActivity.

### GET /activity
Search: ?name=X&number=X&isProjectActivity=true&isGeneral=true&isChargeable=true&isTask=false&fields=...

### GET /activity/>forTimeSheet
Find activities valid for timesheet on a date.
Params: projectId, employeeId, date (YYYY-MM-DD), fields

---

## TIMESHEET ENTRY

### POST /timesheet/entry
Create a timesheet entry. One entry per employee/date/activity/project combo.
Fields: activity ({id}), employee ({id}), project ({id}),
  date (YYYY-MM-DD), hours (number), comment (string)

### PUT /timesheet/entry/{id}
Update entry. Fields set to 0 or absent will be nulled.

### GET /timesheet/entry
Search: ?employeeId=X&projectId=X&activityId=X&dateFrom=X&dateTo=X&fields=...

### DELETE /timesheet/entry/{id}
Delete entry. Query param: version (required).

### GET /timesheet/entry/>totalHours
Get total hours for employee in period. Params: employeeId, startDate, endDate

### Common Pattern — Create Timesheet Entry
1. GET /activity or GET /activity/>forTimeSheet → capture activity_id
2. POST /timesheet/entry {activity: {id: activity_id}, employee: {id}, project: {id}, date: "YYYY-MM-DD", hours: 7.5}

---

## BANK RECONCILIATION

### POST /bank/reconciliation
Create a bank reconciliation.
Fields: account ({id}), accountingPeriod ({id}),
  type ("MANUAL"|"AUTOMATIC"), bankAccountClosingBalanceCurrency (number)

### GET /bank/reconciliation
Search: ?accountId=X&accountingPeriodId=X&fields=...

### GET /bank/reconciliation/>last
Get last created reconciliation. Params: accountId

### PUT /bank/reconciliation/{id}
Update reconciliation (e.g. close it with isClosed: true).

### DELETE /bank/reconciliation/{id}
Delete reconciliation.

### POST /bank/reconciliation/match
Create a match between bank transactions and postings.
Fields: bankReconciliation ({id}), type ("MANUAL"|"APPROVED_SUGGESTION"|"ADJUSTMENT"),
  transactions (array of {id}), postings (array of {id})

### GET /bank/reconciliation/match
Search: ?bankReconciliationId=X&approved=true&fields=...

### DELETE /bank/reconciliation/match/{id}
Delete a match.

---

## BALANCE SHEET

### GET /balanceSheet
Get balance sheet (saldobalanse). Returns rows with account balances.
Required params: dateFrom (YYYY-MM-DD), dateTo (YYYY-MM-DD)
Optional: accountNumberFrom, accountNumberTo, customerId, employeeId,
  departmentId, projectId, includeSubProjects (boolean),
  includeActiveAccountsWithoutMovements (boolean)
Response: {rows: [...], sumBalanceIn, sumBalanceChange, sumBalanceOut}

---

## ASSET

### POST /asset
Create a fixed asset.
Fields: name (string), description, dateOfAcquisition (YYYY-MM-DD),
  acquisitionCost (number), account ({id}), lifetime (integer, months),
  depreciationAccount ({id}), depreciationMethod ("STRAIGHT_LINE"|"TAX_RELATED"|"MANUAL"|"CUSTOMIZED_AMOUNT"|"NO_DEPRECIATION"),
  depreciationFrom (YYYY-MM-DD), department ({id}), project ({id})

### PUT /asset/{id}
Update asset.

### GET /asset
Search: ?name=X&description=X&fields=...

### DELETE /asset/{id}
Delete asset. Check /asset/canDelete/{id} first.

---

## INCOMING INVOICE

### POST /incomingInvoice
Create a supplier invoice. [BETA]
Body (IncomingInvoiceAggregateExternalWrite):
  invoiceHeader: {vendorId (int), invoiceDate (YYYY-MM-DD), dueDate (YYYY-MM-DD),
    currencyId (int), invoiceAmount (number, incl VAT), description,
    invoiceNumber (string), voucherTypeId (int), purchaseOrderId (int)}
  orderLines: array (optional)
  version: integer
Query param: sendTo (optional)

### GET /incomingInvoice/search
Search: ?vendorId=X&invoiceDateFrom=X&invoiceDateTo=X&invoiceNumber=X&status=X&fields=...

### GET /incomingInvoice/{voucherId}
Get invoice by voucher ID.

### POST /incomingInvoice/{voucherId}/addPayment
Register payment on incoming invoice.
Body: paymentDate (YYYY-MM-DD), amountCurrency (number),
  creditorIbanOrBban (string), kidOrReceiverReference (string),
  useDefaultPaymentType (boolean), partialPayment (boolean)

---

## PURCHASE ORDER

### POST /purchaseOrder
Create purchase order. Requires Logistics Basic module.
Fields: supplier ({id}), deliveryDate (YYYY-MM-DD),
  project ({id}), department ({id}), ourContact ({id}),
  receiverEmail, comments, currency ({id}), isClosed (boolean)

### GET /purchaseOrder
Search: ?supplierId=X&number=X&deliveryDateFrom=X&deliveryDateTo=X&isClosed=false&fields=...

### PUT /purchaseOrder/{id}
Update purchase order.

### DELETE /purchaseOrder/{id}
Delete purchase order.

### POST /purchaseOrder/orderline
Create purchase order line.
Fields: purchaseOrder ({id}), product ({id}), description,
  count (number), unitCostCurrency (number), discount (number %)

### PUT /purchaseOrder/{id}/:send
Send PO. Query param: sendType ("EMAIL"|"FTP")

---

## DIVISION

### GET /company/divisions
List existing divisions. USE THIS to find division IDs.
Params: ?fields=id or ?fields=*
Returns: {values: [{id, name, ...}]}
NOTE: Divisions already exist in the sandbox. ALWAYS use this endpoint
to find an existing division instead of trying to create one.

### GET /division
Search: ?query=X&fields=...

### POST /division
Create a division — WARNING: Almost always fails with 422 in sandbox environments
because it requires organizationNumber and municipality. Use GET /company/divisions instead.
Fields: name (string), startDate (YYYY-MM-DD), endDate,
  organizationNumber (string), municipality ({id})

### PUT /division/{id}
Update division.

---

## PROJECT HOURLY RATES

### POST /project/hourlyRates
Create project hourly rate.
Fields: project ({id}), startDate (YYYY-MM-DD),
  hourlyRateModel ("TYPE_PREDEFINED_HOURLY_RATES"|"TYPE_PROJECT_SPECIFIC_HOURLY_RATES"|"TYPE_FIXED_HOURLY_RATE"),
  fixedRate (number — when model is TYPE_FIXED_HOURLY_RATE),
  projectSpecificRates (array — when model is TYPE_PROJECT_SPECIFIC_HOURLY_RATES),
  showInProjectOrder (boolean)

### GET /project/hourlyRates
Search: ?projectId=X&type=X&startDateFrom=X&startDateTo=X&fields=...

### POST /project/hourlyRates/projectSpecificRates
Create specific rate for employee/activity combo.
Fields: projectHourlyRate ({id}), employee ({id}), activity ({id}),
  hourlyRate (number)

---

## PROJECT ORDER LINE

### POST /project/orderline
Create project order line. [BETA]
Fields: project ({id}), product ({id}), description (string),
  count (number), unitPriceExcludingVatCurrency (number),
  unitCostCurrency (number), vatType ({id}), discount (number %),
  date (YYYY-MM-DD), isChargeable (boolean), markup (number %)

### GET /project/orderline
Search: ?projectId=X&isBudget=false&fields=...

### PUT /project/orderline/{id}
Update order line.

### DELETE /project/orderline/{id}
Delete order line.

---

## PROJECT SETTINGS (via PUT /project/{id})

To configure fixed-price or price-ceiling projects, use PUT /project/{id}:
  isFixedPrice: true → makes it a fixed-price project
  fixedprice: (number) → the fixed price amount
  isPriceCeiling: true → enables price ceiling on hourly-rate projects
  priceCeilingAmount: (number) → ceiling amount
Include version field. These are regular project fields, not a separate endpoint.

---

## INVENTORY

### POST /inventory
Create an inventory (warehouse).
Fields: name (string), number (string), isMainInventory (boolean),
  isInactive (boolean), description, email, phone, address ({...})

### GET /inventory
Search: ?name=X&isMainInventory=true&isInactive=false&fields=...

### PUT /inventory/{id}
Update inventory.

### DELETE /inventory/{id}
Delete inventory.

### POST /inventory/location
Create inventory location within a warehouse. Requires Logistics Basic.
Fields: inventory ({id}), name (string), isInactive (boolean)

### GET /inventory/location
Search: ?warehouseId=X&name=X&isInactive=false&fields=...

### Common Pattern — Set Up Inventory
1. POST /inventory {name: "Main Warehouse", isMainInventory: true} → capture inventory_id
2. POST /inventory/location {inventory: {id: inventory_id}, name: "Shelf A"}
3. PUT /product/{id} {isStockItem: true} to enable stock tracking on a product
"""
