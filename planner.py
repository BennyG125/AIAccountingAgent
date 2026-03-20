# planner.py

import json
import logging
import os
import re
from datetime import date
from typing import Any

from google import genai
from google.genai import types

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client & model
# ---------------------------------------------------------------------------

genai_client = genai.Client(
    vertexai=True,
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "global"),
)

MODEL = "gemini-3.1-pro-preview"

# ---------------------------------------------------------------------------
# Source-of-truth: schema constants used by both _validate_plan and the
# Gemini response_json_schema. Everything derives from these.
# ---------------------------------------------------------------------------

ALLOWED_TOP_LEVEL_KEYS = {"reasoning", "steps"}
ALLOWED_STEP_KEYS = {"method", "endpoint", "body", "params", "capture"}
VALID_METHODS = {"GET", "POST", "PUT", "DELETE"}
BODY_ALLOWED_METHODS = {"POST", "PUT"}
PARAMS_ALLOWED_METHODS = {"GET", "DELETE"}
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# JSON schema passed to Gemini's structured-output mode.
# Derived from the same constants above to stay in sync.
PLAN_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "reasoning": {"type": "string"},
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["method", "endpoint"],
                "properties": {
                    "method": {"type": "string", "enum": sorted(VALID_METHODS)},
                    "endpoint": {"type": "string", "minLength": 1},
                    "body": {"type": "object"},
                    "params": {"type": "object"},
                    "capture": {"type": "object"},
                },
            },
        },
    },
    "required": ["steps"],
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_plan(plan: dict) -> None:
    """Validate a plan dict against the executor-safe schema.

    Raises ValueError on any violation.
    """
    if not isinstance(plan, dict):
        raise ValueError(f"Plan must be a dict, got {type(plan).__name__}")

    unknown_top = set(plan.keys()) - ALLOWED_TOP_LEVEL_KEYS
    if unknown_top:
        raise ValueError(f"Unknown top-level keys: {unknown_top}")

    if "reasoning" in plan and not isinstance(plan["reasoning"], str):
        raise ValueError("'reasoning' must be a string")

    if "steps" not in plan:
        raise ValueError("Plan missing required key 'steps'")

    steps = plan["steps"]
    if not isinstance(steps, list):
        raise ValueError(f"'steps' must be a list, got {type(steps).__name__}")
    if len(steps) == 0:
        raise ValueError("'steps' must be non-empty")

    for i, step in enumerate(steps):
        _validate_step(step, i)


def _validate_step(step: dict, index: int) -> None:
    """Validate a single step dict."""
    prefix = f"Step {index}"

    if not isinstance(step, dict):
        raise ValueError(f"{prefix}: step must be a dict, got {type(step).__name__}")

    unknown = set(step.keys()) - ALLOWED_STEP_KEYS
    if unknown:
        raise ValueError(f"{prefix}: unknown keys: {unknown}")

    # -- method --
    method = step.get("method")
    if method not in VALID_METHODS:
        raise ValueError(
            f"{prefix}: invalid method '{method}', must be one of {sorted(VALID_METHODS)}"
        )

    # -- endpoint --
    endpoint = step.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        raise ValueError(f"{prefix}: endpoint must be a non-empty string")
    if endpoint != endpoint.strip():
        raise ValueError(f"{prefix}: endpoint has leading/trailing whitespace: '{endpoint}'")
    if not endpoint.startswith("/"):
        raise ValueError(f"{prefix}: endpoint must start with '/', got '{endpoint}'")
    if "?" in endpoint:
        raise ValueError(f"{prefix}: endpoint must not contain '?' — use params instead")
    if "//" in endpoint:
        raise ValueError(f"{prefix}: endpoint must not contain '//' (empty path segment)")

    # -- body --
    if "body" in step:
        body = step["body"]
        if not isinstance(body, dict):
            raise ValueError(f"{prefix}: body must be a dict")
        # Allow empty body — Gemini structured output may emit {} for optional fields
        if body and method not in BODY_ALLOWED_METHODS:
            raise ValueError(f"{prefix}: body not allowed for {method}")

    # -- params --
    if "params" in step:
        params = step["params"]
        if not isinstance(params, dict):
            raise ValueError(f"{prefix}: params must be a dict")
        # Allow empty params — Gemini structured output may emit {} for optional fields
        if params and method not in PARAMS_ALLOWED_METHODS:
            raise ValueError(f"{prefix}: params not allowed for {method}")

    # -- capture --
    if "capture" in step:
        capture = step["capture"]
        if not isinstance(capture, dict):
            raise ValueError(f"{prefix}: capture must be a dict")
        # Allow empty capture — Gemini structured output may emit {} for optional fields
        for key, val in capture.items():
            if not _IDENTIFIER_RE.match(key):
                raise ValueError(
                    f"{prefix}: capture key '{key}' is not a valid identifier"
                )
            if not isinstance(val, str) or not val:
                raise ValueError(
                    f"{prefix}: capture value for '{key}' must be a non-empty string"
                )


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def build_planning_prompt(task_prompt: str, file_contents: list[dict]) -> str:
    """Build the full text prompt sent to Gemini for planning."""
    today = date.today().isoformat()

    system = f"""You are an expert accounting agent. You receive a task prompt describing an accounting
operation in the Tripletex system. Your job is to produce a precise JSON execution plan.

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
5. The account starts EMPTY. Create prerequisite entities (customer, product, order)
   before entities that depend on them (invoice, payment).
6. Use the MINIMUM number of API calls needed — every extra call hurts efficiency score.
   - Do NOT add verification GETs after successful creates unless required for a later dependency.
   - Do NOT search before creating if the task plainly says "create X".
   - Prefer direct create/update when the prompt already provides the needed values.
   - Only use GET when needed to locate an existing resource or prerequisite.
   - Never emit speculative calls or fallback branches.
7. Get it right on the first try — every 4xx error costs points.
8. Use today's date ({today}) unless the prompt specifies otherwise.
9. Output ONE linear plan only — no "if not found" branching, no alternative paths.
10. Only use allowed fields: reasoning (optional string), steps (required non-empty array).
    Each step may only have: method, endpoint, body, params, capture.

## Output Schema
{{
  "reasoning": "Brief explanation of what the task requires",
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

    parts = [system, f"\n## Task\n{task_prompt}"]

    for f in file_contents:
        text = f.get("text_content")
        if text and text.strip():
            parts.append(f"\n### Attached file: {f['filename']}\n{text}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------


def _parse_json(raw_text: str) -> dict:
    """Parse JSON from Gemini response, with single-fence fallback.

    Only unwraps if the entire response is a single fenced JSON block.
    Does NOT extract JSON from mixed prose.
    """
    text = raw_text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: if the entire response is a single fenced block, unwrap it
    if text.startswith("```") and text.endswith("```"):
        inner = text.split("\n", 1)
        if len(inner) == 2:
            inner_text = inner[1].rsplit("```", 1)[0].strip()
            logger.info("Fallback: stripped markdown fences from Gemini response")
            try:
                return json.loads(inner_text)
            except json.JSONDecodeError:
                pass

    raise ValueError(
        f"Failed to parse Gemini response as JSON. "
        f"Raw response preview: {raw_text[:300]}"
    )


def plan_task(task_prompt: str, file_contents: list[dict]) -> dict:
    """Use Gemini to generate an execution plan for the accounting task."""

    text_prompt = build_planning_prompt(task_prompt, file_contents)

    # Build content parts — text first, then images for multimodal input
    content_parts: list[Any] = [text_prompt]

    text_count = 0
    image_count = 0
    ignored_count = 0

    for f in file_contents:
        mime = f.get("mime_type", "")
        if mime.startswith("image/") and "raw_bytes" in f:
            content_parts.append(
                types.Part.from_bytes(data=f["raw_bytes"], mime_type=mime)
            )
            image_count += 1
        elif f.get("text_content", "").strip():
            text_count += 1  # already included in text_prompt
        else:
            ignored_count += 1

    logger.info(
        f"Planning request to {MODEL}: "
        f"prompt_length={len(text_prompt)}, "
        f"text_attachments={text_count}, "
        f"image_attachments={image_count}, "
        f"ignored_attachments={ignored_count}"
    )

    response = genai_client.models.generate_content(
        model=MODEL,
        contents=content_parts,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text
    plan = _parse_json(raw_text)
    _validate_plan(plan)

    logger.info(f"Plan generated: {len(plan['steps'])} steps")
    return plan
