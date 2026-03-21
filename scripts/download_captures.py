#!/usr/bin/env python3
"""Download captured competition requests from GCS into real-requests/logs/.

Each request gets its own numbered folder with request.json and any decoded files.

Usage:
    python scripts/download_captures.py                    # all default buckets
    python scripts/download_captures.py --bucket my-bucket # specific bucket
"""
import argparse
import base64
import json
import os
import re

from google.cloud import storage

DEFAULT_BUCKETS = [
    "ai-nm26osl-1799-competition-logs",
    "ai-nm26osl-1799-dev-logs",
]
OUTPUT_DIR = "real-requests/logs"


def _safe_name(text: str, max_len: int = 40) -> str:
    """Convert text to a filesystem-safe directory name."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", text).strip("_")
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    return safe[:max_len]


def _extract_request(raw: dict) -> dict:
    """Extract the request payload from either format (direct or wrapped)."""
    if "request" in raw:
        return raw["request"]
    return raw


def download(buckets: list[str] | None = None):
    buckets = buckets or DEFAULT_BUCKETS
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    idx = 1
    seen_prompts = set()  # deduplicate across buckets

    for bucket_name in buckets:
        print(f"\n--- Scanning gs://{bucket_name} ---")
        try:
            client = storage.Client()
            bucket = client.bucket(bucket_name)
        except Exception as e:
            print(f"  Skipping (cannot access): {e}")
            continue

        prefixes = ["captured/", "requests/"]

        for prefix in prefixes:
            try:
                blobs = sorted(
                    bucket.list_blobs(prefix=prefix), key=lambda b: b.name
                )
            except Exception:
                continue

            for blob in blobs:
                try:
                    raw = json.loads(blob.download_as_text())
                except Exception:
                    continue

                data = _extract_request(raw)
                prompt = (
                    data.get("prompt") or data.get("task_prompt") or "unknown"
                )

                # Deduplicate by prompt text
                prompt_key = prompt.strip()[:200]
                if prompt_key in seen_prompts:
                    continue
                seen_prompts.add(prompt_key)

                prompt_preview = _safe_name(prompt)
                folder = os.path.join(OUTPUT_DIR, f"{idx:03d}_{prompt_preview}")
                os.makedirs(folder, exist_ok=True)

                # Save full raw payload
                with open(os.path.join(folder, "request.json"), "w") as f:
                    json.dump(raw, f, indent=2, ensure_ascii=False)

                # Decode and save attached files
                files = data.get("files") or data.get("attached_files") or []
                for file_idx, file_entry in enumerate(files):
                    filename = file_entry.get("filename", f"file_{file_idx}")
                    # Try all known base64 field names
                    content_b64 = (
                        file_entry.get("content")
                        or file_entry.get("data")
                        or file_entry.get("content_base64", "")
                    )
                    if content_b64:
                        try:
                            file_data = base64.b64decode(content_b64)
                            filepath = os.path.join(folder, filename)
                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                            with open(filepath, "wb") as f:
                                f.write(file_data)
                            print(f"  Decoded file: {filepath}")
                        except Exception as e:
                            print(f"  Warning: could not decode {filename}: {e}")

                print(f"  [{bucket_name}] {folder}")
                idx += 1

    print(f"\nDone. {idx - 1} requests saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download captured requests from GCS")
    parser.add_argument(
        "--bucket", action="append",
        help="GCS bucket to download from (can specify multiple). Defaults to all known buckets.",
    )
    args = parser.parse_args()
    download(args.bucket)
