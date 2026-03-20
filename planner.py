# planner.py
"""Structured output parsing and pattern matching for deterministic execution.

parse_prompt() — Claude extracts a TaskPlan from the prompt (1 LLM call).
is_known_pattern() — Checks if the plan can be executed deterministically.
FallbackContext — Shared context for tool-use fallback handoff.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field

from claude_client import get_claude_client, CLAUDE_MODEL
from task_registry import ENTITY_SCHEMAS, ACTION_SCHEMAS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parse prompt
# ---------------------------------------------------------------------------

PARSE_SYSTEM_PROMPT = """You are a task parser for the Tripletex accounting API.

Given an accounting task prompt (in any language: nb, nn, en, es, pt, de, fr),
extract a structured plan of actions.

For each entity, extract:
- entity type (department, employee, customer, product, order, invoice, etc.)
- action type (create, update, delete, or a named action like send_invoice)
- field values using EXACT API field names
- search_fields for finding existing entities (used with update/delete/action patterns)
- dependencies between entities (which entity fields reference other entities)

API field names per entity:
- department: name, departmentNumber
- employee: firstName, lastName, email, userType, department
- customer: name, email, phoneNumber, organizationNumber
- product: name, priceExcludingVatCurrency, vatType
- order: customer, orderDate, deliveryDate, orderLines[{product, count, unitPriceExcludingVatCurrency, vatType}]
- invoice: invoiceDate, invoiceDueDate, orders
- register_payment: paymentDate, paidAmount, paidAmountCurrency, paymentTypeId
- travel_expense: employee, title
- travel_expense_cost: travelExpense, date, amountCurrencyIncVat, costCategory, paymentType, currency
- project: name, projectManager, startDate
- voucher: date, description, postings[{accountNumber, amount}]
- contact: firstName, lastName, email, customer
- employee_employment: employee, startDate, endDate, taxDeductionCode, isMainEmployer
- employee_employment_details: employment, date, employmentType, annualSalary, hourlyWage
- supplier: name, email, phoneNumber, organizationNumber, supplierNumber
- customer_category: name, number, description, type
- product_unit: name, nameShort, commonCode
- order_line: order, product, count, unitPriceExcludingVatCurrency, vatType, discount
- project_participant: project, employee, adminAccess
- travel_expense_per_diem: travelExpense, rateCategory, rateType, countryCode, location, count, amount, overnightAccommodation
- travel_expense_mileage: travelExpense, rateCategory, rateType, date, departureLocation, destination, km, rate
- travel_expense_accommodation: travelExpense, rateCategory, rateType, location, count, rate, amount
- ledger_account: number, name
- salary_transaction: date, month, year, payslips, isHistorical
- delivery_address: (updated via PUT with full object)
- company: name, organizationNumber (singleton — update only)
- supplier_invoice: (read-only — use action patterns for approve/reject/pay)

For update/modify tasks:
- action="update", search_fields={fields to find the entity}, fields={fields to change}

For delete tasks:
- action="delete", search_fields={fields to find the entity}, fields={}

For invoice actions:
- action="send_invoice", search_fields={fields to find the invoice}, fields={sendType, overrideEmailAddress}
- action="create_credit_note", search_fields={fields to find the invoice}, fields={}
- action="register_payment" uses depends_on, not search_fields

For voucher reversal:
- action="reverse_voucher", search_fields={fields to find the voucher}, fields={}

For employee admin/entitlements:
- action="grant_entitlements", search_fields={fields to find the employee}, fields={entitlementTemplate}

For travel expense workflow:
- action="approve_travel_expense", search_fields={fields to find the travel expense}, fields={}
- action="deliver_travel_expense", search_fields={fields to find the travel expense}, fields={}

For supplier invoice actions:
- action="approve_supplier_invoice", search_fields={fields to find the supplier invoice}, fields={}
- action="reject_supplier_invoice", search_fields={fields to find the supplier invoice}, fields={}
- action="pay_supplier_invoice", search_fields={fields to find the supplier invoice}, fields={paymentType, amount, paymentDate}

For invoice reminder:
- action="create_reminder", search_fields={fields to find the invoice}, fields={}

For company updates (singleton — no search needed):
- action="update", entity="company", search_fields={}, fields={fields to change}

For salary:
- action="create", entity="salary_transaction", fields={date, month, year, payslips}

IMPORTANT — Bulk operations:
When a task requires creating multiple entities of the same type (e.g., "create 3 employees",
"add 5 products"), output each as a separate create action. The executor will automatically
batch them into a single API call using bulk endpoints (POST /*/list) when possible.
This saves API calls and improves efficiency.

Examples:

Prompt: "Opprett en avdeling med navn Salg og avdelingsnummer 200"
Output:
{"actions": [{"action": "create", "entity": "department", "fields": {"name": "Salg", "departmentNumber": "200"}, "search_fields": {}, "ref": "dep1", "depends_on": {}}]}

Prompt: "Create a customer Acme AS, create a product Consulting at 1500 NOK ex VAT, create an order with the product, invoice it, and register payment"
Output:
{"actions": [
  {"action": "create", "entity": "customer", "fields": {"name": "Acme AS"}, "search_fields": {}, "ref": "cust1", "depends_on": {}},
  {"action": "create", "entity": "product", "fields": {"name": "Consulting", "priceExcludingVatCurrency": 1500}, "search_fields": {}, "ref": "prod1", "depends_on": {}},
  {"action": "create", "entity": "order", "fields": {"orderLines": [{"count": 1, "unitPriceExcludingVatCurrency": 1500}]}, "search_fields": {}, "ref": "ord1", "depends_on": {"customer": "cust1", "product": "prod1"}},
  {"action": "create", "entity": "invoice", "fields": {}, "search_fields": {}, "ref": "inv1", "depends_on": {"orders": ["ord1"]}},
  {"action": "register_payment", "entity": "register_payment", "fields": {"paidAmount": 1500}, "search_fields": {}, "ref": "pay1", "depends_on": {"invoice": "inv1"}}
]}

Prompt: "Erstellen Sie einen Mitarbeiter namens Hans Müller mit E-Mail hans@test.de"
Output:
{"actions": [{"action": "create", "entity": "employee", "fields": {"firstName": "Hans", "lastName": "Müller", "email": "hans@test.de"}, "search_fields": {}, "ref": "emp1", "depends_on": {}}]}

Output the TaskPlan JSON. Use "ref" labels (dep1, emp1, cust1, etc.) for
cross-references. Set depends_on to map field names to refs.

Output ONLY the JSON object. No explanation, no markdown code fences, no other text."""


def parse_prompt(prompt: str, file_contents: list[dict]) -> dict | None:
    """Parse a task prompt into a structured TaskPlan via Claude."""
    start = time.time()

    # Build text context from files (images already OCR'd by this point)
    text_parts = []
    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            text_parts.append(f"[Attached file: {f['filename']}]\n{text}")

    user_message = "\n\n".join(text_parts + [prompt]) if text_parts else prompt

    try:
        client = get_claude_client()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            system=PARSE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=4096,
            temperature=0.0,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        # Claude returns JSON as text — parse it
        raw_text = response.content[0].text
        # Handle case where Claude wraps JSON in markdown code block
        raw_text = re.sub(r'^```\w*\n?', '', raw_text.strip())
        raw_text = raw_text.rsplit("```", 1)[0].strip()
        result = json.loads(raw_text)

        if isinstance(result, dict) and "actions" in result:
            actions = result["actions"]
            entities = [a.get("entity", "?") for a in actions]
            logger.info(f"parse: task_plan_actions={len(actions)} entities={entities} "
                       f"parse_time_ms={elapsed_ms}")
            for a in actions:
                logger.info(f"parse: action ref={a.get('ref')} action={a.get('action')} "
                           f"entity={a.get('entity')} fields={a.get('fields')} "
                           f"depends_on={a.get('depends_on')}")
            return result

        logger.warning(f"parse: unexpected format, parse_time_ms={elapsed_ms}")
        return None

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.warning(f"parse: error=\"{e}\" parse_time_ms={elapsed_ms}")
        return None


# ---------------------------------------------------------------------------
# Pattern matcher
# ---------------------------------------------------------------------------

DETERMINISTIC_ACTIONS = {
    # Creates
    "create", "register_payment", "lookup",
    # Generic modifications
    "update", "delete",
    # Invoice actions
    "send_invoice", "create_credit_note", "create_reminder",
    # Voucher actions
    "reverse_voucher",
    # Employee actions
    "grant_entitlements",
    # Travel expense workflow
    "approve_travel_expense", "deliver_travel_expense", "unapprove_travel_expense",
    # Supplier invoice actions
    "approve_supplier_invoice", "reject_supplier_invoice", "pay_supplier_invoice",
}


def is_known_pattern(task_plan: dict | None) -> bool:
    """Check if a TaskPlan can be executed deterministically."""
    if not task_plan or not task_plan.get("actions"):
        return False

    actions = task_plan["actions"]
    all_refs = {a["ref"] for a in actions}

    for action in actions:
        action_type = action.get("action")

        # Check 1: action type supported
        if action_type not in DETERMINISTIC_ACTIONS:
            logger.info(f"match: result=fallback reason=unsupported_action:{action_type}")
            return False

        entity = action.get("entity", "")

        # Check 2: entity validation (branched by action type)
        if action_type in ("create", "register_payment", "lookup"):
            # Creates require entity in ENTITY_SCHEMAS
            if entity not in ENTITY_SCHEMAS:
                logger.info(f"match: result=fallback reason=unknown_entity:{entity}")
                return False
        elif action_type in ("update", "delete"):
            # Update/delete require entity in ENTITY_SCHEMAS + non-empty search_fields
            if entity not in ENTITY_SCHEMAS:
                logger.info(f"match: result=fallback reason=unknown_entity:{entity}")
                return False
            # Singletons (e.g., company) don't need search_fields
            if not ENTITY_SCHEMAS[entity].get("singleton") and not action.get("search_fields"):
                logger.info(f"match: result=fallback reason=missing_search_fields:{entity}")
                return False
        elif action_type in ACTION_SCHEMAS:
            # Named actions: action must be in ACTION_SCHEMAS, entity must be valid
            expected_entity = ACTION_SCHEMAS[action_type].get("entity")
            if expected_entity and entity != expected_entity:
                logger.info(f"match: result=fallback reason=entity_mismatch:{entity}!={expected_entity}")
                return False
            if not action.get("search_fields"):
                logger.info(f"match: result=fallback reason=missing_search_fields:{action_type}")
                return False

        # Check 3: depends_on refs resolve (for create actions)
        if action_type in ("create", "register_payment", "lookup"):
            depends_on = action.get("depends_on", {})
            for field_name, ref_val in depends_on.items():
                refs_to_check = ref_val if isinstance(ref_val, list) else [ref_val]
                for ref in refs_to_check:
                    if ref not in all_refs:
                        logger.info(f"match: result=fallback reason=unresolved_ref:{ref}")
                        return False

    logger.info("match: result=deterministic")
    return True


# ---------------------------------------------------------------------------
# Fallback context
# ---------------------------------------------------------------------------

@dataclass
class FallbackContext:
    """Shared context for tool-use fallback handoff."""
    task_plan: dict | None = None
    completed_refs: dict = field(default_factory=dict)
    failed_action: dict | None = None
    error: str | None = None
