# Create Employee (Tier 1)
1. GET /department → capture first department ID (or create one if none exist)
2. POST /employee {firstName, lastName, email, userType: "STANDARD", department: {id}}
Include dateOfBirth, phoneNumberMobile, address if mentioned. No "isAdministrator" field exists.
