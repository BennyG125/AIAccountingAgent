---
name: agent-debugger
description: Debug the AI Accounting Agent by investigating LangSmith traces and GCS request logs. Use this skill whenever the user mentions debugging agent behavior, checking logs, investigating failures or errors, looking at traces, analyzing what happened with a request, finding slow runs or timeouts, or wants to understand why the agent did something. Also trigger when the user mentions task_id, trace_id, LangSmith, GCS logs, competition logs, dev logs, or wants to replay/inspect a request. Even if the user just says "check the logs" or "what went wrong" in the context of this project, use this skill.
---

# Agent Debugger

Debug the AI Accounting Agent by correlating LangSmith traces (agent thinking, tool calls, errors) with GCS request logs (full payloads, files, results).

## Two Observability Systems

| System | What it captures | Query tool |
|--------|-----------------|------------|
| **LangSmith** | Agent behavior: LLM calls (thinking, tool selections, stop reasons), tool executions (inputs/outputs/status codes), token usage, latency | `langsmith` CLI |
| **GCS** | Full request payload: prompt, attached files (base64), Tripletex credentials, agent result (iterations, errors, timing) | `gsutil` CLI |

## Correlation ID: task_id

Every request generates a 12-char hex `task_id` that links both systems:

| Location | Where task_id appears |
|----------|----------------------|
| GCS filename | `requests/{timestamp}_{task_id}_{prompt_preview}.json` |
| GCS payload | `"task_id": "a1b2c3d4e5f6"` |
| LangSmith | `metadata.task_id` on the root `handle_accounting_task` trace |
| Cloud Run logs | `task_id=a1b2c3d4e5f6` |

For older traces without task_id, correlate by matching timestamp + prompt text between the two systems.

## Environment Setup

Before running any debug commands, set up the environment:

```bash
export PATH="/Users/torbjornbeining/.local/bin:$PATH"
source .env
```

Then configure for the target environment:

```bash
# Dev environment
export LANGSMITH_API_KEY=$LANGSMITH_API_KEY
export LANGSMITH_PROJECT=ai-accounting-agent-dev
GCS_BUCKET=ai-nm26osl-1799-dev-logs

# Competition environment
export LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP
export LANGSMITH_PROJECT=ai-accounting-agent-comp
GCS_BUCKET=ai-nm26osl-1799-competition-logs
```

Default to **competition** unless the user specifies dev. Competition is where scoring happens, so most debugging starts there.

## Debugging Workflow

### 1. Identify what you're looking for

- **Specific request by task_id** → jump to step 2 with the task_id
- **Recent failures or errors** → list recent traces filtered by error
- **Slow or timed-out runs** → filter by latency
- **Pattern analysis across multiple runs** → list and compare several traces
- **Specific competition submission** → check GCS logs by timestamp

**Skip already-analyzed traces:** When listing traces, use `--include-feedback` to see which ones have been analyzed. Traces with `feedback_stats` containing `status: analyzed` have already been investigated — skip them unless re-analysis is needed.

```bash
# List recent traces, showing which are already analyzed
langsmith trace list --project $LANGSMITH_PROJECT --limit 20 --include-feedback --format json \
  | python3 -c "
import json, sys
for t in json.load(sys.stdin):
    fb = t.get('feedback_stats', {})
    tag = ' [ANALYZED]' if fb else ''
    print(f'{t[\"start_time\"][:19]}  {t[\"run_id\"][:36]}{tag}')
"
```

### 2. Query LangSmith (agent behavior)

```bash
# List recent traces
langsmith trace list --project $LANGSMITH_PROJECT --limit 10 --format pretty

# Find trace by task_id
langsmith run list --project $LANGSMITH_PROJECT --metadata task_id=<task_id> --format json

# View full trace tree (shows agent flow)
langsmith trace get <trace-id> --project $LANGSMITH_PROJECT --format pretty

# List all runs in a trace with full I/O
langsmith run list --project $LANGSMITH_PROJECT --trace-ids <trace-id> --include-io --include-metadata --format json

# Get details of a single run
langsmith run get <run-id> --project $LANGSMITH_PROJECT --include-io --format pretty
```

**Filtering:**
```bash
# By type
langsmith run list --project $LANGSMITH_PROJECT --run-type tool --format pretty    # tool calls
langsmith run list --project $LANGSMITH_PROJECT --run-type llm --format pretty     # LLM calls
langsmith run list --project $LANGSMITH_PROJECT --error --format pretty            # errors only

# By time
langsmith run list --project $LANGSMITH_PROJECT --last-n-minutes 60
langsmith run list --project $LANGSMITH_PROJECT --since 2026-03-21T07:00:00Z

# Slow traces (>60s)
langsmith run list --project $LANGSMITH_PROJECT --min-latency 60 --run-type chain
```

**Key fields per LangSmith run:**
- `name`: `claude_N` (LLM) or `tripletex_*` (tool)
- `run_type`: `llm`, `tool`, or `chain`
- `inputs`: for tools → `path`, `args`; for LLM → `message_count`, `latest_input`
- `outputs`: for tools → `status_code`, `success`, `body`, `error`; for LLM → `stop_reason`, `thinking`, `text`, `tool_calls`
- `error`: non-null if the run failed

### 3. Query GCS (full request payload)

```bash
# List logs (use the appropriate bucket)
gsutil ls gs://$GCS_BUCKET/requests/

# Find by task_id
gsutil ls gs://$GCS_BUCKET/requests/ | grep <task_id>

# Read full payload
gsutil cat gs://$GCS_BUCKET/requests/<filename>.json | python3 -m json.tool
```

**GCS payload structure:**
```json
{
  "task_id": "a1b2c3d4e5f6",
  "request": {
    "prompt": "Register invoice from ...",
    "files": [{"filename": "invoice.pdf", "mime_type": "application/pdf", "content_base64": "..."}],
    "tripletex_credentials": {"base_url": "https://xxx.tripletex.dev/v2", "session_token": "..."}
  },
  "result": {
    "status": "completed",
    "iterations": 11,
    "time_ms": 172540,
    "api_calls": 12,
    "api_errors": 2,
    "error_details": [{"tool": "tripletex_post", "path": "/incomingInvoice", "status": 403, "error": "..."}],
    "tokens": {"input": 97000, "output": 5000, "cache_creation": 12000, "cache_read": 80000}
  },
  "timestamp": "2026-03-21T07:08:31.846563+00:00"
}
```

**Decode attached files** (useful for OCR debugging):
```bash
gsutil cat gs://$GCS_BUCKET/requests/<filename>.json | python3 -c "
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

### 4. Inspect attached files and OCR (for file-based tasks)

Some tasks include attached files (PDFs, images, CSVs). The processing pipeline is:
1. `process_files()` decodes base64, extracts PDF text via pymupdf, renders PDF pages as PNG
2. `gemini_ocr()` sends images to Gemini for OCR text extraction
3. OCR text is appended to file contents and included in Claude's user message

**Check if a request had files:**
```bash
gsutil cat gs://$GCS_BUCKET/requests/<filename>.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
files = data['request'].get('files', [])
print(f'Files: {len(files)}')
for f in files:
    print(f'  {f[\"filename\"]} ({f[\"mime_type\"]}, {len(f.get(\"content_base64\", \"\"))} base64 chars)')
"
```

**Decode and save attached files locally** (to inspect what the evaluator sent):
```bash
gsutil cat gs://$GCS_BUCKET/requests/<filename>.json | python3 -c "
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

**Check OCR quality in LangSmith:**
The `gemini_ocr` span is the first child of `run_agent` in the trace tree. Its outputs include:
- `ocr_text`: the full text Gemini extracted
- `chars_extracted`: character count

```bash
# Find the gemini_ocr run in a trace
langsmith run list --project $LANGSMITH_PROJECT --trace-ids <trace-id> --include-io --format json
# Look for the run with name "gemini_ocr" and run_type "llm"
```

**OCR debugging patterns:**
| Pattern | What it means | Fix |
|---------|--------------|-----|
| `chars_extracted: 0` but files were attached | OCR failed or no images in the file | Check if PDF has extractable text vs scanned images |
| OCR text is garbled or incomplete | Gemini struggled with the document | May need to adjust OCR prompt or image DPI in `agent.py` |
| OCR text is good but agent ignored data | Agent didn't use the extracted information | Recipe should explicitly reference OCR-extracted data |
| `(no images)` in OCR output | File was text/CSV, not an image-bearing PDF | Expected — text files are extracted directly by pymupdf |

### 5. Analyze patterns

Look for these common issues:

| Pattern | What it means | Fix |
|---------|--------------|-----|
| **403 errors** | Endpoint not available | Add to system prompt blocklist |
| **422 validation errors** | Wrong field format or missing required field | Improve recipe with correct schema |
| **Delete-then-retry loops** | Agent created wrong entity, deleted, retried | Improve recipe to get it right first time |
| **High iteration count (>10)** | Agent is struggling or looping | Check for missing recipe or bad guidance |
| **Timeout (270s)** | Agent didn't finish in time | Check for infinite retry loops |
| **cache_creation on every LLM call** | Prompt caching not working | System prompt is changing between calls |
| **cache_read >> 0** | Prompt caching working correctly | Good — no action needed |
| **Repeated calls to same endpoint** | Agent retrying without changing approach | Add guidance for when to stop retrying |

### 6. Mark the trace as analyzed

After completing your analysis, add feedback to the root run so it's not re-analyzed:

```bash
python3 -c "
from langsmith import Client
import os
client = Client(api_key=os.environ['LANGSMITH_API_KEY'])
client.create_feedback(
    run_id='<ROOT_RUN_ID>',
    key='status',
    value='analyzed',
    comment='Investigated via agent-debugger skill'
)
print('Marked as analyzed')
"
```

To see which traces have been analyzed, use `--include-feedback` and look for non-empty `feedback_stats`:
```bash
langsmith trace list --project $LANGSMITH_PROJECT --limit 20 --include-feedback --format json \
  | python3 -c "
import json, sys
for t in json.load(sys.stdin):
    fb = t.get('feedback_stats', {})
    tag = ' [ANALYZED]' if fb else ''
    print(f'{t[\"start_time\"][:19]}  {t[\"run_id\"][:36]}{tag}')
"
```

### 7. Suggest improvements

Based on patterns found, recommend changes to these files (ordered by impact):

1. **`prompts.py`** — system prompt with recipes and rules (most impactful, each change is prompt edit → redeploy → resubmit)
2. **`recipes/*.md`** — individual recipe files loaded by prompts.py
3. **`api_knowledge/cheat_sheet.py`** — API reference (941 lines)
4. **`agent.py`** — agentic loop, tool definitions, OCR
5. **`file_handler.py`** — file processing, PDF text extraction, image rendering (if OCR issues)

## Agent Architecture

```
POST / → main.py:solve()
  ├── Generate task_id (correlation ID)
  ├── _preconfigure_bank_account() → ensures ledger 1920 has bank account
  ├── _handle_task() → @traceable root span
  │   ├── process_files() → decode base64, extract PDF text + images
  │   └── run_agent() → agent.py
  │       ├── gemini_ocr() → Gemini extracts text from images
  │       └── Claude agentic loop (max 20 iterations, 270s timeout)
  │           ├── claude_N (llm) → Claude decides what to do
  │           └── tripletex_* (tool) → executes API call
  └── _save_request_to_gcs() → full payload + result to GCS
```

LangSmith trace hierarchy:
```
handle_accounting_task (chain)        ← root, has task_id in metadata
└── run_agent (chain)
    ├── gemini_ocr (llm)
    ├── claude_1 (llm)               ← first LLM call
    ├── tripletex_post (tool)        ← tool execution
    ├── claude_2 (llm)               ← second LLM call
    └── ...
```

## Next Steps

After completing your diagnosis, recommend the appropriate next action:

| Root cause | Recommendation |
|-----------|----------------|
| Recipe is wrong or missing (bad API sequence, missing fields, wrong endpoint) | "The issue is in the recipe. Want me to fix it? (invoke recipe-builder)" |
| Recipe exists but agent didn't follow it (wording unclear) | "The recipe wording needs improvement. Want me to update it? (invoke recipe-builder)" |
| Agent code bug (agent.py, tool definitions, OCR) | Suggest a code fix directly — no skill needed |
| Infrastructure issue (timeout, deployment, credentials) | Suggest the fix directly |

Do NOT automatically invoke recipe-builder. Present the diagnosis and let the user decide.

## Full Reference

For the complete CLI reference, advanced filtering, and additional cross-referencing techniques, read `docs/debugging-skill-prompt.md` in the project root.
