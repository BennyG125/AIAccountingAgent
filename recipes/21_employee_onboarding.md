# Employee Onboarding from PDF Contract (Tier 3)

## CRITICAL — Field Name Traps
- **percentageOfFullTimeEquivalent**: NOT `percentOfFullTimeEquivalent`. The missing "age" causes 422.
- **employment/details body**: Only these fields: `employment`, `date`, `employmentType`, `occupationCode`, `percentageOfFullTimeEquivalent`, `annualSalary`. Any other field name causes "Request mapping failed".
- **nationalIdentityNumber**: May be invalid in the PDF. If 422, retry WITHOUT it.

## Task Pattern
Create an employee in Tripletex with full employment details extracted from an attached PDF contract or offer letter.
Prompts appear in FR, PT, DE, EN, NO, NN, ES. Typical prompt: "You received an employment contract (see attached PDF). Create the employee in Tripletex with all contract details: national identity number, date of birth, department, occupation code, salary, employment percentage, and start date."

The attached PDF is always a Norwegian employment contract ("arbeidskontrakt") or offer letter ("tilbudsbrev") containing structured employee data in Norwegian.

## File Handling
**PDF types:**
- "Arbeidskontrakt" — full contract with all fields (name, DOB, national ID, email, bank account, department, STYRK code, employment form, salary type, position %, annual salary, start date)
- "Tilbudsbrev" — offer letter with fewer fields (name, DOB, department, position %, annual salary, start date, working hours). May be MISSING: email, national ID, bank account, STYRK code.

**PDF text extraction (pymupdf)** works well on these PDFs — the text is selectable, not scanned. The OCR output is supplementary but the pymupdf-extracted text is the primary data source.

**Field mapping from PDF to API:**
| PDF field (Norwegian) | API field |
|----------------------|-----------|
| Arbeidstaker (name) | `firstName`, `lastName` |
| Fødselsdato | `dateOfBirth` (convert DD.MM.YYYY → YYYY-MM-DD) |
| Personnummer | `nationalIdentityNumber` (11 digits, may be invalid — skip if POST returns 422) |
| E-post | `email` (if missing, generate as `firstname.lastname@company.no`) |
| Bankkonto | Not used in employee creation |
| Avdeling | `department` — search existing, create if not found |
| Stillingskode (STYRK) | `occupationCode: {id: <styrk_number>}` |
| Ansettelsesform | `employmentType` — "Fast stilling" → "ORDINARY" |
| Stillingsprosent | `percentageOfFullTimeEquivalent` (number, e.g., 80 or 100) |
| Årslønn | `annualSalary` (number, e.g., 710000) |
| Tiltredelse | `startDate` on employment (convert DD.MM.YYYY → YYYY-MM-DD) |
| Arbeidstid | Not a direct field — informational only |

## Optimal API Sequence
1. GET /department → find matching department by name [1 call]
   If not found: POST /department → dept_id [+1 call]
2. POST /employee → employee_id [1 call]
   Include: firstName, lastName, email, dateOfBirth, userType: "STANDARD", department: {id}
   Include nationalIdentityNumber if available (11-digit personnummer).
   If 422 on nationalIdentityNumber ("Ugyldig format"): retry WITHOUT nationalIdentityNumber.
   If email not in contract: generate as `firstname.lastname@company.no`.
3. GET /company/divisions → division_id (use first result) [1 call]
4. POST /employee/employment → employment_id [1 call]
   Body: `{employee: {id}, startDate: "YYYY-MM-DD", division: {id}}`
5. POST /employee/employment/details → detail_id [1 call]
   Body: `{employment: {id}, date: "YYYY-MM-DD", employmentType, occupationCode: {id}, percentageOfFullTimeEquivalent, annualSalary}`

**Target: 5-6 calls, 0 errors**

## Field Reference

### POST /employee
```json
{
  "firstName": "Arthur",
  "lastName": "Moreau",
  "email": "arthur.moreau@example.org",
  "dateOfBirth": "1993-07-06",
  "nationalIdentityNumber": "06079385393",
  "userType": "STANDARD",
  "department": {"id": "<dept_id>"}
}
```

### POST /employee/employment
```json
{
  "employee": {"id": "<employee_id>"},
  "startDate": "2026-08-10",
  "division": {"id": "<division_id>"}
}
```

### POST /employee/employment/details
```json
{
  "employment": {"id": "<employment_id>"},
  "date": "2026-08-10",
  "employmentType": "ORDINARY",
  "occupationCode": {"id": 2511},
  "percentageOfFullTimeEquivalent": 80,
  "annualSalary": 710000
}
```

## Known Gotchas

### Critical field name trap
- **percentageOfFullTimeEquivalent**: NOT `percentOfFullTimeEquivalent`. The missing "age" causes 422 "Feltet eksisterer ikke i objektet" (field does not exist in object).

### Employment creation requires division
- `division: {id}` is required on POST /employee/employment. Use GET /company/divisions and take the first result.
- Some sandboxes may auto-assign division — but always include it to be safe.

### nationalIdentityNumber validation
- The API validates the Norwegian national identity number (fødselsnummer) checksum.
- If the PDF contains an invalid number, POST /employee will return 422 "Ugyldig format".
- **Recovery**: Retry WITHOUT `nationalIdentityNumber`. The employee can be created without it.

### Email is required
- POST /employee requires `email`. If the PDF doesn't contain an email (common in "tilbudsbrev"), generate one: `firstname.lastname@company.no` (lowercased).

### occupationCode uses STYRK number as ID
- The STYRK code from the contract (e.g., 2511) is used directly as `occupationCode: {id: 2511}`.
- If the PDF doesn't include a STYRK code, omit `occupationCode` from employment details.

### Date format
- PDF dates are DD.MM.YYYY (e.g., "06.07.1993"). API expects YYYY-MM-DD (e.g., "1993-07-06").

### employmentType mapping
- "Fast stilling" → `"ORDINARY"`
- If not specified, default to `"ORDINARY"`

## Expected Performance
- Calls: 5-6 (5 if department exists, 6 if creating department)
- Errors: 0
- Time: ~30-50s
