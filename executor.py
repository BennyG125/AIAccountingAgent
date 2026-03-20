# executor.py
"""Deterministic executor — runs a validated TaskPlan against the Tripletex API.

Takes a TaskPlan (from planner.py), topologically sorts actions by dependencies,
builds payloads from the entity registry, and executes API calls in order —
threading response IDs into subsequent calls.
"""

import logging
import time
from datetime import date

from task_registry import ENTITY_SCHEMAS, KNOWN_CONSTANTS, generate_auto_value
from planner import FallbackContext
from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)


def execute_plan(client: TripletexClient, task_plan: dict) -> dict:
    """Execute a TaskPlan deterministically. Returns success or FallbackContext."""
    actions = _topological_sort(task_plan["actions"])
    ref_map: dict[str, int] = {}  # ref label → real API id
    total_api_calls = 0
    start = time.time()

    # Resolve lookup_defaults before execution
    _resolve_lookup_defaults(client, actions, ref_map)

    for i, action in enumerate(actions):
        step = f"{i + 1}/{len(actions)}"
        payload = _build_payload(action, ref_map)

        method = payload["method"]
        endpoint = payload["endpoint"]
        logger.info(f"exec: step={step} method={method} endpoint={endpoint} ref={action['ref']}")

        call_start = time.time()
        if payload.get("use_query_params"):
            result = client.put(endpoint, params=payload.get("params"))
        elif method == "POST":
            result = client.post(endpoint, body=payload.get("body"))
        elif method == "PUT":
            result = client.put(endpoint, body=payload.get("body"), params=payload.get("params"))
        elif method == "GET":
            result = client.get(endpoint, params=payload.get("params"))
        else:
            result = {"success": False, "error": f"Unsupported method: {method}"}

        call_ms = int((time.time() - call_start) * 1000)
        total_api_calls += 1

        if not result["success"]:
            error_msg = result.get("error", str(result.get("body", "")))
            logger.warning(f"exec: step={step} method={method} endpoint={endpoint} "
                         f"status={result.get('status_code')} error=\"{error_msg}\" "
                         f"body={result.get('body')} time_ms={call_ms}")
            logger.info(f"exec: fallback_triggered completed_refs={ref_map} failed_action={action['ref']}")

            return {
                "success": False,
                "fallback_context": FallbackContext(
                    task_plan=task_plan,
                    completed_refs=dict(ref_map),
                    failed_action=action,
                    error=error_msg,
                ),
            }

        # Extract created entity ID
        entity_id = _extract_id(result)
        if entity_id is not None:
            ref_map[action["ref"]] = entity_id

        logger.info(f"exec: step={step} status={result.get('status_code')} success=true "
                    f"ref={action['ref']} id={entity_id} time_ms={call_ms}")

    total_ms = int((time.time() - start) * 1000)
    logger.info(f"exec: completed total_api_calls={total_api_calls} total_time_ms={total_ms}")

    return {"success": True, "ref_map": ref_map, "api_calls": total_api_calls}


def _topological_sort(actions: list[dict]) -> list[dict]:
    """Sort actions so dependencies come first."""
    ref_to_action = {a["ref"]: a for a in actions}
    visited = set()
    result = []

    def visit(ref):
        if ref in visited:
            return
        visited.add(ref)
        action = ref_to_action.get(ref)
        if not action:
            return
        for dep_ref in _all_dep_refs(action):
            visit(dep_ref)
        result.append(action)

    for action in actions:
        visit(action["ref"])
    return result


def _all_dep_refs(action: dict) -> list[str]:
    """Extract all dependency refs from an action (handles both single and array)."""
    refs = []
    for val in action.get("depends_on", {}).values():
        if isinstance(val, list):
            refs.extend(val)
        else:
            refs.append(val)
    return refs


def _build_payload(action: dict, ref_map: dict) -> dict:
    """Build the API payload for an action using the registry."""
    entity = action["entity"]
    schema = ENTITY_SCHEMAS[entity]

    body = dict(action.get("fields", {}))

    # Inject defaults
    for key, val in schema.get("defaults", {}).items():
        if key not in body:
            body[key] = val

    # Auto-generate missing values
    for field in schema.get("auto_generate", []):
        if field not in body:
            body[field] = generate_auto_value(field)

    # Resolve dependency refs → {"id": real_id}
    for field_name, ref_val in action.get("depends_on", {}).items():
        if isinstance(ref_val, list):
            body[field_name] = [{"id": ref_map[r]} for r in ref_val if r in ref_map]
        elif ref_val in ref_map:
            body[field_name] = {"id": ref_map[ref_val]}

    # Resolve endpoint (may have {id} placeholder)
    endpoint = schema["endpoint"]
    if "{id}" in endpoint:
        # For register_payment, the invoice ID comes from depends_on
        invoice_ref = action.get("depends_on", {}).get("invoice")
        if invoice_ref and invoice_ref in ref_map:
            endpoint = endpoint.replace("{id}", str(ref_map[invoice_ref]))

    # Build result
    result = {
        "method": schema["method"],
        "endpoint": endpoint,
    }

    if schema.get("use_query_params"):
        result["use_query_params"] = True
        result["params"] = body
    else:
        result["body"] = body

    return result


def _resolve_lookup_defaults(client: TripletexClient, actions: list[dict], ref_map: dict):
    """Insert GET lookups for entities that need dependencies not in the plan."""
    all_refs = {a["ref"] for a in actions}

    for action in actions:
        entity = action["entity"]
        schema = ENTITY_SCHEMAS.get(entity, {})
        lookup_defaults = schema.get("lookup_defaults", {})

        for field_name, endpoint in lookup_defaults.items():
            # Check if this field is already provided via depends_on
            dep_ref = action.get("depends_on", {}).get(field_name)
            if dep_ref and (dep_ref in all_refs or dep_ref in ref_map):
                continue

            # Need to look up a default
            logger.info(f"exec: lookup_default field={field_name} endpoint={endpoint}")
            result = client.get(endpoint, params={"fields": "id,name", "count": "1"})
            if result["success"] and result["body"].get("values"):
                default_id = result["body"]["values"][0]["id"]
                # Create a synthetic ref and inject into depends_on
                synth_ref = f"_lookup_{field_name}"
                ref_map[synth_ref] = default_id
                action.setdefault("depends_on", {})[field_name] = synth_ref


def _extract_id(result: dict) -> int | None:
    """Extract the entity ID from an API response."""
    body = result.get("body", {})
    if isinstance(body, dict):
        value = body.get("value", {})
        if isinstance(value, dict) and "id" in value:
            return value["id"]
    return None
