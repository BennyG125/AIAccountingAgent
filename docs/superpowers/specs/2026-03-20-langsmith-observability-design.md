# LangSmith Observability — Design Spec

**Goal:** Add full observability to the AI Accounting Agent via LangSmith tracing, covering LLM calls, tool executions, and the agent loop with competition metadata for filtering.

**Branch:** `feat/langsmith-observability` (merges into `feat/tool-use-agent`)

**Constraint:** The `feat/tool-use-agent` branch is actively being rewritten (pure agent redesign). Changes here must be minimal and easy to re-apply after merge conflicts in `agent.py`.

---

## Architecture

### Trace Hierarchy

```
solve (top-level, @traceable)
  ├── metadata: {prompt_hash, prompt_preview, file_count}
  ├── gemini_ocr (@traceable, run_type="llm")
  └── run_agent (@traceable)
      ├── [Claude LLM call — iteration 1] (auto-traced by wrap_anthropic)
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

Add `langsmith` dependency.

### 2. `claude_client.py`

Wrap the `AnthropicVertex` client with `wrap_anthropic` from `langsmith.wrappers`. This automatically traces all `messages.create()` and `messages.stream()` calls with inputs, outputs, token usage, and latency.

Fallback: if `wrap_anthropic` doesn't accept `AnthropicVertex` (type check failure), catch the error and return the unwrapped client. Log a warning.

### 3. `agent.py`

Add `@traceable` decorators to:
- `run_agent()` — name="run_agent", metadata with prompt_hash and iteration count
- `execute_tool()` — run_type="tool", name dynamically set to tool name
- `gemini_ocr()` — run_type="llm", name="gemini_ocr"
- `build_user_message()` — name="build_user_message"

Since `agent.py` is being rewritten by the other session, keep changes minimal — only add decorators and imports. No structural changes.

### 4. `main.py`

Add `@traceable` to `solve()` endpoint as the root span. Attach metadata:
- `prompt_hash` — first 8 chars of SHA256 of the prompt (for grouping)
- `prompt_preview` — first 80 chars of prompt text
- `file_count` — number of attached files

### 5. `CLAUDE.md`

Update deploy commands to include LangSmith env vars:
- `LANGSMITH_API_KEY`
- `LANGSMITH_TRACING=true`
- `LANGSMITH_PROJECT=ai-accounting-agent`

---

## Environment Variables

| Variable | Value | Where |
|----------|-------|-------|
| `LANGSMITH_API_KEY` | `lsv2_pt_...` | `.env` (local), Cloud Run env vars |
| `LANGSMITH_TRACING` | `true` | `.env` (local), Cloud Run env vars |
| `LANGSMITH_PROJECT` | `ai-accounting-agent` | `.env` (local), Cloud Run env vars |

---

## Error Handling

- If `langsmith` is not installed: import fails silently, decorators become no-ops, `wrap_anthropic` is skipped
- If `wrap_anthropic` rejects `AnthropicVertex`: catch exception, log warning, return unwrapped client
- If LangSmith API key is missing/invalid: traces silently fail (langsmith SDK handles this gracefully)
- No code path changes — only additive decorators and wrapper

---

## Testing

- Unit tests: verify `get_claude_client()` returns a working client with or without langsmith installed
- Manual: run locally with `LANGSMITH_TRACING=true`, verify traces appear in LangSmith UI
- No new test file needed — this is purely observability, not business logic
