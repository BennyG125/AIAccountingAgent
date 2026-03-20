# Parse Fix + Registry Expansion — Design Spec

**Goal:** Fix the deterministic parse (empty `fields` bug) and expand the entity registry to cover all competition task categories, including update/delete/action patterns.

**Context:** The deterministic execution layer (Tasks 1-4, branch `feat/tool-use-agent`) works end-to-end but Gemini returns empty `fields` objects because the JSON schema lacks guidance. Additionally, the registry only covers 12 create-only entity types, missing 8 entity types and all action patterns needed for the full competition task set.

### Migration: consolidating lookup mechanisms

The existing codebase has two overlapping lookup mechanisms:
- `lookup_defaults` on employee schema + `_resolve_lookup_defaults()` in executor
- `lookup_constants_inject` on travel_expense_cost schema + `LOOKUP_CONSTANTS` dict

This spec **replaces both** with a single unified mechanism: `pre_lookups`. Migration:
- `employee.lookup_defaults: {"department": "/department"}` → `employee.pre_lookups: {"department": "/department"}`
- `travel_expense_cost.lookup_constants_inject` → `travel_expense_cost.pre_lookups`
- Remove `LOOKUP_CONSTANTS` dict (its entries move into `pre_lookups` on affected schemas)
- Remove `_resolve_lookup_defaults()` from executor (replaced by `_resolve_pre_lookups()`)
- The `lookup_defaults` and `lookup_constants_inject` keys are deleted from all schemas

---

## 1. Parse Fix

### Problem

`TASK_PLAN_SCHEMA` in `planner.py` defines:
```json
"fields": {"type": "object"}
```
No description, no property hints. Gemini structured output returns `{}` for every action's fields.

### Fix

**Schema change** — add description to `fields` and add `search_fields`:

```python
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
                    "fields": {
                        "type": "object",
                        "description": "Key-value map of API field names to values extracted from the prompt. Use exact Tripletex API field names (e.g., firstName, departmentNumber, priceExcludingVatCurrency). Include all values mentioned in the prompt."
                    },
                    "search_fields": {
                        "type": "object",
                        "description": "Fields to search for an existing entity (used with update/delete/action patterns). Maps API field names to search values."
                    },
                    "ref": {"type": "string"},
                    "depends_on": {"type": "object"},
                },
                "required": ["action", "entity", "fields", "ref", "depends_on"],
            },
        },
    },
    "required": ["actions"],
}
```

**Few-shot examples** — add 3 examples to `PARSE_SYSTEM_PROMPT`:

Example 1 (nb, simple create):
```
Prompt: "Opprett en avdeling med navn Salg og avdelingsnummer 200"
Output:
{"actions": [{"action": "create", "entity": "department", "fields": {"name": "Salg", "departmentNumber": "200"}, "search_fields": {}, "ref": "dep1", "depends_on": {}}]}
```

Example 2 (en, multi-step flow):
```
Prompt: "Create a customer Acme AS, create a product Consulting at 1500 NOK ex VAT, create an order with the product, invoice it, and register payment"
Output:
{"actions": [
  {"action": "create", "entity": "customer", "fields": {"name": "Acme AS"}, "search_fields": {}, "ref": "cust1", "depends_on": {}},
  {"action": "create", "entity": "product", "fields": {"name": "Consulting", "priceExcludingVatCurrency": 1500}, "search_fields": {}, "ref": "prod1", "depends_on": {}},
  {"action": "create", "entity": "order", "fields": {"orderLines": [{"count": 1, "unitPriceExcludingVatCurrency": 1500}]}, "search_fields": {}, "ref": "ord1", "depends_on": {"customer": "cust1", "product": "prod1"}},
  {"action": "create", "entity": "invoice", "fields": {}, "search_fields": {}, "ref": "inv1", "depends_on": {"orders": ["ord1"]}},
  {"action": "register_payment", "entity": "register_payment", "fields": {"paidAmount": 1500}, "search_fields": {}, "ref": "pay1", "depends_on": {"invoice": "inv1"}}
]}
```

Example 3 (de, single create):
```
Prompt: "Erstellen Sie einen Mitarbeiter namens Hans Müller mit E-Mail hans@test.de"
Output:
{"actions": [{"action": "create", "entity": "employee", "fields": {"firstName": "Hans", "lastName": "Müller", "email": "hans@test.de"}, "search_fields": {}, "ref": "emp1", "depends_on": {}}]}
```

### Parse prompt additions

Add to `PARSE_SYSTEM_PROMPT` after the field names section:

```
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
```

---

## 2. Registry Expansion

### Existing entity migrations (pre_lookups replaces old mechanisms)

```python
# task_registry.py — modify existing schemas

"employee": {
    ...
    # REMOVE: "lookup_defaults": {"department": "/department"},
    # ADD:
    "pre_lookups": {"department": "/department"},
},
"travel_expense_cost": {
    ...
    # REMOVE: "lookup_constants_inject": {"costCategory": ..., "paymentType": ...},
    # ADD:
    "pre_lookups": {
        "costCategory": "/travelExpense/costCategory",
        "paymentType": "/travelExpense/paymentType",
    },
},
```

Also remove `LOOKUP_CONSTANTS` dict entirely — `nok`, `norway`, and VAT IDs stay in `KNOWN_CONSTANTS`.

### New entity types (8 additions → 20 total)

```python
# task_registry.py additions

"employee_employment": {
    "endpoint": "/employee/employment",
    "method": "POST",
    "required": ["employee", "startDate"],
    "defaults": {"isMainEmployer": True},
    "auto_generate": ["startDate"],
},
"employee_employment_details": {
    "endpoint": "/employee/employment/details",
    "method": "POST",
    "required": ["employment", "date"],
    "defaults": {},
    "auto_generate": ["date"],
},
"supplier": {
    "endpoint": "/supplier",
    "method": "POST",
    "required": ["name"],
    "defaults": {},
},
"project_participant": {
    "endpoint": "/project/participant",
    "method": "POST",
    "required": ["project", "employee"],
    "defaults": {},
},
"travel_expense_per_diem": {
    "endpoint": "/travelExpense/perDiemCompensation",
    "method": "POST",
    "required": ["travelExpense", "rateCategory"],
    "defaults": {},
    "pre_lookups": {
        "rateCategory": "/travelExpense/rateCategory",
        "rateType": "/travelExpense/rate",
    },
},
"travel_expense_mileage": {
    "endpoint": "/travelExpense/mileageAllowance",
    "method": "POST",
    "required": ["travelExpense", "rateCategory", "date"],
    "defaults": {},
    "auto_generate": ["date"],
    "pre_lookups": {
        "rateCategory": "/travelExpense/rateCategory",
        "rateType": "/travelExpense/rate",
    },
},
"travel_expense_accommodation": {
    "endpoint": "/travelExpense/accommodationAllowance",
    "method": "POST",
    "required": ["travelExpense", "rateCategory"],
    "defaults": {},
    "pre_lookups": {
        "rateCategory": "/travelExpense/rateCategory",
    },
},
"order_line": {
    "endpoint": "/order/orderline",
    "method": "POST",
    "required": ["order", "product"],
    "defaults": {},
},
```

### Action schemas (new concept)

**Entity resolution rule:** For ALL action types, `action["entity"]` in the parsed plan is always
the base entity name from `ENTITY_SCHEMAS` (e.g., `"invoice"`, `"voucher"`, `"employee"`).
The planner is instructed to use the base entity name. Named actions like `send_invoice` use
`ACTION_SCHEMAS` only to determine the action endpoint and HTTP method — the entity's base
schema in `ENTITY_SCHEMAS` provides the search endpoint.

```python
# task_registry.py — new section

ACTION_SCHEMAS = {
    "update": {
        "flow": "search_put",
        "description": "Search for entity by search_fields, then PUT with merged fields",
    },
    "delete": {
        "flow": "search_delete",
        "description": "Search for entity by search_fields, then DELETE",
    },
    "send_invoice": {
        "entity": "invoice",
        "flow": "search_action",
        "action_endpoint": "/invoice/{id}/:send",
        "action_method": "PUT",
    },
    "create_credit_note": {
        "entity": "invoice",
        "flow": "search_action",
        "action_endpoint": "/invoice/{id}/:createCreditNote",
        "action_method": "PUT",
    },
    "reverse_voucher": {
        "entity": "voucher",
        "flow": "search_action",
        "action_endpoint": "/ledger/voucher/{id}/:reverse",
        "action_method": "PUT",
    },
    "grant_entitlements": {
        "entity": "employee",
        "flow": "search_action",
        "action_endpoint": "/employee/entitlement/:grantEntitlementsByTemplate",
        "action_method": "PUT",
        "action_params_from_search": {"employeeId": "id"},
        # Note: this endpoint uses query params, not {id} in path.
        # The executor passes employeeId as a query param from the searched entity's id.
    },
}
```

### Search field mapping

Each entity type that supports search needs a mapping from field names to query parameters:

```python
SEARCH_PARAMS = {
    "department": {"name": "name", "departmentNumber": "departmentNumber"},
    "employee": {"firstName": "firstName", "lastName": "lastName", "email": "email"},
    "customer": {"name": "name", "email": "email", "organizationNumber": "organizationNumber"},
    "product": {"name": "name", "number": "number"},
    "order": {"customerName": "customerName", "number": "number"},
    "invoice": {"customerId": "customerId", "invoiceNumber": "invoiceNumber"},
    "supplier": {"name": "name", "organizationNumber": "organizationNumber"},
    "contact": {"firstName": "firstName", "lastName": "lastName", "email": "email"},
    "project": {"name": "name", "number": "number"},
    "voucher": {"number": "number", "dateFrom": "dateFrom", "dateTo": "dateTo"},
    "travel_expense": {"employeeId": "employeeId"},
}
```

### Updated dependency graph

```python
DEPENDENCIES = {
    # existing
    "department": [],
    "employee": ["department"],
    "customer": [],
    "product": [],
    "contact": ["customer"],
    "order": ["customer", "product"],
    "order_line": ["order", "product"],
    "invoice": ["order"],
    "register_payment": ["invoice"],
    "travel_expense": ["employee"],
    "travel_expense_cost": ["travel_expense"],
    "project": ["employee"],
    "voucher": [],
    # new
    "supplier": [],
    "employee_employment": ["employee"],
    "employee_employment_details": ["employee_employment"],
    "project_participant": ["project", "employee"],
    "travel_expense_per_diem": ["travel_expense"],
    "travel_expense_mileage": ["travel_expense"],
    "travel_expense_accommodation": ["travel_expense"],
}
```

---

## 3. Executor Changes

### New capability: `_resolve_pre_lookups()`

Before execution, scan actions for entities with `pre_lookups` in their schema. For each, issue a GET to the lookup endpoint, cache the first result's ID, and inject it into the action's fields.

```python
def _resolve_pre_lookups(client, actions, ref_map, lookup_cache):
    """GET lookup endpoints for entities that need runtime constants."""
    for action in actions:
        schema = ENTITY_SCHEMAS.get(action["entity"], {})
        for field_name, endpoint in schema.get("pre_lookups", {}).items():
            if field_name in lookup_cache:
                continue
            result = client.get(endpoint, params={"count": "1", "fields": "id,name"})
            if result["success"] and result["body"].get("values"):
                lookup_cache[field_name] = result["body"]["values"][0]["id"]
    # Inject cached IDs into action fields
    for action in actions:
        schema = ENTITY_SCHEMAS.get(action["entity"], {})
        for field_name in schema.get("pre_lookups", {}):
            if field_name in lookup_cache and field_name not in action.get("fields", {}):
                action.setdefault("fields", {})[field_name] = {"id": lookup_cache[field_name]}
```

### New capability: `_resolve_by_search()`

For update/delete/action patterns, search for the entity first.
Uses `SEARCH_PARAMS` to translate field names to query parameter names.

```python
def _resolve_by_search(client, action) -> dict | None:
    """GET search for an existing entity. Returns {id, version, ...} or None."""
    entity = action["entity"]
    search_fields = action.get("search_fields", {})
    if not search_fields:
        return None

    # Get search endpoint from entity schema
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
```

### Action dispatch in `execute_plan()`

Extend the main loop to handle action types. `_build_payload()` is only called for
create/register_payment/lookup actions. Update/delete/named actions construct payloads inline.

Note: DELETE responses have no body, so `_extract_id()` returns None — this is expected.
The deleted entity's ref will not appear in ref_map, which is correct.

```python
action_type = action.get("action")

if action_type in ("create", "register_payment", "lookup"):
    # existing create flow — uses _build_payload()
    payload = _build_payload(action, ref_map)
    ...

elif action_type == "update":
    found = _resolve_by_search(client, action)
    if not found:
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

elif action_type == "delete":
    found = _resolve_by_search(client, action)
    if not found:
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

elif action_type in ACTION_SCHEMAS:
    action_schema = ACTION_SCHEMAS[action_type]
    found = _resolve_by_search(client, action)
    if not found:
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
    # Handle endpoints that use query params instead of {id} in path
    params = None
    if "action_params_from_search" in action_schema:
        params = {
            param: found[source_field]
            for param, source_field in action_schema["action_params_from_search"].items()
        }
    if action_schema["action_method"] == "PUT":
        result = client.put(endpoint, body=body, params=params)
    elif action_schema["action_method"] == "DELETE":
        result = client.delete(endpoint)
```

### Pattern matcher: full updated `is_known_pattern()`

Replaces the existing function in `planner.py`:

```python
DETERMINISTIC_ACTIONS = {
    "create", "register_payment", "lookup",
    "update", "delete",
    "send_invoice", "create_credit_note", "reverse_voucher", "grant_entitlements",
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
            if not action.get("search_fields"):
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
```

### Tests that need updating

The following existing tests will change behavior and must be updated:
- `tests/test_planner.py::TestIsKnownPattern::test_rejects_update_action` → now returns True (update with search_fields)
- `tests/test_planner.py::TestIsKnownPattern::test_rejects_delete_action` → now returns True (delete with search_fields)

New tests replace them:
- `test_rejects_update_without_search_fields` → update with empty search_fields returns False
- `test_rejects_delete_without_search_fields` → delete with empty search_fields returns False
- `test_accepts_update_with_search_fields` → update with search_fields returns True
- `test_accepts_delete_with_search_fields` → delete with search_fields returns True
- `test_accepts_named_action` → send_invoice with correct entity + search_fields returns True
- `test_rejects_named_action_wrong_entity` → send_invoice with entity="department" returns False

---

## 4. Complete API Coverage Tracking

### All Tripletex endpoints vs coverage status

| Endpoint | Registry Entity | Det. Path | Fallback |
|---|---|---|---|
| POST /department | `department` | create | yes |
| PUT /department/{id} | `department` | update | yes |
| DELETE /department/{id} | `department` | delete | yes |
| POST /employee | `employee` | create | yes |
| PUT /employee/{id} | `employee` | update | yes |
| POST /employee/employment | `employee_employment` | create | yes |
| POST /employee/employment/details | `employee_employment_details` | create | yes |
| PUT /employee/entitlement/:grant... | — | grant_entitlements | yes |
| POST /customer | `customer` | create | yes |
| PUT /customer/{id} | `customer` | update | yes |
| DELETE /customer/{id} | `customer` | delete | yes |
| POST /contact | `contact` | create | yes |
| PUT /contact/{id} | `contact` | update | yes |
| POST /product | `product` | create | yes |
| PUT /product/{id} | `product` | update | yes |
| DELETE /product/{id} | `product` | delete | yes |
| POST /supplier | `supplier` | create | yes |
| PUT /supplier/{id} | `supplier` | update | yes |
| DELETE /supplier/{id} | `supplier` | delete | yes |
| POST /order | `order` | create | yes |
| PUT /order/{id} | `order` | update | yes |
| DELETE /order/{id} | `order` | delete | yes |
| POST /order/orderline | `order_line` | create | yes |
| POST /invoice | `invoice` | create | yes |
| PUT /invoice/{id}/:payment | `register_payment` | create | yes |
| PUT /invoice/{id}/:send | — | send_invoice | yes |
| PUT /invoice/{id}/:createCreditNote | — | create_credit_note | yes |
| POST /travelExpense | `travel_expense` | create | yes |
| DELETE /travelExpense/{id} | `travel_expense` | delete | yes |
| POST /travelExpense/cost | `travel_expense_cost` | create | yes |
| POST /travelExpense/perDiemCompensation | `travel_expense_per_diem` | create | yes |
| POST /travelExpense/mileageAllowance | `travel_expense_mileage` | create | yes |
| POST /travelExpense/accommodationAllowance | `travel_expense_accommodation` | create | yes |
| POST /project | `project` | create | yes |
| PUT /project/{id} | `project` | update | yes |
| DELETE /project/{id} | `project` | delete | yes |
| POST /project/participant | `project_participant` | create | yes |
| POST /ledger/voucher | `voucher` | create | yes |
| PUT /ledger/voucher/{id}/:reverse | — | reverse_voucher | yes |
| DELETE /ledger/voucher/{id} | `voucher` | delete | yes |
| GET /ledger/account | — | (pre-lookup) | yes |
| GET /travelExpense/costCategory | — | (pre-lookup) | yes |
| GET /travelExpense/paymentType | — | (pre-lookup) | yes |
| GET /travelExpense/rateCategory | — | (pre-lookup) | yes |
| GET /travelExpense/rate | — | (pre-lookup) | yes |
| GET /invoice/paymentType | — | (pre-lookup) | yes |
| GET /country, /currency, /municipality | — | — | yes |
| POST /salary/transaction | — | — | yes |
| GET /company, PUT /company | — | — | yes |

**Coverage: 35 endpoints deterministic, all endpoints via fallback.**

---

## 5. File Changes Summary

| File | Action | What changes |
|---|---|---|
| `planner.py` | Modify | Schema description + search_fields, few-shot examples, action types in prompt |
| `task_registry.py` | Modify | 8 new entities, ACTION_SCHEMAS, SEARCH_PARAMS, pre_lookups, updated DEPENDENCIES |
| `executor.py` | Modify | `_resolve_pre_lookups()`, `_resolve_by_search()`, action dispatch in execute_plan |
| `tests/test_task_registry.py` | Modify | Tests for new entities, ACTION_SCHEMAS, SEARCH_PARAMS |
| `tests/test_planner.py` | Modify | Tests for updated schema, action patterns in is_known_pattern |
| `tests/test_executor.py` | Modify | Tests for pre_lookups, search-then-act, update/delete dispatch |
| `docs/architecture-decisions.md` | Create | 10 ADRs covering all architectural decisions |
| `smoke_test.py` | Modify | Add Tier 2 + action pattern test cases |

---

## 6. Test Plan

### Parse tests (test_planner.py)
- Verify fields populated for simple create, multi-step, update, delete
- Verify search_fields populated for update/delete actions

### Registry tests (test_task_registry.py)
- 20 entities have required keys (endpoint, method, required)
- No DAG cycles in expanded DEPENDENCIES
- ACTION_SCHEMAS keys are valid, each has flow + action_endpoint/action_method
- SEARCH_PARAMS covers all entities that support update/delete
- `pre_lookups` replaces old `lookup_constants_inject` and `lookup_defaults` — verify neither exists

### Executor tests (test_executor.py)
- `_resolve_pre_lookups()` injects IDs from GET results into action fields
- `_resolve_pre_lookups()` caches — second call for same field skips GET
- `_resolve_by_search()` translates field names via SEARCH_PARAMS
- `_resolve_by_search()` returns None when no results
- Update dispatch: searches, merges fields, PUTs with version
- Delete dispatch: searches, DELETEs, `_extract_id()` returns None (expected)
- Named action dispatch: searches, substitutes {id}, PUTs action endpoint
- `grant_entitlements` dispatch: passes employeeId as query param
- Search-not-found returns FallbackContext with descriptive error

### Pattern matcher tests (test_planner.py) — updated
- `test_rejects_update_action` → **replaced by** `test_rejects_update_without_search_fields`
- `test_rejects_delete_action` → **replaced by** `test_rejects_delete_without_search_fields`
- New: `test_accepts_update_with_search_fields`
- New: `test_accepts_delete_with_search_fields`
- New: `test_accepts_named_action` (send_invoice)
- New: `test_rejects_named_action_wrong_entity`

### Smoke tests (smoke_test.py)
- All Tier 1 tasks pass (4 entity types + 2 multilingual)
- Tier 2 flows: invoice flow, travel expense, project
- Action patterns: update customer, delete department

### Regression
- Existing tests updated where behavior intentionally changes (2 planner tests)
- All other existing tests unaffected
