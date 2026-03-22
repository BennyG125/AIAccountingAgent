# Project Lifecycle (Tier 3)

STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## Task Pattern
Full project lifecycle: create customer, employees, project with budget, register hours, register supplier cost, invoice customer, and close the project. Prompts appear in NO, EN, ES, PT, DE, FR. Typical: "Execute the full lifecycle for project X (Customer Y): 1) Budget: Z NOK. 2) Register hours for employees. 3) Register supplier cost. 4) Invoice customer."

## Step 1: Create the customer
**API call:** `POST /customer`
**Payload:**
```json
{"name": "<customer_name>", "organizationNumber": "<org_number>"}
```
**Capture:** `customer_id`
**On error 422 "Kundenummeret er i bruk":** `GET /customer?organizationNumber=<org_number>` to find existing ID.

## Step 2: Get or create department
**API call:** `GET /department?fields=id,name`
**Capture:** `dept_id` (use first result)
**If empty:** `POST /department {"name": "Avdeling", "departmentNumber": "100"}` and capture `dept_id`.

## Step 3: Create project manager employee
**API call:** `POST /employee`
**Payload:**
```json
{
  "firstName": "<pm_first>",
  "lastName": "<pm_last>",
  "email": "<pm_email or pm_first.pm_last@example.org>",
  "userType": "STANDARD",
  "department": {"id": <dept_id>}
}
```
**Capture:** `pm_id`
**On error 422 "e-postadressen er i bruk":** `GET /employee?email=<email>` to find existing ID.

## Step 4: Grant ALL_PRIVILEGES to project manager
**API call:** `PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=<pm_id>&template=ALL_PRIVILEGES`
**QUERY PARAMS ONLY — NO request body. Returns 200 with empty body.**
**MANDATORY:** This MUST happen BEFORE Step 6 (project creation) or you get 422 "Prosjektleder mangler rettigheter".

## Step 5: Create other employees (consultants, etc.)
For EACH additional employee in the prompt:
**API call:** `POST /employee`
**Payload:**
```json
{
  "firstName": "<first>",
  "lastName": "<last>",
  "email": "<email or first.last@example.org>",
  "userType": "STANDARD",
  "department": {"id": <dept_id>}
}
```
**Capture:** `employee_N_id`
**On error 422 "e-postadressen er i bruk":** `GET /employee?email=<email>` to find existing ID.

## Step 6: Create project with budget
**API call:** `POST /project`
**Payload:**
```json
{
  "name": "<project_name>",
  "projectManager": {"id": <pm_id>},
  "customer": {"id": <customer_id>},
  "startDate": "{today}",
  "isFixedPrice": true,
  "fixedprice": <budget_amount>
}
```
**Capture:** `project_id`
**NOTE:** If budget is described as a ceiling (not fixed price), use `"isPriceCeiling": true, "priceCeilingAmount": <amount>` instead of `isFixedPrice`/`fixedprice`.

## Step 7: Find or create a timesheet activity
**API call:** `GET /activity?name=Consulting&isGeneral=true&fields=id,name`
**Capture:** `activity_id`
**If empty:** `POST /activity {"name": "Consulting", "activityType": "PROJECT_GENERAL_ACTIVITY"}` and capture `activity_id`.
**On error 422 "Navnet er i bruk":** `GET /activity?name=Consulting` to find existing ID.

## Step 8: Register hours for each employee
For EACH employee with hours to register:
**API call:** `POST /timesheet/entry`
**Payload:**
```json
{
  "activity": {"id": <activity_id>},
  "employee": {"id": <employee_id>},
  "project": {"id": <project_id>},
  "date": "{today}",
  "hours": <hours>
}
```
**NOTE:** `hours` is a decimal number. If a single entry with large hours (e.g. 135) is rejected for exceeding daily limit, split across multiple consecutive dates (e.g. 18 entries of 7.5h each). Try the full amount first — many sandboxes accept it.

## Step 9: Create supplier
**API call:** `POST /supplier`
**Payload:**
```json
{"name": "<supplier_name>", "organizationNumber": "<supplier_org_number>"}
```
**Capture:** `supplier_id`
**On error 422:** `GET /supplier?organizationNumber=<org_number>` to find existing ID.

## Step 10: Look up account IDs and VAT type (3 parallel GETs)
**API calls (run all 3 in parallel):**
```
GET /ledger/account?number=7000&fields=id,number,name   → expense_account_id
GET /ledger/account?number=2400&fields=id,number,name   → supplier_debt_account_id
GET /ledger/vatType?fields=id,number,percentage          → vat_type_id (incoming 25% VAT, usually id=1)
```

## Step 11: Post supplier cost as ledger voucher
**API call:** `POST /ledger/voucher`
**Payload:**
```json
{
  "date": "{today}",
  "description": "Leverandørkostnad - <supplier_name>",
  "postings": [
    {
      "account": {"id": <expense_account_id>},
      "amount": <net_amount>,
      "amountCurrency": <net_amount>,
      "amountGross": <gross_amount>,
      "amountGrossCurrency": <gross_amount>,
      "currency": {"id": 1},
      "vatType": {"id": <vat_type_id>},
      "supplier": {"id": <supplier_id>},
      "project": {"id": <project_id>},
      "description": "Leverandørkostnad <project_name>",
      "row": 1
    },
    {
      "account": {"id": <supplier_debt_account_id>},
      "amount": <negative_gross_amount>,
      "amountCurrency": <negative_gross_amount>,
      "currency": {"id": 1},
      "description": "Leverandørgjeld <supplier_name>",
      "row": 2
    }
  ]
}
```

**Amount calculations:**
- `gross_amount` = the supplier cost from the prompt (e.g., 70700)
- `net_amount` = gross_amount / 1.25 (e.g., 70700 / 1.25 = 56560)
- Row 1: amount = net_amount (positive), amountGross = gross_amount (positive)
- Row 2: amount = -gross_amount (negative), NO vatType, NO amountGross

**CRITICAL rules:**
- Row 2 MUST NOT have vatType or amountGross fields
- System auto-creates row 0 for VAT account 2710 — do NOT create it
- Rows start at 1 (row 0 is system-reserved)
- ALWAYS set both amount AND amountCurrency (same value)
- ALWAYS set both amountGross AND amountGrossCurrency on row 1

## Step 12: Create order and invoice for the project
**API call:** `POST /invoice` (creates order inline — 1 call instead of 2)
**Payload:**
```json
{
  "invoiceDate": "{today}",
  "invoiceDueDate": "<today + 30 days>",
  "orders": [{
    "customer": {"id": <customer_id>},
    "orderDate": "{today}",
    "deliveryDate": "{today}",
    "orderLines": [
      {
        "description": "Prosjektleveranse <project_name>",
        "count": 1,
        "unitPriceExcludingVatCurrency": <budget_amount>
      }
    ]
  }]
}
```
**Capture:** `invoice_id`
**CRITICAL:** Do NOT link the order to the project (no `"project": {"id": ...}` on the order). Tripletex treats project-linked orders as "underordre" that must be closed before the project can close, and there is no order-close endpoint. This will cause Step 14 (close project) to fail.
**NOTE:** Use the budget/fixed price amount as the order line price. No product needed — use description-only orderLine.

## Step 13: Get project version for closing
**API call:** `GET /project/<project_id>?fields=id,version`
**Capture:** `version`

## Step 14: Close the project
**API call:** `PUT /project/<project_id>`
**Payload:**
```json
{
  "id": <project_id>,
  "version": <version>,
  "isClosed": true
}
```

## IMPORTANT
- Grant entitlements (Step 4) MUST happen BEFORE project creation (Step 6) — this is the #1 cause of errors.
- The supplier cost voucher uses NET on the expense row and GROSS on the debt row — the system adds the VAT row automatically.
- If an employee email is not provided in the prompt, generate it as `firstname.lastname@example.org` (lowercased).
- Do NOT verify with GET calls after successful creates — wastes calls.
- If any step fails mid-sequence, do NOT re-create entities that succeeded — use their IDs from prior responses.
- Target: 14-17 calls, 0 errors.
