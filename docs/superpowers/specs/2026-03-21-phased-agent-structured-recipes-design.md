# Design: Phased Agent with Structured Recipes

**Status:** Draft
**Date:** 2026-03-21
**Goal:** Reduce API errors and wasted calls by splitting the agentic loop into focused phases and adding code-level validation from structured recipe data.

---

## Problem

The current agent runs a single agentic loop where Claude Opus handles everything: task classification, value extraction, recipe recall, API payload construction, execution, and error recovery. This works for simple tasks (1-3 calls, zero errors) but breaks down on complex multi-step tasks:

| Task Type | Optimal Calls | Actual Calls | Actual Errors | Root Cause |
|-----------|--------------|--------------|---------------|------------|
| create_invoice | 4-5 | 12-19 | 2-9 | vatType hallucination, verification GETs |
| run_salary | ~8 | 13-24 | 2-10 | Field confusion, retries |
| travel_expense | ~7 | 12 | 5 | Field name traps (name vs description) |
| register_payment | ~5 | 10-15 | 0-2 | Unnecessary lookups |

The 13k-token system prompt contains all recipes + a 941-line API cheat sheet. As the conversation grows with tool results and error messages, attention to recipe details degrades. By iteration 6+, Claude is effectively guessing at field names it read 20k+ tokens ago.

Simple tasks succeed because they complete before attention degrades. Complex tasks fail because they don't.

## Solution Overview

Split the agent into phases that each do one thing well, and add a code-level validation layer that catches known mistakes before they hit the API.

```
Request arrives
    │
    ▼
Phase 1: CLASSIFY + EXTRACT (one LLM call, structured output)
    │   Input: prompt + compact task type catalog
    │   Output: {task_type, extracted_values}
    │
    ├── Known task type ──────────────────────┐
    │                                         │
    │   Phase 2a: FOCUSED AGENTIC LOOP        │
    │   • System prompt: only matched recipe   │
    │   • User msg: includes extracted values  │
    │   • Tools: 4 generic + validation layer  │
    │                                         │
    ├── Unknown task type ────────────────────┐
    │                                         │
    │   Phase 2b: FULL AGENTIC LOOP (current) │
    │   • Full system prompt (all recipes)     │
    │   • Current 4 generic tools              │
    │                                         │
    ▼                                         │
Phase 3: VALIDATION MIDDLEWARE (in execute_tool)
    │   Every API call passes through field_guards
    │   before reaching Tripletex
    └──────────────────────────────────────────┘
```

## Design Sections

### 1. Structured Recipe Format

Each task type has three files:

```
recipes/
  17_travel_expense.md              # Claude reads (existing, unchanged)
  17_travel_expense.guard.json      # Middleware reads (NEW)
  17_travel_expense.extract.json    # Phase 1 reads (NEW)
```

#### `.guard.json` — Field validation rules

```json
{
  "task_type": "travel_expense",
  "field_guards": {
    "/travelExpense/rateCategory": {
      "allowed_fields_filter": ["id", "name", "type", "fromDate", "toDate", "isValidDomestic"],
      "forbidden_fields_filter": ["description"]
    },
    "/travelExpense/costCategory": {
      "allowed_fields_filter": ["id", "description", "showOnTravelExpenses"]
    },
    "/travelExpense": {
      "body_rename": {"costs[].description": "costs[].comments"},
      "body_strip": []
    },
    "/product": {
      "body_strip": ["vatType"]
    },
    "/employee": {
      "body_strip": ["isAdministrator"]
    }
  },
  "expected_calls_range": [7, 8],
  "max_errors": 0
}
```

**Field guard rules:**
- `allowed_fields_filter`: When a GET request includes `?fields=...`, only these field names are permitted. Forbidden fields are **removed** (not replaced). If the resulting fields list is empty, the `fields` param is removed entirely so the API returns all fields.
- `forbidden_fields_filter`: These field names are explicitly rejected from `?fields=...` params and removed.
- `body_rename`: Before POST/PUT, rename fields in the request body. Supports nested array paths with `[]` notation: `costs[].description` means "for every element in the `costs` array, rename the key `description` to `comments` if present." Only operates on direct keys of array items — no deeper nesting.
- `body_strip`: Before POST/PUT, remove these fields from the body entirely. Also applies to nested objects recursively.
- `expected_calls_range` / `max_errors`: Metadata fields for recipe-validator only. The runtime ignores these.

#### `.extract.json` — Value extraction schema

```json
{
  "task_type": "travel_expense",
  "description": "Register a travel expense report with per diem and out-of-pocket costs",
  "keywords": ["travel expense", "reiseregning", "despesa de viagem", "Reisekostenabrechnung", "frais de voyage", "gastos de viaje", "diett", "per diem", "Tagegeld"],
  "fields": {
    "employee_email": {"type": "string", "required": true, "hint": "Employee email address"},
    "employee_name": {"type": "string", "required": false, "hint": "Employee full name if given"},
    "title": {"type": "string", "required": true, "hint": "Trip title/description"},
    "departure_date": {"type": "date", "required": false},
    "return_date": {"type": "date", "required": false},
    "departure_from": {"type": "string", "required": false},
    "destination": {"type": "string", "required": false},
    "per_diem_days": {"type": "integer", "required": false},
    "per_diem_rate": {"type": "number", "required": false},
    "overnight_accommodation": {"type": "boolean", "required": false, "default": true},
    "costs": {
      "type": "array",
      "items": {
        "description": {"type": "string", "hint": "What the expense was for"},
        "amount": {"type": "number", "hint": "Amount in NOK including VAT"}
      }
    }
  }
}
```

#### Global guards

Some guards apply to ALL task types (e.g., never include `vatType` on `/product`). These live in a single `recipes/_global.guard.json`:

```json
{
  "task_type": "_global",
  "field_guards": {
    "/product": {
      "body_strip": ["vatType"]
    },
    "/employee": {
      "body_strip": ["isAdministrator"]
    }
  }
}
```

Task-specific guards **extend** (union) global guards at startup — task-specific rules never remove global rules. If both global and task-specific guards define rules for the same path, their `body_strip` and `forbidden_fields_filter` lists are concatenated, and `body_rename` entries are merged (task-specific wins on conflicts).

### 2. Phase 1: Classify + Extract

A single LLM call before the agentic loop. Uses the `.extract.json` schemas to build a structured output request.

**Implementation in `agent.py`:**

```python
def classify_and_extract(prompt: str, extraction_schemas: dict) -> dict:
    """Classify task type and extract values. One LLM call.

    Uses messages.create (non-streaming) since we need only a single
    structured tool_use response. The system param is a plain string
    (no cache_control) since this call is one-shot, not iterative.
    """
    client = get_claude_client()

    # Build a compact catalog from all .extract.json files
    catalog = []
    for task_type, schema in extraction_schemas.items():
        catalog.append({
            "task_type": task_type,
            "description": schema["description"],
            "keywords": schema["keywords"],
            "fields": schema["fields"],
        })

    response = client.messages.create(
        model=CLAUDE_MODEL,
        system="You are a task classifier and value extractor for Tripletex accounting tasks. "
               "Classify the task and extract all relevant values. If unsure of the task type, "
               "return task_type: 'unknown'. Tasks may be in NO, EN, ES, PT, DE, or FR.",
        messages=[{
            "role": "user",
            "content": f"Task types:\n{json.dumps(catalog, indent=2)}\n\nPrompt:\n{prompt}"
        }],
        tools=[{
            "name": "classify_result",
            "description": "Return classification and extracted values",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_type": {"type": "string"},
                    "confidence": {"type": "number", "description": "0.0-1.0"},
                    "extracted_values": {"type": "object"},
                },
                "required": ["task_type", "confidence", "extracted_values"],
            }
        }],
        tool_choice={"type": "tool", "name": "classify_result"},
        max_tokens=2000,
    )
    # Extract the tool_use result
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    return {"task_type": "unknown", "confidence": 0.0, "extracted_values": {}}
```

**Decision: confidence threshold.** If `confidence < 0.7` or `task_type == "unknown"`, fall back to the current full-prompt agentic loop. No risk of wrong recipe selection.

**Decision: Phase 1 timeout.** The classify call has a 15-second timeout. If it fails or times out, the system skips to the full agentic loop with zero degradation. Phase 1 is best-effort only.

**Token cost:** This call is cheap — small system prompt, small catalog (~2k tokens for 19 types), one tool_use response. Estimated ~3k input + ~500 output tokens. Adds ~3-5 seconds latency.

**Recipe file mapping.** The `task_type` string in `.extract.json` maps to recipe filenames by suffix: task_type `"travel_expense"` matches `17_travel_expense.md`. The mapping is built at startup by scanning all recipe files and extracting the portion after the `NN_` prefix (stripping the extension). This avoids a hardcoded lookup table.

### 3. Phase 2: Focused Agentic Loop

The existing `run_agent()` function, modified to accept an optional task context:

```python
def run_agent(prompt, file_contents, base_url, session_token,
              task_type=None, extracted_values=None):
    """Run the agentic loop. If task_type is provided, use focused mode."""
    if task_type and task_type != "unknown":
        system_prompt = build_focused_prompt(task_type, extracted_values)
    else:
        system_prompt = build_system_prompt()  # current full prompt

    # ... rest of the loop is unchanged
```

**`build_focused_prompt()`** loads only the matched recipe `.md` file plus the global gotchas section (scoring rules, known constants, critical gotchas from `prompts.py`). No cheat sheet, no other recipes. Estimated ~1-2k tokens.

**Prompt caching:** The current system wraps the system prompt in `cache_control: {"type": "ephemeral"}` (agent.py:295-300) to cache the 13k prompt across iterations. In focused mode the prompt is ~1.5k tokens, which may be below the minimum cacheable block size. The `cache_control` wrapper should still be applied — if the prompt is too small to cache, the API simply ignores the hint with no error. If iteration count is high, even small prompt caching helps.

**Extracted values are injected into the user message:**

```python
def build_user_message(prompt, file_contents, extracted_values=None):
    parts = []
    if extracted_values:
        parts.append(f"[Pre-extracted values]\n{json.dumps(extracted_values, indent=2)}")
    # ... existing file content handling
    parts.append(prompt)
    return "\n\n".join(parts)
```

This gives Claude a head start — it doesn't need to re-parse the multilingual prompt to find the employee email or cost amounts.

### 4. Phase 3: Validation Middleware

A new module `recipe_guards.py` that sits between Claude's tool calls and the Tripletex API:

```python
class RecipeGuards:
    """Validates and transforms API calls against structured recipe rules."""

    def __init__(self, guards_dir: Path):
        self.global_guards = self._load_guard("_global")
        self.task_guards = {}
        for f in guards_dir.glob("*.guard.json"):
            guard = json.loads(f.read_text())
            self.task_guards[guard["task_type"]] = guard

    def set_active_task(self, task_type: str):
        """Merge global + task-specific guards."""
        self.active = self._merge(
            self.global_guards,
            self.task_guards.get(task_type, {})
        )

    def validate_request(self, method: str, path: str,
                         body: dict | None, params: dict | None
                         ) -> tuple[dict | None, dict | None, list[str]]:
        """Validate and transform a request. Returns (body, params, warnings)."""
        warnings = []
        guards = self._find_matching_guard(path)
        if not guards:
            return body, params, warnings

        # Apply field filter validation
        if params and "fields" in params:
            params, field_warnings = self._validate_fields_filter(
                params, guards)
            warnings.extend(field_warnings)

        # Apply body transformations
        if body:
            body, body_warnings = self._transform_body(body, guards)
            warnings.extend(body_warnings)

        return body, params, warnings
```

**Guard path matching.** `_find_matching_guard(path)` uses longest-prefix match. Guard keys are path prefixes (e.g., `/travelExpense/rateCategory`). Given Claude's request path `/travelExpense/rateCategory`, the algorithm:
1. Strips any trailing ID segments (e.g., `/employee/123` → `/employee`)
2. Tries exact match first
3. Falls back to longest matching prefix
4. Returns `None` if no guard matches (call passes through unmodified)

**Body transformation algorithm.** `_transform_body(body, guards)` applies rules in order:
1. `body_strip`: Walk top-level keys. If key is in strip list, remove it. Also walk any nested dicts/arrays to remove deeply nested forbidden keys.
2. `body_rename` with `[]` syntax: Parse the path `costs[].description` as "array key = `costs`, item key = `description`". Iterate `body["costs"]`, rename `description` → `comments` on each item. Only one level of `[]` nesting is supported.

**Integration in `execute_tool()`:**

```python
def execute_tool(name, args, client, guards: RecipeGuards = None):
    path = args.get("path", "")
    params = args.get("params")
    body = args.get("body")

    # Apply guards before sending
    if guards:
        body, params, warnings = guards.validate_request(
            method=name.replace("tripletex_", "").upper(),
            path=path, body=body, params=params,
        )
        for w in warnings:
            logger.warning(f"Guard: {w}")

    # ... existing execution logic
```

**What guards catch (examples from real errors):**

| Error | Guard Rule | Fix Applied |
|-------|-----------|-------------|
| `description` in rateCategory fields filter | `forbidden_fields_filter: ["description"]` | Removed from fields list |
| `vatType` in product POST body | `body_strip: ["vatType"]` | Removed from body |
| `description` instead of `comments` in travel costs | `body_rename: {"costs[].description": "costs[].comments"}` | Field renamed |
| `isAdministrator` on employee | `body_strip: ["isAdministrator"]` | Removed from body |

### 5. Skill Pipeline Integration

The existing skill pipeline becomes the authoring workflow for structured recipes:

```
recipe-builder skill
    ├── Discovers optimal API sequence via curl (existing)
    ├── Writes recipes/NN_task.md (existing)
    ├── Writes recipes/NN_task.guard.json (NEW)
    │     Field guards derived from API exploration
    └── Writes recipes/NN_task.extract.json (NEW)
          Extraction schema derived from prompt analysis

save-and-replay skill
    ├── Saves competition requests locally (existing)
    └── Replays against dev container (existing)

recipe-validator skill
    ├── Deploys and sends test request (existing)
    ├── Verifies API call count against expected_calls_range (ENHANCED)
    └── Verifies zero guardrail warnings in logs (NEW)
```

**Workflow for improving a task type:**
1. `agent-debugger`: Find the failure, identify the field error
2. `save-and-replay`: Save the request for reproduction
3. `recipe-builder`: Fix the `.md` recipe AND add a guard rule to `.guard.json`
4. `recipe-validator`: Deploy, replay, verify zero errors + call count in range

The guard rule is immediately active — no need to hope Claude "learns" from updated prompt text.

### 6. Fallback Strategy

The system degrades gracefully:

| Scenario | Behavior |
|----------|----------|
| Phase 1 classifies correctly | Focused prompt + guards active |
| Phase 1 confidence < 0.7 | Full prompt, guards still active (global only) |
| Phase 1 returns "unknown" | Full prompt, global guards only |
| Guard catches a field error | Field fixed, warning logged, call proceeds |
| No guard exists for an endpoint | Call passes through unmodified |
| Phase 1 call fails (timeout, error) | Skip to full agentic loop, zero risk |

No path through this system is worse than the current system. Every path is the same or better.

## Files to Create/Modify

| File | Change | Effort |
|------|--------|--------|
| `recipe_guards.py` | **NEW** — Validation middleware | Medium |
| `agent.py` | Add `classify_and_extract()`, modify `run_agent()` to accept task context, integrate guards into `execute_tool()` | Medium |
| `prompts.py` | Add `build_focused_prompt()` alongside existing `build_system_prompt()` | Small |
| `recipes/_global.guard.json` | **NEW** — Global guard rules | Small |
| `recipes/NN_*.guard.json` | **NEW** — Per-task guard rules (start with top 4-5 error-prone types) | Medium |
| `recipes/NN_*.extract.json` | **NEW** — Per-task extraction schemas | Medium |
| `.claude/skills/recipe-builder/SKILL.md` | Update to output `.guard.json` and `.extract.json` alongside `.md` | Small |
| `.claude/skills/recipe-validator/SKILL.md` | Add guard warning verification | Small |

## Build Order (Incremental, Each Step Independently Deployable)

### Step 1: Validation middleware + global guards
- Create `recipe_guards.py`
- Create `recipes/_global.guard.json` with known global rules (vatType on products, isAdministrator on employees)
- Integrate into `execute_tool()`
- Test: replay saved requests, verify errors drop

### Step 2: Task-specific guards for top error-prone types
- Create `.guard.json` for: travel_expense, create_invoice, run_salary, register_supplier_invoice
- Test: replay saved requests for these types specifically

### Step 3: Pre-classification + focused prompting
- Add `classify_and_extract()` to `agent.py`
- Create `.extract.json` for all 19 task types
- Add `build_focused_prompt()` to `prompts.py`
- Test: verify classification accuracy on all 37 test fixtures

### Step 4: Upgrade skill pipeline
- Update recipe-builder to output all three file formats
- Update recipe-validator to check guard warnings and expected_calls_range
- Validate end-to-end with save-and-replay

## Token Budget

| Mode | System Prompt | Tools | Phase 1 Cost | Total First Turn |
|------|--------------|-------|-------------|-----------------|
| Current (full) | ~13,000 | ~150 | 0 | ~13,150 |
| Focused (known task) | ~1,500 | ~150 | ~3,500 | ~5,150 |
| Fallback (unknown) | ~13,000 | ~150 | ~3,500 | ~16,650 |

Focused mode saves ~8k tokens per turn. Over a 10-iteration loop, that's ~80k fewer input tokens — faster responses and lower cost.

## Test Plan

### Unit tests (`tests/test_recipe_guards.py`)
- `RecipeGuards.validate_request` strips `vatType` from `/product` POST body
- `RecipeGuards.validate_request` removes `description` from `/travelExpense/rateCategory` fields filter
- `RecipeGuards.validate_request` renames `costs[].description` → `costs[].comments` in travel expense body
- `RecipeGuards.validate_request` passes through unguarded endpoints unchanged
- Guard merging: task-specific extends global, never removes global rules
- Path matching: `/employee/123` matches `/employee` guard, `/travelExpense/rateCategory` exact match wins over `/travelExpense` prefix

### Unit tests (`tests/test_classify.py`) — Step 3 only
- `classify_and_extract` returns correct task_type for each of the 37 test fixtures (mocked LLM response)
- `classify_and_extract` returns "unknown" with low confidence for unrecognized prompts
- `classify_and_extract` timeout/failure falls back gracefully (returns unknown)
- `build_focused_prompt` loads correct recipe file for each task_type
- Recipe file mapping: task_type string → recipe filename suffix

### Integration tests (via save-and-replay + recipe-validator)
- Replay saved competition requests after deploying with guards enabled
- Verify: error count drops, call count drops or stays same
- Verify: guard warning logs appear for corrected fields (no silent changes)
- Verify: no regression on tasks that already had zero errors

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Phase 1 misclassifies task | Low — task types are distinct, keywords are multilingual | Confidence threshold, fallback to full prompt |
| Guards are too aggressive (strip valid fields) | Low — guards only target known-bad patterns | Log warnings, review in recipe-validator |
| Phase 1 adds latency | Certain — ~3-5s | Offset by fewer iterations in Phase 2 |
| Tier 3 tasks are completely novel | Possible | Falls back to current system, zero regression |
| Guard rules get stale | Low — updated via recipe-builder skill | Skill pipeline is the single source of truth |
