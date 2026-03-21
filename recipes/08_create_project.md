# Create Project (Tier 2)
1. POST /customer {name, organizationNumber} → capture customer_id
2. GET /department → capture dept_id (or create one: POST /department {name: "Avdeling", departmentNumber: "100"})
3. POST /employee {firstName, lastName, email, userType: "STANDARD", department: {id: dept_id}} → capture pm_id
   If employee already exists ("e-postadressen er i bruk"): GET /employee?email=X → use existing ID.
4. **CRITICAL — grant entitlements BEFORE creating project:**
   PUT /employee/entitlement/:grantEntitlementsByTemplate?employeeId=PM_ID&template=ALL_PRIVILEGES
   - This is a PUT with QUERY PARAMS ONLY. Send NO request body (empty or omit).
   - The template value MUST be exactly "ALL_PRIVILEGES" — not "project_manager" or anything else.
   - Returns 200 with empty body on success.
5. POST /project {name, projectManager: {id: pm_id}, startDate: "{today}",
   customer: {id: customer_id}, description, ...} → capture project_id
6. If prompt mentions participants: POST /project/participant {project: {id}, employee: {id}}
