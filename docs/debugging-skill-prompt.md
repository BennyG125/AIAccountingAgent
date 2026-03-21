# Debugging Skill Prompt — LangSmith + GCS for AI Accounting Agent

Use this as the foundation for a debugging/analysis skill that connects to LangSmith traces and GCS request logs to diagnose agent behavior and suggest improvements.

---

## Context

You are debugging an AI accounting agent that runs as a Cloud Run container.
The agent receives accounting tasks (create invoice, register payment, etc.) via `POST /` and executes them against the Tripletex REST API using a Claude Opus agentic loop.

Two observability systems capture different data:

| System | What it captures | How to query |
|--------|-----------------|--------------|
| **LangSmith** | Agent behavior: LLM calls (thinking, tool selections, stop reasons), tool executions (inputs/outputs/status codes), token usage, latency per step | `langsmith` CLI |
| **GCS** | Full request payload: prompt, attached files (base64), Tripletex credentials, agent result (iterations, errors, timing) | `gsutil` CLI |

They are linked by a **`task_id`** — a 12-char hex string generated per request. It appears as:
- **LangSmith**: `metadata.task_id` on the root `handle_accounting_task` trace
- **GCS**: `task_id` field in the JSON payload, and in the GCS object filename (`requests/{timestamp}_{task_id}_{prompt_preview}.json`)

For traces created before the `task_id` was added, correlate by matching the timestamp and prompt text between the two systems.

## Environment Setup

```bash
# LangSmith CLI must be on PATH
export PATH="/Users/torbjornbeining/.local/bin:$PATH"

# Load API keys from .env
source .env

# For dev traces:
export LANGSMITH_API_KEY=$LANGSMITH_API_KEY
export LANGSMITH_PROJECT=ai-accounting-agent-dev

# For competition traces:
export LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP
export LANGSMITH_PROJECT=ai-accounting-agent-comp
```

## LangSmith Projects

| Project | Container | Purpose |
|---------|-----------|---------|
| `ai-accounting-agent-dev` | `ai-accounting-agent-det` | Dev/testing — safe to send test requests |
| `ai-accounting-agent-comp` | `accounting-agent-comp` | Competition — never send test requests here |

## GCS Buckets

| Bucket | Container |
|--------|-----------|
| `ai-nm26osl-1799-dev-logs` | Dev |
| `ai-nm26osl-1799-competition-logs` | Competition |

---

## LangSmith CLI Reference

### List recent traces

```bash
langsmith trace list --project ai-accounting-agent-comp --limit 10 --format pretty
```

### View trace tree (agent flow overview)

```bash
langsmith trace get <trace-id> --project ai-accounting-agent-comp --format pretty
```

This shows the hierarchy:
```
handle_accounting_task (chain)
└── run_agent (chain)
    ├── gemini_ocr (llm)
    ├── claude_1 (llm)        ← first LLM call
    ├── tripletex_post (tool) ← tool execution
    ├── claude_2 (llm)        ← second LLM call
    └── ...
```

### List all runs in a trace (chronological, with I/O)

```bash
langsmith run list \
  --project ai-accounting-agent-comp \
  --trace-ids <trace-id> \
  --include-io \
  --include-metadata \
  --format json
```

Key fields per run:
- `name`: `claude_N` (LLM) or `tripletex_*` (tool)
- `run_type`: `llm`, `tool`, or `chain`
- `inputs`: for tools — `path`, `args` (the API call details); for LLM — `message_count`, `latest_input`
- `outputs`: for tools — `status_code`, `success`, `body`, `error`; for LLM — `stop_reason`, `thinking`, `text`, `tool_calls`
- `error`: non-null if the run failed

### Get a single run with full I/O

```bash
langsmith run get <run-id> --project ai-accounting-agent-comp --include-io --format pretty
```

### Filter runs by type

```bash
# All tool calls
langsmith run list --project ai-accounting-agent-comp --run-type tool --format pretty

# Only errors
langsmith run list --project ai-accounting-agent-comp --error --format pretty

# Only LLM calls
langsmith run list --project ai-accounting-agent-comp --run-type llm --format pretty
```

### Filter by metadata (e.g., find by task_id)

```bash
langsmith run list --project ai-accounting-agent-comp --metadata task_id=<task-id> --format json
```

### Filter by time

```bash
# Last 60 minutes
langsmith run list --project ai-accounting-agent-comp --last-n-minutes 60

# Since a specific timestamp
langsmith run list --project ai-accounting-agent-comp --since 2026-03-21T07:00:00Z
```

### Filter by latency

```bash
# Slow traces (>60s)
langsmith run list --project ai-accounting-agent-comp --min-latency 60 --run-type chain
```

---

## GCS Log Reference

### List request logs

```bash
# Competition logs
gsutil ls gs://ai-nm26osl-1799-competition-logs/requests/

# Dev logs
gsutil ls gs://ai-nm26osl-1799-dev-logs/requests/
```

Filenames follow the pattern: `requests/{timestamp}_{task_id}_{prompt_preview}.json`

### Read a request log

```bash
gsutil cat gs://ai-nm26osl-1799-competition-logs/requests/<filename>.json | python3 -m json.tool
```

### GCS payload structure

```json
{
  "task_id": "a1b2c3d4e5f6",
  "request": {
    "prompt": "Register invoice from ...",
    "files": [
      {
        "filename": "invoice.pdf",
        "mime_type": "application/pdf",
        "content_base64": "JVBERi0xLjQ..."
      }
    ],
    "tripletex_credentials": {
      "base_url": "https://xxx.tripletex.dev/v2",
      "session_token": "..."
    }
  },
  "result": {
    "status": "completed",
    "iterations": 11,
    "time_ms": 172540,
    "api_calls": 12,
    "api_errors": 2,
    "error_details": [
      {
        "tool": "tripletex_post",
        "path": "/incomingInvoice",
        "status": 403,
        "error": "You do not have permission to access this feature."
      }
    ],
    "tokens": {
      "input": 97000,
      "output": 5000,
      "cache_creation": 12000,
      "cache_read": 80000
    }
  },
  "timestamp": "2026-03-21T07:08:31.846563+00:00",
  "agent_version": "ai-accounting-agent-det-00042-abc"
}
```

### Decode attached files from GCS

To inspect what the evaluator actually sent (useful for OCR debugging):

```bash
# Extract and decode a PDF file from the request log
gsutil cat gs://ai-nm26osl-1799-competition-logs/requests/<filename>.json \
  | python3 -c "
import json, sys, base64
data = json.load(sys.stdin)
for f in data['request'].get('files', []):
    name = f['filename']
    raw = base64.b64decode(f['content_base64'])
    with open(name, 'wb') as out:
        out.write(raw)
    print(f'Saved {name} ({len(raw)} bytes)')
"
```

---

## Cross-referencing GCS and LangSmith

### By task_id (after correlation ID was added)

```bash
# 1. Find the GCS log
gsutil ls gs://ai-nm26osl-1799-competition-logs/requests/ | grep <task_id>

# 2. Find the LangSmith trace
langsmith run list --project ai-accounting-agent-comp --metadata task_id=<task_id> --format pretty
```

### By timestamp + prompt (for older logs without task_id)

```bash
# 1. List GCS logs around a time window
gsutil ls gs://ai-nm26osl-1799-competition-logs/requests/ | grep "2026-03-21T07"

# 2. List LangSmith traces in the same window
langsmith trace list --project ai-accounting-agent-comp --since 2026-03-21T07:00:00Z --format pretty

# 3. Match by prompt text — read GCS log prompt, find the matching LangSmith trace
```

---

## Debugging Workflow

1. **Start from LangSmith** — list recent traces, identify failures or slow runs
2. **Drill into trace tree** — see the full agent flow, identify retry loops and errors
3. **Check tool I/O** — look at specific tool call inputs/outputs for API errors
4. **Cross-reference GCS** — get the full request payload (files, prompt, credentials) for replay
5. **Identify patterns** — common errors, wasted API calls, missing recipes
6. **Suggest prompt/recipe improvements** — changes to `prompts.py` to prevent the error pattern

### Key things to look for

- **403 errors**: endpoint not available in sandbox — add to system prompt blocklist
- **422 validation errors**: wrong field format — improve recipe with correct schema
- **Delete-then-retry loops**: agent created something wrong, deleted, tried again — improve recipe to get it right first time
- **High iteration count**: agent is struggling — check if there's a missing recipe
- **Timeout (270s)**: agent didn't finish — check for infinite retry loops
- **Token usage**: cache_read >> 0 means prompt caching is working; cache_creation on every call means it's not

---

## Agent Architecture (for context)

```
POST / → main.py:solve()
  ├── Generate task_id (correlation ID for GCS + LangSmith)
  ├── _preconfigure_bank_account() — ensures ledger 1920 has bank account
  ├── _handle_task() — @traceable root span
  │   ├── process_files() — decode base64, extract PDF text + images
  │   └── run_agent() — agent.py
  │       ├── gemini_ocr() — Gemini extracts text from images
  │       └── Claude agentic loop (max 20 iterations, 270s timeout)
  │           ├── claude_N (llm) — Claude decides what to do
  │           └── tripletex_* (tool) — executes API call
  └── _save_request_to_gcs() — full payload + result to GCS
```

Key files for improvement:
- `prompts.py` — system prompt with recipes and rules (most impactful to change)
- `api_knowledge/cheat_sheet.py` — API reference (941 lines)
- `agent.py` — agentic loop, tool definitions, OCR
