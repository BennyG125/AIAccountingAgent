# Employee Onboarding from PDF Contract (Tier 3)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## CRITICAL — Field Name Traps (Read FIRST)
- **percentageOfFullTimeEquivalent**: NOT `percentOfFullTimeEquivalent`. The missing "age" causes 422.
- **employment/details allowed fields ONLY**: `employment`, `date`, `employmentType`, `occupationCode`, `percentageOfFullTimeEquivalent`, `annualSalary`. ANY other field → "Request mapping failed".
- **NEVER add**: `workingHours`, `hoursPerWeek`, `standardHours`, `scheduleType`, `salaryType`, `maritimeEmploymentType` — even if the prompt mentions working hours. Those are informational only.
- **NEVER create a division**: Always GET /company/divisions and use existing. POST /division requires organizationNumber and WILL fail.
- **nationalIdentityNumber**: May be invalid in the PDF. If POST /employee returns 422 → retry WITHOUT it immediately.

## Task Pattern
Create an employee in Tripletex with full employment details extracted from an attached PDF contract or offer letter.
The attached PDF is always a Norwegian "arbeidskontrakt" (full contract) or "tilbudsbrev" (offer letter).

**PDF types:**
- **"Arbeidskontrakt"** — full contract: name, DOB, national ID, email, bank account, department, STYRK code, employment form, salary, position %, start date
- **"Tilbudsbrev"** — offer letter: name, DOB, department, position %, salary, start date, working hours. MISSING: email, national ID, STYRK code. Proceed WITHOUT these fields.

## Step 1: OCR the PDF (non-API)
Extract ALL fields from the attached PDF in one pass. Map Norwegian field names:
| PDF field | API field |
|-----------|-----------|
| Arbeidstaker (name) | `firstName`, `lastName` |
| Fødselsdato | `dateOfBirth` (convert DD.MM.YYYY → YYYY-MM-DD) |
| Personnummer | `nationalIdentityNumber` (11 digits — skip if absent) |
| E-post | `email` (if absent → generate `firstname.lastname@company.no`) |
| Avdeling | department name → search and create if needed |
| Stillingskode (STYRK) | `occupationCode: {id: <styrk_number>}` (skip if absent) |
| Ansettelsesform | `employmentType` — "Fast stilling" → "ORDINARY". Default "ORDINARY". |
| Stillingsprosent | `percentageOfFullTimeEquivalent` (number, e.g. 80 or 100) |
| Årslønn | `annualSalary` (number, e.g. 710000) |
| Tiltredelse | `startDate` (convert DD.MM.YYYY → YYYY-MM-DD) |
| Arbeidstid | NOT a direct field — informational only, IGNORE |

## Step 2: Find or Create Department
**API call:** `GET /department?name=<department_name_from_pdf>`
- If `values` has a match → capture `dept_id = values[0].id`
- If empty → `POST /department {name: "<name>", departmentNumber: "<any_unique_string>"}` → capture `id`

**departmentNumber** must be a STRING (e.g. "10", "AVD-1"). NOT an integer.

## Step 3: Create Employee
**API call:** `POST /employee`
**Payload:**
```json
{
  "firstName": "<first>",
  "lastName": "<last>",
  "email": "<email or firstname.lastname@company.no>",
  "dateOfBirth": "YYYY-MM-DD",
  "userType": "STANDARD",
  "department": {"id": "<dept_id>"}
}
```
Include `nationalIdentityNumber` ONLY if present in PDF and 11 digits.

**On error 422 "Ugyldig format" or "Validering feilet":** Retry immediately WITHOUT `nationalIdentityNumber`. Do NOT change anything else.
**On error 422 "e-postadressen er i bruk":** `GET /employee?email=X` → use existing `values[0].id`.

Capture `employee_id`.

## Step 4: Get Division ID
**API call:** `GET /company/divisions`
Capture `division_id = values[0].id`. NEVER try to create a division.

## Step 5: Create Employment
**API call:** `POST /employee/employment`
**Payload:**
```json
{
  "employee": {"id": "<employee_id>"},
  "startDate": "YYYY-MM-DD",
  "division": {"id": "<division_id>"}
}
```
Capture `employment_id`.

## Step 6: Create Employment Details
**API call:** `POST /employee/employment/details`
**Payload:**
```json
{
  "employment": {"id": "<employment_id>"},
  "date": "YYYY-MM-DD",
  "employmentType": "ORDINARY",
  "percentageOfFullTimeEquivalent": 80,
  "annualSalary": 710000
}
```
Add `"occupationCode": {"id": <styrk_code>}` ONLY if STYRK code was in the PDF. Otherwise omit entirely.

**WHITELIST — only these fields are allowed in the body:**
- `employment` (object with id) — REQUIRED
- `date` (YYYY-MM-DD) — REQUIRED
- `employmentType` (string) — REQUIRED
- `percentageOfFullTimeEquivalent` (number) — REQUIRED
- `annualSalary` (number) — REQUIRED
- `occupationCode` (object with id) — OPTIONAL
ANY other field name causes 422 "Request mapping failed". Do NOT add workingHours, hoursPerWeek, or any field not in this list.

## IMPORTANT
- Date format: PDF uses DD.MM.YYYY (e.g. "06.07.1993") → API requires YYYY-MM-DD ("1993-07-06"). ALWAYS convert.
- `percentageOfFullTimeEquivalent` — spell it exactly. NOT `percentOfFullTimeEquivalent`.
- STYRK code (e.g. 2511) is used directly as integer ID: `occupationCode: {id: 2511}`.
- If PDF is "tilbudsbrev" (offer letter): expect NO email, NO national ID, NO STYRK code. Generate email, skip the others. Do NOT search for them.
- Target: 5 calls (dept exists), 6 calls (dept created). 0 errors.
