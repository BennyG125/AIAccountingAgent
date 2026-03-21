# Travel Expense with Per Diem + Costs (Tier 2)

## Optimal API Sequence
1. GET /department → dept_id (or create: POST /department {name: "Avdeling", departmentNumber: "100"})
2. POST /employee {firstName, lastName, email, userType: "STANDARD", department: {id}} → employee_id
   If exists ("e-postadressen er i bruk"): GET /employee?email=X → use existing ID.
3. PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=EMPLOYEE_ID&template=ALL_PRIVILEGES
   QUERY PARAMS ONLY, NO body. Template MUST be exactly "ALL_PRIVILEGES".
4. GET /travelExpense/paymentType → find payment type ID (use first result)
5. GET /travelExpense/costCategory?fields=id,description → find cost category IDs
   **IMPORTANT**: Use `fields=id,description` — NOT `fields=id,name`. The field is `description`, not `name`.
6. GET /travelExpense/rateCategory?fields=id,description → find per diem rate category
   **IMPORTANT**: Do NOT use /travelExpense/rate — it returns 10000+ results (422 "Result set too large").
   Use /travelExpense/rateCategory instead.
7. POST /travelExpense — embed ALL compensations and costs in ONE call:

## Field Reference
```json
{
  "employee": {"id": "<employee_id>"},
  "title": "Trip description from prompt",
  "isChargeable": false,
  "paymentType": {"id": "<payment_type_id>"},
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
      "countDays": <number_of_days>,
      "location": "City/country"
    }
  ],
  "costs": [
    {
      "paymentType": {"id": "<payment_type_id>"},
      "date": "YYYY-MM-DD",
      "costCategory": {"id": "<cost_category_id>"},
      "amountCurrencyIncVat": <amount>,
      "currency": {"id": 1},
      "description": "Cost description"
    }
  ]
}
```

## Known Gotchas
- **costCategory fields**: Use `?fields=id,description` — NOT `name`. Using `name` returns 400 "Illegal field".
- **travelExpense/rate**: Do NOT use directly — returns 422 "Result set too large". Use /travelExpense/rateCategory instead.
- **rate vs rateCategory**: The perDiemCompensations field uses `rateCategory` (not `rateType`).
- **countDays vs count**: The field is `countDays` (not `count`).
- **paymentType**: Required both on the travel expense itself AND on each cost item.
- Embed ALL compensations and costs in the POST body — do NOT create them separately.
- If employee already exists, use GET /employee?email=X to find them.
