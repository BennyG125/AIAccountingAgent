# Create Employee (Tier 1)
1. GET /department → capture first department ID (or create one if none exist)
2. POST /employee {firstName, lastName, email, dateOfBirth: "YYYY-MM-DD", userType: "STANDARD", department: {id}}
ALWAYS include dateOfBirth — use "1980-01-01" if not specified. Employment creation FAILS without it.
Include phoneNumberMobile, address if mentioned. No "isAdministrator" field exists.
NEVER include startDate on the employee body — startDate belongs on POST /employee/employment, not on the employee itself. Including it causes 422 "Feltet eksisterer ikke".
