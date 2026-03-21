# Travel Expense with Per Diem + Costs (Tier 2)

## CRITICAL — Read Before Making ANY Call

**FORBIDDEN fields that cause instant 422 "Request mapping failed":**
- `paymentType` at TOP level of travelExpense → PUT IT ON EACH **cost** ITEM ONLY
- `countDays` → DOES NOT EXIST. Use `count` on perDiemCompensations
- `description` on cost items → DOES NOT EXIST. Use `comments`
- `rateCategory?fields=id,description` → 400 error. The field is `name`, NOT `description`. Use `?fields=id,name`
- `costCategory?fields=id,name` → 400 error. The field is `description`, NOT `name`. Use `?fields=id,description`

If you ignore this list you WILL waste 3-5 API calls on retries.

## Task Pattern
Register a travel expense report for an employee with per diem (diett/dagpenger) and out-of-pocket costs (expenses).
Prompts appear in NO, NN, DE, EN, FR, PT, ES. Typical prompt: "Register travel expense for [Name] ([email]) for [trip description]. The trip lasted N days with overnight stays. Expenses: flight XXXX, taxi XXX, hotel XXXX."

## Optimal API Sequence
1. GET /department → dept_id [1 call]
2. GET /employee?email=X → check if employee exists [1 call]
   - If NOT found: POST /employee → employee_id [1 call]
   - **ALWAYS search first** — employees often already exist in the sandbox.
3. PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=ID&template=ALL_PRIVILEGES [1 call]
   QUERY PARAMS ONLY, NO body. Template MUST be exactly "ALL_PRIVILEGES".
4. GET /travelExpense/paymentType → payment_type_id (use first result) [1 call]
5. GET /travelExpense/costCategory?fields=id,description&showOnTravelExpenses=true → match costs to categories [1 call]
6. GET /travelExpense/rateCategory?fields=id,name,type,fromDate,toDate,isValidDomestic → find per diem rate category [1 call]
   **Select the rateCategory where:** type=PER_DIEM, fromDate <= travel date, toDate >= travel date, isValidDomestic matches the trip.
   For 2026 domestic overnight: use rateCategory with name containing "Overnatting over 12 timer - innland" and fromDate=2026-01-01.
7. POST /travelExpense — embed ALL compensations and costs in ONE call [1 call]

**Target: 7-8 calls, 0 errors** (8 if employee doesn't exist and needs creation)

## Field Reference

### POST /travelExpense body
```json
{
  "employee": {"id": "<employee_id>"},
  "title": "Trip description from prompt",
  "isChargeable": false,
  "travelDetails": {
    "departureDate": "YYYY-MM-DD",
    "returnDate": "YYYY-MM-DD",
    "departureFrom": "City/location",
    "destination": "City/location",
    "purpose": "work"
  },
  "perDiemCompensations": [
    {
      "rateCategory": {"id": "<rate_category_id>"},
      "count": 3,
      "location": "City/country"
    }
  ],
  "costs": [
    {
      "paymentType": {"id": "<payment_type_id>"},
      "date": "YYYY-MM-DD",
      "costCategory": {"id": "<cost_category_id>"},
      "amountCurrencyIncVat": 2500,
      "currency": {"id": 1},
      "comments": "What this expense was for"
    }
  ]
}
```

**NOTICE:** `paymentType` appears ONLY inside each `costs[]` item. `count` (NOT countDays) on perDiemCompensations. `comments` (NOT description) on costs.

## Rate Category Selection
- There are 459 rate categories spanning many years. You MUST filter by date range matching the travel dates.
- For 2026 domestic overnight trips: look for `name` containing "Overnatting" with `fromDate=2026-01-01`.
- For 2026 domestic day trips over 12h: look for "Dagsreise over 12 timer" with `fromDate=2026-01-01`.
- For 2026 domestic day trips 6-12h: look for "Dagsreise 6-12 timer" with `fromDate=2026-01-01`.
- **Do NOT use /travelExpense/rate** — it returns 10000+ results (422 "Result set too large"). Use /travelExpense/rateCategory instead.

## Employee Handling
- **Search before creating**: GET /employee?email=X first. Most sandbox employees already exist.
- If employee creation returns 422 "e-postadressen er i bruk", search by email and use existing ID.

## Other
- Embed ALL perDiemCompensations and costs in the single POST /travelExpense call.
- `currency: {"id": 1}` = NOK.
- Match cost descriptions from the prompt to the closest costCategory by `description` (e.g., "Fly" for flights, "Taxi" for taxi, "Hotell" for hotel).

## Expected Performance
- Calls: 7-8 (7 if employee exists, 8 if new)
- Errors: 0
- Time: ~40-60s
