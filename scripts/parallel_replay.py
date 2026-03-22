#!/usr/bin/env python3
"""Replay competition requests in parallel against the dev container.

Usage:
    source .env && export TRIPLETEX_BASE_URL TRIPLETEX_SESSION_TOKEN
    python scripts/parallel_replay.py [--concurrent N] [--files f1.json f2.json ...]
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

DEV_URL = "https://ai-accounting-agent-det-590159115697.europe-north1.run.app"

sys.path.insert(0, str(Path(__file__).parent.parent))
from execution_plans._classifier import classify_task


def replay_one(filepath, base_url, session_token, target_url):
    with open(filepath) as f:
        saved = json.load(f)

    prompt = saved["prompt"]
    task_type = classify_task(prompt) or "UNKNOWN"

    payload = {
        "prompt": prompt,
        "files": saved.get("files", []),
        "tripletex_credentials": {
            "base_url": base_url,
            "session_token": session_token,
        },
    }

    start = time.time()
    try:
        resp = requests.post(f"{target_url}/", json=payload, timeout=300)
        elapsed = time.time() - start
        body = resp.json() if resp.status_code == 200 else {}
    except Exception as e:
        elapsed = time.time() - start
        return {
            "file": Path(filepath).name,
            "task_type": task_type,
            "status": "ERROR",
            "elapsed": round(elapsed, 1),
            "error": str(e),
        }

    executor = body.get("executor", "?")
    api_calls = body.get("api_calls", "?")
    api_errors = body.get("api_errors", "?")

    return {
        "file": Path(filepath).name,
        "task_type": task_type,
        "status": "OK" if resp.status_code == 200 else f"HTTP_{resp.status_code}",
        "executor": executor,
        "api_calls": api_calls,
        "api_errors": api_errors,
        "elapsed": round(elapsed, 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrent", type=int, default=10)
    parser.add_argument("--url", default=DEV_URL)
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    base_url = os.environ.get("TRIPLETEX_BASE_URL")
    session_token = os.environ.get("TRIPLETEX_SESSION_TOKEN")
    if not base_url or not session_token:
        print("ERROR: Set TRIPLETEX_BASE_URL and TRIPLETEX_SESSION_TOKEN")
        sys.exit(1)

    files = args.files
    if not files:
        import glob
        # Pick one per task type
        task_samples = {}
        for f in sorted(glob.glob("competition/requests/*.json")):
            with open(f) as fh:
                d = json.load(fh)
            tt = classify_task(d.get("prompt", "")) or "UNKNOWN"
            if tt not in task_samples:
                task_samples[tt] = f
        files = list(task_samples.values())

    print(f"Replaying {len(files)} requests with {args.concurrent} concurrent workers...")
    print(f"Target: {args.url}")
    print()

    start_all = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=args.concurrent) as executor:
        futures = {
            executor.submit(replay_one, f, base_url, session_token, args.url): f
            for f in files
        }
        for future in as_completed(futures):
            r = future.result()
            status_icon = "OK" if r.get("api_errors", 1) == 0 else "!!"
            if r["status"] != "OK":
                status_icon = "XX"
            print(
                f"  [{status_icon}] {r['task_type']:30s} "
                f"exec={r.get('executor','?'):15s} "
                f"calls={r.get('api_calls','?'):>3} "
                f"errs={r.get('api_errors','?'):>2} "
                f"{r['elapsed']:5.1f}s"
            )
            results.append(r)

    wall_time = time.time() - start_all

    # Summary
    print(f"\n{'='*70}")
    det_count = sum(1 for r in results if r.get("executor") == "deterministic")
    claude_count = sum(1 for r in results if r.get("executor") == "claude")
    det_errors = sum(r.get("api_errors", 0) for r in results if r.get("executor") == "deterministic")
    claude_errors = sum(r.get("api_errors", 0) for r in results if r.get("executor") == "claude")
    http_errors = sum(1 for r in results if r["status"] != "OK")
    total_calls = sum(r.get("api_calls", 0) for r in results if isinstance(r.get("api_calls"), int))

    print(f"Total: {len(results)} requests in {wall_time:.0f}s")
    print(f"  Deterministic: {det_count} requests, {det_errors} errors")
    print(f"  Claude:        {claude_count} requests, {claude_errors} errors")
    print(f"  HTTP errors:   {http_errors}")
    print(f"  Total API calls: {total_calls}")


if __name__ == "__main__":
    main()
