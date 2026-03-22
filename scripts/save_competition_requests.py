"""Download competition requests from GCS and save locally for replay.

Strips credentials, keeps prompt + files + result summary.
Saves to competition/requests/{task_id}.json.

Usage:
    # Save all competition requests
    python scripts/save_competition_requests.py

    # Save a specific task_id
    python scripts/save_competition_requests.py --task-id 752c1e06d0c3

    # Save from dev logs instead of competition
    python scripts/save_competition_requests.py --env dev
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

BUCKETS = {
    "comp": "ai-nm26osl-1799-competition-logs",
    "dev": "ai-nm26osl-1799-dev-logs",
}

OUTPUT_DIR = Path(__file__).parent.parent / "competition" / "requests"


def list_gcs_files(bucket: str) -> list[str]:
    result = subprocess.run(
        ["gsutil", "ls", f"gs://{bucket}/requests/"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"ERROR: gsutil ls failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def download_gcs_file(gcs_path: str) -> dict:
    result = subprocess.run(
        ["gsutil", "cat", gcs_path],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"ERROR: gsutil cat failed for {gcs_path}: {result.stderr}", file=sys.stderr)
        return {}
    return json.loads(result.stdout)


def strip_and_save(payload: dict, gcs_filename: str) -> Path | None:
    """Strip credentials, keep prompt + files + result summary."""
    task_id = payload.get("task_id")
    request = payload.get("request", {})
    result = payload.get("result", {})

    # Extract task_id from filename if not in payload (older logs)
    if not task_id:
        # Format: requests/{timestamp}_{task_id}_{prompt}.json
        # or: requests/{timestamp}_{prompt}.json (no task_id)
        parts = gcs_filename.split("/")[-1].replace(".json", "").split("_", 2)
        if len(parts) >= 2 and len(parts[1]) == 12:
            task_id = parts[1]
        else:
            # No task_id — use timestamp as identifier
            task_id = parts[0].replace("-", "").replace("T", "_")

    # Build stripped payload
    saved = {
        "task_id": task_id,
        "timestamp": payload.get("timestamp", ""),
        "prompt": request.get("prompt", ""),
        "files": [
            {
                "filename": f.get("filename", ""),
                "mime_type": f.get("mime_type", ""),
                "content_base64": f.get("content_base64", ""),
            }
            for f in request.get("files", [])
        ],
        "result_summary": {
            "status": (result or {}).get("status"),
            "iterations": (result or {}).get("iterations"),
            "api_calls": (result or {}).get("api_calls"),
            "api_errors": (result or {}).get("api_errors"),
            "time_ms": (result or {}).get("time_ms"),
            "error_details": (result or {}).get("error_details", []),
        },
    }

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / f"{task_id}.json"
    filepath.write_text(json.dumps(saved, indent=2, ensure_ascii=False) + "\n")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Save competition requests locally")
    parser.add_argument("--task-id", help="Save a specific task_id only")
    parser.add_argument("--env", choices=["comp", "dev"], default="comp",
                        help="Which environment to pull from (default: comp)")
    args = parser.parse_args()

    bucket = BUCKETS[args.env]
    print(f"Listing requests from gs://{bucket}/requests/")

    gcs_files = list_gcs_files(bucket)
    print(f"Found {len(gcs_files)} requests")

    saved = 0
    skipped = 0
    for gcs_path in gcs_files:
        filename = gcs_path.split("/")[-1]

        # Filter by task_id if specified
        if args.task_id and args.task_id not in filename:
            continue

        # Check if already saved
        # Try to extract task_id from filename
        parts = filename.replace(".json", "").split("_", 2)
        if len(parts) >= 2 and len(parts[1]) == 12:
            existing = OUTPUT_DIR / f"{parts[1]}.json"
        else:
            existing = None

        if existing and existing.exists() and not args.task_id:
            skipped += 1
            continue

        payload = download_gcs_file(gcs_path)
        if not payload:
            continue

        filepath = strip_and_save(payload, filename)
        if filepath:
            task_id = filepath.stem
            prompt_preview = payload.get("request", {}).get("prompt", "")[:60]
            errors = (payload.get("result") or {}).get("api_errors", 0)
            print(f"  Saved {filepath.name} ({errors} errors) — {prompt_preview}")
            saved += 1

    print(f"\nDone: {saved} saved, {skipped} already existed")


if __name__ == "__main__":
    main()
