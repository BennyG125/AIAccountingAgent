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

# Task types with flat, simple schemas (<=5 fields) — use faster extraction
SIMPLE_SCHEMAS = {
    "create_product", "create_customer", "create_supplier",
    "create_departments", "credit_note",
}

# Only these task types are allowed to run deterministically.
# All others fall through to Claude for better accuracy.
DETERMINISTIC_WHITELIST = {
    # Tier 1 — proven 100%
    "create_product",
    "create_invoice",
    "create_customer",
    "create_supplier",
    "create_departments",
    "create_employee",
    "credit_note",
    "register_payment",
    "create_order",
    # Tier 2-3 — proven 0 errors on deterministic
    "employee_onboarding",
    "register_supplier_invoice",
    "travel_expense",
    "project_lifecycle",
    "overdue_invoice_reminder",
    "bank_reconciliation",
    "cost_analysis_projects",
    "forex_payment",
    "register_hours",
    "fixed_price_project",
    # Tier 3 — Claude performs worse, try deterministic
    "monthly_closing",
    "year_end_close",
    "year_end_corrections",
    "run_salary",
    "custom_dimension",
    "create_project",
    "reverse_payment",
}

# Import all plan modules to trigger @register decorators
import execution_plans.create_customer  # noqa: F401
import execution_plans.create_employee  # noqa: F401
import execution_plans.create_supplier  # noqa: F401
import execution_plans.create_product  # noqa: F401
import execution_plans.create_departments  # noqa: F401
import execution_plans.create_invoice  # noqa: F401
import execution_plans.credit_note  # noqa: F401
import execution_plans.register_payment  # noqa: F401
import execution_plans.register_supplier_invoice  # noqa: F401
import execution_plans.register_hours  # noqa: F401
import execution_plans.run_salary  # noqa: F401
import execution_plans.custom_dimension  # noqa: F401
import execution_plans.fixed_price_project  # noqa: F401
import execution_plans.forex_payment  # noqa: F401
import execution_plans.overdue_invoice_reminder  # noqa: F401
import execution_plans.employee_onboarding  # noqa: F401
import execution_plans.travel_expense  # noqa: F401
import execution_plans.cost_analysis_projects  # noqa: F401
import execution_plans.bank_reconciliation  # noqa: F401
import execution_plans.year_end_corrections  # noqa: F401
import execution_plans.monthly_closing  # noqa: F401
import execution_plans.year_end_close  # noqa: F401
import execution_plans.project_lifecycle  # noqa: F401
import execution_plans.create_project  # noqa: F401
import execution_plans.reverse_payment  # noqa: F401
import execution_plans.create_order  # noqa: F401

# ---------------------------------------------------------------------------
# Extraction schemas — auto-collected from each plan module's EXTRACTION_SCHEMA
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMAS: dict[str, dict] = {}

# Collect schemas from all plan modules that define EXTRACTION_SCHEMA
import execution_plans as _ep_pkg
import importlib as _importlib
import pkgutil as _pkgutil

for _info in _pkgutil.iter_modules(_ep_pkg.__path__):
    if _info.name.startswith("_"):
        continue
    _mod = _importlib.import_module(f"execution_plans.{_info.name}")
    _schema = getattr(_mod, "EXTRACTION_SCHEMA", None)
    if _schema and isinstance(_schema, dict):
        # Find the plan's task_type
        for _attr_name in dir(_mod):
            _attr = getattr(_mod, _attr_name)
            if isinstance(_attr, type) and hasattr(_attr, "task_type"):
                _inst = _attr()
                if _inst.task_type:
                    EXTRACTION_SCHEMAS[_inst.task_type] = _schema
                    break


_ALL_TASK_TYPES = sorted(DETERMINISTIC_WHITELIST)


def detect_and_translate(prompt: str) -> tuple[str, str]:
    """Detect language and translate prompt to English in one Gemini call.

    Returns (language_name, english_prompt).
    If already English, returns the original prompt unchanged.
    Falls back to heuristic detection + original prompt on error.
    """
    # Quick check: if it looks English already, skip the API call
    from execution_plans._classifier import detect_language
    heuristic = detect_language(prompt)
    if heuristic == "en":
        return "English", prompt

    try:
        from google import genai
        from google.genai import types
        import os

        client = genai.Client(
            vertexai=True,
            project=os.getenv("GCP_PROJECT_ID"),
            location=os.getenv("GCP_LOCATION", "global"),
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=[types.Content(role="user", parts=[
                types.Part.from_text(
                    f"Task: Detect the language and translate to English.\n\n"
                    f"Text:\n{prompt}\n\n"
                    f"Reply in EXACTLY this format (two lines, nothing else):\n"
                    f"LANGUAGE: <language name>\n"
                    f"TRANSLATION: <full English translation preserving all names, numbers, emails, dates, org numbers exactly as-is>"
                ),
            ])],
            config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=2048),
        )
        text = (response.text or "").strip()

        # Parse the two-line response
        language = "Unknown"
        translation = prompt  # fallback to original
        for line in text.split("\n"):
            line = line.strip()
            if line.upper().startswith("LANGUAGE:"):
                language = line.split(":", 1)[1].strip().rstrip(".")
            elif line.upper().startswith("TRANSLATION:"):
                translation = line.split(":", 1)[1].strip()

        # If translation is suspiciously short, keep original
        if len(translation) < len(prompt) * 0.3:
            translation = prompt

        logger.info(f"Gemini: lang={language}, translated {len(prompt)}→{len(translation)} chars")
        return language, translation
    except Exception as e:
        logger.warning(f"Gemini detect+translate failed: {e}")
        lang_map = {"no": "Norwegian", "nn": "Nynorsk", "de": "German",
                     "fr": "French", "es": "Spanish", "pt": "Portuguese", "en": "English"}
        return lang_map.get(heuristic, "Unknown"), prompt


def extract_params(prompt: str, task_type: str, language: str = "Unknown") -> tuple[dict | None, str | None]:
    """Extract task parameters from the prompt using Claude Opus 4.6.

    Also asks Claude to verify the regex classification is correct.

    Returns (params_dict, confirmed_task_type) or (None, None) on failure.
    confirmed_task_type is the task type Claude thinks is correct — may differ
    from the regex-classified task_type.
    """
    schema = EXTRACTION_SCHEMAS.get(task_type)
    if not schema:
        logger.warning(f"No extraction schema for task_type='{task_type}'")
        return None, None

    is_simple = task_type in SIMPLE_SCHEMAS

    if is_simple:
        extraction_prompt = (
            f"Extract fields from this accounting prompt as JSON. "
            f"Return ONLY valid JSON matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            f'Include "confirmed_task_type": "{task_type}" as first field.\n'
            f"Preserve exact names, numbers, emails, dates from the text.\n"
            f"Use null for fields not mentioned.\n\n"
            f"Prompt:\n{prompt}"
        )
    else:
        all_types_str = ", ".join(_ALL_TASK_TYPES)

        extraction_prompt = (
            f"You are extracting structured data from an accounting task prompt.\n"
            f"The regex classifier assigned task type: {task_type}\n"
            f"Detected language: {language}\n\n"
            f"Here is the prompt (in {language}):\n"
            f'"""\n{prompt}\n"""\n\n'
            f"Step 1 — REFLECT AND VERIFY:\n"
            f"Before extracting anything, read the prompt carefully word by word.\n"
            f"Question every assumption:\n"
            f"- Is '{task_type}' the correct task type for this prompt?\n"
            f"- Valid task types: {all_types_str}\n"
            f"- Set confirmed_task_type to the correct one (same as '{task_type}' if correct).\n\n"
            f"Step 2 — EXTRACT PARAMETERS for the confirmed task type:\n"
            f"Extract ALL relevant fields into this JSON structure:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            f"EXTRACTION RULES — follow these relentlessly:\n"
            f"- ONLY extract values that appear VERBATIM in the prompt text\n"
            f"- For names: preserve exact spelling, accents, and special characters from the prompt\n"
            f"- For amounts: extract the exact number from the prompt — never round, convert, or infer\n"
            f"- For dates: use YYYY-MM-DD format, converting from the prompt's format\n"
            f"- For emails: copy character-for-character from the prompt\n"
            f"- For account numbers: ONLY extract accounts explicitly mentioned — never infer\n"
            f"- If a field is not explicitly mentioned in the prompt, use null — NEVER guess\n"
            f"- If the prompt mentions additional items (allowances, supplements, tillegg), extract ALL of them\n"
            f'- ALWAYS include "confirmed_task_type": "<task_type>" as the FIRST field\n'
            f"- Return ONLY a valid JSON object. No markdown, no explanation."
        )

    # Simple schemas: disable thinking and use shorter max_tokens for speed
    thinking_config = {"type": "disabled"} if is_simple else {"type": "adaptive"}
    max_tokens = 1024 if is_simple else 4096

    try:
        from claude_client import get_claude_client, CLAUDE_MODEL

        client = get_claude_client()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            thinking=thinking_config,
            messages=[{"role": "user", "content": extraction_prompt}],
        )

        # With thinking enabled, find the text block (skip thinking blocks)
        text = ""
        for block in response.content:
            if block.type == "text":
                text = (block.text or "").strip()
                break
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        params = json.loads(text)

        # For simple schemas, trust the regex classification directly
        if is_simple:
            confirmed = task_type  # trust regex for simple types
            params.pop("confirmed_task_type", None)
        else:
            # Extract confirmed_task_type (pop it so it doesn't pollute plan params)
            confirmed = params.pop("confirmed_task_type", task_type)
            # Only accept valid task types
            if confirmed not in DETERMINISTIC_WHITELIST:
                confirmed = task_type

        # Validate: if all values are null/empty/zero, extraction failed
        def _has_meaningful_value(v):
            if v is None:
                return False
            if isinstance(v, str) and not v.strip():
                return False
            if isinstance(v, (int, float)) and v == 0:
                return False
            if isinstance(v, list) and len(v) == 0:
                return False
            if isinstance(v, dict):
                return any(_has_meaningful_value(sv) for sv in v.values())
            return True

        meaningful = sum(1 for v in params.values() if _has_meaningful_value(v))
        if meaningful == 0:
            logger.warning(
                f"Extraction returned all empty/null for '{task_type}', "
                f"raw={text[:200]}"
            )
            return None, None

        return params, confirmed
    except json.JSONDecodeError:
        logger.warning(f"JSON parse failed for '{task_type}' extraction")
        return None, None
    except Exception as e:
        logger.warning(f"Param extraction error for '{task_type}': {e}")
        return None, None


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

        # 1. Extract text from files (fast path: PyMuPDF for PDFs, skip Gemini OCR)
        ocr_text = ""
        if files:
            try:
                from file_handler import process_files
                file_contents = process_files(files)
                # Use PyMuPDF text extraction first (instant)
                text_parts = [
                    fc.get("text_content", "")
                    for fc in file_contents
                    if fc.get("text_content", "").strip()
                ]
                if text_parts:
                    ocr_text = "\n\n".join(text_parts)
                    logger.info(f"Fast text extraction: {len(ocr_text)} chars from {len(text_parts)} files")
                else:
                    # Fallback to Gemini OCR only for scanned/image files
                    from agent import gemini_ocr
                    ocr_text = gemini_ocr(file_contents)
                    logger.info(f"Gemini OCR: {len(ocr_text)} chars")
            except Exception as e:
                logger.warning(f"File processing failed in deterministic executor: {e}")

        # 1b. Extract CSV/text content from files (in addition to OCR)
        csv_text = ""
        if files:
            for file_entry in files:
                filename = (file_entry.get("filename") or "").lower()
                if filename.endswith(".csv"):
                    import base64
                    content_b64 = (
                        file_entry.get("content")
                        or file_entry.get("data")
                        or file_entry.get("content_base64", "")
                    )
                    if content_b64:
                        try:
                            csv_text = base64.b64decode(content_b64).decode(
                                "utf-8", errors="replace"
                            )
                        except Exception:
                            pass

        # Build full_prompt with OCR and CSV data
        full_prompt = prompt
        if ocr_text:
            full_prompt = f"{prompt}\n\n{ocr_text}"
        if csv_text:
            full_prompt = f"{full_prompt}\n\nCSV content:\n{csv_text}"

        # 2. Detect language + translate to English (single Gemini call, ~300ms)
        language, english_prompt = detect_and_translate(full_prompt)

        # 3. Classify on English translation (or original if translation failed)
        classify_lang = "English" if english_prompt != full_prompt else language
        task_type = classify_task(english_prompt, language=classify_lang)
        if task_type is None:
            logger.info(f"Deterministic: no classifier match (lang={language}), falling back")
            return None

        # 3b. Whitelist check — only proven task types run deterministically
        if task_type not in DETERMINISTIC_WHITELIST:
            logger.info(f"Deterministic: '{task_type}' not in whitelist, falling back to Claude")
            return None

        # 3c. Check if we have an execution plan
        plan = PLANS.get(task_type)
        if plan is None:
            logger.info(f"Deterministic: no plan for '{task_type}', falling back")
            return None

        logger.info(f"Deterministic: lang={language}, regex matched '{task_type}'")

        # 4. Extract parameters + verify classification (single Claude call)
        params, confirmed_type = extract_params(full_prompt, task_type, language=language)
        if params is None:
            logger.warning(
                f"Deterministic: param extraction failed for '{task_type}', falling back"
            )
            return None

        # 4a. Handle classification override from Claude
        if confirmed_type and confirmed_type != task_type:
            logger.warning(
                f"Deterministic: Claude overrides regex '{task_type}' → '{confirmed_type}'"
            )
            # Switch to the correct plan
            override_plan = PLANS.get(confirmed_type)
            if override_plan and confirmed_type in DETERMINISTIC_WHITELIST:
                # Re-extract with the correct schema
                params2, _ = extract_params(full_prompt, confirmed_type, language=language)
                if params2 is not None:
                    task_type = confirmed_type
                    plan = override_plan
                    params = params2
                    logger.info(f"Deterministic: re-extracted params for '{task_type}'")
                else:
                    logger.warning(
                        f"Deterministic: re-extraction failed for '{confirmed_type}', "
                        f"continuing with original '{task_type}'"
                    )

        # 4b. Inject raw CSV data for bank_reconciliation
        if task_type == "bank_reconciliation" and csv_text:
            params["csv_data"] = csv_text

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
