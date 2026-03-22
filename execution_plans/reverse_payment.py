"""Execution plan: Reverse Payment (Tier 2).

A customer payment was returned by the bank. Create the full invoice chain
(customer → product → order → invoice → payment), find the payment voucher,
and reverse it.
"""
import logging
from datetime import date, timedelta

from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    "customer_name": "string (customer/company name)",
    "customer_org_number": "string (organization number)",
    "product_name": "string (product/service name from invoice description)",
    "amount_excl_vat": "number (amount excluding VAT in NOK)",
}


@register
class ReversePaymentPlan(ExecutionPlan):
    task_type = "reverse_payment"
    description = "Reverse a customer payment that was returned by the bank"

    def execute(self, client, params, start_time):
        # Validate required params
        required = ["customer_name", "product_name", "amount_excl_vat"]
        missing = [f for f in required if not params.get(f)]
        if missing:
            logger.warning(f"Missing required params for {self.task_type}: {missing}")
            return None

        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0
        error_details = []
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        due_date = (date.today() + timedelta(days=14)).isoformat()
        amount = params["amount_excl_vat"]
        amount_incl_vat = round(amount * 1.25, 2)

        # 1. Create customer
        customer_id = None
        r = client.post("/customer", body={
            "name": params["customer_name"],
            "organizationNumber": params.get("customer_org_number"),
        })
        api_calls += 1
        if r["success"]:
            customer_id = r["body"]["value"]["id"]
        else:
            api_errors += 1
            # Try searching by org number first
            if params.get("customer_org_number"):
                r2 = client.get("/customer", params={
                    "organizationNumber": params.get("customer_org_number"),
                    "fields": "id", "count": 1,
                })
                api_calls += 1
                if r2["success"] and r2["body"].get("values"):
                    customer_id = r2["body"]["values"][0]["id"]

            # Try searching by name if org number search failed
            if customer_id is None:
                r3 = client.get("/customer", params={
                    "name": params["customer_name"],
                    "fields": "id", "count": 1,
                })
                api_calls += 1
                if r3["success"] and r3["body"].get("values"):
                    customer_id = r3["body"]["values"][0]["id"]

            if customer_id is None:
                error_details.append(f"Failed to create/find customer: {r.get('error')}")
                logger.warning("reverse_payment: could not create or find customer")
                return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        self._check_timeout(start_time)

        # 2. Create product
        product_id = None
        r = client.post("/product", body={
            "name": params["product_name"],
            "priceExcludingVatCurrency": amount,
        })
        api_calls += 1
        if r["success"]:
            product_id = r["body"]["value"]["id"]
        else:
            api_errors += 1
            # Try searching for existing product by name
            r2 = client.get("/product", params={
                "name": params["product_name"],
                "fields": "id", "count": 1,
            })
            api_calls += 1
            if r2["success"] and r2["body"].get("values"):
                product_id = r2["body"]["values"][0]["id"]

            if product_id is None:
                error_details.append(f"Failed to create/find product: {r.get('error')}")
                logger.warning("reverse_payment: could not create or find product")
                return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        self._check_timeout(start_time)

        # 3. Create order with inline orderLine
        order_id = None
        r = client.post("/order", body={
            "customer": {"id": customer_id},
            "orderDate": today,
            "deliveryDate": today,
            "orderLines": [{
                "product": {"id": product_id},
                "count": 1,
                "unitPriceExcludingVatCurrency": amount,
            }],
        })
        api_calls += 1
        if r["success"]:
            order_id = r["body"]["value"]["id"]
        else:
            api_errors += 1
            error_details.append(f"Failed to create order: {r.get('error')}")
            logger.warning("reverse_payment: could not create order")
            return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        self._check_timeout(start_time)

        # 4. Create invoice
        invoice_id = None
        r = client.post("/invoice", body={
            "invoiceDate": today,
            "invoiceDueDate": due_date,
            "orders": [{"id": order_id}],
        })
        api_calls += 1
        if r["success"]:
            invoice_id = r["body"]["value"]["id"]
        else:
            api_errors += 1
            error_details.append(f"Failed to create invoice: {r.get('error')}")
            logger.warning("reverse_payment: could not create invoice")
            return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        self._check_timeout(start_time)

        # 5. Get payment type
        r = client.get("/invoice/paymentType", params={"fields": "*"})
        api_calls += 1
        if r["success"] and r["body"].get("values"):
            payment_type_id = r["body"]["values"][0]["id"]
        else:
            payment_type_id = 1  # fallback

        self._check_timeout(start_time)

        # 6. Register payment
        r = client.put(
            f"/invoice/{invoice_id}/:payment",
            params={
                "paymentDate": today,
                "paymentTypeId": payment_type_id,
                "paidAmount": amount_incl_vat,
                "paidAmountCurrency": amount_incl_vat,
            },
        )
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            error_details.append(f"Failed to register payment: {r.get('error')}")
            logger.warning("reverse_payment: could not register payment")
            return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        self._check_timeout(start_time)

        # 7. Find payment voucher
        r = client.get("/ledger/voucher", params={
            "dateFrom": today,
            "dateTo": tomorrow,
            "fields": "id,number,date,description",
        })
        api_calls += 1
        voucher_id = None
        if r["success"] and r["body"].get("values"):
            # Get the most recent voucher (last in list)
            vouchers = r["body"]["values"]
            voucher_id = vouchers[-1]["id"]
        else:
            api_errors += 1
            error_details.append(f"Failed to find payment voucher: {r.get('error')}")
            logger.warning("reverse_payment: could not find payment voucher")
            return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)

        self._check_timeout(start_time)

        # 8. Reverse the voucher
        r = client.put(
            f"/ledger/voucher/{voucher_id}/:reverse",
            params={"date": today},
        )
        api_calls += 1
        if not r["success"]:
            api_errors += 1
            error_details.append(f"Failed to reverse voucher: {r.get('error')}")
            logger.warning("reverse_payment: voucher reversal failed")

        return self._make_result(api_calls=api_calls, api_errors=api_errors, error_details=error_details)
