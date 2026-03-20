#!/usr/bin/env python3
"""Local test harness — sends task payloads to /solve using sandbox credentials.

Usage:
  # Start server first: uvicorn main:app --port 8000
  python test_harness.py "Opprett en ansatt med navn Ola Nordmann"
  python test_harness.py --file receipt.pdf "Registrer denne fakturaen"
  python test_harness.py --list  # show sample tasks
"""

import argparse
import base64
import json
import mimetypes
import sys
import time
from pathlib import Path

import requests

# --- Configuration (edit these or set via environment) ---
SOLVE_URL = "http://localhost:8000/solve"
SANDBOX_BASE_URL = "https://kkpqfuj-amager.tripletex.dev/v2"
SANDBOX_TOKEN = ""  # Set via TRIPLETEX_SESSION_TOKEN env var or --token flag

SAMPLE_TASKS = {
    "employee-simple": "Opprett en ansatt med navn Ola Nordmann i IT-avdelingen",
    "employee-en": "Create an employee named Jane Smith in the Sales department with email jane@example.com",
    "customer": "Opprett en kunde med navn Acme AS, epost post@acme.no",
    "product": "Lag et produkt med navn 'Konsulenttime' til 1500 kr eks mva",
    "invoice": "Lag en faktura til kunden Nordmann AS for 3 timer konsulentarbeid à 1500 kr",
    "department": "Opprett en avdeling med navn 'Utvikling' og avdelingsnummer '300'",
    "employee-de": "Erstellen Sie einen Mitarbeiter namens Hans Müller in der Buchhaltungsabteilung",
    "employee-es": "Crea un empleado llamado Carlos García en el departamento de Ventas",
}


def build_payload(prompt: str, file_paths: list[str], token: str) -> dict:
    """Build the competition-format payload."""
    files = []
    for path_str in file_paths:
        path = Path(path_str)
        if not path.exists():
            print(f"WARNING: File not found: {path}")
            continue
        mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        files.append({
            "filename": path.name,
            "content_base64": base64.b64encode(path.read_bytes()).decode(),
            "mime_type": mime_type,
        })

    return {
        "prompt": prompt,
        "files": files,
        "tripletex_credentials": {
            "base_url": SANDBOX_BASE_URL,
            "session_token": token,
        },
    }


def main():
    import os
    parser = argparse.ArgumentParser(description="Test harness for Tripletex agent")
    parser.add_argument("prompt", nargs="?", help="Task prompt to send")
    parser.add_argument("--file", action="append", default=[], help="Attach file(s)")
    parser.add_argument("--token", default=os.getenv("TRIPLETEX_SESSION_TOKEN", SANDBOX_TOKEN))
    parser.add_argument("--url", default=SOLVE_URL, help="Solve endpoint URL")
    parser.add_argument("--list", action="store_true", help="List sample tasks")
    parser.add_argument("--sample", help="Run a sample task by name")
    args = parser.parse_args()

    if args.list:
        print("Sample tasks:")
        for name, prompt in SAMPLE_TASKS.items():
            print(f"  {name:20s} → {prompt}")
        return

    if args.sample:
        if args.sample not in SAMPLE_TASKS:
            print(f"Unknown sample: {args.sample}. Use --list to see options.")
            return
        prompt = SAMPLE_TASKS[args.sample]
    elif args.prompt:
        prompt = args.prompt
    else:
        parser.print_help()
        return

    if not args.token:
        print("ERROR: No session token. Set TRIPLETEX_SESSION_TOKEN or use --token")
        sys.exit(1)

    payload = build_payload(prompt, args.file, args.token)

    print(f"Sending to {args.url}")
    print(f"  Prompt: {prompt}")
    print(f"  Files: {len(payload['files'])}")
    print()

    start = time.time()
    try:
        resp = requests.post(args.url, json=payload, timeout=310)
        elapsed = time.time() - start
        print(f"Response: {resp.status_code} in {elapsed:.1f}s")
        print(f"  Body: {resp.json()}")
    except requests.Timeout:
        print(f"TIMEOUT after {time.time() - start:.1f}s")
    except requests.ConnectionError:
        print("ERROR: Cannot connect. Is the server running? (uvicorn main:app --port 8000)")


if __name__ == "__main__":
    main()
