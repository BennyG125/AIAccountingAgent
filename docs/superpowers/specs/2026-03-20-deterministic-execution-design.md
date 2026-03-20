# Deterministic Execution Layer — Design Spec

## Problem

The current tool-use loop lets Gemini decide API calls dynamically. This leads to:
- Unnecessary calls (lookups for known constants, verification GETs after creates)
- 4xx errors from wrong field names or missing required fields
- Non-deterministic behavior — same prompt can produce different call counts

The competition scores efficiency (fewer calls + zero 4xx = bonus). We're leaving points on the table.

## Solution

Hybrid architecture: deterministic execution for known patterns, tool-use fallback for unknown.

```
Prompt → Gemini structured parse (1 LLM call) → Pattern match
  ├─ known    → Deterministic executor (code only, 0 LLM calls)
  └─ unknown  → Tool-use loop (current agent, Gemini decides calls)
```

## Flow

1. **Parse** — Gemini structured output extracts entities, actions, fields, dependencies from prompt (+ OCR via file_handler for PDF/image attachments). Single LLM call.
2. **Match** — Code checks: all entities in registry? Required fields present? Dependencies resolvable? If yes → deterministic. If no → fallback.
3. **Execute (deterministic)** — Topological sort on dependencies → build payloads from registry → execute in order → thread response IDs into dependent calls.
4. **Execute (fallback)** — Current tool-use loop with the parsed TaskPlan injected as context so Gemini has a head start.
5. **Error recovery** — If deterministic executor hits a 4xx, stop and hand off to tool-use loop with full context of what was already created and what failed.

## Structured Output Schema

Gemini returns a `TaskPlan`:

```json
{
  "actions": [
    {
      "action": "create",
      "entity": "department",
      "fields": {"name": "IT", "departmentNumber": "100"},
      "ref": "dep1",
      "depends_on": {}
    },
    {
      "action": "create",
      "entity": "employee",
      "fields": {"firstName": "Kari", "lastName": "Nordmann", "email": "kari@test.no"},
      "ref": "emp1",
      "depends_on": {"department": "dep1"}
    }
  ]
}
```

- **action**: `create`, `update`, `delete`, `find`, `register_payment`, `send_invoice`
- **entity**: `department`, `employee`, `customer`, `product`, `order`, `invoice`, `travel_expense`, `project`, `voucher`, `contact`
- **ref**: internal label for cross-action references
- **depends_on**: maps field name → ref. Executor replaces ref with `{"id": <real_id>}` at runtime.
- **fields**: uses actual API field names. Gemini is given the field list in the structured output prompt.

## Entity Registry (`task_registry.py`)

Static Python module (~200 lines) with three data structures:

**ENTITY_SCHEMAS** — per entity: endpoint, required fields, defaults, embeddable sub-entities.

```python
"employee": {
    "endpoint": "/employee",
    "required": ["firstName", "lastName", "userType", "department"],
    "defaults": {"userType": "STANDARD"},
}
"order": {
    "endpoint": "/order",
    "required": ["customer", "orderDate", "deliveryDate"],
    "embed": ["orderLines"],  # saves separate POST calls
}
```

**KNOWN_CONSTANTS** — injected automatically, never looked up via API.

```python
"vat_25": {"id": 3}, "vat_15": {"id": 5}, "vat_0": {"id": 6},
"nok": {"id": 1}, "norway": {"id": 162}
```

**DEPENDENCIES** — directed graph for topological sorting.

```python
"employee": ["department"], "order": ["customer", "product"],
"invoice": ["order"], "payment": ["invoice"],
"travel_expense": ["employee"], "project": ["employee"]
```

## Pattern Matcher (`planner.py`)

`is_known_pattern(task_plan)` returns True when:
1. All `action.entity` values are keys in `ENTITY_SCHEMAS`
2. All required fields present (after applying defaults from registry)
3. All `depends_on` refs resolve to other actions in the plan

If any check fails → tool-use fallback.

## Deterministic Executor (`executor.py`)

1. Topological sort actions by `depends_on`
2. For each action:
   - Look up schema from registry
   - Inject defaults and known constants
   - Replace dependency refs with real IDs from `ref_map`
   - Build exact API payload
   - Execute via TripletexClient
   - Store response ID in `ref_map[action.ref]`
3. On 4xx error: stop, return error context for fallback

Special cases handled in code:
- `register_payment` → PUT with query params, not body
- `order` → embed orderLines in POST body
- Missing dates → inject today
- Missing `departmentNumber` → auto-generate
- `voucher` → GET /ledger/account?number=X before POST

## Router (`agent.py`)

```python
def run_agent(prompt, file_contents, base_url, session_token):
    client = TripletexClient(base_url, session_token)
    task_plan = parse_prompt(prompt, file_contents)

    if is_known_pattern(task_plan):
        result = execute_plan(client, task_plan)
        if result["success"]:
            return {"status": "completed"}
        fallback_context = result["error_context"]
    else:
        fallback_context = task_plan

    return run_tool_loop(prompt, file_contents, client, fallback_context)
```

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `task_registry.py` | Create | Entity schemas, constants, dependency graph |
| `planner.py` | Create | Gemini structured output parse + pattern matcher |
| `executor.py` | Create | Deterministic executor with topo-sort + ref threading |
| `agent.py` | Modify | Router: deterministic → fallback. Current tool-use loop becomes `run_tool_loop()` |
| `main.py` | No change | Still calls `run_agent()` |

## Testing

- **task_registry.py** — unit tests: schema completeness, all competition entities covered, dependency graph is a valid DAG
- **planner.py** — unit tests: prompt → TaskPlan (mock Gemini structured output), pattern matcher accepts/rejects correctly
- **executor.py** — unit tests: TaskPlan → ordered API calls (mock TripletexClient), ref threading, error handoff
- **agent.py** — unit tests: routing logic (deterministic vs fallback)
- **Integration tests** — existing suite, expect fewer API calls and zero 4xx errors

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| LLM calls per task | 3-10 (tool-use iterations) | 1 (parse only) for known patterns |
| API calls | Model decides, often suboptimal | Minimum possible (computed) |
| 4xx errors | Model guesses fields wrong | Near zero (validated before execution) |
| Latency | 15-60s per task | 5-15s per task |
| Efficiency bonus | Low | Maximum |
