# AI Accounting Agent — Project Guide

## Competition

NM i AI 2026 — Tripletex task. Agent receives accounting prompts (multilingual: NO, EN, ES, PT, DE, FR) and executes them against the Tripletex REST API.

- **Deadline:** Saturday March 22 at 15:00 CET
- **Submissions:** 180/day (resets daily)
- **Scoring:** Field-by-field verification, tier multipliers (1x/2x/3x), efficiency bonus
- **Tiers:** 1 & 2 open now, Tier 3 opens Saturday morning

## Containers

| Service | Purpose | GCS Bucket | URL |
|---------|---------|------------|-----|
| `ai-accounting-agent-det` | **Dev/testing** | `ai-nm26osl-1799-dev-logs` | `https://ai-accounting-agent-det-590159115697.europe-north1.run.app` |
| `accounting-agent-comp` | **Competition only** | `ai-nm26osl-1799-competition-logs` | `https://accounting-agent-comp-590159115697.europe-north1.run.app` |
| `ai-accounting-agent` | Legacy Gemini (do not use) | none | — |

**Rules:**
- **NEVER** send test requests to `accounting-agent-comp` — it logs everything to GCS for replay
- Test against `ai-accounting-agent-det` only
- Both containers use the same source code — only `REQUEST_LOG_BUCKET` env var differs
- Deploy both when shipping changes: dev first, then comp after verifying

### Deploy commands

```bash
# Dev (test here first)
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 --project ai-nm26osl-1799 --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs" --quiet

# Competition (only after dev is verified)
gcloud run deploy accounting-agent-comp --source . --region europe-north1 --project ai-nm26osl-1799 --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs" --quiet
```

## Architecture

```
POST / → main.py
  ├── _save_request_to_gcs()     — full payload to GCS (if REQUEST_LOG_BUCKET set)
  ├── _preconfigure_bank_account() — ensures ledger 1920 has bank account
  ├── gemini_ocr()               — Gemini extracts text from images (if any)
  ├── parse_prompt()             — Claude Opus 4.6 extracts TaskPlan JSON
  ├── is_known_pattern()         — validates plan can run deterministically
  │   ├── TRUE → execute_plan()  — deterministic API calls (no LLM)
  │   └── FALSE → run_tool_loop() — Claude tool-use fallback
  └── return {"status": "completed"}
```

- **Claude Opus 4.6** via Vertex AI (region `us-east5`, project `ai-nm26osl-1799`)
- **Gemini** retained for OCR only (lazy-initialized via `_get_genai_client()`)
- API knowledge in `api_knowledge/cheat_sheet.py` (941 lines, injected into system prompt)

## Key Files

| File | What |
|------|------|
| `main.py` | FastAPI endpoint, request logging, bank pre-config |
| `agent.py` | Claude tool-use loop, gemini_ocr, tool definitions |
| `planner.py` | Claude parse, pattern matcher, FallbackContext |
| `executor.py` | Deterministic execution, pre-checks, vatType retry |
| `claude_client.py` | Shared AnthropicVertex client (cached singleton) |
| `task_registry.py` | Entity schemas, action schemas, known constants |
| `tripletex_api.py` | HTTP client wrapper (Basic Auth, 30s timeout) |
| `api_knowledge/cheat_sheet.py` | Full API reference (system prompt) |

## Ground Truth

- `docs/analysis/competition-ground-truth.md` — 25 real competition requests analyzed
- `tests/competition_tasks/` — 23 JSON fixtures in evaluator format
- GCS buckets contain full request payloads for replay

## Testing

```bash
# Run all unit tests
python -m pytest tests/ -v --ignore=tests/integration

# Run smoke tests against dev container
source .env && export TRIPLETEX_SESSION_TOKEN
python smoke_test.py --tier 1
python smoke_test.py --tier 2
```

## Important Implementation Notes

- Python 3.13 locally, 3.11 in Docker — `X | None` syntax is fine
- `genai_client` is lazy-initialized (NOT module-level) — prevents cold-start crashes
- Evaluator sends `POST /` (root path), not `/solve`
- `tripletex_credentials` may be `null` — always use `or {}`
- vatType IDs vary per sandbox — executor retries without vatType on rejection
- All `requests.*` calls have `timeout=30`
- Cloud Run must allow unauthenticated access for the evaluator
