# Custom Dimension + Voucher (Tier 2)
1. GET /company/salesmodules → check which modules are active
2. If dimension module not active: POST /company/salesmodules to enable it
3. Discover dimension endpoints: try GET /dimension with ?fields=* to see available dimensions.
   Also try GET /dimension/v2 or similar versioned endpoints if GET /dimension returns 404.
4. Create the dimension and values as described in the prompt.
5. If the task includes posting a voucher with the dimension:
   - GET /ledger/account?number=XXXX for each account
   - POST /ledger/voucher with postings that include the dimension reference
NOTE: This is the hardest task type (254s avg, 5 errors in competition). Explore systematically
with GET ?fields=* rather than guessing field names. Read error messages carefully.
