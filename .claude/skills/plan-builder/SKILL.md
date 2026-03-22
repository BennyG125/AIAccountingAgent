---
name: plan-builder
description: Create new deterministic execution plans from real competition requests. Analyzes real requests to understand what the task requires, checks the Tripletex API docs for relevant endpoints, creates an optimal-sequence doc, then implements the execution plan with EXTRACTION_SCHEMA, classifier patterns, and whitelist entry. Use whenever the user says "create a plan", "add execution plan", "make this deterministic", "new plan for X", or when the competition-loop skill identifies missing execution plans. Also trigger when the user mentions a task type that's falling through to Claude and wants to fix it.
---

# Execution Plan Builder

Create new deterministic execution plans from real competition requests. The workflow: analyze requests → document optimal sequence → implement execution plan → register.

## Step 1: Analyze Real Requests

Find real competition requests for the target task type. Saved requests are pre-classified with `task_type`, `classified_by`, and `tier`:

```bash
# Find all requests for a specific task type
grep -l '"task_type": "register_payment"' competition/requests/*.json

# Check pipeline coverage to see what's missing
python scripts/coverage_report.py --gaps
```

Or search by keyword for detailed analysis:
```python
import json, glob
for f in sorted(glob.glob('competition/requests/*.json')):
    with open(f) as fh:
        d = json.load(fh)
    # Use pre-classified task_type or search by keyword
    if d.get('task_type') == 'register_payment':
        print(d['prompt'][:200])
        print(f"Calls: {d.get('result_summary', {}).get('api_calls')}")
        print(f"Errors: {d.get('result_summary', {}).get('api_errors')}")
```

Key things to identify:
- What entities need to be created (customer, employee, product, etc.)
- What the end goal is (invoice, voucher, project, etc.)
- What languages the prompts come in (NO, EN, ES, PT, DE, FR + Nynorsk)
- What parameters need to be extracted from the prompt

## Step 2: Check API Reference

Read the cheat sheet for relevant endpoints:
```bash
grep -A5 'POST /endpoint' api_knowledge/cheat_sheet.py
```

For each endpoint, identify:
- Required vs optional fields
- Bulk endpoints (`POST /{resource}/list`) for efficiency
- Query param vs body conventions
- Known gotchas (check `prompts.py` Critical Gotchas section)

Also check existing similar plans for patterns:
```bash
ls execution_plans/*.py  # find similar plans to use as templates
```

## Step 3: Create Optimal Sequence Doc

Write `real-requests/optimal-sequence/<task_type>.md` with:

```markdown
# <task_type> — Optimal Sequence

## Summary
Tier X (Nx multiplier). Brief description. N API calls, ~Xs.

## Parameters to Extract
| Parameter | Source | Notes |
|-----------|--------|-------|
| `param` | Prompt — description | Required/Optional |

## API Sequence
### Step N: Description (N calls)
```
POST /endpoint
{ body }
```
Capture `var`. On error: fallback.

## Critical Notes
- Known gotchas specific to this task
- Target: N calls, 0 errors
```

## Step 4: Create Execution Plan

Create `execution_plans/<task_type>.py` following this template:

```python
"""Execution plan: <TaskName> (Tier N)."""
from execution_plans._base import ExecutionPlan
from execution_plans._registry import register

EXTRACTION_SCHEMA = {
    "field": "type (description)",
}

@register
class TaskNamePlan(ExecutionPlan):
    task_type = "<task_type>"
    description = "Brief description"

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)
        api_calls = 0
        api_errors = 0

        # Implementation following optimal sequence
        # Use self._check_timeout(start_time) between steps
        # Use self._safe_post() for calls that might 422
        # Handle 422 with search fallback (find-or-create pattern)

        return self._make_result(api_calls=api_calls, api_errors=api_errors)
```

Key patterns from existing plans:
- **find-or-create**: POST, on 422 → GET to find existing
- **dateOfBirth**: Always include on employee creation (default "1990-01-01")
- **entitlements**: Grant before project creation
- **No vatType**: Never on products
- **Query params**: Payment registration, /:reverse, /:send use query params not body
- **Bulk calls**: Use `/list` endpoints where available (products, participants)

## Step 5: Register the Plan

1. **Import** in `deterministic_executor.py`:
   ```python
   import execution_plans.<task_type>  # noqa: F401
   ```

2. **Whitelist** in `DETERMINISTIC_WHITELIST`:
   ```python
   "<task_type>",
   ```

3. **Classifier** — verify patterns exist in `execution_plans/_classifier.py`:
   ```python
   from execution_plans._classifier import classify_task
   classify_task("test prompt in each language")
   ```
   Add missing patterns for all 6 languages + Nynorsk if needed.

## Step 6: Test

```bash
python -m pytest tests/ -v --ignore=tests/integration -x
```

## Language Agnosticism Checklist

All plans must handle prompts in: Norwegian (Bokmål + Nynorsk), English, Spanish, Portuguese, German, French.

This is handled at two levels:
1. **Classifier** (`_classifier.py`): Must have regex patterns for all 6+ languages
2. **Parameter extraction** (Gemini Flash): The extraction prompt already specifies multilingual support — just ensure EXTRACTION_SCHEMA field descriptions are clear enough for Gemini to extract from any language

Common Nynorsk gaps to watch for:
- "tilsett" = ansatt (employee)
- "hovudbok" = hovedbok (ledger)
- "månavslutninga" = månedsavslutning (monthly closing)
- "årsoppgjer" = årsoppgjør (year-end close)
- "bilag" = voucher
- "avdeling" works in both Bokmål and Nynorsk
