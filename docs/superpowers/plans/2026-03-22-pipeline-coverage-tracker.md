# Pipeline Coverage Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a request tagging + coverage reporting system so pipeline gaps and replay candidates are visible at a glance.

**Architecture:** Auto-tag competition requests with `task_type`/`classified_by`/`tier` fields. A coverage report script scans the filesystem to build a matrix of which components exist per task type. No manifest file — only non-derivable metadata is persisted.

**Tech Stack:** Python 3.13, `execution_plans._classifier.classify_task()`, `pathlib`, `argparse`, `json`

**Spec:** `docs/superpowers/specs/2026-03-22-pipeline-coverage-tracker-design.md`

---

### Task 1: Create shared constants (`scripts/_task_tiers.py`)

**Files:**
- Create: `scripts/_task_tiers.py`

- [ ] **Step 1: Create `_task_tiers.py` with TASK_TIERS and RECIPE_NAME_OVERRIDES**

```python
"""Shared constants for pipeline coverage tools."""

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

# Recipe/guard filenames that don't match task_type names.
# None = orphan recipe with no corresponding task type.
RECIPE_NAME_OVERRIDES: dict[str, str | None] = {
    "custom_dimension_voucher": "custom_dimension",
    "reverse_payment_voucher": "reverse_payment",
    "asset_registration": None,
}
```

- [ ] **Step 2: Verify import works**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python -c "from scripts._task_tiers import TASK_TIERS, RECIPE_NAME_OVERRIDES; print(f'{len(TASK_TIERS)} tiers, {len(RECIPE_NAME_OVERRIDES)} overrides')"`

Expected: `26 tiers, 3 overrides`

- [ ] **Step 3: Commit**

```bash
git add scripts/_task_tiers.py
git commit -m "feat: add shared TASK_TIERS and RECIPE_NAME_OVERRIDES constants"
```

---

### Task 2: Create backfill tagger (`scripts/tag_requests.py`)

**Files:**
- Create: `scripts/tag_requests.py`
- Read: `execution_plans/_classifier.py` (imports `classify_task`)
- Read: `scripts/_task_tiers.py` (imports `TASK_TIERS`)

- [ ] **Step 1: Create `tag_requests.py`**

```python
"""Tag competition requests with task_type, classified_by, and tier.

Usage:
    python scripts/tag_requests.py              # Tag all untagged requests
    python scripts/tag_requests.py --force      # Re-classify auto-tagged (skip manual)
    python scripts/tag_requests.py --dry-run    # Preview without writing
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from execution_plans._classifier import classify_task
from scripts._task_tiers import TASK_TIERS

REQUESTS_DIR = Path(__file__).parent.parent / "competition" / "requests"


def main():
    parser = argparse.ArgumentParser(description="Tag competition requests with task_type")
    parser.add_argument("--force", action="store_true",
                        help="Re-classify all auto-tagged requests (skip manual)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing files")
    args = parser.parse_args()

    tagged = unclassified = skipped = 0
    for filepath in sorted(REQUESTS_DIR.glob("*.json")):
        data = json.loads(filepath.read_text())

        # Preserve manual overrides
        if data.get("classified_by") == "manual":
            skipped += 1
            continue

        # Skip already-tagged unless --force
        if data.get("task_type") is not None and not args.force:
            skipped += 1
            continue

        task_type = classify_task(data.get("prompt", ""))
        tier = TASK_TIERS.get(task_type) if task_type else None

        data["task_type"] = task_type
        data["classified_by"] = "auto"
        data["tier"] = tier

        if task_type:
            tagged += 1
        else:
            unclassified += 1

        if not args.dry_run:
            filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

        label = task_type or "UNCLASSIFIED"
        prefix = "[DRY RUN] " if args.dry_run else ""
        print(f"  {prefix}{filepath.name} → {label}")

    print(f"\nDone: {tagged} tagged, {unclassified} unclassified, {skipped} skipped")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test dry-run against existing requests**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python scripts/tag_requests.py --dry-run 2>&1 | tail -5`

Expected: Summary line like `Done: N tagged, M unclassified, 0 skipped` (all requests are currently untagged, so skipped=0).

- [ ] **Step 3: Run the actual backfill**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python scripts/tag_requests.py`

Expected: All 223 requests tagged. Check a sample file to verify the new fields exist:
Run: `python -c "import json; d=json.load(open('competition/requests/013b91b50adc.json')); print(d.get('task_type'), d.get('classified_by'), d.get('tier'))"`

- [ ] **Step 4: Commit**

```bash
git add scripts/tag_requests.py
git commit -m "feat: add backfill tagger for competition requests"
```

---

### Task 3: Modify `save_competition_requests.py` to auto-tag

**Files:**
- Modify: `scripts/save_competition_requests.py:1-5,16-20,52-96`

- [ ] **Step 1: Add imports at top of file (after line 20)**

Add after `from pathlib import Path`:

```python
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from execution_plans._classifier import classify_task
from scripts._task_tiers import TASK_TIERS
```

Note: `sys` is already imported — just add the `sys.path.insert` and the two imports.

- [ ] **Step 2: Add auto-tagging to `strip_and_save()` (after line 89, before the `# Save` comment)**

Insert after the `result_summary` dict is built (after line 89) and before `# Save` (line 92):

```python
    # Auto-tag with task_type
    prompt = request.get("prompt", "")
    task_type = classify_task(prompt)
    saved["task_type"] = task_type
    saved["classified_by"] = "auto"
    saved["tier"] = TASK_TIERS.get(task_type) if task_type else None
```

- [ ] **Step 3: Preserve manual overrides on `--task-id` re-save**

In `strip_and_save()`, after `filepath = OUTPUT_DIR / f"{task_id}.json"` (line 94) and before `filepath.write_text(...)` (line 95), add:

```python
    # Preserve manual classification on re-save
    if filepath.exists():
        existing = json.loads(filepath.read_text())
        if existing.get("classified_by") == "manual":
            saved["task_type"] = existing["task_type"]
            saved["classified_by"] = "manual"
            saved["tier"] = existing.get("tier")
```

- [ ] **Step 4: Verify the script still works**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python scripts/save_competition_requests.py --help`

Expected: Help text prints without import errors.

- [ ] **Step 5: Commit**

```bash
git add scripts/save_competition_requests.py
git commit -m "feat: auto-tag competition requests with task_type on save"
```

---

### Task 4: Create coverage report (`scripts/coverage_report.py`)

**Files:**
- Create: `scripts/coverage_report.py`
- Read: `execution_plans/_classifier.py` (imports `TASK_PATTERNS`)
- Read: `deterministic_executor.py` (imports `DETERMINISTIC_WHITELIST`)
- Read: `scripts/_task_tiers.py` (imports `TASK_TIERS`, `RECIPE_NAME_OVERRIDES`)

- [ ] **Step 1: Create `coverage_report.py`**

```python
"""Pipeline coverage report — shows which components exist per task type.

Usage:
    python scripts/coverage_report.py            # Pretty terminal table
    python scripts/coverage_report.py --json     # Machine-readable JSON
    python scripts/coverage_report.py --gaps     # Show only incomplete task types
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from execution_plans._classifier import TASK_PATTERNS
from deterministic_executor import DETERMINISTIC_WHITELIST
from scripts._task_tiers import TASK_TIERS, RECIPE_NAME_OVERRIDES

PLANS_DIR = ROOT / "execution_plans"
OPTSEQ_DIR = ROOT / "real-requests" / "optimal-sequence"
RECIPES_DIR = ROOT / "recipes"
REQUESTS_DIR = ROOT / "competition" / "requests"

PLAN_EXCLUDES = {"_base", "_classifier", "_registry", "__init__"}


def _strip_recipe_prefix(name: str) -> str:
    """Strip leading number prefix: '07_register_payment' -> 'register_payment'."""
    return re.sub(r"^\d+_", "", name)


def scan_coverage() -> dict:
    # Canonical task types
    classifier_types = {tt for tt, _ in TASK_PATTERNS}
    canonical = classifier_types | set(TASK_TIERS.keys())

    # Filesystem scans
    plans = {p.stem for p in PLANS_DIR.glob("*.py") if p.stem not in PLAN_EXCLUDES}
    optseqs = {p.stem for p in OPTSEQ_DIR.glob("*.md")} if OPTSEQ_DIR.exists() else set()

    recipes = set()
    orphan_recipes = []
    for p in RECIPES_DIR.glob("*.md"):
        name = _strip_recipe_prefix(p.stem)
        mapped = RECIPE_NAME_OVERRIDES.get(name, name)
        if mapped is None:
            orphan_recipes.append(name)
        else:
            recipes.add(mapped)

    guards = set()
    for p in RECIPES_DIR.glob("*.guard.json"):
        raw_name = p.stem.removesuffix(".guard")  # "06_create_invoice.guard" -> "06_create_invoice"
        name = _strip_recipe_prefix(raw_name)
        if name == "_global":
            continue
        mapped = RECIPE_NAME_OVERRIDES.get(name, name)
        if mapped is not None:
            guards.add(mapped)

    # Request counts
    request_counts: dict[str, int] = {}
    unclassified_ids: list[str] = []
    for p in REQUESTS_DIR.glob("*.json"):
        data = json.loads(p.read_text())
        tt = data.get("task_type")
        if tt:
            request_counts[tt] = request_counts.get(tt, 0) + 1
        else:
            unclassified_ids.append(p.stem)

    # Build per-type coverage
    task_types = {}
    for tt in sorted(canonical):
        task_types[tt] = {
            "classifier": tt in classifier_types,
            "optimal_sequence": tt in optseqs,
            "execution_plan": tt in plans,
            "recipe": tt in recipes,
            "guard": tt in guards,
            "whitelist": tt in DETERMINISTIC_WHITELIST,
            "request_count": request_counts.get(tt, 0),
            "tier": TASK_TIERS.get(tt),
        }

    total_requests = sum(request_counts.values()) + len(unclassified_ids)
    n = len(canonical)
    totals = {
        "task_types": n,
        "classifier": sum(1 for v in task_types.values() if v["classifier"]),
        "optimal_sequence": sum(1 for v in task_types.values() if v["optimal_sequence"]),
        "execution_plan": sum(1 for v in task_types.values() if v["execution_plan"]),
        "recipe": sum(1 for v in task_types.values() if v["recipe"]),
        "guard": sum(1 for v in task_types.values() if v["guard"]),
        "whitelist": sum(1 for v in task_types.values() if v["whitelist"]),
        "total_requests": total_requests,
        "classified_requests": total_requests - len(unclassified_ids),
    }

    return {
        "task_types": task_types,
        "unclassified_requests": unclassified_ids,
        "orphan_recipes": orphan_recipes,
        "totals": totals,
    }


def print_table(data: dict, gaps_only: bool = False):
    task_types = data["task_types"]
    totals = data["totals"]
    n = totals["task_types"]

    header = f"{'Task Type':<27} {'Cls':>3}  {'OptSeq':>6}  {'Plan':>4}  {'Recipe':>6}  {'Guard':>5}  {'WL':>2}  {'Reqs':>4}  {'Tier':>4}"
    sep = "─" * len(header)

    print(header)
    print(sep)

    for tt, v in task_types.items():
        if gaps_only and all(v[k] for k in ["classifier", "optimal_sequence", "execution_plan", "recipe", "whitelist"]):
            continue
        ck = "✓" if v["classifier"] else "✗"
        os = "✓" if v["optimal_sequence"] else "✗"
        pl = "✓" if v["execution_plan"] else "✗"
        rc = "✓" if v["recipe"] else "✗"
        gd = "✓" if v["guard"] else "✗"
        wl = "✓" if v["whitelist"] else "✗"
        rq = str(v["request_count"])
        ti = f"T{v['tier']}" if v["tier"] else "??"
        print(f"{tt:<27} {ck:>3}  {os:>6}  {pl:>4}  {rc:>6}  {gd:>5}  {wl:>2}  {rq:>4}  {ti:>4}")

    print(sep)

    cl = f"{totals['classifier']}/{n}"
    os = f"{totals['optimal_sequence']}/{n}"
    pl = f"{totals['execution_plan']}/{n}"
    rc = f"{totals['recipe']}/{n}"
    gd = f"{totals['guard']}/{n}"
    wl = f"{totals['whitelist']}/{n}"
    rq = f"{totals['classified_requests']}/{totals['total_requests']}"
    print(f"{'COVERAGE':<27} {cl:>3}  {os:>6}  {pl:>4}  {rc:>6}  {gd:>5}  {wl:>2}  {rq:>4}")

    if data["unclassified_requests"]:
        print(f"\nUnclassified requests ({len(data['unclassified_requests'])}): {', '.join(data['unclassified_requests'][:10])}")
        if len(data["unclassified_requests"]) > 10:
            print(f"  ... and {len(data['unclassified_requests']) - 10} more")

    if data["orphan_recipes"]:
        print(f"\nOrphan recipes (no task type): {', '.join(data['orphan_recipes'])}")


def main():
    parser = argparse.ArgumentParser(description="Pipeline coverage report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--gaps", action="store_true", help="Show only incomplete task types")
    args = parser.parse_args()

    data = scan_coverage()

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_table(data, gaps_only=args.gaps)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the coverage report**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python scripts/coverage_report.py`

Expected: A table showing all 26 task types with check/cross marks across 6 columns, plus request counts and tiers.

- [ ] **Step 3: Test `--gaps` flag**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python scripts/coverage_report.py --gaps`

Expected: Only rows with at least one `✗` are shown.

- [ ] **Step 4: Test `--json` flag**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python scripts/coverage_report.py --json | python -m json.tool | head -20`

Expected: Valid JSON with `task_types`, `unclassified_requests`, `orphan_recipes`, `totals` keys.

- [ ] **Step 5: Commit**

```bash
git add scripts/coverage_report.py
git commit -m "feat: add pipeline coverage report script"
```

---

### Task 5: Commit tagged requests

**Files:**
- Modified: `competition/requests/*.json` (all 223 files, already tagged in Task 2)

- [ ] **Step 1: Verify a sample of tagged requests**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && for f in competition/requests/013b91b50adc.json competition/requests/0192322a5a8c.json competition/requests/06bafa319b6b.json; do echo "=== $f ==="; python -c "import json; d=json.load(open('$f')); print(d.get('task_type'), d.get('classified_by'), d.get('tier'))"; done`

Expected: Each prints a task_type (or None), "auto", and a tier number (or None).

- [ ] **Step 2: Commit all tagged requests**

```bash
git add competition/requests/
git commit -m "data: tag all competition requests with task_type, classified_by, tier"
```

---

### Task 6: Verify end-to-end workflow

- [ ] **Step 1: Run full coverage report and verify output**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python scripts/coverage_report.py`

Verify: Table renders correctly, totals make sense, orphan recipes listed.

- [ ] **Step 2: Test finding replay candidates by task type**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && grep -l '"task_type": "register_payment"' competition/requests/*.json | wc -l`

Expected: A number > 0 — these are the requests you'd replay after fixing the register_payment plan.

- [ ] **Step 3: Test the `--force` re-tag flow (simulates classifier update)**

Run: `cd /Users/torbjornbeining/Alias_NM/challenges/AIAccountingAgent && python scripts/tag_requests.py --force --dry-run 2>&1 | tail -3`

Expected: Shows re-classification preview for all auto-tagged requests, skipping 0 manual.
