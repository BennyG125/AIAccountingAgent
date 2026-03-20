# planner.py
"""Structured output parsing and pattern matching for deterministic execution.

parse_prompt() — Gemini extracts a TaskPlan from the prompt (1 LLM call).
is_known_pattern() — Checks if the plan can be executed deterministically.
FallbackContext — Shared context for tool-use fallback handoff.
"""

import logging
import os
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from task_registry import ENTITY_SCHEMAS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (shared with agent.py)
# ---------------------------------------------------------------------------

genai_client = genai.Client(
    vertexai=True,
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "global"),
)

MODEL = "gemini-3.1-pro-preview"
PARSE_TIMEOUT = 20  # seconds

# ---------------------------------------------------------------------------
# Parse prompt
# ---------------------------------------------------------------------------

PARSE_SYSTEM_PROMPT = """You are a task parser for the Tripletex accounting API.

Given an accounting task prompt (in any language: nb, nn, en, es, pt, de, fr),
extract a structured plan of actions.

For each entity to create, extract:
- entity type (department, employee, customer, product, order, invoice, etc.)
- field values using EXACT API field names
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

For tasks involving sending invoices, deleting entities, or modifying existing records,
output action="update"/"delete"/"send_invoice" — these will be handled by the fallback path.

Output the TaskPlan JSON. Use "ref" labels (dep1, emp1, cust1, etc.) for
cross-references. Set depends_on to map field names to refs."""


TASK_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "entity": {"type": "string"},
                    "fields": {"type": "object"},
                    "ref": {"type": "string"},
                    "depends_on": {"type": "object"},
                },
                "required": ["action", "entity", "fields", "ref", "depends_on"],
            },
        },
    },
    "required": ["actions"],
}


def parse_prompt(prompt: str, file_contents: list[dict]) -> dict | None:
    """Parse a task prompt into a structured TaskPlan via Gemini."""
    start = time.time()

    # Build user content with file attachments
    parts: list[types.Part] = []
    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            parts.append(types.Part.from_text(
                text=f"[Attached file: {f['filename']}]\n{text}"
            ))
        for img in f.get("images", []):
            parts.append(types.Part.from_bytes(
                data=img["data"], mime_type=img["mime_type"]
            ))
    parts.append(types.Part.from_text(text=prompt))

    config = types.GenerateContentConfig(
        system_instruction=PARSE_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=TASK_PLAN_SCHEMA,
        temperature=0.0,
    )

    try:
        response = genai_client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=parts)],
            config=config,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        # Extract parsed JSON
        result = response.parsed
        if isinstance(result, dict) and "actions" in result:
            actions = result["actions"]
            entities = [a.get("entity", "?") for a in actions]
            logger.info(f"parse: task_plan_actions={len(actions)} entities={entities} parse_time_ms={elapsed_ms}")
            for a in actions:
                logger.info(f"parse: action ref={a.get('ref')} action={a.get('action')} "
                           f"entity={a.get('entity')} depends_on={a.get('depends_on')}")
            return result

        logger.warning(f"parse: unexpected response format, parse_time_ms={elapsed_ms}")
        return None

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.warning(f"parse: error=\"{e}\" parse_time_ms={elapsed_ms}")
        return None


# ---------------------------------------------------------------------------
# Pattern matcher
# ---------------------------------------------------------------------------

DETERMINISTIC_ACTIONS = {"create", "register_payment", "lookup"}


def is_known_pattern(task_plan: dict | None) -> bool:
    """Check if a TaskPlan can be executed deterministically."""
    if not task_plan or not task_plan.get("actions"):
        return False

    actions = task_plan["actions"]
    all_refs = {a["ref"] for a in actions}

    for action in actions:
        # Check 1: action type supported
        if action.get("action") not in DETERMINISTIC_ACTIONS:
            logger.info(f"match: result=fallback reason=unsupported_action:{action.get('action')}")
            return False

        # Check 2: entity type known
        entity = action.get("entity", "")
        if entity not in ENTITY_SCHEMAS:
            logger.info(f"match: result=fallback reason=unknown_entity:{entity}")
            return False

        # Check 3: depends_on refs resolve
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
