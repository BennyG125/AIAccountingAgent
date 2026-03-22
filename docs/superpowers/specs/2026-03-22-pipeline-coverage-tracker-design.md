# Pipeline Coverage Tracker — Design Spec

**Date:** 2026-03-22
**Status:** Approved

## Problem

26 task types are connected across 6 pipeline components via an implicit `task_type` string convention. Two questions are expensive to answer today:

1. **Coverage gaps:** "What's the status of task type X?" requires manually checking 6 locations: classifier patterns, optimal sequence docs, execution plans, recipes, guards, and the whitelist.
2. **Request mapping:** 223+ competition requests in `competition/requests/` have no metadata linking them to task types. After fixing a plan, finding relevant replay candidates requires reading every prompt.

## Design Principle

**Never store what you can derive.** Coverage data (does file X exist?) comes from filesystem scans. Only non-derivable metadata (which task type does request Y belong to?) gets persisted — as tags on existing request JSON files.

No manifest file. No registry directory. No runtime changes.

## Components

### 1. Request Tagging

Three fields added to each `competition/requests/{id}.json`:

```json
{
  "task_id": "013b91b50adc",
  "task_type": "overdue_invoice_reminder",
  "classified_by": "auto",
  "tier": 2,
  "timestamp": "...",
  "prompt": "...",
  "files": [],
  "result_summary": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_type` | `string \| null` | Result of `classify_task()`, or `null` if unclassified |
| `classified_by` | `"auto" \| "manual"` | `"auto"` = regex classifier, `"manual"` = human override |
| `tier` | `int \| null` | From `TASK_TIERS` lookup, `null` if unknown |

**Rules:**
- Backfill script skips requests where `classified_by` is `"manual"` (preserves human overrides)
- `task_type: null` means the classifier couldn't match — these show up as "UNCLASSIFIED" in the report

### 2. Backfill Script — `scripts/tag_requests.py`

One-time script to tag all existing requests.

**Behavior:**
1. Import `classify_task` from `execution_plans._classifier`
2. For each `competition/requests/*.json`:
   - Skip if `classified_by` is `"manual"` (preserve overrides)
   - Run `classify_task(prompt)` to get `task_type`
   - Look up `tier` from `TASK_TIERS`
   - Write `task_type`, `classified_by: "auto"`, and `tier` into the JSON
3. Print summary: N tagged, N unclassified, N skipped (manual)

**CLI:**
```bash
python scripts/tag_requests.py              # Tag all untagged requests
python scripts/tag_requests.py --force      # Re-run classifier on all auto-tagged (skip manual), useful after classifier updates
python scripts/tag_requests.py --dry-run    # Preview without writing
```

**Size:** ~40 lines.

### 3. Auto-tagging in `save_competition_requests.py`

Modify the `strip_and_save()` function to call `classify_task()` on the prompt and add `task_type`, `classified_by`, and `tier` to the saved JSON.

**Change:** ~10 lines added to `strip_and_save()`.

**Behavior:** New requests are tagged on save. Existing requests are not re-tagged (the skip-if-exists logic already prevents overwrites). When `--task-id` is used (which bypasses skip-if-exists), the script reads the existing file first and preserves any `classified_by: "manual"` tag — it only overwrites auto-classified or untagged requests.

### 4. Coverage Report — `scripts/coverage_report.py`

Scans the filesystem and prints a coverage matrix.

**What it scans:**

| Component | Source | How |
|-----------|--------|-----|
| Classifier | `execution_plans/_classifier.py` | Import `TASK_PATTERNS`, extract task type keys |
| Optimal Sequences | `real-requests/optimal-sequence/*.md` | Filename = task type |
| Execution Plans | `execution_plans/*.py` | Filename = task type (exclude `_base`, `_classifier`, `_registry`, `__init__`) |
| Recipes | `recipes/*.md` | Filename with number prefix stripped, then mapped through `RECIPE_NAME_OVERRIDES` (see below) |
| Guards | `recipes/*.guard.json` | Filename with number prefix stripped, then mapped through `RECIPE_NAME_OVERRIDES` (exclude `_global`) |
| Whitelist | `deterministic_executor.py` | Import `DETERMINISTIC_WHITELIST` set |
| Requests | `competition/requests/*.json` | Count by `task_type` field |

**Canonical task type list:** The union of `TASK_PATTERNS` keys (from classifier) and `TASK_TIERS` keys. Task types discovered only from filesystem scans (e.g., a recipe with no classifier pattern) appear as extra rows with `??` tier. The denominator in totals uses this canonical count.

**Recipe/guard name overrides:** Some recipe filenames don't match task type names. A `RECIPE_NAME_OVERRIDES` dict handles these:

```python
RECIPE_NAME_OVERRIDES = {
    "custom_dimension_voucher": "custom_dimension",
    "reverse_payment_voucher": "reverse_payment",
    "asset_registration": None,  # No corresponding task type — excluded from coverage
}
```

A `None` value means the recipe exists but has no corresponding task type — it appears as a footnote, not a row.

**Output (terminal):**
```
Task Type                  Cls  OptSeq  Plan  Recipe  Guard  WL  Reqs  Tier
─────────────────────────  ───  ──────  ────  ──────  ─────  ──  ────  ────
create_product             ✓    ✗       ✓     ✓       ✗      ✓   12    T1
create_invoice             ✓    ✓       ✓     ✓       ✓      ✓   18    T1
register_payment           ✓    ✓       ✓     ✓       ✗      ✓    9    T2
─────────────────────────  ───  ──────  ────  ──────  ─────  ──  ────  ────
COVERAGE                   26/26  22/26  26/26  26/26  4/26  27/26  220/223
UNCLASSIFIED               ─    ─       ─     ─       ─      ─    3    ─

Orphan recipes (no task type): asset_registration
```

**CLI:**
```bash
python scripts/coverage_report.py            # Pretty terminal table
python scripts/coverage_report.py --json     # Machine-readable JSON
python scripts/coverage_report.py --gaps     # Show only incomplete task types
```

**`--json` output structure:**
```json
{
  "task_types": {
    "create_product": {
      "classifier": true,
      "optimal_sequence": false,
      "execution_plan": true,
      "recipe": true,
      "guard": false,
      "whitelist": true,
      "request_count": 12,
      "tier": 1
    }
  },
  "unclassified_requests": ["abc123", "def456"],
  "totals": {
    "classifier": 28, "optimal_sequence": 22,
    "execution_plan": 26, "recipe": 27,
    "guard": 4, "whitelist": 27,
    "total_requests": 223, "classified_requests": 220
  }
}
```

**Size:** ~80 lines.

### 5. Tier Lookup

A `TASK_TIERS` dict, defined in a shared location importable by both `tag_requests.py` and `coverage_report.py`. Placed in `scripts/_task_tiers.py`:

```python
TASK_TIERS: dict[str, int] = {
    # Tier 1
    "create_product": 1, "create_invoice": 1, "create_customer": 1,
    "create_supplier": 1, "create_departments": 1, "create_employee": 1,
    "create_order": 1, "create_project": 1,
    # Tier 2
    "register_payment": 2, "credit_note": 2, "register_supplier_invoice": 2,
    "register_hours": 2, "run_salary": 2, "custom_dimension": 2,
    "employee_onboarding": 2, "travel_expense": 2, "fixed_price_project": 2,
    "reverse_payment": 2, "overdue_invoice_reminder": 2, "forex_payment": 2,
    # Tier 3
    "bank_reconciliation": 3, "year_end_close": 3, "year_end_corrections": 3,
    "monthly_closing": 3, "project_lifecycle": 3, "cost_analysis_projects": 3,
}
```

## What is NOT built

- No `manifest.json` — derivable data should not be stored
- No per-task registry directory — 26 individual files is over-engineering
- No golden request system — finding requests by task_type via grep is sufficient
- No runtime changes — classifier, executor, agent are untouched
- No changes to `analyze_logs.py` — it serves a different purpose (recent failures vs overall coverage)

## Workflow Change

Before (current):
```
1. save_competition_requests.py  →  raw JSONs, no metadata
2. Manual checking across 6 locations to find gaps
3. Fix gaps
4. Manually identify requests to replay
```

After:
```
1. save_competition_requests.py  →  auto-tagged JSONs
2. coverage_report.py            →  gaps visible at a glance
3. Fix gaps
4. grep task_type to find replay candidates
```

## Files

| File | Action | Lines |
|------|--------|-------|
| `scripts/tag_requests.py` | Create | ~40 |
| `scripts/save_competition_requests.py` | Modify | ~10 added |
| `scripts/coverage_report.py` | Create | ~80 |
| `scripts/_task_tiers.py` | Create | ~15 |
| `competition/requests/*.json` | Modify | 3 fields added per file |
