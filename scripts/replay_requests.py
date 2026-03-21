#!/usr/bin/env python3
"""Replay captured competition requests against the dev container.

Sends each request.json from real-requests/logs/ to the dev container,
using sandbox credentials instead of the competition proxy credentials.
Reports results per request. Supports concurrent execution.

Usage:
    source .env && export TRIPLETEX_SESSION_TOKEN
    python scripts/replay_requests.py                          # all requests (sequential)
    python scripts/replay_requests.py --concurrent 5           # 5 concurrent requests
    python scripts/replay_requests.py --request 003            # single request (by number prefix)
    python scripts/replay_requests.py --url http://localhost:8080  # local server
    python scripts/replay_requests.py --dry-run                # classify only, no API calls
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests as http_requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DEV_URL = "https://ai-accounting-agent-det-590159115697.europe-north1.run.app"
SANDBOX_BASE_URL = "https://kkpqfuj-amager.tripletex.dev/v2"
LOGS_DIR = Path("real-requests/logs")
RESULTS_DIR = Path("real-requests/replay-results")


def load_request(folder: Path) -> dict | None:
    """Load request.json from a log folder."""
    req_file = folder / "request.json"
    if not req_file.exists():
        return None
    with open(req_file) as f:
        raw = json.load(f)
    # Handle wrapped format {request: {prompt, files, ...}} vs direct
    if "request" in raw:
        return raw["request"]
    return raw


def send_request(url: str, request_data: dict, session_token: str, timeout: int = 300) -> dict:
    """Send a request to the dev container with sandbox credentials."""
    # Replace competition proxy credentials with our sandbox
    payload = {
        "prompt": request_data.get("prompt", ""),
        "files": request_data.get("files", []),
        "tripletex_credentials": {
            "base_url": SANDBOX_BASE_URL,
            "session_token": session_token,
        },
    }

    start = time.time()
    try:
        resp = http_requests.post(
            url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
        elapsed = time.time() - start
        return {
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code == 200 else resp.text,
            "elapsed_seconds": round(elapsed, 1),
        }
    except http_requests.exceptions.Timeout:
        return {
            "status_code": 0,
            "response": "TIMEOUT",
            "elapsed_seconds": round(time.time() - start, 1),
        }
    except Exception as e:
        return {
            "status_code": 0,
            "response": f"ERROR: {e}",
            "elapsed_seconds": round(time.time() - start, 1),
        }


def classify_only(request_data: dict) -> str:
    """Run classifier locally without sending to server."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from execution_plans._classifier import classify_task
    from execution_plans._registry import PLANS
    prompt = request_data.get("prompt", "")
    task_type = classify_task(prompt) or "UNKNOWN"
    has_plan = task_type in PLANS
    return f"{task_type} (plan={'YES' if has_plan else 'NO'})"


def _replay_one(args_tuple):
    """Worker function for concurrent replay."""
    idx, total, folder, url, session_token, timeout = args_tuple
    request_data = load_request(folder)
    if request_data is None:
        return None

    prompt = request_data.get("prompt", "?")[:80]
    files_count = len(request_data.get("files", []))
    folder_name = folder.name

    result = send_request(url, request_data, session_token, timeout)
    status = "OK" if result["status_code"] == 200 else "FAIL"
    print(f"[{status}] [{idx:3d}/{total}] {folder_name:55s} {result['elapsed_seconds']:6.1f}s")

    entry = {
        "folder": folder_name,
        "prompt_preview": prompt,
        "files": files_count,
        "status_code": result["status_code"],
        "elapsed_seconds": result["elapsed_seconds"],
        "response": result["response"],
    }

    # Save individual result
    result_file = RESULTS_DIR / f"{folder_name}.json"
    with open(result_file, "w") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)

    return entry


def main():
    parser = argparse.ArgumentParser(description="Replay competition requests against dev")
    parser.add_argument("--url", default=DEV_URL, help="Target URL")
    parser.add_argument("--request", help="Replay single request by number prefix (e.g., '003')")
    parser.add_argument("--dry-run", action="store_true", help="Classify only, don't send")
    parser.add_argument("--timeout", type=int, default=300, help="Request timeout in seconds")
    parser.add_argument("--concurrent", type=int, default=1, help="Number of concurrent requests")
    args = parser.parse_args()

    session_token = os.getenv("TRIPLETEX_SESSION_TOKEN", "")
    if not session_token and not args.dry_run:
        print("ERROR: TRIPLETEX_SESSION_TOKEN not set. Run: source .env && export TRIPLETEX_SESSION_TOKEN")
        sys.exit(1)

    # Find request folders
    if not LOGS_DIR.exists():
        print(f"ERROR: {LOGS_DIR} not found. Run scripts/download_captures.py first.")
        sys.exit(1)

    folders = sorted(LOGS_DIR.iterdir())
    if args.request:
        folders = [f for f in folders if f.name.startswith(args.request)]
        if not folders:
            print(f"No request folder matching '{args.request}'")
            sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    total = len(folders)

    if args.dry_run:
        for idx, folder in enumerate(folders, 1):
            request_data = load_request(folder)
            if request_data is None:
                continue
            classification = classify_only(request_data)
            prompt = request_data.get("prompt", "?")[:80]
            print(f"[{idx:3d}/{total}] {folder.name}: {classification}")
        return

    # Build work items
    work = []
    for idx, folder in enumerate(folders, 1):
        work.append((idx, total, folder, args.url, session_token, args.timeout))

    start_all = time.time()

    if args.concurrent > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        print(f"Replaying {total} requests with {args.concurrent} concurrent workers...\n")
        results = []
        with ThreadPoolExecutor(max_workers=args.concurrent) as executor:
            futures = {executor.submit(_replay_one, w): w for w in work}
            for future in as_completed(futures):
                entry = future.result()
                if entry:
                    results.append(entry)
    else:
        print(f"Replaying {total} requests sequentially...\n")
        results = []
        for w in work:
            entry = _replay_one(w)
            if entry:
                results.append(entry)

    wall_time = time.time() - start_all

    # Sort results by folder name for display
    results.sort(key=lambda r: r["folder"])

    # Summary
    print(f"\n{'='*70}")
    ok = sum(1 for r in results if r["status_code"] == 200)
    fail = sum(1 for r in results if r["status_code"] != 200)
    sum_time = sum(r["elapsed_seconds"] for r in results)
    avg_time = sum_time / len(results) if results else 0
    print(f"Results: {ok} OK, {fail} FAIL out of {len(results)} requests")
    print(f"Avg request time: {avg_time:.1f}s | Wall time: {wall_time:.0f}s ({wall_time/60:.1f}min)")
    if args.concurrent > 1:
        print(f"Concurrency: {args.concurrent} workers | Speedup: {sum_time/wall_time:.1f}x")
    print()
    for r in results:
        status = "OK  " if r["status_code"] == 200 else "FAIL"
        print(f"  [{status}] {r['folder']:55s} {r['elapsed_seconds']:6.1f}s")

    # Save summary
    summary_file = RESULTS_DIR / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
