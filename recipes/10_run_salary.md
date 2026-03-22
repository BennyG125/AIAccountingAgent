# Run Salary (Tier 2)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## Step 1: Find or Create Employee
**API call:** `GET /employee?email=<email>&fields=id,firstName,lastName`
- If found → capture `employee_id`. Skip to Step 3.
- If empty → Step 2.

## Step 2: Create Employee (only if not found)
**API call:** `GET /department?fields=id,name` → capture `dept_id` (first result)
**API call:** `POST /employee`
```json
{"firstName": "<first>", "lastName": "<last>", "email": "<email>", "dateOfBirth": "<dob or 1990-01-01>", "userType": "STANDARD", "department": {"id": <dept_id>}}
```
**On 422 "e-postadressen er i bruk":** `GET /employee?email=X` → use existing ID.

## Step 3: Get Division (REQUIRED for employment)
**API call:** `GET /company/divisions?fields=id`
Capture `division_id = values[0].id`. NEVER try to POST /division — it always fails.

## Step 4: Check/Create Employment
**API call:** `GET /employee/employment?employeeId=<employee_id>&fields=id`
- If found → capture `employment_id`. Skip to Step 5.
- If empty → create:

**API call:** `POST /employee/employment`
```json
{"employee": {"id": <employee_id>}, "startDate": "{today}", "division": {"id": <division_id>}}
```
Do NOT include `isMainEmployer`. Capture `employment_id`.

## Step 5: Create Employment Details
**API call:** `POST /employee/employment/details`
```json
{"employment": {"id": <employment_id>}, "date": "{today}", "annualSalary": <salary>, "employmentType": "ORDINARY"}
```
Only allowed fields: `employment`, `date`, `annualSalary`, `employmentType`, `occupationCode`, `percentageOfFullTimeEquivalent`. ANY other field → 422.

## Step 6: Get Salary Types
**API call:** `GET /salary/type?fields=id,number,name`
Find base salary type (number=1000 or name containing "Fastlønn"/"Fast lønn"). Capture `base_type_id`.
If additional salary types are mentioned (e.g., bonus), find those too.

## Step 7: Create Salary Transaction
**API call:** `POST /salary/transaction`
```json
{
  "date": "{today}",
  "month": <current_month_number>,
  "year": <current_year>,
  "payslips": [{
    "employee": {"id": <employee_id>},
    "date": "{today}",
    "specifications": [
      {"salaryType": {"id": <base_type_id>}, "rate": <monthly_salary>, "count": 1}
    ]
  }]
}
```
**Monthly salary** = annualSalary / 12 (round to nearest integer).

## IMPORTANT
- NEVER call `GET /company/1` or `GET /company/<id>` — returns 404. Use `GET /company` (no ID) if you need company info.
- Division is REQUIRED on employment. Always GET /company/divisions first.
- The field is `percentageOfFullTimeEquivalent` (NOT `percentOfFullTimeEquivalent`).
- Target: 6-8 calls, 0 errors.
