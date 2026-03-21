# AI Accounting Agent — Team Guide

## What This Is

NM i AI 2026 competition entry. The agent receives accounting prompts in 7 languages (NO, NN, EN, DE, FR, PT, ES) and executes them against the Tripletex REST API. It uses Claude Opus 4.6 for reasoning/tool use and Gemini for OCR on attached files.

**Deadline:** Saturday March 22 at 15:00 CET
**Submissions:** 180/day (resets daily)
**Scoring:** Field-by-field verification, tier multipliers (1x/2x/3x), efficiency bonus (fewer API calls = higher score), every 4xx error reduces score.

---

## Quick Start

### 1. Environment Setup

```bash
cp .env.example .env
# Fill in these values:
```

Required `.env` variables:

| Variable | What | Where to get |
|----------|------|-------------|
| `GCP_PROJECT_ID` | `ai-nm26osl-1799` | GCP console |
| `GCP_LOCATION` | `global` | Fixed |
| `TRIPLETEX_BASE_URL` | `https://kkpqfuj-amager.tripletex.dev/v2` | Competition sandbox |
| `TRIPLETEX_SESSION_TOKEN` | Session token for sandbox | Tripletex sandbox |
| `LANGSMITH_API_KEY` | Dev tracing key | LangSmith settings |
| `LANGSMITH_API_KEY_COMP` | Competition tracing key | LangSmith settings |

You also need GCP auth:
```bash
gcloud auth application-default login
gcloud config set project ai-nm26osl-1799
```

### 2. Run Tests

```bash
python -m pytest tests/ -v --ignore=tests/integration
```

### 3. Run Smoke Tests Against Dev Container

```bash
source .env && export TRIPLETEX_SESSION_TOKEN
python smoke_test.py --tier 1
python smoke_test.py --tier 2
```

---

## Architecture

```
POST / (evaluator)
  │
  ├── main.py: solve()
  │     ├── Generate task_id (12-char hex — correlation ID)
  │     ├── _preconfigure_bank_account() → ensures ledger 1920 has bank account
  │     ├── process_files() → decode base64, extract PDF text (pymupdf), render pages as PNG
  │     │
  │     └── run_agent() → agent.py
  │           ├── gemini_ocr() → send PNG images to Gemini, get structured JSON
  │           └── Claude agentic loop (max 20 iterations, 270s timeout)
  │                 ├── System prompt: rules + 21 recipes + API cheat sheet
  │                 ├── claude_N (LLM call) → decides what tool to call
  │                 └── tripletex_* (tool call) → executes API request
  │
  └── _save_request_to_gcs() → full payload + result to GCS bucket
```

### Key Files

| File | What |
|------|------|
| `main.py` | FastAPI endpoint, request logging to GCS, bank pre-config |
| `agent.py` | Claude agentic loop, streaming, Gemini OCR, 4 tool definitions |
| `prompts.py` | System prompt builder: loads recipes + cheat sheet + rules |
| `claude_client.py` | Cached AnthropicVertex singleton (region: us-east5) |
| `tripletex_api.py` | HTTP wrapper (Basic Auth `0:<token>`, 30s timeout) |
| `file_handler.py` | PDF text extraction (pymupdf), PDF-to-PNG rendering |
| `observability.py` | LangSmith tracing helpers (graceful no-op if unavailable) |
| `api_knowledge/cheat_sheet.py` | Full Tripletex API reference (~960 lines) |

### Models

| Model | Purpose | Region |
|-------|---------|--------|
| Claude Opus 4.6 | Agent reasoning + tool use | us-east5 (Vertex AI) |
| Gemini 3.1 Pro Preview | OCR only (lazy-initialized) | global (Vertex AI) |

---

## Containers

| Container | Purpose | URL |
|-----------|---------|-----|
| `ai-accounting-agent-det` | Dev/testing | `https://ai-accounting-agent-det-590159115697.europe-north1.run.app` |
| `accounting-agent-comp` | Competition scoring | `https://accounting-agent-comp-590159115697.europe-north1.run.app` |

**Rules:**
- **NEVER** send test requests to `accounting-agent-comp` — it logs everything for replay
- Test against `ai-accounting-agent-det` only
- Both use the same source code — only the GCS bucket and LangSmith project differ
- Always deploy to dev first, verify, then deploy to comp

### Deploy Commands

```bash
# Always source .env first (loads LangSmith API keys)
source .env

# Dev (test here first)
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-dev,LANGSMITH_API_KEY=$LANGSMITH_API_KEY" \
  --quiet

# Competition (ONLY after dev is verified)
gcloud run deploy accounting-agent-comp --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-comp,LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP" \
  --quiet
```

**WARNING:** `--set-env-vars` **replaces ALL** env vars on the container. If you omit the LangSmith API key it gets wiped and tracing breaks silently. Dev and comp use **separate** LangSmith keys.

---

## Observability

We have two parallel observability systems linked by a **task_id** (12-char hex).

### LangSmith (Agent Behavior)

**What it captures:** LLM calls (thinking, tool selections, stop reasons), tool executions (inputs/outputs/status codes), token usage, latency.

**Projects:**
- `ai-accounting-agent-dev` — dev container traces
- `ai-accounting-agent-comp` — competition container traces

**CLI examples:**
```bash
export PATH="/Users/torbjornbeining/.local/bin:$PATH"
source .env
export LANGSMITH_API_KEY=$LANGSMITH_API_KEY       # for dev
# export LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP  # for comp

# List recent traces
langsmith trace list --project ai-accounting-agent-dev --limit 10 --format pretty

# Find trace by task_id
langsmith run list --project ai-accounting-agent-dev --metadata task_id=<task_id> --format json

# View full trace tree
langsmith run list --project ai-accounting-agent-dev --trace-ids <trace-id> --include-io --format json

# Filter by errors
langsmith run list --project ai-accounting-agent-dev --error --format pretty
```

**LangSmith trace hierarchy:**
```
handle_accounting_task (chain)        <- root, has task_id in metadata
└── run_agent (chain)
    ├── gemini_ocr (llm)             <- OCR result
    ├── claude_1 (llm)               <- first LLM call
    ├── tripletex_post (tool)        <- tool execution
    ├── claude_2 (llm)               <- second LLM call
    └── ...
```

### GCS (Full Request Payloads)

**What it captures:** Complete request payload (prompt, attached files as base64, Tripletex credentials), agent result (iterations, errors, timing, token usage).

**Buckets:**
- `ai-nm26osl-1799-dev-logs` — dev requests
- `ai-nm26osl-1799-competition-logs` — competition requests

**CLI examples:**
```bash
# List recent logs
gsutil ls gs://ai-nm26osl-1799-competition-logs/requests/ | tail -10

# Read full payload
gsutil cat gs://ai-nm26osl-1799-competition-logs/requests/<filename>.json | python3 -m json.tool

# Find by task_id
gsutil ls gs://ai-nm26osl-1799-competition-logs/requests/ | grep <task_id>
```

**GCS filename format:** `requests/{timestamp}_{task_id}_{prompt_preview}.json`

**GCS payload structure:**
```json
{
  "task_id": "a1b2c3d4e5f6",
  "request": {
    "prompt": "Register invoice from ...",
    "files": [{"filename": "invoice.pdf", "mime_type": "application/pdf", "content_base64": "..."}],
    "tripletex_credentials": {"base_url": "...", "session_token": "..."}
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

### Correlation

| Location | Where task_id appears |
|----------|----------------------|
| GCS filename | `requests/{timestamp}_{task_id}_{prompt_preview}.json` |
| GCS payload | `"task_id": "a1b2c3d4e5f6"` |
| LangSmith | `metadata.task_id` on the root `handle_accounting_task` trace |
| Cloud Run logs | `task_id=a1b2c3d4e5f6` |

---

## Recipes

Recipes are the primary lever for improving competition scores. Each recipe is a markdown file in `recipes/` that tells the agent the exact API call sequence with exact field names. The agent's system prompt instructs it to **always follow recipes before improvising**.

### Current Recipes (21)

| # | Recipe | Tier | Key |
|---|--------|------|-----|
| 01 | Create customer | 1 | POST /customer |
| 02 | Create employee | 1 | POST /employee |
| 03 | Create supplier | 1 | POST /supplier |
| 04 | Create departments | 1 | Parallel POST /department |
| 05 | Create product | 1 | Never include `number` field |
| 06 | Create invoice | 1 | Customer -> product -> order -> invoice (16% of competition) |
| 07 | Register payment | 1 | PUT /invoice/:payment with **query params, not body** |
| 08 | Create project | 1 | POST /project |
| 09 | Fixed price project | 1 | POST /project variant |
| 10 | Run salary | 1 | POST /payslip |
| 11 | Register supplier invoice | 1 | POST /incomingInvoice (or voucher fallback on 403) |
| 12 | Create order | 1 | POST /order |
| 13 | Custom dimension voucher | 1 | Voucher with custom dimensions |
| 14 | Reverse payment voucher | 1 | Voucher for payment reversal |
| 15 | Credit note | 1 | POST /creditNote |
| 16 | Register hours | 1 | POST /timeSheet |
| 17 | Travel expense | 2 | Per diem + costs in one POST. Uses `count` not `countDays`, `comments` not `description` |
| 18 | Bank reconciliation | 2 | POST /bank/reconciliation |
| 19 | Asset registration | 3 | POST /asset with depreciation |
| 20 | Year-end corrections | 3 | Find and correct ledger errors |
| 21 | Employee onboarding (PDF) | 3 | Extract from PDF contract. Uses `percentageOfFullTimeEquivalent` |

### How Recipes Work

1. `prompts.py` loads all `recipes/*.md` files at startup
2. They're concatenated into the system prompt under "Recipes for Known Task Types"
3. The system prompt tells Claude: "Before making ANY API call, find the matching recipe"
4. Each recipe specifies exact JSON field names, known gotchas, and expected call count

### Editing Recipes

Change the recipe markdown file, then deploy. That's it. The prompt rebuilds on each request.

```bash
# Edit the recipe
vim recipes/17_travel_expense.md

# Verify it loads
python3 -c "from prompts import build_system_prompt; p = build_system_prompt(); print('OK' if '<unique text>' in p else 'MISSING')"

# Deploy to dev and test
```

---

## Skills (Claude Code Workflows)

We have 4 Claude Code skills that form an integrated debugging and optimization workflow. Invoke them with `/skill-name` in Claude Code.

### Workflow Overview

```
Competition submission comes in
        │
        v
/agent-debugger ─── Investigate traces, find errors, identify root cause
        │
        v
/save-and-replay ── Save the failing request locally for reproduction
        │
        v
/recipe-builder ─── Fix or create the recipe (curl against sandbox API)
        │
        v
/save-and-replay ── Replay saved request against dev to verify fix
        │
        v
/recipe-validator ─ Deploy to dev, full end-to-end validation
        │
        v
Deploy to competition (manual confirmation)
```

### /agent-debugger

**When:** After a competition submission, to investigate what went wrong (or right).

**What it does:**
1. Lists recent LangSmith traces (filters already-analyzed ones)
2. Pulls trace hierarchy (LLM calls, tool executions, errors)
3. Cross-references with GCS logs (full payload, timing, files)
4. Inspects OCR quality for file-based tasks
5. Identifies patterns (403s, 422 validation errors, retry loops, timeouts)
6. Marks traces as analyzed to avoid re-investigation
7. Recommends next action (recipe fix, code fix, replay)

**Key commands it uses:**
```bash
langsmith trace list --project <project> --limit 20 --include-feedback --format json
langsmith run list --project <project> --trace-ids <id> --include-io --format json
gsutil cat gs://<bucket>/requests/<filename>.json
```

### /save-and-replay

**When:** After finding a failure to save it, or after fixing a recipe to verify the fix.

**Save:**
```bash
python scripts/save_competition_requests.py --task-id <task_id>
# Saves to competition/requests/{task_id}.json (credentials stripped)
```

**Replay:**
```bash
source .env && export TRIPLETEX_BASE_URL TRIPLETEX_SESSION_TOKEN
python scripts/replay_request.py competition/requests/<task_id>.json
```

### /recipe-builder

**When:** Creating a new recipe or fixing a broken one.

**What it does:**
1. Checks existing recipes (never duplicates)
2. Explores the Tripletex API with curl to discover correct field names and schemas
3. Tests the full call sequence against the sandbox
4. Optimizes for minimum calls and zero errors
5. Writes the recipe file with all required sections
6. Verifies the recipe loads into the system prompt

**Key principle:** Every field name in a recipe must be verified by actual API calls, not guessed.

### /recipe-validator

**When:** After creating/updating a recipe, to do a full end-to-end deployment test.

**What it does:**
1. Deploys to dev container
2. Sends test request (text or file-based)
3. Finds the trace in GCS + LangSmith
4. Compares actual agent behavior against recipe expectations
5. Verifies sandbox state (entities created correctly)
6. Reports pass/fail with comparison table
7. Optionally promotes to competition container

---

## Common Patterns and Gotchas

### API Field Gotchas (The Agent Will Hit These Without Recipes)

| Gotcha | Wrong | Correct |
|--------|-------|---------|
| Payment registration | JSON body | **Query params** on PUT |
| Object references | Bare integer `123` | Always `{"id": 123}` |
| Product creation | Include `number` field | **Omit** `number` (causes conflict) |
| VAT type IDs | Hardcode `{"id": 3}` | **Never hardcode** — lookup or omit |
| Travel expense count | `countDays` | `count` |
| Travel expense cost text | `description` | `comments` |
| Travel expense paymentType | Top-level | **On each cost item only** |
| Rate category field filter | `fields=id,description` | `fields=id,name` |
| Cost category field filter | `fields=id,name` | `fields=id,description` |
| Employment percentage | `percentOfFullTimeEquivalent` | `percentageOfFullTimeEquivalent` |
| Department number | Integer | **String** |

### Competition Scoring Optimization

1. **Minimize API calls** — every unnecessary call reduces efficiency bonus
2. **Zero 4xx errors** — each error is a penalty. Recipes prevent these.
3. **No verification GETs** — don't GET after POST to "check". Trust the 201.
4. **Embed sub-entities** — include orderLines in the order POST, costs in travel expense POST
5. **Use known constants** — NOK = `{"id": 1}`, Norway = `{"id": 162}`
6. **Stop when done** — don't add summary text after the last tool call

### Timeout Budget

- **Hard limit:** 300s (competition enforced)
- **Agent timeout:** 270s (30s buffer)
- **Max iterations:** 20
- **Typical Tier 1:** 15-30s, 2-5 iterations
- **Typical Tier 2:** 40-90s, 5-10 iterations
- **Typical Tier 3:** 60-180s, 6-12 iterations

---

## File-Based Tasks (PDFs, Images)

Some competition tasks include attached files. The processing pipeline:

```
Evaluator sends base64 file
     │
     v
file_handler.py: process_files()
     ├── PDF: pymupdf extracts text + renders pages as PNG
     ├── Image: passed through as-is
     └── CSV/Text: decoded to string
     │
     v
agent.py: gemini_ocr()
     └── Sends PNG images to Gemini
     └── Returns structured JSON (field labels as keys)
     │
     v
Both pymupdf text AND OCR JSON included in Claude's user message
```

**OCR prompt** asks Gemini to return a flat JSON object with field labels as keys. This gives the agent two complementary views of the document: raw text extraction and structured field extraction.

---

## Project Structure

```
AIAccountingAgent/
├── main.py                    # FastAPI endpoint
├── agent.py                   # Claude agentic loop + Gemini OCR
├── prompts.py                 # System prompt builder (loads recipes + cheat sheet)
├── claude_client.py           # AnthropicVertex singleton
├── tripletex_api.py           # HTTP client wrapper
├── file_handler.py            # PDF/image/text processing
├── observability.py           # LangSmith tracing helpers
├── smoke_test.py              # End-to-end smoke tests
├── Dockerfile                 # Python 3.11-slim + uvicorn
├── requirements.txt           # 9 dependencies
├── .env                       # Local secrets (not committed)
├── .env.example               # Template
├── CLAUDE.md                  # Project instructions for Claude Code
├── guide.md                   # This file
│
├── api_knowledge/
│   └── cheat_sheet.py         # Full Tripletex API reference (~960 lines)
│
├── recipes/                   # 21 task-type recipes (the main optimization lever)
│   ├── 01_create_customer.md
│   ├── ...
│   └── 21_employee_onboarding.md
│
├── scripts/
│   ├── save_competition_requests.py   # Download GCS logs locally
│   └── replay_request.py             # Replay saved request against dev
│
├── competition/
│   └── requests/              # Saved competition requests (for replay)
│       ├── 52de793e3d13.json
│       └── ...
│
├── tests/
│   ├── test_agent.py          # Agent loop tests
│   ├── test_prompts.py        # System prompt + recipe loading
│   ├── test_file_handler.py   # File processing
│   ├── ...
│   ├── competition_tasks/     # 38 JSON fixtures in evaluator format
│   └── integration/           # Live sandbox integration tests
│
├── docs/
│   ├── analysis/
│   │   └── competition-ground-truth.md   # 25 real requests analyzed
│   ├── architecture-decisions.md
│   ├── competition-format.md
│   └── plans/                 # Historical design documents
│
└── .claude/
    └── skills/                # Claude Code automation skills
        ├── agent-debugger/
        ├── recipe-builder/
        ├── recipe-validator/
        └── save-and-replay/
```

---

## Typical Day Workflow

### 1. Check latest competition results

```
/agent-debugger — latest traces in accounting-agent-comp
```

This pulls recent LangSmith traces, shows call counts, errors, and timing. Identifies which tasks scored well and which need work.

### 2. Fix a failing task type

```
/save-and-replay — save the failing request
/recipe-builder — fix the recipe (explores API with curl, tests fields)
/save-and-replay — replay to verify the fix (compare error count before/after)
/recipe-validator — deploy to dev, full end-to-end validation
```

### 3. Deploy to competition

After validation passes:
```bash
source .env
gcloud run deploy accounting-agent-comp --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-comp,LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP" \
  --quiet
```

### 4. Iterate

Repeat: debug traces -> save failing requests -> fix recipes -> validate -> deploy.

Each recipe improvement is a prompt edit that goes live on next deploy. No code changes needed for most fixes — just edit the recipe markdown and redeploy.
