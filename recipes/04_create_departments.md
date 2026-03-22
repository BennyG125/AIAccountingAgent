# Create Departments — Batch (Tier 1)
For multiple departments, make one POST /department per department.
Each needs: name (string), departmentNumber (string — NOT int).
Use HIGH numbers to avoid conflicts: start at "10001", "10002", "10003" (NOT "100", "200" — those are often taken).
If POST fails with "Nummeret er i bruk", increment and retry.
If the prompt specifies department numbers, use those instead.
