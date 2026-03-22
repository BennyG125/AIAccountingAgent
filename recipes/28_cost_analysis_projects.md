# Cost Analysis — Create Projects for Top Expense Increases (Tier 3)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## Task Pattern
Compare ledger postings between two months (typically January and February 2026). Identify the 3 expense accounts with the largest absolute increase in total posted amount. For each, create an internal project and an activity.

Extract from prompt: the two comparison periods (usually January 2026 vs February 2026), the number of top accounts (usually 3), and whether to create internal projects with activities.

## Step 1: Get January Expense Postings
**API call:** `GET /ledger/posting?dateFrom=2026-01-01&dateTo=2026-01-31&accountNumberFrom=4000&accountNumberTo=8999&fields=id,account(id,name,number),amount,date`

Group results by `account.number`. Sum `amount` per account → `jan_totals` dictionary.
Example: `{5000: 45000, 6300: 12000, 7000: 8500, ...}`

## Step 2: Get February Expense Postings
**API call:** `GET /ledger/posting?dateFrom=2026-02-01&dateTo=2026-02-28&accountNumberFrom=4000&accountNumberTo=8999&fields=id,account(id,name,number),amount,date`

Group results by `account.number`. Sum `amount` per account → `feb_totals` dictionary.

**In-agent computation (NO API call):**
- For each account in feb_totals: compute `increase = feb_total - jan_total` (use 0 for jan_total if account absent in January)
- Sort accounts by `increase` descending
- Take top 3 accounts
- Record: `account_number`, `account_name` (from `account.name` in posting response), `increase`

**If `account.name` is missing from posting response:** do `GET /ledger/account?number=XXXX&fields=id,name,number` for each top-3 account (3 extra calls).

## Step 3: Get Department + Create Project Manager (2-3 calls)
**API calls (parallel):**
- `GET /department?fields=id,name` → capture `dept_id = values[0].id`
- `POST /employee {firstName: "Project", lastName: "Manager", userType: "STANDARD", department: {id: <dept_id>}}` → capture `pm_id`

Then immediately:
**API call:** `PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=<pm_id>&template=ALL_PRIVILEGES`
Query params only, NO body. This MUST succeed before creating any projects.

**On employee already exists error:** Use any existing employee as project manager. GET /employee and use values[0].id.

## Step 4: Create 3 Internal Projects (3 parallel calls)
For each of the top 3 accounts:
**API call:** `POST /project`
**Payload:**
```json
{
  "name": "<account_name>",
  "projectManager": {"id": "<pm_id>"},
  "startDate": "2026-01-01",
  "isInternal": true
}
```
The project name MUST be the account name (e.g. "Lonn og honorarer", "Kontorkostnader"), NOT the account number.

Capture `project_id_1`, `project_id_2`, `project_id_3`.

## Step 5: Create 3 Activities (3 parallel calls)
For each project:
**API call:** `POST /activity`
**Payload:**
```json
{
  "name": "<account_name>",
  "activityType": "GENERAL_ACTIVITY"
}
```

**On error 422 with `GENERAL_ACTIVITY`:** This should not happen. Do NOT try `PROJECT_SPECIFIC_ACTIVITY` — it requires creation via `/project/projectActivity` which is more complex.

Then STOP. Do NOT verify.

## IMPORTANT
- Expense accounts in Norwegian chart of accounts: range 4000-8999. Always filter with `accountNumberFrom=4000&accountNumberTo=8999`.
- Use `fields=id,account(id,name,number),amount,date` to get account names inline — avoids separate account lookups.
- The "increase" = Feb total - Jan total. Accounts only in Feb (not in Jan) use 0 for Jan total.
- Project name = account name (human-readable), NOT the account number.
- Grant entitlements BEFORE creating projects — otherwise project creation fails with 403.
- If the prompt mentions different months, adjust dateFrom/dateTo accordingly. Default is Jan vs Feb 2026.
- Target: 11 calls (8 if account names come from posting response and activities embedded). 0 errors.
