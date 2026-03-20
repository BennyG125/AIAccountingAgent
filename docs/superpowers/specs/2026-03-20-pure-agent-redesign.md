# Pure Agent Redesign — Recipe-Enhanced Claude Tool-Use

**Date:** 2026-03-20
**Status:** Approved
**Supersedes:** deterministic-execution-design, parse-fix-registry-expansion-design, claude-migration-design

## Problem

The current two-path architecture (deterministic executor + tool-use fallback) scores 100% on simple Tier 1 tasks but 0% on complex Tier 2/3 multi-step workflows. The deterministic path is brittle — edge cases fall through to a fallback loop that inherits half-created state and gets confused. Tier 3 tasks (opening early Saturday, March 21) are unknown and cannot be pre-registered in a static entity registry.

The competition scores correctness × tier_multiplier × (1 + efficiency_bonus). Efficiency bonus only applies at 100% correctness. A single Tier 3 task going from 0% to 80% is worth more than perfecting all Tier 1 efficiency bonuses combined.

## Decision

Replace the entire two-path architecture with a single Claude Opus 4.6 agentic loop. No deterministic path, no pattern matching, no entity registry, no executor, no recovery module. One agent, one code path, one system prompt.

"Recipes" in the system prompt provide deterministic-level efficiency on known task categories. For unknown Tier 3 tasks, Claude improvises using the 4 REST tools and the API reference.

## Architecture

```
POST /solve (FastAPI, Cloud Run)
│
├── 1. Parse payload (prompt, files, credentials)
├── 2. Process files (PDF → text + images, CSV → text)
├── 3. OCR (Gemini 3.1 Pro, only if images present)
│
├── 4. Claude Opus 4.6 agentic loop:
│      system_prompt = API reference + recipes + rules + constants
│      tools = [tripletex_get, tripletex_post, tripletex_put, tripletex_delete]
│      thinking = adaptive
│      max_iterations = 20, timeout = 270s
│
│      while not done:
│          stream response (prevents HTTP timeouts)
│          if end_turn: break
│          execute tool calls against Tripletex API
│          feed results back into conversation
│
└── 5. Return {"status": "completed"}
```

## Key Design Decisions

### 1. Single Agent, No Routing

Opus 4.6 with adaptive thinking handles task classification, planning, and execution in one loop. Routing to specialized sub-agents would add latency and multiply LLM calls without improving accuracy. The 5-minute timeout makes every second count.

### 2. Four Generic REST Tools

```
tripletex_get(path, params)    — GET, for searching/listing
tripletex_post(path, body)     — POST, for creating entities
tripletex_put(path, body)      — PUT, for updating entities
tripletex_delete(path)         — DELETE, for removing entities
```

Entity-specific tools (27+) would bloat the tool list and duplicate system prompt knowledge. Generic tools give Claude full flexibility to call any endpoint. The system prompt provides the domain knowledge.

### 3. Recipes in System Prompt (Not Code)

For each known task category, the system prompt includes a step-by-step recipe:

- **Employee:** POST /department → POST /employee (userType, department required)
- **Customer + Product:** POST /customer → POST /product (vatType as {id: 3})
- **Invoice flow:** customer → product → order (embed orderLines) → invoice
- **Payment:** PUT /invoice/{id}/:payment — QUERY PARAMS (paymentDate, paymentTypeId, paidAmount, paidAmountCurrency)
- **Travel expense:** employee → travelExpense → cost/mileage/perDiem/accommodation
- **Project:** employee → project → POST /project/participant
- **Voucher:** GET /ledger/account → POST /ledger/voucher (balanced postings)
- **Send invoice:** POST /invoice/{id}/:sendToCustomer (method=email)
- **Credit note:** POST /invoice/{id}/:createCreditNote
- **Supplier:** POST /supplier

Claude follows recipes when they match and improvises when they don't. Adding a new recipe is adding a paragraph, not writing an executor branch.

### 4. Adaptive Thinking

`thinking: {type: "adaptive"}` lets Opus reason through complex multi-step tasks before making the first tool call. Critical for Tier 3 tasks where the plan isn't obvious.

### 5. Prompt Caching

`cache_control: {type: "ephemeral"}` on the system prompt. After the first iteration, subsequent tool loop iterations reuse cached context — faster and cheaper.

### 6. Streaming

All Claude calls use `.messages.stream()` with `.get_final_message()`. Prevents HTTP timeouts during long thinking passes. Essential for adaptive thinking on complex tasks.

### 7. Vertex AI

AnthropicVertex client, us-east5 region, GCP project ai-nm26osl-1799. Authentication via Application Default Credentials (Cloud Run service account). Same as current setup.

## System Prompt Structure

```
§1 — Role & Rules (~200 tokens)
§2 — Authentication & Response Format (~100 tokens)
§3 — Known Constants (~50 tokens)
     VAT: 25%={id:3}, 15%={id:5}, 0%={id:6}. NOK={id:1}. Norway={id:162}.
§4 — API Reference (~1500 tokens)
     Every endpoint with required/optional fields, from sandbox-verified testing.
§5 — Recipes for Known Flows (~800 tokens)
     Step-by-step optimal sequences for each task category.
§6 — Common Gotchas (~200 tokens)
     Payment=query params, object refs={id:N}, departmentNumber=string,
     embed orderLines, voucher postings must balance, product number collisions.
§7 — Tier 3 Guidance (~200 tokens)
     Explore unfamiliar endpoints with ?fields=*. Read error messages.
     Break complex problems into smaller steps.

Total: ~3000 tokens
```

## Error Handling

- Tool execution wraps all API calls — errors returned to Claude as `is_error: true` tool results
- Claude reads error messages and adapts (e.g., "422: email required" → adds field, retries)
- No separate recovery module — the conversation IS the recovery mechanism
- Hard stop at 270s (30s safety margin before 300s competition timeout)
- Always return `{"status": "completed"}` — partial work earns partial credit

## Scoring Strategy

Baked into the system prompt:
- "Every 4xx error reduces your efficiency score. Get it right on the first call."
- "Never make verification GETs after successful creates."
- "Use known constants directly — never look them up."
- "Embed orderLines in order POST — saves separate API calls."
- Recipes encode the optimal call sequence for each task category.

## File Structure

| File | Purpose | ~Lines |
|------|---------|--------|
| `main.py` | FastAPI endpoint, payload parsing | ~50 |
| `agent.py` | Claude agentic loop (streaming, timeout, tools) | ~120 |
| `prompts.py` | System prompt: API ref + recipes + rules + constants | ~300 |
| `tripletex_api.py` | HTTP wrapper for Tripletex API (keep existing) | ~60 |
| `file_handler.py` | PDF/image processing + Gemini OCR | ~100 |
| `claude_client.py` | AnthropicVertex cached client (keep existing) | ~26 |

**Total: ~650 lines** (down from ~2000+)

## Files to Delete

- `planner.py` — replaced by Claude's own reasoning
- `executor.py` — replaced by tool-use loop
- `task_registry.py` — replaced by system prompt recipes
- `api_knowledge/cheat_sheet.py` — merged into prompts.py
- `api_knowledge/__init__.py` — directory removed

## Files to Rewrite

- `main.py` — simplified, no deterministic path routing
- `agent.py` — clean agentic loop, no planner/executor imports
- `tests/` — new tests for new architecture

## Testing Strategy

- **Unit tests:** Mock AnthropicVertex, test tool execution, test message building
- **Smoke tests:** Real requests against sandbox, verify correctness
- **Prompt iteration:** Submit to competition, read scores, adjust recipes and system prompt

The fastest path to improving scores is: deploy → submit → read results → adjust prompt → repeat. The system prompt is the only thing that needs to change between iterations.

## Migration Path

1. Create new branch from feat/tool-use-agent
2. Delete planner.py, executor.py, task_registry.py, api_knowledge/
3. Rewrite agent.py (clean agentic loop)
4. Create prompts.py (system prompt with recipes)
5. Simplify main.py
6. Update tests
7. Deploy to Cloud Run
8. Submit to competition and iterate on prompts

## Why Not Agent SDK

The Claude Agent SDK wraps the Claude Code CLI. It's designed for agents needing file system, web browsing, and terminal access. This agent needs HTTP calls to a REST API. The Agent SDK adds CLI process overhead, unused built-in tools, and deployment complexity without benefit. The raw Anthropic SDK with tool-use is the correct tier.

## Why Not Subagents / Routing

- Routing adds latency for marginal benefit — Opus handles classification + execution in one loop
- Subagents multiply LLM calls — with a 5-minute timeout, every token should go to one capable agent
- Deep research agents are for open-ended exploration — competition tasks are bounded

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Opus makes wrong API calls | Recipes + detailed API reference minimize guessing |
| Tier 3 tasks are completely novel | Adaptive thinking + ?fields=* exploration guidance |
| Agent loop too slow (>300s) | Streaming + 270s hard stop + iteration cap |
| Prompt too large for context | ~3000 tokens — well within 200K window |
| Efficiency bonus lower than deterministic | Recipes achieve near-optimal call counts; correctness gains far outweigh |
| Vertex AI latency spikes | Streaming prevents timeouts; us-east5 is close to Anthropic infra |
