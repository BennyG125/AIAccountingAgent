"""Replay a saved competition request against the dev container.

Injects credentials from .env and sends the exact same prompt + files.

Usage:
    source .env && export TRIPLETEX_BASE_URL TRIPLETEX_SESSION_TOKEN

    # Replay a specific request
    python scripts/replay_request.py competition/requests/752c1e06d0c3.json

    # Replay against a different URL
    python scripts/replay_request.py competition/requests/752c1e06d0c3.json --url https://...
"""
import argparse
import json
import os
import sys
import time

import requests


DEV_URL = "https://ai-accounting-agent-det-590159115697.europe-north1.run.app"


def main():
    parser = argparse.ArgumentParser(description="Replay a competition request")
    parser.add_argument("request_file", help="Path to saved request JSON")
    parser.add_argument("--url", default=DEV_URL, help="Container URL (default: dev)")
    args = parser.parse_args()

    # Load saved request
    with open(args.request_file) as f:
        saved = json.load(f)

    # Get credentials from environment
    base_url = os.environ.get("TRIPLETEX_BASE_URL")
    session_token = os.environ.get("TRIPLETEX_SESSION_TOKEN")
    if not base_url or not session_token:
        print("ERROR: Set TRIPLETEX_BASE_URL and TRIPLETEX_SESSION_TOKEN", file=sys.stderr)
        print("  source .env && export TRIPLETEX_BASE_URL TRIPLETEX_SESSION_TOKEN", file=sys.stderr)
        sys.exit(1)

    # Build payload in evaluator format
    payload = {
        "prompt": saved["prompt"],
        "files": saved.get("files", []),
        "tripletex_credentials": {
            "base_url": base_url,
            "session_token": session_token,
        },
    }

    task_id = saved.get("task_id", "?")
    prompt_preview = saved["prompt"][:80]
    prev_errors = saved.get("result_summary", {}).get("api_errors", "?")

    print(f"Replaying task_id={task_id}")
    print(f"  Prompt: {prompt_preview}...")
    print(f"  Previous: {prev_errors} errors")
    print(f"  Target: {args.url}/")
    print()

    # Send request
    start = time.time()
    resp = requests.post(
        f"{args.url}/",
        json=payload,
        timeout=300,
    )
    elapsed = time.time() - start

    print(f"  Response: HTTP {resp.status_code} in {elapsed:.1f}s")
    print(f"  Body: {resp.text[:200]}")


if __name__ == "__main__":
    main()
