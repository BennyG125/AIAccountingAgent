# Register Hours / Timesheet (Tier 2)
Full flow: create customer → employee → grant entitlements → project → activity → timesheet entry.
1. POST /customer {name, organizationNumber} → capture customer_id
2. GET /department → dept_id (or create: POST /department {name: "Avdeling", departmentNumber: "100"})
3. POST /employee {firstName, lastName, email, userType: "STANDARD", department: {id}} → employee_id
   If exists ("e-postadressen er i bruk"): GET /employee?email=X → use existing ID.
4. PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=EMPLOYEE_ID&template=ALL_PRIVILEGES
   QUERY PARAMS ONLY, NO body. Template MUST be exactly "ALL_PRIVILEGES".
5. POST /project {name, projectManager: {id: employee_id}, startDate: "{today}",
   customer: {id: customer_id}} → project_id
6. POST /activity {name, activityType: "PROJECT_GENERAL_ACTIVITY"} → activity_id
   If exists ("Navnet er i bruk"): GET /activity?name=X → use existing ID.
7. POST /timesheet/entry {activity: {id: activity_id}, employee: {id: employee_id},
   project: {id: project_id}, date: "YYYY-MM-DD", hours: N}
NOTE: hours is a decimal (e.g. 7.5 for 7h30m). One entry per date/activity/project combo.
