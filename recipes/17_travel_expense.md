# Travel Expense with Per Diem + Costs (Tier 2)
STOP. Follow these steps IN ORDER. Do NOT think about alternative approaches. Execute immediately.

## CRITICAL — Forbidden Fields (Read FIRST)
These cause instant 400/422 errors. Memorize before making ANY call:
- `paymentType` at TOP level of travelExpense → 422 "Request mapping failed". Put it on each `costs[]` item ONLY.
- `countDays` → DOES NOT EXIST. Use `count` on perDiemCompensations.
- `description` on cost items → DOES NOT EXIST. Use `comments`.
- `costCategory?fields=id,name` → 400 error. Field is `description`, NOT `name`. Use `?fields=id,description`.
- `rateCategory?fields=id,description` → 400 error. Field is `name`, NOT `description`. Use `?fields=id,name,type,fromDate,toDate,isValidDomestic`.
- NEVER call `/travelExpense/rate` → 422 "Result set too large" (10000+ results). Use `/travelExpense/rateCategory` only.

## Task Pattern
Register a travel expense report for an employee with per diem (diett/Tagegeld/per diem/dieta) and/or out-of-pocket costs.

## Step 1: Find Employee (+ Get Department)
**API calls (parallel):**
- `GET /employee?email=<email>&fields=id,firstName,lastName`
- `GET /department?fields=id,name`

If employee found → capture `employee_id`, skip to Step 3.
If NOT found → proceed to Step 2.

## Step 2: Create Employee (only if not found)
**API call:** `POST /employee`
**Payload:**
```json
{
  "firstName": "<first>",
  "lastName": "<last>",
  "email": "<email>",
  "userType": "STANDARD",
  "department": {"id": "<dept_id>"}
}
```
Capture `employee_id`.

Then grant entitlements:
**API call:** `PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=<employee_id>&template=ALL_PRIVILEGES`
Query params only, NO body.

**On error 422 "e-postadressen er i bruk":** `GET /employee?email=X` → use existing ID. Skip entitlement grant.

## Step 3: Get Payment Type + Cost Categories + Rate Categories (parallel)
Issue ALL needed lookups in ONE tool_use response:
- `GET /travelExpense/paymentType?fields=id,description` → `payment_type_id = values[0].id`
- `GET /travelExpense/costCategory?fields=id,description&showOnTravelExpenses=true` → match expenses to categories
- `GET /travelExpense/rateCategory?fields=id,name,type,fromDate,toDate,isValidDomestic` → find per diem rate (only if prompt mentions per diem)

**Cost category matching** (use `description` field, NOT `name`):
| Expense type | Match costCategory description containing |
|-------------|-------------------------------------------|
| Flight/fly/Flug/vol/voo | "Fly" or "Flybillett" |
| Taxi | "Taxi" |
| Hotel/hotell/Hotel/hotel | "Hotell" |
| Restaurant/mat/repas/refeicao | "Restaurant" or "Mat" |
| Parking/parkering | "Parkering" |
| Generic/other | Use first available category as fallback |

**Rate category selection** (for per diem — use `name` field, NOT `description`):
1. Filter: `type == "PER_DIEM"`
2. Filter: `fromDate <= travel_start_date` AND (`toDate >= travel_end_date` OR toDate is null)
3. For 2026 domestic overnight trips: pick entry with `name` containing "Overnatting over 12 timer - innland" and `fromDate=2026-01-01`
4. For day trips over 12h: "Dagsreise over 12 timer" with `fromDate=2026-01-01`
5. If unsure: use the overnight domestic category as default

## Step 4: Create Travel Expense (single call)
**API call:** `POST /travelExpense`
**Payload:**
```json
{
  "employee": {"id": "<employee_id>"},
  "title": "<trip title from prompt>",
  "isChargeable": false,
  "travelDetails": {
    "departureDate": "YYYY-MM-DD",
    "returnDate": "YYYY-MM-DD",
    "departureFrom": "<origin city>",
    "destination": "<destination city>",
    "purpose": "work"
  },
  "perDiemCompensations": [
    {
      "rateCategory": {"id": "<rate_category_id>"},
      "count": "<number_of_days>",
      "location": "<destination city>"
    }
  ],
  "costs": [
    {
      "paymentType": {"id": "<payment_type_id>"},
      "date": "YYYY-MM-DD",
      "costCategory": {"id": "<matched_cost_category_id>"},
      "amountCurrencyIncVat": 2500,
      "currency": {"id": 1},
      "comments": "Flybillett Oslo-Trondheim"
    }
  ]
}
```

**Rules:**
- Omit `perDiemCompensations` entirely if no per diem in prompt
- Omit `costs` entirely if no expenses in prompt
- `paymentType` goes INSIDE each `costs[]` item — NOT at travelExpense top level
- `count` (NOT `countDays`) for number of per diem days
- `comments` (NOT `description`) on each cost item
- `amountCurrencyIncVat` is a number (not string)
- `currency: {"id": 1}` = NOK
- Infer dates: `departureDate = today`, `returnDate = today + N days - 1` if not specified

Then STOP. Do NOT verify.

## IMPORTANT
- Per diem language patterns: NO "diett/dagssats", DE "Tagegeld", EN "per diem", FR "indemnites journalieres", PT "diaria/dieta", ES "dieta/viaticos"
- The `description` field on costCategory is the ONLY name field. The `name` field on rateCategory is the ONLY name field. These are SWAPPED compared to what you might expect.
- Target: 5-7 calls (5 if employee exists + no per diem, 7 with per diem + new employee). 0 errors.
