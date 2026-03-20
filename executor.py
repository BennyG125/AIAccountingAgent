# executor.py
"""Deterministic executor — runs a validated TaskPlan against the Tripletex API.

Takes a TaskPlan (from planner.py), topologically sorts actions by dependencies,
builds payloads from the entity registry, and executes API calls in order —
threading response IDs into subsequent calls.

Supports: create, update, delete, named actions (send_invoice, approve_travel_expense, etc.),
auto-batching via bulk endpoints, and pre-lookups for runtime constants.
"""

import logging
import time
from collections import defaultdict

from task_registry import (
    ENTITY_SCHEMAS, KNOWN_CONSTANTS, generate_auto_value,
    ACTION_SCHEMAS, BULK_ENDPOINTS, SEARCH_PARAMS,
)
from planner import FallbackContext
from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)


def execute_plan(client: TripletexClient, task_plan: dict) -> dict:
    """Execute a TaskPlan deterministically. Returns success or FallbackContext."""
    actions = _topological_sort(task_plan["actions"])
    ref_map: dict[str, int] = {}  # ref label → real API id
    total_api_calls = 0
    start = time.time()

    # Resolve pre-lookups before execution (replaces old _resolve_lookup_defaults)
    lookup_cache: dict[str, int] = {}
    _resolve_pre_lookups(client, actions, ref_map, lookup_cache)

    # Auto-batch independent creates of the same entity type
    actions = _auto_batch(actions)

    for i, action in enumerate(actions):
        step = f"{i + 1}/{len(actions)}"
        action_type = action.get("action")

        # ---- Create / register_payment / lookup (existing flow) ----
        if action_type in ("create", "register_payment", "lookup"):
            # Pre-check: reuse existing entity if unique fields match
            if action_type == "create":
                schema = ENTITY_SCHEMAS.get(action["entity"], {})
                existing_id = _check_existing(client, action, schema)
                if existing_id is not None:
                    ref_map[action["ref"]] = existing_id
                    logger.info(f"exec: step={step} reused_existing ref={action['ref']} id={existing_id}")
                    total_api_calls += 1
                    continue

            payload = _build_payload(action, ref_map)

            # Grant PM entitlements before project creation
            if action["entity"] == "project" and "projectManager" in payload.get("body", {}):
                pm = payload["body"]["projectManager"]
                pm_id = pm.get("id") if isinstance(pm, dict) else pm
                if pm_id:
                    logger.info(f"exec: granting PM entitlements to employee {pm_id}")
                    client.put("/employee/entitlement/:grantEntitlementsByTemplate",
                               params={"employeeId": str(pm_id)})
                    total_api_calls += 1

            method = payload["method"]
            endpoint = payload["endpoint"]
            logger.info(f"exec: step={step} method={method} endpoint={endpoint} ref={action['ref']}")

            call_start = time.time()
            if payload.get("use_query_params"):
                result = client.put(endpoint, params=payload.get("params"))
            elif method == "POST":
                result = client.post(endpoint, body=payload.get("body"))
                # Retry without vatType if sandbox rejects it (not VAT-registered)
                if not result["success"] and result.get("status_code") == 422:
                    error_msgs = result.get("body", {}).get("validationMessages", [])
                    if any("mva-kode" in (m.get("message", "") or "").lower() for m in error_msgs):
                        body = payload.get("body", {})
                        if "vatType" in body:
                            logger.info(f"exec: step={step} retrying without vatType (sandbox rejects mva-kode)")
                            del body["vatType"]
                            result = client.post(endpoint, body=body)
                            total_api_calls += 1
            elif method == "PUT":
                result = client.put(endpoint, body=payload.get("body"), params=payload.get("params"))
            elif method == "GET":
                result = client.get(endpoint, params=payload.get("params"))
            else:
                result = {"success": False, "error": f"Unsupported method: {method}"}

        # ---- Update (search + PUT) ----
        elif action_type == "update":
            logger.info(f"exec: step={step} action=update entity={action['entity']} ref={action['ref']}")
            call_start = time.time()
            found = _resolve_by_search(client, action)
            if not found:
                total_ms = int((time.time() - start) * 1000)
                logger.warning(f"exec: step={step} search_not_found entity={action['entity']}")
                return {
                    "success": False,
                    "fallback_context": FallbackContext(
                        task_plan=task_plan,
                        completed_refs=dict(ref_map),
                        failed_action=action,
                        error=f"Search returned 0 results for {action.get('search_fields')}",
                    ),
                }
            schema = ENTITY_SCHEMAS[action["entity"]]
            merged = {**found, **action.get("fields", {})}
            result = client.put(f"{schema['endpoint']}/{found['id']}", body=merged)

        # ---- Delete (search + DELETE) ----
        elif action_type == "delete":
            logger.info(f"exec: step={step} action=delete entity={action['entity']} ref={action['ref']}")
            call_start = time.time()
            found = _resolve_by_search(client, action)
            if not found:
                total_ms = int((time.time() - start) * 1000)
                logger.warning(f"exec: step={step} search_not_found entity={action['entity']}")
                return {
                    "success": False,
                    "fallback_context": FallbackContext(
                        task_plan=task_plan,
                        completed_refs=dict(ref_map),
                        failed_action=action,
                        error=f"Search returned 0 results for {action.get('search_fields')}",
                    ),
                }
            schema = ENTITY_SCHEMAS[action["entity"]]
            result = client.delete(f"{schema['endpoint']}/{found['id']}")

        # ---- Batch create (auto-batched by _auto_batch) ----
        elif action_type == "create_batch":
            entity = action["entity"]
            endpoint = BULK_ENDPOINTS[entity]
            logger.info(f"exec: step={step} action=create_batch entity={entity} count={len(action['batch_items'])} ref={action['ref']}")
            call_start = time.time()
            bodies = []
            for item in action["batch_items"]:
                payload = _build_payload(item, ref_map)
                bodies.append(payload.get("body", {}))
            result = client.post(endpoint, body=bodies)
            if result["success"]:
                values = result["body"].get("values", [])
                for item, value in zip(action["batch_items"], values):
                    if isinstance(value, dict) and "id" in value:
                        ref_map[item["ref"]] = value["id"]

        # ---- Named actions (send_invoice, approve_travel_expense, etc.) ----
        elif action_type in ACTION_SCHEMAS:
            action_schema = ACTION_SCHEMAS[action_type]
            logger.info(f"exec: step={step} action={action_type} entity={action['entity']} ref={action['ref']}")
            call_start = time.time()
            found = _resolve_by_search(client, action)
            if not found:
                total_ms = int((time.time() - start) * 1000)
                logger.warning(f"exec: step={step} search_not_found action={action_type}")
                return {
                    "success": False,
                    "fallback_context": FallbackContext(
                        task_plan=task_plan,
                        completed_refs=dict(ref_map),
                        failed_action=action,
                        error=f"Search returned 0 results for {action.get('search_fields')}",
                    ),
                }
            endpoint = action_schema["action_endpoint"].replace("{id}", str(found["id"]))
            body = action.get("fields", {}) or None
            params = None
            if "action_params_from_search" in action_schema:
                params = {
                    param: found[source_field]
                    for param, source_field in action_schema["action_params_from_search"].items()
                }
            if action_schema.get("body_from_search"):
                body = [{"id": found["id"]}]
            if action_schema["action_method"] == "PUT":
                result = client.put(endpoint, body=body, params=params)
            elif action_schema["action_method"] == "POST":
                result = client.post(endpoint, body=body)
            elif action_schema["action_method"] == "DELETE":
                result = client.delete(endpoint)
            else:
                result = {"success": False, "error": f"Unsupported action method: {action_schema['action_method']}"}

        else:
            logger.warning(f"exec: step={step} unsupported_action={action_type}")
            result = {"success": False, "error": f"Unsupported action: {action_type}"}
            call_start = time.time()

        call_ms = int((time.time() - call_start) * 1000)
        total_api_calls += 1

        if not result["success"]:
            error_msg = result.get("error", str(result.get("body", "")))
            logger.warning(f"exec: step={step} action={action_type} "
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

        # Extract created entity ID (for create and named actions)
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

    # Wrap bare values in {"id": X} for object reference fields
    for field in schema.get("object_ref_fields", []):
        if field in body and not isinstance(body[field], dict):
            body[field] = {"id": body[field]}

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


def _resolve_pre_lookups(client: TripletexClient, actions: list[dict],
                         ref_map: dict, lookup_cache: dict):
    """GET lookup endpoints for entities that need runtime constants.

    Replaces the old _resolve_lookup_defaults() and _resolve_lookup_constants_inject().
    Unified: all lookups go through pre_lookups on entity schemas.
    """
    # Phase 1: Fetch all needed lookups (deduplicated via cache)
    for action in actions:
        schema = ENTITY_SCHEMAS.get(action["entity"], {})
        for field_name, endpoint in schema.get("pre_lookups", {}).items():
            if field_name in lookup_cache:
                continue
            # Skip if the field is already set by the user
            if field_name in action.get("fields", {}):
                continue
            logger.info(f"exec: pre_lookup field={field_name} endpoint={endpoint}")
            result = client.get(endpoint, params={"count": "1", "fields": "id,name"})
            if result["success"] and result["body"].get("values"):
                lookup_cache[field_name] = result["body"]["values"][0]["id"]

    # Phase 2: Inject cached IDs into action fields
    for action in actions:
        schema = ENTITY_SCHEMAS.get(action["entity"], {})
        for field_name in schema.get("pre_lookups", {}):
            if field_name in lookup_cache and field_name not in action.get("fields", {}):
                action.setdefault("fields", {})[field_name] = {"id": lookup_cache[field_name]}


def _resolve_by_search(client: TripletexClient, action: dict) -> dict | None:
    """GET search for an existing entity. Returns {id, version, ...} or None."""
    entity = action["entity"]
    search_fields = action.get("search_fields", {})
    if not search_fields:
        return None

    schema = ENTITY_SCHEMAS.get(entity, {})
    endpoint = schema.get("endpoint", "")

    # Translate field names to query params using SEARCH_PARAMS
    param_mapping = SEARCH_PARAMS.get(entity, {})
    params = {"fields": "*", "count": "1"}
    for field_name, value in search_fields.items():
        query_param = param_mapping.get(field_name, field_name)
        params[query_param] = value

    result = client.get(endpoint, params=params)
    if result["success"] and result["body"].get("values"):
        return result["body"]["values"][0]
    return None


def _auto_batch(actions: list[dict]) -> list[dict]:
    """Merge same-type creates with no cross-deps into batch actions.

    E.g., 3 independent employee creates → 1 batch action using POST /employee/list.
    Only batches entity types that have BULK_ENDPOINTS entries.
    Actions that depend on each other (via depends_on refs) are NOT batched.
    """
    groups = defaultdict(list)
    for action in actions:
        if action.get("action") == "create" and action["entity"] in BULK_ENDPOINTS:
            groups[action["entity"]].append(action)

    if not groups:
        return actions

    batched = []
    batched_refs = set()
    for entity, group_actions in groups.items():
        group_refs = {a["ref"] for a in group_actions}
        independent = []
        for a in group_actions:
            dep_refs = set()
            for v in a.get("depends_on", {}).values():
                if isinstance(v, list):
                    dep_refs.update(v)
                else:
                    dep_refs.add(v)
            if not dep_refs.intersection(group_refs):
                independent.append(a)

        if len(independent) >= 2:
            batch_action = {
                "action": "create_batch",
                "entity": entity,
                "batch_items": independent,
                "ref": f"_batch_{entity}",
                "depends_on": {},
            }
            batched.append(batch_action)
            batched_refs.update(a["ref"] for a in independent)

    result = [a for a in actions if a["ref"] not in batched_refs]
    result.extend(batched)
    return result


def _check_existing(client: TripletexClient, action: dict, schema: dict) -> int | None:
    """Check if entity already exists by unique fields. Returns existing ID or None."""
    unique_checks = schema.get("unique_check_fields", {})
    if not unique_checks:
        return None

    fields = action.get("fields", {})
    endpoint = schema["endpoint"]

    for field_name, query_param in unique_checks.items():
        value = fields.get(field_name)
        if not value:
            continue
        # Unwrap {"id": X} to bare value for search
        if isinstance(value, dict) and "id" in value:
            value = value["id"]
        result = client.get(endpoint, params={query_param: str(value), "count": "1", "fields": "id"})
        if result["success"] and result["body"].get("values"):
            existing_id = result["body"]["values"][0]["id"]
            logger.info(f"exec: found_existing entity={action['entity']} field={field_name} value={value} id={existing_id}")
            return existing_id

    return None


def _extract_id(result: dict) -> int | None:
    """Extract the entity ID from an API response."""
    body = result.get("body", {})
    if isinstance(body, dict):
        value = body.get("value", {})
        if isinstance(value, dict) and "id" in value:
            return value["id"]
    return None
