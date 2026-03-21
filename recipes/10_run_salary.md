# Run Salary (Tier 2)
1. Search or create employee: GET /employee?email=X or POST /employee
2. GET /employee/employment?employeeId=ID → check for existing employment
3. If no employment: POST /employee/employment {employee: {id}, startDate: "{today}"}
4. POST /employee/employment/details {employment: {id}, date: "{today}",
   annualSalary: AMOUNT, employmentType: "ORDINARY"}
5. GET /salary/type → find salary type IDs for base salary + additions
6. POST /salary/transaction {date: "{today}", month: CURRENT_MONTH, year: CURRENT_YEAR,
   payslips: [{employee: {id}, date: "{today}", specifications: [
     {salaryType: {id}, rate: AMOUNT, count: 1}
   ]}]}
NOTE: The salary API is complex. If the above fails, read the error message carefully.
Use GET /salary/type?fields=* to discover available salary types and their structure.
