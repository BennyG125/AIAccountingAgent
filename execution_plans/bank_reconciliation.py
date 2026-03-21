"""Execution plan: Bank Reconciliation (Tier 3).

Processes a bank statement CSV (semicolon-delimited) and creates all required
entries in Tripletex:
  - Customer payments: create customer → product → order → invoice → register payment
  - Supplier payments: find/create supplier → POST /ledger/voucher (debit 2400, credit 1920)
  - Bank fees: POST /ledger/voucher (debit 7770, credit 1920) or reversed if in Inn column

CSV format:
  Dato;Forklaring;Inn;Ut;Saldo
  YYYY-MM-DD;<description>;<inn_amount>;;<running_balance>
  YYYY-MM-DD;<description>;;-<ut_amount>;<running_balance>

Transaction classification by Forklaring:
  "Innbetaling fra <Name> / Faktura <N>" → customer payment (Inn column)
  "Betaling <Name>" / "Betaling Fournisseur <Name>" / "Betaling Lieferant <Name>" → supplier payment (Ut column)
  "Bankgebyr" → bank fee (Inn = credit/refund, Ut = standard expense)

CRITICAL:
  - PUT /invoice/{id}/:payment  (NOT /:createPayment)
  - Supplier voucher 2400 posting MUST include supplier id
  - amountCurrency must always equal amount
  - Do NOT use /incomingInvoice (returns 403)
"""
import io
import csv
import re

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

# Minimal extraction schema — CSV data comes from file attachment
EXTRACTION_SCHEMA = {
    "csv_data": "string — parsed CSV content from the attached bank statement file (required)",
}


def _parse_amount(raw: str) -> float | None:
    """Parse a CSV amount cell into a positive float, or None if empty/zero."""
    s = raw.strip()
    if not s:
        return None
    # Handle European comma-decimal and whitespace
    s = s.replace(" ", "").replace(",", ".")
    # Strip leading minus (we use sign from column position)
    s = s.lstrip("-")
    try:
        val = float(s)
        return val if val > 0 else None
    except ValueError:
        return None


def _extract_customer_name(forklaring: str) -> str:
    """Extract customer name from 'Innbetaling fra <Name> / Faktura <N>'."""
    m = re.match(r"Innbetaling fra (.+?) / Faktura", forklaring, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Fallback: everything after "fra "
    m = re.match(r"Innbetaling fra (.+)", forklaring, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return forklaring.strip()


def _extract_supplier_name(forklaring: str) -> str:
    """Extract supplier name from 'Betaling [Fournisseur|Lieferant] <Name>'."""
    m = re.match(
        r"Betaling\s+(?:Fournisseur|Lieferant)\s+(.+)",
        forklaring,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    m = re.match(r"Betaling\s+(.+)", forklaring, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return forklaring.strip()


def _parse_csv(csv_data: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Parse CSV and return (customer_rows, supplier_rows, fee_rows).

    Each customer row: {date, customer_name, amount}
    Each supplier row: {date, supplier_name, amount}
    Each fee row: {date, amount, is_debit} — is_debit=True means expense (Ut column)
    """
    customer_rows = []
    supplier_rows = []
    fee_rows = []

    reader = csv.DictReader(io.StringIO(csv_data.strip()), delimiter=";")
    for row in reader:
        forklaring = row.get("Forklaring", "").strip()
        dato = row.get("Dato", "").strip()
        inn_raw = row.get("Inn", "").strip()
        ut_raw = row.get("Ut", "").strip()

        inn_amount = _parse_amount(inn_raw)
        ut_amount = _parse_amount(ut_raw)

        forklaring_lower = forklaring.lower()

        if "bankgebyr" in forklaring_lower:
            # Fee in Ut = standard expense (is_debit=True)
            # Fee in Inn = bank credit/refund (is_debit=False)
            amount = ut_amount or inn_amount
            if amount:
                is_debit = ut_amount is not None
                fee_rows.append({"date": dato, "amount": amount, "is_debit": is_debit})

        elif forklaring_lower.startswith("innbetaling fra"):
            amount = inn_amount
            if amount:
                customer_name = _extract_customer_name(forklaring)
                customer_rows.append(
                    {"date": dato, "customer_name": customer_name, "amount": amount}
                )

        elif forklaring_lower.startswith("betaling"):
            amount = ut_amount
            if amount:
                supplier_name = _extract_supplier_name(forklaring)
                supplier_rows.append(
                    {"date": dato, "supplier_name": supplier_name, "amount": amount}
                )

    return customer_rows, supplier_rows, fee_rows


@register
class BankReconciliationPlan(ExecutionPlan):
    task_type = "bank_reconciliation"
    description = (
        "Parse bank statement CSV; register customer payments via invoice flow; "
        "post supplier and bank-fee vouchers to /ledger/voucher"
    )

    def execute(self, client, params, start_time):  # noqa: C901
        self._check_timeout(start_time)

        csv_data = params.get("csv_data", "")
        if not csv_data:
            raise RuntimeError("Missing required param: csv_data")

        # ------------------------------------------------------------------ #
        # Step 1: Parse CSV
        # ------------------------------------------------------------------ #
        customer_rows, supplier_rows, fee_rows = _parse_csv(csv_data)

        api_calls = 0
        api_errors = 0

        # ------------------------------------------------------------------ #
        # Step 2: Batch look up required accounts (1 call instead of 3)
        # ------------------------------------------------------------------ #
        self._check_timeout(start_time)
        accounts = self._get_accounts(client, "1920", "2400", "7770")
        api_calls += 1
        account_1920 = accounts["1920"]  # bank account
        account_2400 = accounts["2400"]  # supplier payable
        account_7770 = accounts["7770"]  # bank fees expense

        # ------------------------------------------------------------------ #
        # Step 3: Find or create all unique customers
        # ------------------------------------------------------------------ #
        self._check_timeout(start_time)

        unique_customers: dict[str, int] = {}
        for row in customer_rows:
            name = row["customer_name"]
            if name not in unique_customers:
                customer_id = self._find_or_create(
                    client,
                    search_path="/customer",
                    search_params={"name": name, "count": 1},
                    create_path="/customer",
                    create_body={"name": name},
                )
                api_calls += 2
                unique_customers[name] = customer_id

        # ------------------------------------------------------------------ #
        # Step 4: Find or create all unique suppliers
        # ------------------------------------------------------------------ #
        self._check_timeout(start_time)

        unique_suppliers: dict[str, int] = {}
        for row in supplier_rows:
            name = row["supplier_name"]
            if name not in unique_suppliers:
                supplier_id = self._find_or_create(
                    client,
                    search_path="/supplier",
                    search_params={"name": name, "count": 1},
                    create_path="/supplier",
                    create_body={"name": name},
                )
                api_calls += 2
                unique_suppliers[name] = supplier_id

        # ------------------------------------------------------------------ #
        # Step 5: Look up payment type (shared by all customer payments)
        # ------------------------------------------------------------------ #
        self._check_timeout(start_time)
        pt_result = client.get("/invoice/paymentType")
        api_calls += 1
        payment_type_id = 1  # fallback
        if pt_result["success"]:
            types = pt_result["body"].get("values", [])
            if types:
                payment_type_id = types[0]["id"]

        # ------------------------------------------------------------------ #
        # Step 6: For each customer payment — find existing invoice or create
        # Fast path: search for matching invoice by customer + amount → pay
        # Slow path: create product → order → invoice → pay
        # ------------------------------------------------------------------ #
        from datetime import date, timedelta
        today = date.today()
        date_from = (today - timedelta(days=365)).isoformat()
        date_to = (today + timedelta(days=1)).isoformat()

        product_id = None  # lazy-created only if needed

        for row in customer_rows:
            self._check_timeout(start_time)
            customer_id = unique_customers[row["customer_name"]]
            amount = row["amount"]

            # Try to find an existing unpaid invoice for this customer + amount
            invoice_id = None
            search_result = client.get("/invoice", params={
                "customerId": customer_id,
                "invoiceDateFrom": date_from,
                "invoiceDateTo": date_to,
            })
            api_calls += 1
            if search_result["success"]:
                for inv in search_result["body"].get("values", []):
                    inv_amount = inv.get("amountExcludingVat", 0)
                    # Match by amount (with small tolerance)
                    if abs(inv_amount - amount) < 1.0:
                        invoice_id = inv["id"]
                        break

            if invoice_id is None:
                # No matching invoice — create full flow
                # Lazy-create product
                if product_id is None:
                    search_prod = client.get("/product", params={"name": "Service"})
                    api_calls += 1
                    existing = search_prod.get("body", {}).get("values", [])
                    if existing:
                        product_id = existing[0]["id"]
                    else:
                        prod_result = self._safe_post(
                            client, "/product",
                            {"name": "Service", "priceExcludingVatCurrency": 1},
                            retry_without=["number"],
                        )
                        api_calls += 1
                        if not prod_result["success"]:
                            api_errors += 1
                            raise RuntimeError(f"Failed to create product: {prod_result}")
                        product_id = prod_result["body"]["value"]["id"]

                # Create order
                order_result = client.post("/order", body={
                    "customer": {"id": customer_id},
                    "orderDate": row["date"],
                    "deliveryDate": row["date"],
                    "orderLines": [{
                        "product": {"id": product_id},
                        "count": 1,
                        "unitPriceExcludingVatCurrency": amount,
                    }],
                })
                api_calls += 1
                if not order_result["success"]:
                    api_errors += 1
                    raise RuntimeError(f"Failed to create order: {order_result}")
                order_id = order_result["body"]["value"]["id"]

                # Create invoice from order
                inv_result = client.put(
                    f"/order/{order_id}/:invoice",
                    params={"invoiceDate": row["date"]},
                )
                api_calls += 1
                if not inv_result["success"]:
                    api_errors += 1
                    raise RuntimeError(f"Failed to create invoice: {inv_result}")
                invoice_id = inv_result["body"]["value"]["id"]

            # Register payment
            payment_result = client.put(
                f"/invoice/{invoice_id}/:payment",
                params={
                    "paymentDate": row["date"],
                    "paymentTypeId": payment_type_id,
                    "paidAmount": amount,
                    "paidAmountCurrency": amount,
                },
            )
            api_calls += 1
            if not payment_result["success"]:
                api_errors += 1
                # Non-fatal — continue with other rows

        # ------------------------------------------------------------------ #
        # Step 9: Post vouchers for supplier payments
        # Debit 2400 (supplier payable, negative), credit 1920 (bank, positive)
        # 2400 posting MUST include supplier id
        # ------------------------------------------------------------------ #
        for row in supplier_rows:
            self._check_timeout(start_time)
            supplier_id = unique_suppliers[row["supplier_name"]]
            abs_amount = row["amount"]
            # Paying supplier: DEBIT 2400 (reduce liability, positive amount),
            # CREDIT 1920 (reduce bank, negative amount)
            voucher_body = {
                "date": row["date"],
                "description": f"Betaling til {row['supplier_name']}",
                "postings": [
                    {
                        "row": 1,
                        "account": {"id": account_2400},
                        "supplier": {"id": supplier_id},
                        "amount": abs_amount,
                        "amountCurrency": abs_amount,
                        "amountGross": abs_amount,
                        "amountGrossCurrency": abs_amount,
                    },
                    {
                        "row": 2,
                        "account": {"id": account_1920},
                        "amount": -abs_amount,
                        "amountCurrency": -abs_amount,
                        "amountGross": -abs_amount,
                        "amountGrossCurrency": -abs_amount,
                    },
                ],
            }
            voucher_result = client.post("/ledger/voucher", body=voucher_body)
            api_calls += 1
            if not voucher_result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to post supplier voucher for {row['supplier_name']}: "
                    f"status={voucher_result.get('status_code')}, "
                    f"error={voucher_result.get('error')}"
                )

        # ------------------------------------------------------------------ #
        # Step 10: Post vouchers for bank fees
        # Standard (Ut / is_debit=True): debit 7770, credit 1920
        # Credit/refund (Inn / is_debit=False): debit 1920, credit 7770
        # ------------------------------------------------------------------ #
        for row in fee_rows:
            self._check_timeout(start_time)
            abs_amount = row["amount"]
            if row["is_debit"]:
                # Standard bank fee: expense debit 7770, bank credit 1920
                postings = [
                    {
                        "row": 1,
                        "account": {"id": account_7770},
                        "amount": abs_amount,
                        "amountCurrency": abs_amount,
                        "amountGross": abs_amount,
                        "amountGrossCurrency": abs_amount,
                    },
                    {
                        "row": 2,
                        "account": {"id": account_1920},
                        "amount": -abs_amount,
                        "amountCurrency": -abs_amount,
                        "amountGross": -abs_amount,
                        "amountGrossCurrency": -abs_amount,
                    },
                ]
            else:
                # Bank credit/refund: bank debit 1920, credit 7770
                postings = [
                    {
                        "row": 1,
                        "account": {"id": account_1920},
                        "amount": abs_amount,
                        "amountCurrency": abs_amount,
                        "amountGross": abs_amount,
                        "amountGrossCurrency": abs_amount,
                    },
                    {
                        "row": 2,
                        "account": {"id": account_7770},
                        "amount": -abs_amount,
                        "amountCurrency": -abs_amount,
                        "amountGross": -abs_amount,
                        "amountGrossCurrency": -abs_amount,
                    },
                ]
            voucher_body = {
                "date": row["date"],
                "description": "Bankgebyr",
                "postings": postings,
            }
            voucher_result = client.post("/ledger/voucher", body=voucher_body)
            api_calls += 1
            if not voucher_result["success"]:
                api_errors += 1
                raise RuntimeError(
                    f"Failed to post bank fee voucher on {row['date']}: "
                    f"status={voucher_result.get('status_code')}, "
                    f"error={voucher_result.get('error')}"
                )

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
