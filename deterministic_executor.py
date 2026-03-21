"""Deterministic executor — classify, extract params, execute plan.

Tries to handle the request deterministically. Returns result dict on success,
or None to signal that the caller should fall back to the Claude agentic loop.
"""
import json
import logging
import re
import time

from tripletex_api import TripletexClient
from execution_plans._classifier import classify_task
from execution_plans._registry import PLANS
from observability import traceable

logger = logging.getLogger(__name__)

# Import all plan modules to trigger @register decorators
import execution_plans.create_customer  # noqa: F401
import execution_plans.register_hours   # noqa: F401
# Add imports here as plans are implemented:
# import execution_plans.create_invoice  # noqa: F401
# import execution_plans.run_salary  # noqa: F401
# ... etc

# ---------------------------------------------------------------------------
# Extraction schemas — defines what fields to pull from the prompt per task type.
# These are populated as optimal sequences are researched.
# ---------------------------------------------------------------------------

from execution_plans.register_hours import EXTRACTION_SCHEMA as _RH_SCHEMA

EXTRACTION_SCHEMAS: dict[str, dict] = {
    "create_customer": {
        "name": "string (customer name)",
        "org_number": "string (organization number)",
        "email": "string or null",
        "phone": "string or null",
        "address": {
            "street": "string (street address)",
            "postal_code": "string",
            "city": "string",
        },
    },
    "register_hours": _RH_SCHEMA,
    # Add schemas here as optimal sequences are researched
}


def extract_params(prompt: str, task_type: str) -> dict | None:
    """Extract task parameters from the prompt using Gemini Flash.

    Returns a dict of extracted params, or None if extraction fails.
    """
    schema = EXTRACTION_SCHEMAS.get(task_type)
    if not schema:
        logger.warning(f"No extraction schema for task_type='{task_type}'")
        return None

    extraction_prompt = (
        f"Extract parameters from this accounting task prompt.\n"
        f"Task type: {task_type}\n"
        f"Expected fields: {json.dumps(schema)}\n\n"
        f"Prompt: {prompt}\n\n"
        f"Return ONLY a valid JSON object with the extracted fields. No explanation."
    )

    try:
        from agent import _get_genai_client
        from google.genai import types

        client = _get_genai_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Content(role="user", parts=[
                types.Part.from_text(text=extraction_prompt)
            ])],
            config=types.GenerateContentConfig(temperature=0.0),
        )

        text = (response.text or "").strip()
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"JSON parse failed for '{task_type}' extraction")
        return None
    except Exception as e:
        logger.warning(f"Param extraction error for '{task_type}': {e}")
        return None


class DeterministicExecutor:
    """Tries deterministic execution for known task types.

    Usage:
        executor = DeterministicExecutor(base_url, session_token)
        result = executor.try_execute(prompt, files)
        if result is None:
            # Fall back to Claude agent
    """

    def __init__(self, base_url: str, session_token: str):
        self.client = TripletexClient(base_url, session_token)

    @traceable(name="deterministic_execute")
    def try_execute(self, prompt: str, files: list) -> dict | None:
        """Try deterministic execution.

        Returns result dict on success, or None to trigger fallback.
        """
        start_time = time.time()

        # 1. OCR if files present
        ocr_text = ""
        if files:
            try:
                from file_handler import process_files
                from agent import gemini_ocr

                file_contents = process_files(files)
                ocr_text = gemini_ocr(file_contents)
            except Exception as e:
                logger.warning(f"OCR failed in deterministic executor: {e}")

        full_prompt = f"{prompt}\n\n{ocr_text}" if ocr_text else prompt

        # 2. Classify (keyword — instant, no LLM)
        task_type = classify_task(full_prompt)
        if task_type is None:
            logger.info("Deterministic: no classifier match, falling back")
            return None

        # 3. Check if we have an execution plan
        plan = PLANS.get(task_type)
        if plan is None:
            logger.info(f"Deterministic: no plan for '{task_type}', falling back")
            return None

        logger.info(f"Deterministic: matched '{task_type}'")

        # 4. Extract parameters (single Gemini Flash call)
        params = extract_params(full_prompt, task_type)
        if params is None:
            logger.warning(
                f"Deterministic: param extraction failed for '{task_type}', falling back"
            )
            return None

        # 5. Execute plan
        logger.info(
            f"Deterministic: executing '{task_type}' with "
            f"params={json.dumps(params, ensure_ascii=False)[:200]}"
        )
        try:
            result = plan.execute(self.client, params, start_time)
            result["time_ms"] = int((time.time() - start_time) * 1000)
            logger.info(
                f"Deterministic: '{task_type}' completed in {result['time_ms']}ms, "
                f"{result['api_calls']} calls, {result['api_errors']} errors"
            )
            return result
        except TimeoutError:
            logger.warning(f"Deterministic: '{task_type}' timed out, falling back")
            return None
        except Exception as e:
            logger.warning(
                f"Deterministic: '{task_type}' failed ({e}), falling back"
            )
            return None
