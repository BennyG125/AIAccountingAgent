"""Integration tests — run agent against sandbox, verify results.

Usage:
    # Start server first: uvicorn main:app --port 8000
    pytest tests/integration/ -m integration -v
    pytest tests/integration/ -m integration -v -k "department"  # single category
    pytest tests/integration/ -m integration -v -k "nb"           # single language
"""

import pytest
from tests.integration.task_definitions import TASKS

LANGUAGES = ["nb", "en", "es", "pt", "nn", "de", "fr"]


def task_ids():
    """Generate test IDs and parameter tuples for parametrize."""
    ids = []
    params = []
    for task_name, task_def in TASKS.items():
        for lang in LANGUAGES:
            ids.append(f"{task_name}-{lang}")
            params.append((task_name, lang, task_def))
    return ids, params


_ids, _params = task_ids()


@pytest.mark.integration
@pytest.mark.parametrize("task_name,lang,task_def", _params, ids=_ids)
def test_task(task_name, lang, task_def, solve, verifier):
    """Run a task prompt through the agent and verify the result via API."""
    prompt = task_def["prompts"][lang]

    # Run agent
    result = solve(prompt)
    assert result.get("status") == "completed", f"Agent did not complete: {result}"

    # Verify each verification step (list of checks)
    for check in task_def["verify"]:
        # Skip checks whose search_params contain only None values
        # (e.g. invoice checks that need a customer ID resolved at runtime)
        search_params = check["search_params"]
        if all(v is None for v in search_params.values()):
            continue

        verification = verifier.verify(
            entity_type=check["entity_type"],
            search_params=search_params,
            expected_fields=check["expected_fields"],
        )

        if not verification["verified"]:
            failed = {
                k: v
                for k, v in verification.get("field_results", {}).items()
                if not v["match"]
            }
            pytest.fail(
                f"[{task_name}/{lang}] {check['entity_type']} verification failed.\n"
                f"  Search: {search_params}\n"
                f"  Error:  {verification.get('error', '')}\n"
                f"  Failed fields: {failed}"
            )
