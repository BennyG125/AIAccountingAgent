# Spec: Hybrid Tool Search Architecture

## Status: Post-competition implementation plan

## Problem

The agent uses 4 generic tools (tripletex_get/post/put/delete) with a large system prompt
containing recipes and a cheat sheet. This works but has blind spots:
- Missing parameter enums (e.g., entitlement template values)
- Missing required field constraints
- Agent guesses API formats and burns iterations on wrong calls
- Cheat sheet must be manually maintained

## Proposed Architecture

### Dual-mode agent with fallback

```
POST / → main.py
  ├── _preconfigure_bank_account()
  ├── gemini_ocr()
  └── Agent loop (MODE selected by env var or config)
      ├── MODE=tool_search  → Tool search with per-endpoint tools
      ├── MODE=generic      → Current 4 generic tools + cheat sheet (fallback)
      └── MODE=hybrid       → Tool search + generic tools as always-loaded fallback
```

### Mode: tool_search

- Parse Tripletex OpenAPI spec at startup → generate ~248 accounting-relevant tool definitions
- Each tool maps to one API operation (e.g., `create_employee`, `grant_entitlements_by_template`)
- Full input_schema with enums, required fields, descriptions from OpenAPI
- All tools marked `defer_loading: true` except the 4 generic tools
- Include `tool_search_tool_bm25_20251119` for on-demand discovery
- System prompt: slim (scoring rules + gotchas + recipes only, no cheat sheet)

### Mode: generic (current — fallback)

- 4 generic tools: tripletex_get/post/put/delete
- Full system prompt with cheat sheet (941 lines) + 20 recipes
- No defer_loading, no tool search
- Battle-tested, works today

### Mode: hybrid (recommended)

- 4 generic tools always loaded (NOT deferred) — agent can always fall back to raw API calls
- ~50-100 key endpoint tools generated from OpenAPI, all `defer_loading: true`
- `tool_search_tool_bm25_20251119` included for discovery
- Slim system prompt: recipes reference tool names instead of raw API paths
- If tool search finds the right endpoint tool → agent gets exact schema with enums
- If tool search misses → agent falls back to generic tripletex_post with path/body

## Implementation Plan

### Phase 1: OpenAPI tool generator (offline, build-time)

```
scripts/generate_tools.py
  ├── Fetch /openapi.json from sandbox
  ├── Filter to accounting-relevant tags (35 tags, ~248 operations)
  ├── Resolve $ref chains, strip readOnly fields
  ├── Generate Anthropic tool definitions with defer_loading: true
  ├── Write to api_knowledge/generated_tools.py
  └── Include metadata: endpoint, method, tag, token estimate
```

Key decisions:
- Tool naming: `{tag}_{operation}` e.g. `employee_create`, `entitlement_grant_by_template`
- Descriptions: from OpenAPI summary + parameter details
- Input schema: full properties with enums, required fields
- Strip deeply nested objects beyond 2 levels (token budget)
- Estimated output: ~50-100 tools after filtering (prioritize POST/PUT over GET)

### Phase 2: Tool execution router

```python
# agent.py additions

def execute_tool(name: str, args: dict, client: TripletexClient) -> dict:
    # Existing generic tools
    if name.startswith("tripletex_"):
        return _execute_generic_tool(name, args, client)

    # Generated endpoint tools — route to the right HTTP call
    tool_meta = GENERATED_TOOLS_META.get(name)
    if tool_meta:
        method = tool_meta["method"]       # GET/POST/PUT/DELETE
        path_template = tool_meta["path"]  # e.g. "/employee/entitlement/:grantEntitlementsByTemplate"

        # Separate path params, query params, and body from args
        path = _resolve_path_params(path_template, args)
        query_params = _extract_query_params(args, tool_meta)
        body = _extract_body(args, tool_meta)

        return _dispatch(client, method, path, body=body, params=query_params)

    return {"success": False, "error": f"Unknown tool: {name}"}
```

### Phase 3: Content serialization update

Add handling for new block types in `_serialize_content()`:

```python
elif block.type == "server_tool_use":
    result.append({
        "type": "server_tool_use",
        "id": block.id,
        "name": block.name,
        "input": block.input,
    })
elif block.type == "tool_search_tool_result":
    result.append({
        "type": "tool_search_tool_result",
        "tool_use_id": block.tool_use_id,
        "content": block.content.model_dump(),
    })
```

### Phase 4: System prompt adaptation

```python
def build_system_prompt(mode: str) -> str:
    if mode == "generic":
        return current_prompt()  # Full cheat sheet + recipes

    # tool_search / hybrid modes
    return slim_prompt()  # Scoring rules + gotchas + recipes (no cheat sheet)
    # Recipes reference tool names: "Use create_employee tool" instead of
    # "POST /employee {firstName, lastName, ...}"
```

### Phase 5: Mode switching

```python
# Environment variable controls mode
AGENT_MODE = os.getenv("AGENT_MODE", "generic")  # generic | tool_search | hybrid

# In run_agent():
if AGENT_MODE in ("tool_search", "hybrid"):
    tools = GENERIC_TOOLS + [TOOL_SEARCH_BM25]
    if AGENT_MODE == "hybrid":
        tools = GENERIC_TOOLS + [TOOL_SEARCH_BM25]  # generic always loaded
    tools += GENERATED_TOOLS  # all with defer_loading: true
else:
    tools = GENERIC_TOOLS  # current behavior
```

## Token Budget (hybrid mode)

| Component | Tokens |
|-----------|--------|
| 4 generic tools (always loaded) | ~150 |
| tool_search_tool_bm25 | ~50 |
| ~100 deferred tool names+descriptions (metadata only) | ~3,000 |
| Slim system prompt (no cheat sheet) | ~2,000 |
| **Total before first search** | **~5,200** |
| After tool search loads 3-5 tools | +2,000-10,000 |
| **Total working context** | **~7,000-15,000** |

Compare to current: ~4,150 tokens. Hybrid is only ~1k more initially, but gives
Claude access to exact schemas on demand.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Tool search returns wrong tools | Generic tools always available as fallback |
| OpenAPI spec changes between sandboxes | Regenerate at deploy time, or fetch at startup |
| Token budget exceeded with large schemas | Limit schema depth to 2 levels, strip descriptions > 100 chars |
| Competition deadline pressure | MODE=generic is the current working system — zero risk |
| Vertex AI stops supporting tool search | MODE=generic fallback, no code change needed |

## Files to Create/Modify

| File | Change |
|------|--------|
| `scripts/generate_tools.py` | NEW — OpenAPI → tool definitions generator |
| `api_knowledge/generated_tools.py` | NEW — generated output (committed, not dynamic) |
| `agent.py` | Add tool execution router, content serialization, mode switching |
| `prompts.py` | Add slim_prompt() for tool_search/hybrid modes |
| `main.py` | Pass AGENT_MODE to run_agent() |
| `CLAUDE.md` | Document modes and deploy commands with AGENT_MODE |

## Decision Log

- Keep 4 generic tools as always-loaded — they are the safety net
- Use BM25 over regex — better for natural language task descriptions
- Generate tools at build time, not runtime — deterministic, auditable
- Filter to ~100 tools — keeps deferred metadata under 3k tokens
- Recipes still exist in system prompt — tool search augments, doesn't replace
