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
