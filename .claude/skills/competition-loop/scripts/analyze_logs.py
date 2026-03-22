#!/usr/bin/env python3
"""Pull and analyze GCP competition logs for the AI Accounting Agent.

Usage:
    python .claude/skills/competition-loop/scripts/analyze_logs.py [--bucket BUCKET] [--hours N] [--save-requests]

Downloads latest competition logs from GCS, analyzes error patterns,
executor distribution, timing, and classifier gaps. Outputs a structured
report to stdout.

Options:
    --bucket BUCKET   GCS bucket (default: ai-nm26osl-1799-competition-logs)
    --hours N         Only analyze logs from last N hours (default: 24)
    --save-requests   Save new request fixtures to tests/competition_tasks/
    --output FILE     Write JSON report to file instead of stdout
"""

import argparse
import json
import glob
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone


def download_logs(bucket: str, hours: int, tmpdir: str) -> list[str]:
    """Download recent logs from GCS to a temp directory."""
    prefix = f"gs://{bucket}/requests/"

    # List all files
    result = subprocess.run(
        ["gsutil", "ls", prefix],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"Error listing bucket: {result.stderr}", file=sys.stderr)
        return []

    files = result.stdout.strip().split("\n")
    if not files or files == [""]:
        return []

    # Filter by time
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    for f in files:
        # Extract timestamp from filename: requests/2026-03-22T07-04-43_...
        basename = f.split("/")[-1]
        match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})", basename)
        if match:
            ts = datetime.strptime(match.group(1), "%Y-%m-%dT%H-%M-%S").replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                recent.append(f)

    if not recent:
        print(f"No logs found in last {hours} hours", file=sys.stderr)
        return []

    # Download
    subprocess.run(
        ["gsutil", "-m", "cp"] + recent + [tmpdir + "/"],
        capture_output=True, timeout=120
    )

    return sorted(glob.glob(f"{tmpdir}/*.json"))


def parse_logs(files: list[str]) -> list[dict]:
    """Parse all log files into structured data."""
    entries = []
    for f in files:
        try:
            with open(f) as fh:
                d = json.load(fh)
            r = d.get("result", {})
            if not r:
                continue

            entry = {
                "file": os.path.basename(f),
                "prompt": d.get("request", {}).get("prompt", ""),
                "executor": r.get("executor", "claude"),
                "api_calls": r.get("api_calls", 0) or 0,
                "api_errors": r.get("api_errors", 0) or 0,
                "iterations": r.get("iterations", 0) or 0,
                "time_ms": r.get("time_ms", 0) or 0,
                "error_details": r.get("error_details") or [],
                "has_files": bool(d.get("request", {}).get("files")),
            }
            entries.append(entry)
        except (json.JSONDecodeError, KeyError):
            continue

    return entries


def analyze(entries: list[dict]) -> dict:
    """Analyze log entries and produce a structured report."""

    # Executor distribution
    executor_stats = {}
    for ex in ["deterministic", "claude"]:
        subset = [e for e in entries if e["executor"] == ex]
        if subset:
            executor_stats[ex] = {
                "count": len(subset),
                "total_calls": sum(e["api_calls"] for e in subset),
                "total_errors": sum(e["api_errors"] for e in subset),
                "avg_time_ms": sum(e["time_ms"] for e in subset) // len(subset),
                "avg_calls": round(sum(e["api_calls"] for e in subset) / len(subset), 1),
            }

    # Error patterns
    error_counter = Counter()
    error_prompts = {}
    for e in entries:
        for err in e["error_details"]:
            key = f"{err.get('status', '?')} {err.get('path', '?')}"
            error_counter[key] += 1
            if key not in error_prompts:
                error_prompts[key] = e["prompt"][:100]

    error_patterns = [
        {"pattern": k, "count": v, "example_prompt": error_prompts.get(k, "")}
        for k, v in error_counter.most_common(20)
    ]

    # Claude-handled tasks (potential for deterministic conversion)
    claude_tasks = []
    for e in entries:
        if e["executor"] == "claude":
            claude_tasks.append({
                "prompt": e["prompt"][:120],
                "api_calls": e["api_calls"],
                "api_errors": e["api_errors"],
                "time_ms": e["time_ms"],
                "error_paths": [
                    f"{err.get('status')} {err.get('path')}"
                    for err in e["error_details"][:5]
                ],
            })

    # Slow requests (>60s)
    slow = [
        {
            "prompt": e["prompt"][:100],
            "executor": e["executor"],
            "time_ms": e["time_ms"],
            "api_calls": e["api_calls"],
            "api_errors": e["api_errors"],
        }
        for e in sorted(entries, key=lambda x: -x["time_ms"])
        if e["time_ms"] > 60000
    ]

    # Prompts that went to Claude (for classifier testing)
    claude_prompts = [
        e["prompt"] for e in entries if e["executor"] == "claude"
    ]

    return {
        "total_requests": len(entries),
        "executor_stats": executor_stats,
        "error_patterns": error_patterns,
        "claude_tasks": claude_tasks,
        "slow_requests": slow[:15],
        "claude_prompts": claude_prompts,
    }


def test_classifier(prompts: list[str]) -> list[dict]:
    """Test classifier against Claude-handled prompts."""
    try:
        sys.path.insert(0, os.getcwd())
        from execution_plans._classifier import classify_task
        from execution_plans._registry import PLANS
        # Need to import all plans
        import importlib, pkgutil, execution_plans
        for info in pkgutil.iter_modules(execution_plans.__path__):
            if not info.name.startswith("_"):
                importlib.import_module(f"execution_plans.{info.name}")
    except ImportError:
        return []

    from deterministic_executor import DETERMINISTIC_WHITELIST

    gaps = []
    for prompt in prompts:
        task_type = classify_task(prompt)
        has_plan = task_type in PLANS if task_type else False
        in_whitelist = task_type in DETERMINISTIC_WHITELIST if task_type else False

        if task_type is None or not has_plan or not in_whitelist:
            gaps.append({
                "prompt": prompt[:120],
                "classified_as": task_type,
                "has_plan": has_plan,
                "in_whitelist": in_whitelist,
                "reason": (
                    "no classifier match" if task_type is None
                    else f"no execution plan for '{task_type}'" if not has_plan
                    else f"'{task_type}' not in whitelist"
                ),
            })

    return gaps


def print_report(report: dict, classifier_gaps: list[dict]):
    """Print human-readable report to stdout."""
    print("=" * 70)
    print("COMPETITION LOG ANALYSIS")
    print("=" * 70)

    print(f"\nTotal requests: {report['total_requests']}")
    print("\n--- Executor Distribution ---")
    for ex, stats in report["executor_stats"].items():
        err_rate = (
            f"{100 * stats['total_errors'] / max(1, stats['total_calls']):.0f}%"
            if stats["total_calls"] > 0 else "N/A"
        )
        print(
            f"  {ex}: {stats['count']} requests, "
            f"{stats['total_calls']} calls ({stats['avg_calls']} avg), "
            f"{stats['total_errors']} errors ({err_rate}), "
            f"{stats['avg_time_ms']}ms avg"
        )

    print("\n--- Top Error Patterns ---")
    for ep in report["error_patterns"][:15]:
        print(f"  {ep['count']}x  {ep['pattern']}")

    print("\n--- Classifier Gaps (tasks that went to Claude) ---")
    if classifier_gaps:
        for g in classifier_gaps:
            print(f"  [{g['reason']}] {g['prompt'][:80]}")
    else:
        print("  None — all Claude tasks were correctly classified but fell through for other reasons")

    print("\n--- Slow Requests (>60s) ---")
    for s in report["slow_requests"][:10]:
        print(
            f"  {s['time_ms'] / 1000:.0f}s [{s['executor']}] "
            f"calls={s['api_calls']} errs={s['api_errors']}  "
            f"{s['prompt'][:70]}"
        )

    print("\n--- Claude-Handled Tasks ---")
    for ct in report["claude_tasks"]:
        flag = "⚠️" if ct["api_errors"] > 0 else "✅"
        print(
            f"  {flag} calls={ct['api_calls']} errs={ct['api_errors']} "
            f"time={ct['time_ms']}ms  {ct['prompt'][:70]}"
        )
        if ct["error_paths"]:
            print(f"     errors: {ct['error_paths']}")


def main():
    parser = argparse.ArgumentParser(description="Analyze GCP competition logs")
    parser.add_argument("--bucket", default="ai-nm26osl-1799-competition-logs")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--output", help="Write JSON report to file")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Downloading logs from gs://{args.bucket} (last {args.hours}h)...", file=sys.stderr)
        files = download_logs(args.bucket, args.hours, tmpdir)
        if not files:
            print("No log files found.", file=sys.stderr)
            sys.exit(1)

        print(f"Analyzing {len(files)} log files...", file=sys.stderr)
        entries = parse_logs(files)
        report = analyze(entries)

        # Test classifier
        classifier_gaps = test_classifier(report["claude_prompts"])

        if args.output:
            report["classifier_gaps"] = classifier_gaps
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"Report written to {args.output}", file=sys.stderr)
        else:
            print_report(report, classifier_gaps)


if __name__ == "__main__":
    main()
