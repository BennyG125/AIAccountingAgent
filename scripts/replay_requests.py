#!/usr/bin/env python3
"""Replay captured competition requests against the dev container.

Sends each request.json from real-requests/logs/ to the dev container,
using sandbox credentials instead of the competition proxy credentials.
Reports results per request.

Usage:
    source .env && export TRIPLETEX_SESSION_TOKEN
    python scripts/replay_requests.py                          # all requests
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


def main():
    parser = argparse.ArgumentParser(description="Replay competition requests against dev")
    parser.add_argument("--url", default=DEV_URL, help="Target URL")
    parser.add_argument("--request", help="Replay single request by number prefix (e.g., '003')")
    parser.add_argument("--dry-run", action="store_true", help="Classify only, don't send")
    parser.add_argument("--timeout", type=int, default=300, help="Request timeout in seconds")
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

    results = []
    total = len(folders)

    for idx, folder in enumerate(folders, 1):
        request_data = load_request(folder)
        if request_data is None:
            continue

        prompt = request_data.get("prompt", "?")[:80]
        files_count = len(request_data.get("files", []))
        folder_name = folder.name

        if args.dry_run:
            classification = classify_only(request_data)
            print(f"[{idx:3d}/{total}] {folder_name}")
            print(f"  Classify: {classification}")
            print(f"  Prompt: {prompt}...")
            print(f"  Files: {files_count}")
            results.append({
                "folder": folder_name,
                "classification": classification,
                "prompt_preview": prompt,
                "files": files_count,
            })
            continue

        print(f"\n[{idx:3d}/{total}] {folder_name}")
        print(f"  Prompt: {prompt}...")
        print(f"  Files: {files_count}")

        result = send_request(args.url, request_data, session_token, args.timeout)

        status = "OK" if result["status_code"] == 200 else "FAIL"
        print(f"  Result: {status} ({result['status_code']}) in {result['elapsed_seconds']}s")

        entry = {
            "folder": folder_name,
            "prompt_preview": prompt,
            "files": files_count,
            "status_code": result["status_code"],
            "elapsed_seconds": result["elapsed_seconds"],
            "response": result["response"],
        }
        results.append(entry)

        # Save individual result
        result_file = RESULTS_DIR / f"{folder_name}.json"
        with open(result_file, "w") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*70}")
    if args.dry_run:
        print("DRY RUN — Classification Results")
        for r in results:
            print(f"  {r['folder']}: {r['classification']}")
    else:
        ok = sum(1 for r in results if r["status_code"] == 200)
        fail = sum(1 for r in results if r["status_code"] != 200)
        avg_time = sum(r["elapsed_seconds"] for r in results) / len(results) if results else 0
        print(f"Results: {ok} OK, {fail} FAIL out of {len(results)} requests")
        print(f"Average time: {avg_time:.1f}s")
        print()
        for r in results:
            status = "OK  " if r["status_code"] == 200 else "FAIL"
            print(f"  [{status}] {r['folder']} — {r['elapsed_seconds']}s")

    # Save summary
    summary_file = RESULTS_DIR / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
