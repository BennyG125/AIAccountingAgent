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
2. **Match** — Code checks: all entities in registry? Required fields present? Dependencies resolvable? Action type supported? If yes → deterministic. If no → fallback.
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

### Action types

**Deterministic path supports:**
- `create` — POST to entity endpoint
- `register_payment` — PUT /invoice/{id}/:payment with query params
- `lookup` — GET to resolve an existing entity ID (for voucher accounts, or when update/delete needs an ID)

**Fallback only (always routes to tool-use loop):**
- `update`, `delete`, `find`, `send_invoice` — these require searching for existing entities with unpredictable state. The deterministic path cannot guarantee correct behavior.

### Field conventions

- **ref**: internal label for cross-action references
- **depends_on**: maps field name → ref. Executor replaces ref with `{"id": <real_id>}` at runtime.
- **Array dependencies**: for fields like `orders` (invoice), use `"orders": ["order1"]` — array of refs. Executor maps to `[{"id": <real_id>}]`.
- **fields**: uses actual API field names. Gemini is given the field list in the parse prompt.

## Parse Prompt

The Gemini structured output call uses a dedicated prompt (not the cheat sheet):

```
You are a task parser for the Tripletex accounting API.

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
- travel_expense: employee, title
- travel_expense_cost: travelExpense, date, amountCurrencyIncVat, costCategory, paymentType, currency
- project: name, projectManager, startDate
- voucher: date, description, postings[{accountNumber, amount}] (accountNumber is the chart-of-accounts number like 1920, not the API id — the executor looks up the id)
- contact: firstName, lastName, email, customer

For tasks involving sending invoices, deleting entities, or modifying existing records,
output action="update"/"delete"/"send_invoice" — these will be handled by the fallback path.

Output the TaskPlan JSON. Use "ref" labels (dep1, emp1, cust1, etc.) for
cross-references. Set depends_on to map field names to refs.
```

The response schema is enforced via Gemini's `response_schema` parameter so we get guaranteed valid JSON.

## Entity Registry (`task_registry.py`)

Static Python module (~250 lines) with four data structures:

**ENTITY_SCHEMAS** — per entity: endpoint, HTTP method, required fields, optional fields, defaults, embeddable sub-entities.

```python
"department": {
    "endpoint": "/department",
    "method": "POST",
    "required": ["name", "departmentNumber"],
    "defaults": {},
    "auto_generate": ["departmentNumber"],  # generate sequential string "100", "101", etc.
}
"employee": {
    "endpoint": "/employee",
    "method": "POST",
    "required": ["firstName", "lastName", "userType", "department"],
    "defaults": {"userType": "STANDARD"},
    "lookup_defaults": {"department": "/department"},  # GET first if not in plan
}
"order": {
    "endpoint": "/order",
    "method": "POST",
    "required": ["customer", "orderDate", "deliveryDate"],
    "defaults": {},  # orderDate/deliveryDate default to today if missing
    "auto_generate": ["orderDate", "deliveryDate"],
    "embed": ["orderLines"],
}
"register_payment": {
    "endpoint": "/invoice/{id}/:payment",
    "method": "PUT",
    "use_query_params": True,  # params not body
    "required": ["paymentDate", "paidAmount", "paidAmountCurrency"],
    "defaults": {"paidAmountCurrency": 1, "paymentTypeId": 0},
}
"travel_expense_cost": {
    "endpoint": "/travelExpense/cost",
    "method": "POST",
    "required": ["travelExpense", "date", "amountCurrencyIncVat", "costCategory", "paymentType"],
    "defaults": {"currency": {"id": 1}},
    "lookup_constants_inject": {  # GET once, cache, inject into payload
        "costCategory": "/travelExpense/costCategory",
        "paymentType": "/travelExpense/paymentType",
    },
}
```

**KNOWN_CONSTANTS** — injected automatically, never looked up via API.

```python
"vat_25": {"id": 3}, "vat_15": {"id": 5}, "vat_0": {"id": 6},
"nok": {"id": 1}, "norway": {"id": 162},
"paymentTypeId_default": 0,
```

**LOOKUP_CONSTANTS** — values that require one GET call but are stable per sandbox. Cached after first lookup.

```python
"costCategory": "/travelExpense/costCategory",   # for travel expense costs
"paymentType_travel": "/travelExpense/paymentType",  # for travel expense costs
"rateCategory": "/travelExpense/rateCategory",   # for mileage/per diem
```

**DEPENDENCIES** — directed graph for topological sorting.

```python
"employee":            ["department"],
"contact":             ["customer"],
"order":               ["customer", "product"],
"invoice":             ["order"],
"register_payment":    ["invoice"],
"travel_expense":      ["employee"],
"travel_expense_cost": ["travel_expense"],
"project":             ["employee"],  # employee = projectManager
"voucher":             [],  # account lookups handled via lookup actions
```

## Pattern Matcher (`planner.py`)

`is_known_pattern(task_plan)` returns True when:
1. All `action.action` values are in `{"create", "register_payment", "lookup"}`
2. All `action.entity` values are keys in `ENTITY_SCHEMAS`
3. All required fields present (after applying defaults + auto_generate from registry)
4. All `depends_on` refs resolve to other actions in the plan OR have `lookup_defaults`

If any check fails → tool-use fallback. This means `update`, `delete`, `find`, `send_invoice` always go to fallback.

## Deterministic Executor (`executor.py`)

1. Topological sort actions by `depends_on`
2. Resolve `lookup_defaults` — if an action needs a dependency not in the plan (e.g., employee needs department but no department action exists), insert a GET lookup
3. Resolve `lookup_constants` — if travel expense costs need costCategory/paymentType, GET and cache them
4. For each action:
   - Look up schema from registry
   - Inject defaults, known constants, auto-generated values (today's date, dept numbers)
   - Replace dependency refs with real IDs from `ref_map`
   - For array deps: map list of refs → list of `{"id": N}`
   - Build exact API payload (body or query params based on schema)
   - Execute via TripletexClient
   - Store response ID in `ref_map[action.ref]`
5. On 4xx error: stop, return `FallbackContext` for handoff

### FallbackContext

Unified structure used by both fallback triggers (pattern-match failure and execution failure):

```python
@dataclass
class FallbackContext:
    task_plan: dict | None = None          # parsed TaskPlan (None if parse timed out)
    completed_refs: dict = field(default_factory=dict)  # ref → real ID
    failed_action: dict | None = None      # the action that failed
    error: str | None = None               # API error message
```

The tool-use loop injects this into its system prompt (guarding for None values):
- If `completed_refs`: "These entities were already created: {completed_refs}"
- If `failed_action` and `error`: "This action failed with error: {error}. Fix and continue."
- If `task_plan`: "Here is the parsed task plan for context: {task_plan}"
- If all None: no extra context, tool-use loop runs with raw prompt only

## Timeout Budget

Total: 300s hard limit.

| Phase | Budget | Action if exceeded |
|-------|--------|--------------------|
| Parse (Gemini structured output) | ≤ 20s | Fall back to tool-use with raw prompt |
| Deterministic execution | ≤ 60s | Stop, hand off remaining to tool-use |
| Tool-use fallback | Remainder (~220s+) | Existing timeout logic (270s guard) |

## Router (`agent.py`)

```python
def run_agent(prompt, file_contents, base_url, session_token):
    client = TripletexClient(base_url, session_token)

    # Step 1: Parse (with timeout)
    task_plan = parse_prompt(prompt, file_contents)  # may return None on timeout/error

    if task_plan and is_known_pattern(task_plan):
        # Step 2: Deterministic execution
        result = execute_plan(client, task_plan)
        if result["success"]:
            return {"status": "completed"}
        fallback_ctx = result["fallback_context"]
    else:
        fallback_ctx = FallbackContext(task_plan=task_plan, completed_refs={})

    # Step 3: Tool-use fallback
    return run_tool_loop(prompt, file_contents, client, fallback_ctx)
```

Note: `main.py` is unchanged — it still calls `run_agent()` with the same signature. The `_preconfigure_bank_account` call in `main.py` runs independently before `run_agent`.

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `task_registry.py` | Create | Entity schemas, constants, lookup constants, dependency graph |
| `planner.py` | Create | Gemini structured output parse + pattern matcher |
| `executor.py` | Create | Deterministic executor with topo-sort, ref threading, lookup resolution |
| `agent.py` | Modify | Router: parse → match → deterministic or fallback. Current loop becomes `run_tool_loop()` |
| `main.py` | No change | Still calls `run_agent()` with same signature |

## Testing

- **task_registry.py** — unit tests: schema completeness for all competition entities, dependency graph is valid DAG, no cycles
- **planner.py** — unit tests: mock Gemini structured output → TaskPlan parsing, pattern matcher accepts known patterns (create chains), rejects unknown (update, delete)
- **planner.py** — golden-set eval: 7 sample prompts (one per language) → expected TaskPlan. Validates parse quality.
- **executor.py** — unit tests: TaskPlan → ordered API calls (mock TripletexClient), ref threading for single and array deps, auto-generated dates, lookup_defaults insertion, error handoff with correct FallbackContext
- **agent.py** — unit tests: routing logic (deterministic path, pattern-match fallback, execution-failure fallback)
- **Integration tests** — existing suite with verification, expect fewer API calls and zero 4xx errors
- **Fallback handoff test** — executor partially completes, verify tool-use loop receives correct FallbackContext and can continue

## Logging

Structured logging throughout for full observability in production (Cloud Run → GCP Cloud Logging).

### What we log

**Incoming request:**
```
INFO  solve: prompt_length=54 files=0 has_credentials=true
```

**Parse phase:**
```
INFO  parse: task_plan_actions=2 entities=[department,employee] parse_time_ms=3200
INFO  parse: action ref=dep1 action=create entity=department fields={name,departmentNumber}
INFO  parse: action ref=emp1 action=create entity=employee depends_on={department:dep1}
```

**Pattern match:**
```
INFO  match: result=deterministic|fallback reason=<why fallback if applicable>
```

**Deterministic executor (per API call):**
```
INFO  exec: step=1/5 method=POST endpoint=/department ref=dep1
INFO  exec: step=1/5 status=201 success=true ref=dep1 id=12345 time_ms=340
```

**On error (include response body):**
```
WARN  exec: step=3/5 method=POST endpoint=/employee status=422 error="Validering feilet." body={...}
INFO  exec: fallback_triggered completed_refs={dep1:12345,cust1:501} failed_action=emp1
```

**Tool-use fallback:**
```
INFO  fallback: reason=execution_error|pattern_mismatch context_refs=2
INFO  fallback: iteration=1 tool=tripletex_post path=/employee
INFO  fallback: iteration=1 status=201 success=true
INFO  fallback: completed iterations=3
```

**Parse timeout/error:**
```
WARN  parse: timeout after 20s, falling back to tool-use with raw prompt
WARN  parse: error="<exception>" falling back to tool-use with raw prompt
```

**Summary (always, final log line):**
```
INFO  result: status=completed path=deterministic|fallback|deterministic+fallback total_api_calls=5 errors_4xx=0 llm_calls=1 total_time_ms=8200
```

### What we do NOT log
- Full response bodies on success (large, potentially sensitive)
- Session tokens or auth credentials
- File attachment content

### Implementation
- Use Python `logging` module with structured key=value format
- Log level INFO for normal flow, WARN for 4xx errors, ERROR for exceptions
- All logs go to stdout → Cloud Run captures in GCP Cloud Logging
- The summary line enables easy post-competition analysis: grep for `result:` to see all task outcomes

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| LLM calls per task | 3-10 (tool-use iterations) | 1 (parse only) for known patterns |
| API calls | Model decides, often suboptimal | Minimum possible (computed) |
| 4xx errors | Model guesses fields wrong | Near zero (validated before execution) |
| Latency | 15-60s per task | 5-15s per task |
| Efficiency bonus | Low | Maximum |
