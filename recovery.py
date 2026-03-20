# recovery.py

import json
import logging
from datetime import date
from typing import Any

from google.genai import types

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET
from executor import execute_plan
from planner import (
    MODEL,
    PLAN_JSON_SCHEMA,
    _parse_json,
    _validate_plan,
    genai_client,
)

logger = logging.getLogger(__name__)

MAX_RECOVERY_ATTEMPTS = 2

# Required keys in a valid executor failure result
_FAILURE_RESULT_KEYS = {
    "success", "failed_step", "error", "remaining_steps",
    "variables", "completed_steps", "results",
}


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def _is_valid_failure_result(execution_result: Any) -> bool:
    """Check that execution_result has the expected failure shape."""
    if not isinstance(execution_result, dict):
        return False
    if not _FAILURE_RESULT_KEYS <= set(execution_result.keys()):
        return False
    if execution_result.get("success") is not False:
        return False
    remaining = execution_result.get("remaining_steps")
    if not isinstance(remaining, list) or len(remaining) == 0:
        return False
    # Must have exactly one result entry matching failed_step
    failed_step = execution_result.get("failed_step")
    results = execution_result.get("results", [])
    matching = [r for r in results if isinstance(r, dict) and r.get("step_index") == failed_step]
    if len(matching) != 1:
        return False
    return True


def _find_failed_result(execution_result: dict) -> dict:
    """Find the result entry matching the failed step index."""
    failed_step = execution_result["failed_step"]
    for r in execution_result["results"]:
        if isinstance(r, dict) and r.get("step_index") == failed_step:
            return r
    return {}  # should never happen if _is_valid_failure_result passed


# ---------------------------------------------------------------------------
# Wrapped result builder
# ---------------------------------------------------------------------------


def _wrap_result(
    final_result: dict,
    attempts_used: int,
    succeeded: bool,
    last_plan: dict | None,
) -> dict:
    return {
        "success": final_result.get("success", False),
        "recovery_attempts_used": attempts_used,
        "recovery_succeeded": succeeded,
        "last_corrected_plan": last_plan,
        "final_result": final_result,
    }


# ---------------------------------------------------------------------------
# Recovery prompt
# ---------------------------------------------------------------------------


def build_recovery_prompt(
    task_prompt: str,
    file_contents: list[dict],
    original_plan: dict,
    execution_result: dict,
) -> str:
    """Build an error-aware prompt for Gemini to produce a corrected plan."""
    today = date.today().isoformat()

    # Completed steps summary (compact)
    completed_summary = ""
    completed_indices = set(execution_result.get("completed_steps", []))
    for r in execution_result.get("results", []):
        if isinstance(r, dict) and r.get("step_index") in completed_indices:
            idx = r["step_index"]
            method = r.get("method", "?")
            endpoint = r.get("endpoint", "?")
            status = r.get("status_code", "?")
            completed_summary += f"  Step {idx}: {method} {endpoint} → {status}\n"

    # Captured variables
    variables = execution_result.get("variables", {})
    variables_str = json.dumps(variables, indent=2, default=str) if variables else "None"

    # Failed step details
    failed_step_idx = execution_result.get("failed_step", "?")
    error_msg = execution_result.get("error", "Unknown error")
    remaining = execution_result.get("remaining_steps", [])
    failed_step_dict = json.dumps(remaining[0], indent=2) if remaining else "{}"

    # Error response body from the failed result entry
    failed_result = _find_failed_result(execution_result)
    error_body = json.dumps(failed_result.get("body", {}), indent=2, default=str)

    system = f"""You are an expert accounting agent. You receive a task prompt describing an accounting
operation in the Tripletex system. A previous execution plan partially succeeded but then
failed. Your job is to produce a CORRECTED JSON execution plan for the remaining work.

Today's date is {today}.

{TRIPLETEX_API_CHEAT_SHEET}

## Rules
1. Output ONLY valid JSON — no markdown, no explanation, no code fences.
2. Each step is one API call with method, endpoint, and optionally body/params/capture.
3. Use "capture" to save values from responses for use in later steps.
   Capture paths are dot-paths rooted at the full JSON response object.
   Example: "value.id" extracts response["value"]["id"].
4. Reference captured variables with {{variable_name}} in endpoint paths, body values,
   and param values. Placeholders are NOT allowed in object keys or capture paths.
5. Use the MINIMUM number of API calls needed.
   - Do NOT add verification GETs after successful creates unless required for a later dependency.
   - Never emit speculative calls or fallback branches.
6. Get it right on the first try — every 4xx error costs points.
7. Use today's date ({today}) unless the prompt specifies otherwise.
8. Output ONE linear plan only — no branching, no alternative paths.
9. Only use allowed fields: reasoning (optional string), steps (required non-empty array).
   Each step may only have: method, endpoint, body, params, capture.

## Output Schema
{{
  "reasoning": "Brief explanation of what the corrected plan does",
  "steps": [
    {{
      "method": "POST|PUT|GET|DELETE",
      "endpoint": "/endpoint/path",
      "body": {{}},
      "params": {{}},
      "capture": {{"variable_name": "value.field"}}
    }}
  ]
}}

body is only for POST/PUT. params is only for GET/DELETE. capture is optional.
"""

    parts = [system, f"\n## Original Task\n{task_prompt}"]

    # File attachments (text only, same as planner)
    for f in file_contents:
        text = f.get("text_content")
        if text and text.strip():
            parts.append(f"\n### Attached file: {f['filename']}\n{text}")

    # Recovery context
    parts.append("\n## Already Completed Steps (DO NOT repeat these)")
    if completed_summary.strip():
        parts.append("The following steps already succeeded and have CHANGED REMOTE STATE:")
        parts.append(completed_summary)
    else:
        parts.append("No steps completed successfully.")

    parts.append(f"\n## Captured Variables (use these in your corrected plan)")
    parts.append(f"These IDs already exist — reference them with {{variable_name}} instead of searching again:")
    parts.append(variables_str)

    parts.append(f"\n## Failed Step")
    parts.append(f"Step {failed_step_idx} failed with error: {error_msg}")
    parts.append(f"\nThe failed step was:")
    parts.append(failed_step_dict)
    parts.append(f"\nError response body:")
    parts.append(error_body)

    parts.append("""
## Recovery Instructions
1. Produce a corrected plan for the REMAINING work only.
2. Do NOT repeat already-completed steps — they are done and remote state has changed.
3. Use the captured variables above (e.g., {employee_id}, {customer_id}) in your steps.
4. Fix the specific error described above.
5. If the original approach was fundamentally wrong, you may change it,
   but prefer minimal corrections.
6. Output ONLY valid JSON with the same schema as before.""")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Recovery loop
# ---------------------------------------------------------------------------


def recover_and_execute(
    client: Any,
    task_prompt: str,
    file_contents: list[dict],
    original_plan: dict,
    execution_result: dict,
) -> dict:
    """Attempt to recover from a failed plan execution.

    Loops up to MAX_RECOVERY_ATTEMPTS times, returning a wrapped result.
    Never raises.
    """
    # Defensive: validate input
    if not _is_valid_failure_result(execution_result):
        logger.error("Recovery called with malformed execution_result — skipping")
        return _wrap_result(execution_result, 0, False, None)

    current_plan = original_plan
    current_result = execution_result
    last_corrected_plan: dict | None = None
    attempts_used = 0

    for attempt in range(1, MAX_RECOVERY_ATTEMPTS + 1):
        attempts_used = attempt
        logger.info(f"Recovery attempt {attempt}/{MAX_RECOVERY_ATTEMPTS}")

        # 1. Build prompt
        text_prompt = build_recovery_prompt(
            task_prompt, file_contents, current_plan, current_result
        )

        # 2. Build multimodal content parts
        content_parts: list[Any] = [text_prompt]
        for f in file_contents:
            mime = f.get("mime_type", "")
            if mime.startswith("image/") and "raw_bytes" in f:
                content_parts.append(
                    types.Part.from_bytes(data=f["raw_bytes"], mime_type=mime)
                )

        logger.info(f"Recovery attempt {attempt}: prompt_length={len(text_prompt)}")

        # 3. Call Gemini (same config as planner.py)
        try:
            response = genai_client.models.generate_content(
                model=MODEL,
                contents=content_parts,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                    response_schema=PLAN_JSON_SCHEMA,
                ),
            )
        except Exception as e:
            logger.error(f"Recovery attempt {attempt}: gemini_error: {e}")
            continue

        # 4. Parse JSON
        try:
            corrected_plan = _parse_json(response.text)
        except ValueError as e:
            logger.error(f"Recovery attempt {attempt}: parse_error: {e}")
            continue

        # 5. Validate plan
        try:
            _validate_plan(corrected_plan)
        except ValueError as e:
            logger.error(f"Recovery attempt {attempt}: validation_error: {e}")
            continue

        last_corrected_plan = corrected_plan
        logger.info(
            f"Recovery attempt {attempt}: corrected plan has "
            f"{len(corrected_plan['steps'])} steps"
        )

        # 6. Execute corrected plan
        result = execute_plan(client, corrected_plan)

        # 7. Success → return immediately
        if result["success"]:
            logger.info(f"Recovery attempt {attempt}: success")
            return _wrap_result(result, attempts_used, True, last_corrected_plan)

        # 8. Failure → update context for next attempt
        logger.warning(f"Recovery attempt {attempt}: execution_failure: {result.get('error')}")
        current_plan = corrected_plan
        current_result = result

    logger.warning("All recovery attempts exhausted")
    return _wrap_result(current_result, attempts_used, False, last_corrected_plan)
