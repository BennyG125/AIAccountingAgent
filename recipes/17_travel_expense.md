# Travel Expense with Per Diem + Costs (Tier 2)
1. GET /department → dept_id (or create: POST /department {name: "Avdeling", departmentNumber: "100"})
2. POST /employee {firstName, lastName, email, userType: "STANDARD", department: {id}} → employee_id
   If exists ("e-postadressen er i bruk"): GET /employee?email=X → use existing ID.
3. PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=EMPLOYEE_ID&template=ALL_PRIVILEGES
   QUERY PARAMS ONLY, NO body. Template MUST be exactly "ALL_PRIVILEGES".
4. GET /travelExpense/paymentType → find payment type ID
5. GET /travelExpense/costCategory → find cost category IDs (flight, taxi, etc.)
6. GET /travelExpense/rate or GET /travelExpense/rateCategory → find per diem rateType ID
7. POST /travelExpense — embed ALL compensations and costs in ONE call:
   {employee: {id: employee_id}, title: "Trip description",
     isChargeable: false,
     travelDetails: {departureDate: "YYYY-MM-DD", returnDate: "YYYY-MM-DD",
       departureFrom: "...", destination: "...", purpose: "work"},
     perDiemCompensations: [
       {rateType: {id: RATE_TYPE_ID}, count: NUM_DAYS, location: "..."}
     ],
     costs: [
       {paymentType: {id: PT_ID}, date: "YYYY-MM-DD",
         costCategory: {id: CAT_ID}, amountCurrencyIncVat: AMOUNT}
     ]
   }
NOTE: Embed compensations/costs in the POST body to save API calls. Do NOT create them separately.

### Tier 3 Recipes (anticipated — opens Saturday)
