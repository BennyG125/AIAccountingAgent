# Design: Hybrid Tool Search Architecture for Tripletex Agent

## Problem

The agent uses 4 generic tools (tripletex_get/post/put/delete) with a 941-line cheat sheet
baked into the system prompt. This causes:
- **Blind spots**: Missing parameter enums (e.g., entitlement template values — caused 8 wasted
  iterations in testing), missing required field constraints, undocumented endpoints
- **Manual maintenance**: Every API discovery must be hand-coded into cheat_sheet.py
- **Guessing**: Agent infers API formats from prose descriptions, often incorrectly

## Solution

Use Anthropic's built-in tool search (`tool_search_tool_bm25_20251119`) with `defer_loading: true`
to give Claude on-demand access to ~248 per-endpoint tool definitions generated from the Tripletex
OpenAPI spec. Keep the 4 generic tools always loaded as a fallback.

### Confirmed: Vertex AI supports tool search

Tested on `AnthropicVertex` with `claude-opus-4-6` in `us-east5`:
- `defer_loading: true` accepted on regular tools
- Both BM25 and regex tool search variants work
- Streaming + adaptive thinking works
- Only serialization update needed: handle `server_tool_use` and `tool_search_tool_result` blocks

## Architecture

```
POST / -> main.py
  +-- _preconfigure_bank_account()
  +-- gemini_ocr()
  +-- Agent loop
      +-- AGENT_MODE env var selects behavior:
          +-- "generic"     Current 4 tools + full cheat sheet (zero-risk fallback)
          +-- "hybrid"      4 generic tools (always loaded) + 248 deferred tools + BM25 search
          +-- "tool_search" 248 deferred tools + BM25 search only (no generic fallback)
```

### Mode: generic (current system, default)

- 4 generic tools: tripletex_get/post/put/delete
- Full system prompt: scoring rules + gotchas + 20 recipes + 941-line cheat sheet
- No defer_loading, no tool search
- Battle-tested, deployed to competition today

### Mode: hybrid (recommended for next iteration)

- 4 generic tools always loaded (NOT deferred) — agent can always fall back to raw API calls
- ~248 accounting-relevant endpoint tools generated from OpenAPI, all `defer_loading: true`
- `tool_search_tool_bm25_20251119` included for on-demand discovery
- Slim system prompt: scoring rules + gotchas + recipes (no cheat sheet — tools replace it)
- Flow: Claude searches for relevant tools -> gets exact schema with enums -> calls endpoint tool
- If search misses: Claude falls back to generic tripletex_post/put/get with manual path/body

### Mode: tool_search

- Same as hybrid but without the 4 generic tools as always-loaded
- All tools deferred, Claude must search for everything
- Higher risk but maximum token efficiency

## Components

### 1. scripts/generate_tools.py (NEW)

Offline build-time script:
1. Fetches `/openapi.json` from sandbox (or reads cached copy)
2. Filters to 35 accounting-relevant tags (~248 operations across GET/POST/PUT/DELETE)
3. Resolves `$ref` chains in request body schemas
4. Strips `readOnly` fields (not relevant for input)
5. Preserves enums, required fields, descriptions, format hints
6. Limits nested object depth to 3 levels (token budget)
7. Generates tool naming: `{tag_snake_case}_{operation_id_snake_case}`
   - e.g., `employee_post`, `employee_entitlement_grant_entitlements_by_template`
8. Outputs two artifacts:
   - `GENERATED_TOOLS`: list of Anthropic tool defs (with `defer_loading: true`)
   - `GENERATED_TOOLS_META`: dict mapping tool name -> `{method, path, query_params, body_params}`

Output written to `api_knowledge/generated_tools.py` (committed to repo, not dynamic).

### 2. api_knowledge/generated_tools.py (NEW, generated)

```python
GENERATED_TOOLS = [
    {
        "name": "employee_entitlement_grant_entitlements_by_template",
        "description": "Update employee entitlements. The user will only receive the entitlements which are possible with the registered user type",
        "input_schema": {
            "type": "object",
            "properties": {
                "employeeId": {"type": "integer", "description": "Employee ID"},
                "template": {
                    "type": "string",
                    "description": "Template",
                    "enum": ["NONE_PRIVILEGES", "ALL_PRIVILEGES", "INVOICING_MANAGER",
                             "PERSONELL_MANAGER", "ACCOUNTANT", "AUDITOR", "DEPARTMENT_LEADER"]
                }
            },
            "required": ["employeeId", "template"]
        },
        "defer_loading": True,
    },
    # ... ~247 more tools
]

GENERATED_TOOLS_META = {
    "employee_entitlement_grant_entitlements_by_template": {
        "method": "PUT",
        "path": "/employee/entitlement/:grantEntitlementsByTemplate",
        "path_params": [],
        "query_params": ["employeeId", "template"],
    },
    "invoice_payment": {
        "method": "PUT",
        "path": "/invoice/{id}/:payment",
        "path_params": ["id"],
        "query_params": ["paymentDate", "paymentTypeId", "paidAmount", "paidAmountCurrency"],
    },
    # ... metadata for each tool
}
```

### 3. agent.py changes

**Tool execution router** — extends `execute_tool()`:
```python
def execute_tool(name, args, client):
    if name.startswith("tripletex_"):
        return _execute_generic_tool(name, args, client)

    meta = GENERATED_TOOLS_META.get(name)
    if meta:
        path = _resolve_path_params(meta["path"], meta.get("path_params", []), args)
        query = {k: args[k] for k in meta["query_params"] if k in args}
        body_keys = [k for k in args if k not in meta["query_params"]
                     and k not in meta.get("path_params", [])]
        body = {k: args[k] for k in body_keys} if body_keys else None

        method = meta["method"]
        if method == "GET":
            return client.get(path, params=query or None)
        elif method == "POST":
            return client.post(path, body=body)
        elif method == "PUT":
            return client.put(path, body=body, params=query or None)
        elif method == "DELETE":
            return client.delete(path, params=query or None)

    return {"success": False, "error": f"Unknown tool: {name}"}


def _resolve_path_params(path_template, path_params, args):
    """Replace {param} placeholders in path with values from args.

    Tripletex paths use:
    - {id}, {invoiceId} etc. for entity IDs (curly braces)
    - :action for action segments (e.g., :payment, :reverse) — NOT params, kept as-is
    """
    path = path_template
    for param in path_params:
        if param in args:
            path = path.replace(f"{{{param}}}", str(args[param]))
    return path
```

**Content serialization** — add two new block types:
```python
elif block.type == "server_tool_use":
    # Include caller field if present — API requires it for conversation replay
    entry = {"type": "server_tool_use", "id": block.id, "name": block.name, "input": block.input}
    if hasattr(block, "caller") and block.caller is not None:
        entry["caller"] = block.caller.model_dump(exclude_none=True)
    result.append(entry)
elif block.type == "tool_search_tool_result":
    result.append({
        "type": "tool_search_tool_result",
        "tool_use_id": block.tool_use_id,
        "content": block.content.model_dump(exclude_none=True),
    })
```

**Tool list assembly** — built once at module load, based on AGENT_MODE:
```python
AGENT_MODE = os.getenv("AGENT_MODE", "generic")

# Build tool list once at module level (AGENT_MODE doesn't change during process lifetime)
def _build_tools():
    if AGENT_MODE == "generic":
        return list(GENERIC_TOOLS)
    tools = list(GENERIC_TOOLS)  # always loaded, not deferred
    tools.append({"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"})
    tools.extend(GENERATED_TOOLS)  # all have defer_loading: true
    if AGENT_MODE == "tool_search":
        # In tool_search-only mode, defer generic tools too
        tools = [{**t, "defer_loading": True} for t in tools[:4]] + tools[4:]
    return tools

TOOLS = _build_tools()  # cached at import time, no mutation risk
```

### 4. prompts.py changes

```python
def build_system_prompt(mode: str = "generic") -> str:
    if mode == "generic":
        return _full_prompt()  # Current: scoring + gotchas + recipes + cheat sheet

    return _slim_prompt()  # scoring + gotchas + recipes only (no cheat sheet)
```

The slim prompt keeps all 20 recipes and gotchas (they provide task-level strategy)
but drops the 941-line cheat sheet (endpoint details come from tool schemas now).

The slim prompt must include fallback guidance: "If a searched tool does not exist or
fails, use the generic tripletex_get/post/put/delete tools with the path and body directly."

### 5. main.py changes

Pass `AGENT_MODE` through to `run_agent()` which passes it to `build_system_prompt()`.

## Token Budget

### Generic mode (current)
| Component | Tokens |
|-----------|--------|
| 4 generic tools | ~150 |
| Full system prompt (cheat sheet + recipes) | ~4,000 |
| **Total** | **~4,150** |

### Hybrid mode (248 tools)
| Component | Tokens |
|-----------|--------|
| 4 generic tools (always loaded) | ~150 |
| tool_search_tool_bm25 | ~50 |
| 248 deferred tools (names + descriptions only in context) | ~8,000-10,000 |
| Slim system prompt (recipes, no cheat sheet) | ~2,000 |
| **Total before search** | **~10,200-12,200** |
| After search loads 3-5 tools | +2,000-10,000 |
| **Total working context** | **~12,000-22,000** |

Trade-off: ~8k more tokens initially vs generic mode, but agent gets exact schemas with
enums on demand instead of guessing from prose. Eliminates the class of errors that burned
8+ iterations. Token budget is well within Claude Opus 4.6's 200k context window.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Tool search returns irrelevant tools | Generic tools always available as fallback |
| OpenAPI spec differs between sandboxes | Generate from the competition sandbox; regenerate on deploy |
| Deeply nested schemas blow token budget | Limit depth to 3 levels; strip long descriptions |
| Tool search adds latency (extra API round-trip) | BM25 search is server-side, sub-100ms |
| Competition regression | `AGENT_MODE=generic` is default, zero changes to current behavior |
| Vertex stops supporting tool search | `AGENT_MODE=generic` fallback, no code change needed |
| Tool name length limits | Verify SDK accepts long names (~50 chars). Truncate if needed |
| Generated file size (~100KB+) | Monitor Cloud Run cold start impact. Lazy import if needed |
| Tool name collisions after snake_case | Generator must assert uniqueness, fail loudly on dupes |

## Files

| File | Change |
|------|--------|
| `scripts/generate_tools.py` | NEW — OpenAPI spec parser + tool definition generator |
| `api_knowledge/generated_tools.py` | NEW — generated output (committed, deterministic) |
| `agent.py` | Tool router, content serialization, mode switching, tool list assembly |
| `prompts.py` | Add `_slim_prompt()`, parameterize `build_system_prompt(mode)` |
| `main.py` | Read `AGENT_MODE`, pass to `run_agent()` |
| `CLAUDE.md` | Document modes, deploy commands with `AGENT_MODE` |
| `tests/test_agent.py` | Tests for tool router, new block serialization, mode switching |
| `tests/test_generate_tools.py` | Tests for OpenAPI parser output |

## Decision Log

- Full coverage (248 tools, all GET/POST/PUT/DELETE for 35 accounting tags) — maximizes discoverability
- Keep 4 generic tools always loaded in hybrid mode — safety net for undiscovered endpoints
- BM25 over regex — better for multilingual natural language task descriptions
- Generate at build time, commit output — deterministic, auditable, no runtime dependency on sandbox
- Recipes stay in system prompt — tool search augments endpoint knowledge, recipes provide strategy
- `AGENT_MODE=generic` is default — opt-in to hybrid, never forced
