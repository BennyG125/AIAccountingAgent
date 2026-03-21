# Asset Registration
1. GET /ledger/account?number=XXXX → find asset account and depreciation account
2. POST /asset {name, dateOfAcquisition, acquisitionCost, account: {id},
   lifetime: MONTHS, depreciationAccount: {id},
   depreciationMethod: "STRAIGHT_LINE", depreciationFrom: "YYYY-MM-DD"}
