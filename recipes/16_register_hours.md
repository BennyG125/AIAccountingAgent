# Register Hours / Timesheet (Tier 2)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## Task Pattern
Register timesheet hours for an employee on a project activity. May optionally include generating an invoice.
Extract from prompt: hours, employee name/email, activity name, project name, customer name/org number, hourly rate.

## Step 1: Find or Create Customer
**API call:** `GET /customer?organizationNumber=<org_number>&fields=id,name`
- If `fullResultSize > 0` → capture `customer_id = values[0].id`
- If empty → `POST /customer {name: "<customerName>", organizationNumber: "<org_number>"}` → capture `id`

## Step 2: Find Department
**API call:** `GET /department?fields=id,name`
Capture `dept_id = values[0].id`. If empty → `POST /department {name: "Avdeling", departmentNumber: "1"}` → capture `id`.

## Step 3: Find or Create Employee
**API call:** `GET /employee?email=<email>&fields=id,firstName,lastName`
- If found → capture `employee_id = values[0].id`. Skip to Step 5.
- If empty → `POST /employee {firstName, lastName, email, userType: "STANDARD", department: {id: <dept_id>}}` → capture `employee_id`

**On error 422 "e-postadressen er i bruk":** `GET /employee?email=X` → use existing ID. Skip Step 4.

## Step 4: Grant Entitlements (only if employee was just created)
**API call:** `PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=<employee_id>&template=ALL_PRIVILEGES`
Query params ONLY, NO body. Skip this step if employee already existed.

## Step 5: Find or Create Project
**API call:** `GET /project?name=<projectName>&fields=id,name`
- If found → capture `project_id = values[0].id`. Skip POST.
- If empty → `POST /project {name: "<projectName>", projectManager: {id: <employee_id>}, startDate: "{today}", customer: {id: <customer_id>}}` → capture `project_id`

## Step 6: Find or Create Activity
**API call:** `GET /activity?name=<activityName>&fields=id,name`
- If found → capture `activity_id = values[0].id`. Skip POST.
- If empty → `POST /activity {name: "<activityName>", activityType: "GENERAL_ACTIVITY", isChargeable: true}` → capture `activity_id`

**CRITICAL:** activityType MUST be `"GENERAL_ACTIVITY"`. NOT `"PROJECT_GENERAL_ACTIVITY"`. Using the wrong type causes 422 "Validering feilet."

## Step 7: Set Hourly Rate on Project
**API call:** `GET /project/hourlyRates?projectId=<project_id>&fields=id,hourlyRateModel,fixedRate`
- If `fullResultSize > 0` → hourly rate already set. **Skip POST** (prevents 409 "Duplicate entry").
- If empty →
```json
POST /project/hourlyRates {
  "project": {"id": "<project_id>"},
  "startDate": "{today}",
  "hourlyRateModel": "TYPE_FIXED_HOURLY_RATE",
  "fixedRate": "<hourlyRate>"
}
```

## Step 8: Register Timesheet Entry
**API call:** `POST /timesheet/entry`
**Payload:**
```json
{
  "activity": {"id": "<activity_id>"},
  "employee": {"id": "<employee_id>"},
  "project": {"id": "<project_id>"},
  "date": "{today}",
  "hours": "<hours>"
}
```
`hours` is a decimal number (e.g. 7.5 for 7h30m).

## Step 9: Generate Invoice (ONLY if prompt asks for it)
Skip this step unless the prompt says "generate invoice" / "create invoice" / "Rechnung erstellen" / "gerar fatura" / "generar factura" / "generer faktura".

**Step 9a:** `POST /order`
```json
{
  "customer": {"id": "<customer_id>"},
  "orderDate": "{today}",
  "deliveryDate": "{today}",
  "orderLines": [{
    "description": "<activityName> - <projectName>",
    "count": "<hours>",
    "unitPriceExcludingVatCurrency": "<hourlyRate>"
  }]
}
```
Capture `order_id`.

**Step 9b:** `POST /invoice`
```json
{
  "invoiceDate": "{today}",
  "invoiceDueDate": "<today + 30 days>",
  "orders": [{"id": "<order_id>"}]
}
```

Then STOP. Do NOT verify.

## IMPORTANT
- activityType MUST be `"GENERAL_ACTIVITY"` — the most common error is using `"PROJECT_GENERAL_ACTIVITY"` which causes 422.
- Always check GET before POST for: customer, employee, project, activity, hourlyRates. This avoids duplicates and 409 errors.
- Grant entitlements ONLY for newly created employees — skip for existing ones.
- `hours` is decimal — 7.5 means 7 hours 30 minutes.
- Target: 7 calls (no invoice, all entities exist) / 9 calls (with invoice, fresh entities). 0 errors.
