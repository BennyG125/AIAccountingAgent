#!/usr/bin/env python3
"""Verify execution plans against the Tripletex sandbox.

For each implemented plan:
1. Loads a test fixture from real-requests/logs/ or tests/competition_tasks/
2. Runs the keyword classifier
3. Runs Gemini param extraction
4. Executes the plan against the sandbox
5. Reports success/failure

Usage:
    source .env && export TRIPLETEX_SESSION_TOKEN
    python scripts/verify_plans.py                      # all plans
    python scripts/verify_plans.py --task create_customer  # single plan
"""
import argparse
import json
import logging
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from deterministic_executor import DeterministicExecutor, extract_params
from execution_plans._classifier import classify_task
from execution_plans._registry import PLANS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SANDBOX_BASE_URL = os.getenv("TRIPLETEX_BASE_URL", "https://kkpqfuj-amager.tripletex.dev/v2")
SANDBOX_TOKEN = os.getenv("TRIPLETEX_SESSION_TOKEN", "")

# Test prompts for each task type (simple, English)
TEST_PROMPTS = {
    "create_customer": (
        "Create the customer VerifyTest AS with organization number 999888777. "
        "The address is Testveien 1, 0001 Oslo. Email: verify@test.no"
    ),
    # Add test prompts for each task type as plans are implemented
}


def verify_plan(task_type: str, prompt: str | None = None) -> bool:
    """Verify a single execution plan. Returns True on success."""
    prompt = prompt or TEST_PROMPTS.get(task_type)
    if not prompt:
        logger.warning(f"  No test prompt for '{task_type}', skipping")
        return False

    # Step 1: Classify
    classified = classify_task(prompt)
    if classified != task_type:
        logger.error(f"  Classifier returned '{classified}', expected '{task_type}'")
        return False
    logger.info(f"  Classifier: OK ({task_type})")

    # Step 2: Extract params
    params = extract_params(prompt, task_type)
    if params is None:
        logger.error(f"  Param extraction failed")
        return False
    logger.info(f"  Params: {json.dumps(params, ensure_ascii=False)[:200]}")

    # Step 3: Execute against sandbox
    if not SANDBOX_TOKEN:
        logger.warning("  No TRIPLETEX_SESSION_TOKEN set, skipping sandbox execution")
        return True  # classifier + extraction verified

    executor = DeterministicExecutor(SANDBOX_BASE_URL, SANDBOX_TOKEN)
    plan = PLANS.get(task_type)
    if plan is None:
        logger.error(f"  No plan registered for '{task_type}'")
        return False

    try:
        start = time.time()
        result = plan.execute(executor.client, params, start)
        elapsed = time.time() - start
        logger.info(
            f"  Executed: {result['api_calls']} calls, "
            f"{result['api_errors']} errors, {elapsed:.1f}s"
        )
        return True
    except Exception as e:
        logger.error(f"  Execution failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verify execution plans against sandbox")
    parser.add_argument("--task", help="Verify single task type")
    parser.add_argument("--list", action="store_true", help="List registered plans")
    args = parser.parse_args()

    if args.list:
        for task_type in sorted(PLANS.keys()):
            has_prompt = "+" if task_type in TEST_PROMPTS else "-"
            print(f"  [{has_prompt}] {task_type}: {PLANS[task_type].description}")
        return

    task_types = [args.task] if args.task else sorted(PLANS.keys())
    results = {}

    for task_type in task_types:
        if task_type not in PLANS:
            logger.error(f"Unknown task type: {task_type}")
            results[task_type] = False
            continue

        logger.info(f"\nVerifying: {task_type}")
        results[task_type] = verify_plan(task_type)

    # Summary
    print(f"\n{'='*60}")
    print(f"Results: {sum(results.values())}/{len(results)} passed")
    for task_type, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {task_type}")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
