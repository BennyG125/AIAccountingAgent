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
