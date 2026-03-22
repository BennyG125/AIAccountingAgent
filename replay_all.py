#!/usr/bin/env python3
"""Replay real competition requests against the dev container in parallel.

Usage:
    python replay_all.py                    # replay all 88 requests, 15 concurrent
    python replay_all.py --concurrency 5    # limit parallelism
    python replay_all.py --filter monthly   # only prompts matching "monthly"
    python replay_all.py --dry-run          # show what would be sent without sending
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import aiohttp

DEV_URL = "https://ai-accounting-agent-det-590159115697.europe-north1.run.app"
REQUESTS_DIR = Path("real-requests/latest-batch")
RESULTS_FILE = Path("real-requests/latest-batch/REPLAY_RESULTS.md")
TIMEOUT_S = 330  # slightly over the agent's 270s internal timeout

# Dev sandbox credentials (override competition proxy tokens)
DEV_SANDBOX_BASE_URL = os.environ.get(
    "TRIPLETEX_BASE_URL", "https://kkpqfuj-amager.tripletex.dev/v2"
)
DEV_SANDBOX_TOKEN = os.environ.get("TRIPLETEX_SESSION_TOKEN", "")


async def replay_one(
    session: aiohttp.ClientSession,
    filepath: Path,
    semaphore: asyncio.Semaphore,
    idx: int,
    total: int,
) -> dict:
    """Send one request to the dev container and return the result."""
    with open(filepath) as f:
        data = json.load(f)

    req = data.get("request", data.get("body", {}))
    prompt = req.get("prompt", req.get("task_description", ""))
    files = req.get("files", [])
    creds = req.get("tripletex_credentials", {})

    # Use dev sandbox credentials if available (competition proxy tokens expire)
    if DEV_SANDBOX_TOKEN:
        creds = {
            "base_url": DEV_SANDBOX_BASE_URL,
            "session_token": DEV_SANDBOX_TOKEN,
        }

    if not creds or not creds.get("session_token"):
        return {
            "file": filepath.name,
            "prompt": prompt[:100],
            "status": "skipped",
            "reason": "no credentials",
        }

    payload = {
        "prompt": prompt,
        "files": files,
        "tripletex_credentials": creds,
    }

    async with semaphore:
        short = prompt[:80].replace("\n", " ")
        print(f"[{idx+1}/{total}] Sending: {short}...")
        start = time.time()
        try:
            async with session.post(
                DEV_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_S),
            ) as resp:
                elapsed = time.time() - start
                body = await resp.text()
                try:
                    result = json.loads(body)
                except json.JSONDecodeError:
                    result = {"raw": body[:500]}

                status_code = resp.status
                executor = result.get("executor", "unknown")
                api_calls = result.get("api_calls", "?")
                api_errors = result.get("api_errors", "?")
                print(
                    f"[{idx+1}/{total}] Done in {elapsed:.1f}s | "
                    f"HTTP {status_code} | executor={executor} | "
                    f"calls={api_calls} errors={api_errors} | {short[:50]}"
                )
                return {
                    "file": filepath.name,
                    "prompt": prompt[:100],
                    "status": "completed",
                    "http_status": status_code,
                    "elapsed_s": round(elapsed, 1),
                    "executor": executor,
                    "api_calls": api_calls,
                    "api_errors": api_errors,
                    "result": result,
                }
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            print(f"[{idx+1}/{total}] TIMEOUT after {elapsed:.1f}s | {short[:50]}")
            return {
                "file": filepath.name,
                "prompt": prompt[:100],
                "status": "timeout",
                "elapsed_s": round(elapsed, 1),
            }
        except Exception as e:
            elapsed = time.time() - start
            print(f"[{idx+1}/{total}] ERROR: {e} | {short[:50]}")
            return {
                "file": filepath.name,
                "prompt": prompt[:100],
                "status": "error",
                "elapsed_s": round(elapsed, 1),
                "error": str(e),
            }


def write_results(results: list[dict], elapsed_total: float):
    """Write results to markdown file."""
    completed = [r for r in results if r["status"] == "completed"]
    timeouts = [r for r in results if r["status"] == "timeout"]
    errors = [r for r in results if r["status"] == "error"]
    skipped = [r for r in results if r["status"] == "skipped"]

    det = [r for r in completed if r.get("executor") == "deterministic"]
    claude = [r for r in completed if r.get("executor") != "deterministic"]

    lines = [
        "# Replay Results\n",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**Total requests:** {len(results)}\n",
        f"**Total time:** {elapsed_total:.0f}s\n",
        f"\n## Summary\n",
        f"| Status | Count |",
        f"|--------|-------|",
        f"| Completed | {len(completed)} |",
        f"| Timeout | {len(timeouts)} |",
        f"| Error | {len(errors)} |",
        f"| Skipped | {len(skipped)} |",
        f"\n### Executor Split\n",
        f"| Executor | Count | Avg Time | Avg Calls | Avg Errors |",
        f"|----------|-------|----------|-----------|------------|",
    ]

    for label, group in [("Deterministic", det), ("Claude", claude)]:
        if group:
            avg_time = sum(r["elapsed_s"] for r in group) / len(group)
            avg_calls = sum(
                r["api_calls"] for r in group if isinstance(r["api_calls"], int)
            ) / max(1, len([r for r in group if isinstance(r["api_calls"], int)]))
            avg_errors = sum(
                r["api_errors"] for r in group if isinstance(r["api_errors"], int)
            ) / max(1, len([r for r in group if isinstance(r["api_errors"], int)]))
            lines.append(
                f"| {label} | {len(group)} | {avg_time:.1f}s | {avg_calls:.1f} | {avg_errors:.1f} |"
            )

    lines.append(f"\n## All Results\n")
    lines.append(
        "| # | File | Executor | Time | Calls | Errors | Status | Prompt |"
    )
    lines.append(
        "|---|------|----------|------|-------|--------|--------|--------|"
    )

    for i, r in enumerate(results):
        status = r["status"]
        executor = r.get("executor", "-")
        elapsed = r.get("elapsed_s", "-")
        calls = r.get("api_calls", "-")
        errs = r.get("api_errors", "-")
        prompt = r["prompt"][:60].replace("|", "\\|")
        lines.append(
            f"| {i+1} | {r['file'][:30]} | {executor} | {elapsed}s | {calls} | {errs} | {status} | {prompt} |"
        )

    if timeouts:
        lines.append(f"\n## Timeouts ({len(timeouts)})\n")
        for r in timeouts:
            lines.append(f"- **{r['file']}**: {r['prompt']}")

    if errors:
        lines.append(f"\n## Errors ({len(errors)})\n")
        for r in errors:
            lines.append(f"- **{r['file']}**: {r.get('error', 'unknown')}")

    RESULTS_FILE.write_text("\n".join(lines))
    print(f"\nResults written to {RESULTS_FILE}")


async def main():
    parser = argparse.ArgumentParser(description="Replay competition requests")
    parser.add_argument("--concurrency", type=int, default=15, help="Max parallel requests")
    parser.add_argument("--filter", type=str, default=None, help="Filter prompts by keyword")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be sent")
    parser.add_argument("--url", type=str, default=DEV_URL, help="Target URL")
    args = parser.parse_args()

    # Collect request files
    json_files = sorted(REQUESTS_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {REQUESTS_DIR}")
        sys.exit(1)

    # Apply filter
    if args.filter:
        filtered = []
        for f in json_files:
            with open(f) as fh:
                d = json.load(fh)
                req = d.get("request", d.get("body", {}))
                prompt = req.get("prompt", req.get("task_description", "")).lower()
                if args.filter.lower() in prompt:
                    filtered.append(f)
        json_files = filtered
        print(f"Filtered to {len(json_files)} requests matching '{args.filter}'")

    print(f"Replaying {len(json_files)} requests against {args.url}")
    print(f"Concurrency: {args.concurrency}")
    print()

    if args.dry_run:
        for i, f in enumerate(json_files):
            with open(f) as fh:
                d = json.load(fh)
                req = d.get("request", d.get("body", {}))
                prompt = req.get("prompt", req.get("task_description", ""))[:80]
                has_creds = bool(req.get("tripletex_credentials", {}).get("session_token"))
                print(f"[{i+1}] {'OK' if has_creds else 'NO CREDS'} | {prompt}")
        return

    semaphore = asyncio.Semaphore(args.concurrency)
    start_total = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = [
            replay_one(session, f, semaphore, i, len(json_files))
            for i, f in enumerate(json_files)
        ]
        results = await asyncio.gather(*tasks)

    elapsed_total = time.time() - start_total
    write_results(results, elapsed_total)

    # Print summary
    completed = [r for r in results if r["status"] == "completed"]
    timeouts = [r for r in results if r["status"] == "timeout"]
    errors = [r for r in results if r["status"] == "error"]
    skipped = [r for r in results if r["status"] == "skipped"]
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(results)} requests in {elapsed_total:.0f}s")
    print(f"  Completed: {len(completed)}")
    print(f"  Timeouts:  {len(timeouts)}")
    print(f"  Errors:    {len(errors)}")
    print(f"  Skipped:   {len(skipped)}")

    det = [r for r in completed if r.get("executor") == "deterministic"]
    claude = [r for r in completed if r.get("executor") != "deterministic"]
    if det:
        avg = sum(r["elapsed_s"] for r in det) / len(det)
        print(f"  Deterministic: {len(det)} (avg {avg:.1f}s)")
    if claude:
        avg = sum(r["elapsed_s"] for r in claude) / len(claude)
        print(f"  Claude:        {len(claude)} (avg {avg:.1f}s)")


if __name__ == "__main__":
    asyncio.run(main())
