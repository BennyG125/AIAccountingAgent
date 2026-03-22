# Run Salary (Tier 2)

## CRITICAL WARNINGS
- **GET /company/0** is the ONLY way to get company info. NOT /company (405) or /company/1 (404).
- **GET /company/divisions** to find divisions. NOT /division or /company/division.
- **Division creation** requires municipality and municipalityDate IN ADDITION to name and organizationNumber.
- **Division organizationNumber** must be a unique 9-digit string (Norwegian org number format).
- **percentageOfFullTimeEquivalent**: NOT `percentOfFullTimeEquivalent` (missing "age" causes 422).
- **POST /employee/employment/details** ONLY accepts: employment, date, employmentType, occupationCode, percentageOfFullTimeEquivalent, annualSalary. ANY extra field causes "Request mapping failed".

## Optimal API Sequence
1. Search or create employee: GET /employee?email=X or POST /employee
   CRITICAL: ALWAYS include dateOfBirth (use "1980-01-01" if not specified). Employment creation FAILS without it.
2. GET /company/0 → get company info (org number, name, etc.) [MUST use ID 0, not 1]
3. GET /company/divisions → check for existing divisions
   - If a division exists: use its ID — do NOT create a new one
   - If NO division exists: POST /division — requires municipality! First GET /municipality?fields=id,name&count=1 → municipality_id.
     Then: POST /division {name: "Hovedkontor", organizationNumber: "<unique 9-digit>", startDate: "2026-01-01", municipality: {id: municipality_id}, municipalityDate: "2026-01-01"}
     WARNING: Without municipality/municipalityDate → 422 "Må velges" / "Feltet må fylles ut".
4. GET /employee/employment?employeeId=ID → check for existing employment
5. If no employment: POST /employee/employment {employee: {id}, startDate: "{today}", division: {id}}
   Division is REQUIRED — use the division found/created in step 3.
6. POST /employee/employment/details {employment: {id}, date: "{today}",
   annualSalary: AMOUNT, employmentType: "ORDINARY"}
   ONLY these fields allowed: employment, date, employmentType, occupationCode, percentageOfFullTimeEquivalent, annualSalary.
7. GET /salary/type?fields=* → find salary type IDs for base salary
8. POST /salary/transaction {date: "{today}", month: CURRENT_MONTH, year: CURRENT_YEAR,
   payslips: [{employee: {id}, date: "{today}", specifications: [
     {salaryType: {id}, rate: AMOUNT, count: 1}
   ]}]}

## Field Reference

### POST /division (only if none exists — requires municipality!)
First: GET /municipality?fields=id,name&count=1 → capture municipality_id
```json
{
  "name": "Hovedkontor",
  "organizationNumber": "123456789",
  "startDate": "2026-01-01",
  "municipality": {"id": "<municipality_id>"},
  "municipalityDate": "2026-01-01"
}
```

### POST /employee/employment
```json
{
  "employee": {"id": "<employee_id>"},
  "startDate": "2026-01-01",
  "division": {"id": "<division_id>"}
}
```

### POST /employee/employment/details
```json
{
  "employment": {"id": "<employment_id>"},
  "date": "2026-01-01",
  "employmentType": "ORDINARY",
  "annualSalary": 600000
}
```
ONLY the fields above are allowed. Any extra field causes "Request mapping failed" 422.

### POST /salary/transaction
```json
{
  "date": "2026-01-01",
  "month": 1,
  "year": 2026,
  "payslips": [{
    "employee": {"id": "<employee_id>"},
    "date": "2026-01-01",
    "specifications": [
      {"salaryType": {"id": "<salary_type_id>"}, "rate": 50000, "count": 1}
    ]
  }]
}
```

NOTE: Salary type numbers are NOT 100/200 — they use 1000, 2000, etc.
Common types: 2000=Fastlønn (base salary), 2001=Timelønn (hourly), 1000=Gjeld til ansatte.
Use GET /salary/type?fields=id,number,name to discover available types.
NOTE: GET /company/0 returns HTTP 204 (empty) in some sandboxes. If so, use GET /company/divisions instead.
