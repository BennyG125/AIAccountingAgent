# LangSmith Observability — Design Spec (v2)

**Goal:** Add full observability to the AI Accounting Agent via LangSmith tracing, covering LLM calls, tool executions, and the agent loop with competition metadata for filtering.

**Branch:** `feat/langsmith-observability` (merges into `feat/tool-use-agent`)

**Constraint:** The `feat/tool-use-agent` branch is actively being rewritten (pure agent redesign — deletes planner.py, executor.py, task_registry.py). Changes here must be minimal and easy to re-apply after merge conflicts in `agent.py`.

---

## Architecture

### Trace Hierarchy

```
solve (top-level, @traceable)
  ├── metadata: {prompt_hash, prompt_preview, file_count, tier_guess}
  ├── gemini_ocr (@traceable, run_type="llm")
  └── run_agent (@traceable)
      ├── [Claude LLM call — iteration 1] (auto-traced by wrap_anthropic OR manual @traceable)
      ├── execute_tool (@traceable, run_type="tool")
      │   └── tripletex_post /customer → 201
      ├── [Claude LLM call — iteration 2]
      ├── execute_tool (@traceable, run_type="tool")
      │   └── tripletex_post /product → 201
      └── ...
```

### Graceful Degradation

LangSmith is an **optional** dependency. If `langsmith` is not installed or `LANGSMITH_TRACING` is not set, the agent works identically to before. Implementation uses try/except imports with no-op fallbacks.

---

## File Changes

### 1. `requirements.txt`

Add `langsmith>=0.3.0` (pinned minimum for stable `wrap_anthropic` and `@traceable`).

### 2. `claude_client.py`

**Strategy: try `wrap_anthropic`, fall back to manual wrapping.**

`AnthropicVertex` may not be accepted by `wrap_anthropic` because it inherits from `BaseVertexClient`, not `anthropic.Anthropic`. The `wrap_anthropic` function accesses `client.completions` which `AnthropicVertex` lacks.

Approach:
1. Try `wrap_anthropic(client)` — if it works, we get automatic tracing of all LLM calls
2. If it raises (AttributeError, TypeError, etc), fall back: use `@traceable(run_type="llm")` wrapper around the Claude call in `agent.py` instead
3. Export a boolean `LANGSMITH_LLM_WRAPPED` so `agent.py` knows whether to add its own LLM tracing

```python
LANGSMITH_LLM_WRAPPED = False  # set True if wrap_anthropic succeeds
```

### 3. `agent.py`

Add `@traceable` decorators to:
- `run_agent()` — name="run_agent", metadata with prompt_hash and iteration count
- `execute_tool()` — run_type="tool", name includes the tool name
- `gemini_ocr()` — run_type="llm", name="gemini_ocr"

**Not decorated:** `build_user_message()` — pure string concatenation, no observability value.

If `LANGSMITH_LLM_WRAPPED` is False, wrap the `messages.stream()` call site manually with `langsmith.run_helpers.trace` context manager to capture LLM inputs/outputs/tokens.

Since `agent.py` is being rewritten by the other session, keep changes minimal — only add decorators and imports. No structural changes.

### 4. `main.py`

Add `@traceable` to the inner logic of `solve()` (not the async endpoint directly — `@traceable` wraps a sync helper). Attach metadata:
- `prompt_hash` — first 8 chars of SHA256 of the prompt (for grouping repeated tasks)
- `prompt_preview` — first 80 chars of prompt text
- `file_count` — number of attached files
- `tier_guess` — heuristic from prompt complexity (nice-to-have)

### 5. `CLAUDE.md`

Update deploy commands to include LangSmith env var **names** (not values):
- `LANGSMITH_TRACING=true`
- `LANGSMITH_PROJECT=ai-accounting-agent`

**API key handling:** `LANGSMITH_API_KEY` is set separately via `gcloud run services update --set-secrets` or Cloud Run console. Never commit the key value to CLAUDE.md or any tracked file.

---

## Environment Variables

| Variable | Value | Where |
|----------|-------|-------|
| `LANGSMITH_API_KEY` | `lsv2_pt_...` | `.env` (local, gitignored), Cloud Run secrets |
| `LANGSMITH_TRACING` | `true` | `.env` (local), Cloud Run env vars |
| `LANGSMITH_PROJECT` | `ai-accounting-agent` | `.env` (local), Cloud Run env vars |

---

## Error Handling

- If `langsmith` is not installed: import fails silently, decorators become no-ops, `wrap_anthropic` is skipped
- If `wrap_anthropic` rejects `AnthropicVertex`: catch exception, log warning, set `LANGSMITH_LLM_WRAPPED=False`, agent.py handles LLM tracing manually
- If LangSmith API key is missing/invalid: traces silently fail (langsmith SDK handles this gracefully)
- No code path changes — only additive decorators and wrapper
- Cold start impact: `langsmith` adds ~5-10MB to Docker image (orjson, xxhash native extensions). Acceptable for competition.

---

## Scope Exclusions

- `planner.py`, `executor.py`, `task_registry.py` — being deleted by the other session's pure agent redesign. Not traced.
- `build_user_message()` — pure string concat, no I/O. Not traced.
- `file_handler.py` — file processing. Low observability value. Not traced.

---

## Testing

- Unit test in `tests/test_claude_client.py`: verify `get_claude_client()` returns a working client both when langsmith is available and when it's not
- Manual verification: run locally with `LANGSMITH_TRACING=true`, confirm traces appear in LangSmith UI at smith.langchain.com
- Verify graceful degradation: unset `LANGSMITH_TRACING`, confirm agent works identically
