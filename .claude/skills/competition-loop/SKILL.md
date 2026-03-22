---
name: competition-loop
description: Pull GCP competition logs, analyze error patterns, fix classifier/recipes/prompts/execution plans, test, and deploy. Use this whenever the user says "check logs", "analyze competition", "run the loop", "what's failing", "improve scores", "review and fix", "check errors", or after a competition submission round. Also trigger when the user mentions error patterns, classifier gaps, competition results, or wants to improve competition scores. Even "run it again" or "check what broke" in the context of competition work should trigger this skill.
---

# Competition Optimization Loop

The repeatable cycle: Save → Coverage → Analyze → Fix → Replay → Deploy.

The deterministic executor is dramatically better than Claude fallback (0 errors vs ~17%, 7x faster). The goal is always to move more task types to deterministic and fix the remaining Claude errors.

## Phase 1: Save & Tag Requests

Save first — new requests are auto-tagged with `task_type`, `classified_by`, and `tier` on save:

```bash
python scripts/save_competition_requests.py
```

This gives you fresh tagged data before any analysis.

## Phase 2: Coverage Report

Run the pipeline coverage report to see structural gaps at a glance:

```bash
python scripts/coverage_report.py          # Full matrix
python scripts/coverage_report.py --gaps   # Only task types with missing components
```

This shows per-task-type coverage across 6 components: classifier, optimal sequence, execution plan, recipe, guard, whitelist — plus how many saved requests exist per type.

Structural gaps (missing plan, missing optimal sequence) are root causes that show up as errors in logs. The coverage report tells you what to fix before you even look at logs.

## Phase 3: Analyze Logs

Run the bundled analysis script for runtime errors:

```bash
python .claude/skills/competition-loop/scripts/analyze_logs.py --hours 24
```

This downloads from GCS, parses all logs, and outputs:
- **Executor distribution**: deterministic vs Claude (count, calls, errors, timing)
- **Error patterns**: top errors by frequency with example prompts
- **Classifier gaps**: prompts that went to Claude because the classifier missed them or no execution plan exists
- **Slow requests**: anything over 60s
- **Claude task breakdown**: every Claude-handled task with its errors

For a JSON report you can process further:
```bash
python .claude/skills/competition-loop/scripts/analyze_logs.py --hours 24 --output /tmp/analysis.json
```

To check dev logs instead:
```bash
python .claude/skills/competition-loop/scripts/analyze_logs.py --bucket ai-nm26osl-1799-dev-logs --hours 24
```

## Phase 4: Diagnose

Cross-reference the coverage report (structural gaps) with log analysis (runtime errors) to build a prioritized fix list.

### A. Classifier gaps (tasks falling through to Claude unnecessarily)
Test specific prompts that went to Claude:
```python
from execution_plans._classifier import classify_task
classify_task("the prompt that fell through")  # returns None = gap
```
Common causes: missing language variants (Nynorsk, dialect forms), new task types.

### B. Missing execution plans
The classifier matches but `PLANS.get(task_type)` returns None. The coverage report shows these as ✗ in the Plan column.

### C. Recipe/prompt errors causing Claude failures
Map error patterns to root causes:

| Error pattern | Likely cause |
|---|---|
| `400 /invoice/paymentType` | Using `?fields=id,name` — `name` doesn't exist, use `?fields=*` |
| `404 /resultSheet` | Endpoint doesn't exist — use `/ledger/posting` with dateFrom+dateTo |
| `404 /dimension` variants | Wrong custom dimension endpoint — only `/ledger/accountingDimensionName` and `/ledger/accountingDimensionValue` exist |
| `422 /ledger/voucher` | Missing amountGross/amountGrossCurrency, or unbalanced postings |
| `422 /employee` | Missing dateOfBirth, or email already in use without fallback |
| `422 /division` | Trying to create division instead of using existing one |
| `422 /employee/employment` | Wrong field names (e.g., `percentOfFullTimeEquivalent` → `percentageOfFullTimeEquivalent`) |

### D. Deterministic plan bugs
Check if deterministic-handled tasks have 0 errors. If errors > 0, the plan itself has bugs.

### Prioritize by impact
- **Tier 3 errors first** (3x multiplier — highest scoring impact)
- **Then Tier 2** (2x multiplier)
- **Then Tier 1** (1x but usually already working)
- Within a tier: fix highest-request-count task types first (coverage report shows request counts)

## Phase 5: Create Optimal Sequences (if needed)

For task types identified in Phase 4 that have NO optimal sequence doc in `real-requests/optimal-sequence/`, create one BEFORE building an execution plan.

### Find real requests for the task type
```bash
# Use pre-classified task_type to find all matching requests
grep -l '"task_type": "register_payment"' competition/requests/*.json
```

### Understand the task pattern
Read multiple requests in different languages to identify:
- What entities need to be created (customer, employee, product, etc.)
- What the end goal is (invoice, voucher, project, etc.)
- What parameters need to be extracted from the prompt
- What the minimum API call count could be

### Check API reference
- Read `api_knowledge/cheat_sheet.py` for endpoint schemas
- Check existing similar recipes in `recipes/` for proven patterns
- Check Tripletex API docs at https://tripletex.no/v2-docs/ if needed
- Look for bulk endpoints (`POST /{resource}/list`) to minimize call count

### Write the optimal sequence doc
Save to `real-requests/optimal-sequence/<task_type>.md`:
```markdown
# <task_type> — Optimal Sequence

## Summary
Tier X. Brief description. N API calls.

## Parameters to Extract
| Parameter | Source | Notes |
|-----------|--------|-------|

## API Sequence
### Step N: Description (N calls)
POST /endpoint { body }
Capture var. On error: fallback.

## Critical Notes
- Target: N calls, 0 errors
```

Study existing optimal sequences for the format — they're the source of truth that both recipes and execution plans are built from.

## Phase 6: Fix

Fix issues in priority order (highest impact first):

### 1. Classifier gaps
Edit `execution_plans/_classifier.py`:
- Add missing patterns (Nynorsk, dialect, new languages)
- Verify with: `python -c "from execution_plans._classifier import classify_task; print(classify_task('test prompt'))"`

### 2. Missing execution plans
Create new plan in `execution_plans/<task_type>.py`:
- Use `execution_plans/create_customer.py` as template for simple 1-call plans
- Use `execution_plans/create_invoice.py` as template for multi-step plans
- Add `EXTRACTION_SCHEMA` for Gemini param extraction
- Register with `@register` decorator
- Import in `deterministic_executor.py`
- Add to `DETERMINISTIC_WHITELIST` if proven

### 3. Recipe errors (Claude fallback path)
Edit `recipes/*.md`:
- Fix wrong field names, endpoint paths, query params
- Fix `?fields=id,name` → `?fields=*` where field names vary

### 4. Prompt gotchas (Claude fallback path)
Edit `prompts.py` Critical Gotchas section:
- Add new gotchas for errors that keep recurring
- These are the first thing Claude reads — most effective place for corrections

### 5. Cheat sheet updates
Edit `api_knowledge/cheat_sheet.py`:
- Add endpoint corrections, required params, non-existent endpoints

### 6. Execution plan bugs
Edit the specific plan in `execution_plans/`:
- Fix field names, add missing required fields
- Add error handling for common 422 patterns

## Phase 7: Replay & Verify

After fixing, replay tagged requests to verify before deploying:

```bash
# Find requests for the fixed task type
grep -l '"task_type": "register_payment"' competition/requests/*.json

# Replay one against dev container
source .env && export TRIPLETEX_BASE_URL TRIPLETEX_SESSION_TOKEN
python scripts/replay_request.py competition/requests/<task_id>.json
```

Compare error count before vs after. If 0 errors, the fix is verified.

## Phase 8: Test & Deploy

### Run tests
```bash
python -m pytest tests/ -v --ignore=tests/integration -x
```

### Deploy to dev (test first)
```bash
source .env
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 --project ai-nm26osl-1799 --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-dev,LANGSMITH_API_KEY=$LANGSMITH_API_KEY" --quiet
```

### Deploy to competition (only after dev is verified)
```bash
source .env
gcloud run deploy accounting-agent-comp --source . --region europe-north1 --project ai-nm26osl-1799 --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-comp,LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP" --quiet
```

### Re-tag after deploy
After deploying and receiving new competition results, re-tag to capture fresh data:
```bash
python scripts/save_competition_requests.py
python scripts/tag_requests.py --force   # Re-classify if classifier was updated
python scripts/coverage_report.py        # Verify coverage improved
```

## Key Architecture Facts

- **Dual path**: DeterministicExecutor tries first → Claude fallback if it returns None
- **Classifier**: `execution_plans/_classifier.py` — regex patterns, ordered most-specific-first
- **Plans**: `execution_plans/*.py` — each has `EXTRACTION_SCHEMA` + `execute()` method
- **Whitelist**: `DETERMINISTIC_WHITELIST` in `deterministic_executor.py`
- **Recipes**: `recipes/*.md` — loaded into Claude's system prompt, only matter for Claude fallback
- **Prompts**: `prompts.py` — Critical Gotchas section is highest-impact for Claude fixes
- **Guards**: `recipe_guards.py` — validates/transforms API calls before sending (both paths)
- **Coverage**: `scripts/coverage_report.py` — shows structural gaps across all 6 components
- **Tagging**: Saved requests have `task_type`, `classified_by`, `tier` — use `grep` to find replay candidates
- Competition uses fresh sandboxes — low department numbers and simple defaults are fine
