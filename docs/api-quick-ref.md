# Tripletex API Quick Reference

Auth: Basic `("0", session_token)`. All paths relative to `base_url` (includes `/v2`).

## Response Format

- Single: `{"value": {...}}`
- List: `{"fullResultSize": N, "values": [...]}`
- Error: `{"status": 4xx, "message": "..."}`
- Object refs: always `{"id": <int>}`, never bare ints

## Known Constants

| Entity | ID |
|--------|-----|
| VAT 25% | vatType id=3 |
| VAT 15% | vatType id=5 |
| VAT 0% | vatType id=6 |
| NOK | currency id=1 |
| Norway | country id=162 |

## Endpoints — Required Fields

### POST /department
`name` (str), `departmentNumber` (str — NOT int)

### POST /employee
`firstName`, `lastName`, `userType` ("STANDARD"|"EXTENDED"|"NO_ACCESS"), `department` ({id})
Optional: email, dateOfBirth, phoneNumberMobile, address, employeeCategory

### POST /customer
`name` (str)
Optional: email, phoneNumber, organizationNumber, physicalAddress, invoiceEmail

### POST /contact
`firstName`, `lastName`, `customer` ({id})
Optional: email, phoneNumberMobile

### POST /product
`name` (str)
Optional: priceExcludingVatCurrency, vatType ({id}), productUnit ({id})

### POST /order
`customer` ({id}), `deliveryDate`, `orderDate`
Optional: orderLines (embed here to save calls)

### OrderLine (embedded in order)
`product` ({id}), `count`, `unitPriceExcludingVatCurrency`, `vatType` ({id})

### POST /invoice
`invoiceDate`, `invoiceDueDate`, `orders` ([{id}])
Requires: order must have orderLines, company must have bank account on ledger 1920

### PUT /invoice/{id}/:payment
**QUERY PARAMS only** (not body): `paymentDate`, `paymentTypeId`, `paidAmount`, `paidAmountCurrency`

### POST /project
`name`, `projectManager` ({id}), `startDate`
Optional: customer, department, endDate, description

### POST /project/participant
`project` ({id}), `employee` ({id})

### POST /travelExpense
`employee` ({id}), `title` (str)
Optional: project, department

### POST /travelExpense/cost
`travelExpense` ({id}), `date`, `costCategory` ({id}), `paymentType` ({id}), `amountCurrencyIncVat`

### POST /travelExpense/mileageAllowance
`travelExpense` ({id}), `rateCategory` ({id}), `date`, `km`, `departureLocation`, `destination`

### POST /travelExpense/perDiemCompensation
`travelExpense` ({id}), `rateCategory` ({id}), `rateType` ({id}), `countryCode`, `count`

### POST /travelExpense/accommodationAllowance
`travelExpense` ({id}), `rateCategory` ({id}), `count`, `location`

### POST /ledger/voucher
`date`, `description`, `postings` ([{account: {id}, amount, row}])
Rows start at 1. Postings must balance (sum = 0). Look up account IDs with GET /ledger/account?number=XXXX.

## Common Flows

**Employee:** department → employee
**Invoice:** customer → product → order (with orderLines) → invoice → payment
**Travel:** employee → travelExpense → cost/mileage/perDiem/accommodation
**Project:** employee → project → participant
**Voucher:** lookup accounts → voucher with balanced postings
