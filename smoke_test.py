#!/usr/bin/env python3
"""Smoke test — sends competition-format tasks to deployed /solve endpoint.

Tests all 7 task categories across Tier 1 and Tier 2, then verifies
results via direct Tripletex API calls.

Usage:
  python smoke_test.py                          # test against Cloud Run
  python smoke_test.py --url http://localhost:8000/solve  # test local
  python smoke_test.py --task create_department  # run single task
  python smoke_test.py --list                    # list available tasks
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import date

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLOUD_RUN_URL = "https://ai-accounting-agent-det-590159115697.europe-north1.run.app/solve"
SANDBOX_BASE_URL = os.getenv("TRIPLETEX_BASE_URL", "https://kkpqfuj-amager.tripletex.dev/v2")
SANDBOX_TOKEN = os.getenv("TRIPLETEX_SESSION_TOKEN", "")

_run_id = str(int(time.time()))[-6:]


def u(name: str) -> str:
    """Unique name per test run to avoid collisions."""
    return f"{name}_{_run_id}"


# ---------------------------------------------------------------------------
# Task definitions — mirrors competition format
# ---------------------------------------------------------------------------

TASKS = {
    # Tier 1: single-step
    "create_department": {
        "tier": 1,
        "prompt": f"Opprett en avdeling med navn '{u('TestSalg')}' og avdelingsnummer '{_run_id[:3]}'",
        "verify": {
            "endpoint": "/department",
            "search": {"name": u("TestSalg")},
            "expect": {"name": u("TestSalg")},
        },
    },
    "create_employee": {
        "tier": 1,
        "prompt": (
            f"Opprett en ansatt med fornavn 'Kari', etternavn '{u('Nordmann')}', "
            f"e-post kari_{_run_id}@example.com og brukertype STANDARD"
        ),
        "verify": {
            "endpoint": "/employee",
            "search": {"lastName": u("Nordmann")},
            "expect": {"firstName": "Kari", "lastName": u("Nordmann")},
        },
    },
    "create_customer": {
        "tier": 1,
        "prompt": (
            f"Opprett en kunde med navn '{u('Bergen Consulting AS')}' "
            f"og e-post post_{_run_id}@bergenconsulting.no"
        ),
        "verify": {
            "endpoint": "/customer",
            "search": {"name": u("Bergen Consulting AS")},
            "expect": {"name": u("Bergen Consulting AS")},
        },
    },
    "create_product": {
        "tier": 1,
        "prompt": (
            f"Opprett et produkt med navn '{u('Konsulenttjeneste')}', "
            f"pris 1500 NOK ekskl. mva og MVA-sats 25%"
        ),
        "verify": {
            "endpoint": "/product",
            "search": {"name": u("Konsulenttjeneste")},
            "expect": {"name": u("Konsulenttjeneste")},
        },
    },

    # Tier 1: multilingual
    "create_employee_en": {
        "tier": 1,
        "prompt": (
            f"Create an employee with first name 'Jane', last name '{u('Smith')}', "
            f"email jane_{_run_id}@example.com and user type STANDARD"
        ),
        "verify": {
            "endpoint": "/employee",
            "search": {"lastName": u("Smith")},
            "expect": {"firstName": "Jane", "lastName": u("Smith")},
        },
    },
    "create_customer_de": {
        "tier": 1,
        "prompt": (
            f"Erstellen Sie einen Kunden namens '{u('München GmbH')}' "
            f"mit E-Mail info_{_run_id}@muenchen.de"
        ),
        "verify": {
            "endpoint": "/customer",
            "search": {"name": u("München GmbH")},
            "expect": {"name": u("München GmbH")},
        },
    },

    # Tier 2: multi-step flows
    "create_invoice_flow": {
        "tier": 2,
        "prompt": (
            f"Opprett en kunde '{u('Fjord Tech AS')}', "
            f"opprett et produkt '{u('Rådgivning')}' til 2000 kr ekskl. mva, "
            f"opprett en ordre for kunden med produktet, "
            f"fakturer ordren, og registrer betaling for fakturaen."
        ),
        "verify": {
            "endpoint": "/customer",
            "search": {"name": u("Fjord Tech AS")},
            "expect": {"name": u("Fjord Tech AS")},
        },
    },
    "create_travel_expense": {
        "tier": 2,
        "prompt": (
            f"Opprett en reiseregning med beskrivelse '{u('Kundemøte Oslo')}' "
            f"for en ansatt, med en kostnad på 500 NOK."
        ),
        "verify": {
            "endpoint": "/travelExpense",
            "search": {},
            "expect": {"title": u("Kundemøte Oslo")},
        },
    },
    "create_project": {
        "tier": 2,
        "prompt": (
            f"Opprett et prosjekt med navn '{u('Nettside Redesign')}' "
            f"og sett en prosjektleder."
        ),
        "verify": {
            "endpoint": "/project",
            "search": {"name": u("Nettside Redesign")},
            "expect": {"name": u("Nettside Redesign")},
        },
    },

    # Tier 2: action patterns (update/delete)
    "update_customer": {
        "tier": 2,
        "prompt": (
            f"Opprett en kunde med navn '{u('UpdateTest AS')}', "
            f"deretter oppdater e-posten til kunden til test_{_run_id}@update.no"
        ),
        "verify": {
            "endpoint": "/customer",
            "search": {"name": u("UpdateTest AS")},
            "expect": {"email": f"test_{_run_id}@update.no"},
        },
    },
    "delete_department": {
        "tier": 2,
        "prompt": (
            f"Opprett en avdeling med navn '{u('SlettMeg')}' og avdelingsnummer '{_run_id[:3]}1', "
            f"deretter slett avdelingen"
        ),
        "verify": {
            "endpoint": "/department",
            "search": {"name": u("SlettMeg")},
            "expect": {},  # should NOT be found
        },
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_auth_header(url: str) -> dict:
    """Get auth header — identity token for Cloud Run, none for local."""
    if "run.app" in url:
        import subprocess
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"], text=True
        ).strip()
        return {"Authorization": f"Bearer {token}"}
    return {}


def call_solve(url: str, prompt: str, auth_headers: dict) -> dict:
    """Send a task to the /solve endpoint."""
    payload = {
        "prompt": prompt,
        "files": [],
        "tripletex_credentials": {
            "base_url": SANDBOX_BASE_URL,
            "session_token": SANDBOX_TOKEN,
        },
    }
    resp = requests.post(url, json=payload, headers=auth_headers, timeout=310)
    return {"status_code": resp.status_code, "body": resp.json(), "elapsed": resp.elapsed.total_seconds()}


def verify_in_tripletex(endpoint: str, search_params: dict, expected: dict) -> dict:
    """Verify an entity was created in Tripletex."""
    url = f"{SANDBOX_BASE_URL}{endpoint}"
    params = {**search_params, "fields": "*", "count": "10"}
    resp = requests.get(url, auth=("0", SANDBOX_TOKEN), params=params, timeout=30)
    if resp.status_code != 200:
        return {"found": False, "error": f"GET {endpoint} returned {resp.status_code}"}

    values = resp.json().get("values", [])

    # For endpoints without good search, scan all
    if not search_params and expected:
        key = list(expected.keys())[0]
        val = expected[key]
        values = [v for v in values if v.get(key) == val]

    if not values:
        return {"found": False, "error": f"No results for {search_params}"}

    entity = values[0]
    mismatches = {}
    for field, expected_val in expected.items():
        actual = entity.get(field)
        if actual != expected_val:
            mismatches[field] = {"expected": expected_val, "actual": actual}

    return {"found": True, "entity_id": entity.get("id"), "mismatches": mismatches}


# ---------------------------------------------------------------------------
# Cleanup — delete test entities from sandbox
# ---------------------------------------------------------------------------

# Reverse dependency order: delete children before parents
CLEANUP_ORDER = [
    # Payments/invoices are hard to delete (locked after payment), skip them.
    # Travel expense sub-types
    {"endpoint": "/travelExpense/cost", "search_key": None, "scan_key": "travelExpense"},
    # Travel expense
    {"endpoint": "/travelExpense", "search_key": None, "scan_key": "title"},
    # Project participants (no name search — skip)
    # Projects
    {"endpoint": "/project", "search_key": "name", "scan_key": "name"},
    # Contacts
    {"endpoint": "/contact", "search_key": None, "scan_key": "lastName"},
    # Employees
    {"endpoint": "/employee", "search_key": "lastName", "scan_key": "lastName"},
    # Customers
    {"endpoint": "/customer", "search_key": "name", "scan_key": "name"},
    # Products
    {"endpoint": "/product", "search_key": "name", "scan_key": "name"},
    # Departments
    {"endpoint": "/department", "search_key": "name", "scan_key": "name"},
]


def cleanup_sandbox(run_id: str):
    """Delete all entities created during this test run from the sandbox."""
    logger.info(f"\n{'='*60}")
    logger.info(f"CLEANUP: Removing test entities (run_id={run_id})")
    logger.info(f"{'='*60}")

    deleted = 0
    failed = 0

    for entry in CLEANUP_ORDER:
        endpoint = entry["endpoint"]
        scan_key = entry["scan_key"]

        # Fetch recent entities and filter by run_id suffix
        url = f"{SANDBOX_BASE_URL}{endpoint}"
        params = {"fields": "*", "count": "100"}

        try:
            resp = requests.get(url, auth=("0", SANDBOX_TOKEN), params=params, timeout=30)
            if resp.status_code != 200:
                continue
            values = resp.json().get("values", [])
        except Exception:
            continue

        # Find entities matching our run_id
        to_delete = []
        for v in values:
            scan_val = str(v.get(scan_key, ""))
            if run_id in scan_val:
                to_delete.append(v)

        for entity in to_delete:
            eid = entity["id"]
            try:
                del_resp = requests.delete(
                    f"{SANDBOX_BASE_URL}{endpoint}/{eid}",
                    auth=("0", SANDBOX_TOKEN), timeout=30,
                )
                if 200 <= del_resp.status_code < 300:
                    logger.info(f"  Deleted {endpoint}/{eid} ({entity.get(scan_key, '?')})")
                    deleted += 1
                else:
                    logger.warning(f"  Failed to delete {endpoint}/{eid}: HTTP {del_resp.status_code}")
                    failed += 1
            except Exception as e:
                logger.warning(f"  Failed to delete {endpoint}/{eid}: {e}")
                failed += 1

    logger.info(f"Cleanup complete: {deleted} deleted, {failed} failed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_task(name: str, task: dict, url: str, auth_headers: dict) -> dict:
    """Run a single task: call /solve, then verify."""
    tier = task["tier"]
    prompt = task["prompt"]
    verify = task["verify"]

    logger.info(f"{'='*60}")
    logger.info(f"[Tier {tier}] {name}")
    logger.info(f"  Prompt: {prompt[:100]}...")

    # Call /solve
    start = time.time()
    try:
        result = call_solve(url, prompt, auth_headers)
    except Exception as e:
        logger.error(f"  FAIL: /solve error: {e}")
        return {"name": name, "tier": tier, "solve": "ERROR", "verify": "SKIP", "time": 0}

    elapsed = time.time() - start
    solve_ok = result["status_code"] == 200
    logger.info(f"  /solve: HTTP {result['status_code']} in {elapsed:.1f}s — {result['body']}")

    # Verify in Tripletex
    vresult = verify_in_tripletex(verify["endpoint"], verify["search"], verify["expect"])

    # Delete verification: expect={} means entity should NOT be found
    if not verify["expect"] and verify["search"]:
        if not vresult["found"]:
            logger.info(f"  Verify: PASS (entity correctly deleted)")
            verify_status = "PASS"
        else:
            logger.warning(f"  Verify: FAIL — entity still exists (id={vresult.get('entity_id')})")
            verify_status = "FAIL"
    elif vresult["found"] and not vresult["mismatches"]:
        logger.info(f"  Verify: PASS (entity id={vresult['entity_id']})")
        verify_status = "PASS"
    elif vresult["found"]:
        logger.warning(f"  Verify: PARTIAL — mismatches: {vresult['mismatches']}")
        verify_status = "PARTIAL"
    else:
        logger.warning(f"  Verify: FAIL — {vresult.get('error', 'not found')}")
        verify_status = "FAIL"

    return {
        "name": name,
        "tier": tier,
        "solve": "PASS" if solve_ok else "FAIL",
        "verify": verify_status,
        "time": round(elapsed, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Smoke test for AI Accounting Agent")
    parser.add_argument("--url", default=CLOUD_RUN_URL, help="Solve endpoint URL")
    parser.add_argument("--task", help="Run a single task by name")
    parser.add_argument("--tier", type=int, help="Run tasks for a specific tier only")
    parser.add_argument("--list", action="store_true", help="List available tasks")
    parser.add_argument("--token", help="Override Tripletex session token")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup of test entities")
    args = parser.parse_args()

    if args.list:
        print(f"\nAvailable tasks (run_id={_run_id}):\n")
        for name, task in TASKS.items():
            print(f"  Tier {task['tier']}  {name:30s}  {task['prompt'][:70]}...")
        return

    global SANDBOX_TOKEN
    if args.token:
        SANDBOX_TOKEN = args.token
    if not SANDBOX_TOKEN:
        print("ERROR: Set TRIPLETEX_SESSION_TOKEN or use --token")
        sys.exit(1)

    auth_headers = get_auth_header(args.url)

    # Select tasks
    if args.task:
        if args.task not in TASKS:
            print(f"Unknown task: {args.task}. Use --list.")
            sys.exit(1)
        tasks = {args.task: TASKS[args.task]}
    elif args.tier:
        tasks = {k: v for k, v in TASKS.items() if v["tier"] == args.tier}
    else:
        tasks = TASKS

    logger.info(f"Running {len(tasks)} tasks against {args.url}")
    logger.info(f"Sandbox: {SANDBOX_BASE_URL}")
    logger.info(f"Run ID: {_run_id}")

    results = []
    for name, task in tasks.items():
        r = run_task(name, task, args.url, auth_headers)
        results.append(r)

    # Summary
    print(f"\n{'='*70}")
    print(f"SMOKE TEST RESULTS (run_id={_run_id})")
    print(f"{'='*70}")
    print(f"{'Task':<30s} {'Tier':>4s} {'Solve':>6s} {'Verify':>8s} {'Time':>6s}")
    print("-" * 70)
    for r in results:
        print(f"{r['name']:<30s} {r['tier']:>4d} {r['solve']:>6s} {r['verify']:>8s} {r['time']:>5.1f}s")
    print("-" * 70)

    pass_count = sum(1 for r in results if r["solve"] == "PASS" and r["verify"] == "PASS")
    total = len(results)
    print(f"\n{pass_count}/{total} fully passed")

    # Cleanup test entities from sandbox
    if not args.no_cleanup:
        cleanup_sandbox(_run_id)

    if pass_count < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
