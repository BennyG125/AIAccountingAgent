# agent.py
"""Claude tool-use agentic loop for Tripletex accounting tasks.

Uses Claude Opus 4.6 via Vertex AI for tool-use fallback.
Gemini retained for OCR (image text extraction) only.
"""

import json
import logging
import os
import time
from datetime import date
from typing import Any

from google import genai
from google.genai import types

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET
from tripletex_api import TripletexClient
from planner import parse_prompt, is_known_pattern, FallbackContext
from executor import execute_plan
from claude_client import get_claude_client, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (retained for OCR only)
# ---------------------------------------------------------------------------

_genai_client = None


def _get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=os.getenv("GCP_PROJECT_ID"),
            location=os.getenv("GCP_LOCATION", "global"),
        )
    return _genai_client

GEMINI_MODEL = "gemini-3.1-pro-preview"
MAX_ITERATIONS = 25
TIMEOUT_SECONDS = 270  # 30s buffer before 300s hard limit

# ---------------------------------------------------------------------------
# Tool definitions (Anthropic format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "tripletex_get",
        "description": "GET request to Tripletex API. Use for listing, searching, and fetching entities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee', '/customer/123'"},
                "params": {"type": "object", "description": "Query params e.g. {\"fields\": \"id,name\"}"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "tripletex_post",
        "description": "POST request to create entities. ALWAYS include body with the JSON payload.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee'"},
                "body": {"type": "object", "description": "JSON request body for creating entities"},
                "params": {"type": "object", "description": "Query params (rare for POST)"},
            },
            "required": ["path", "body"],
        },
    },
    {
        "name": "tripletex_put",
        "description": "PUT request for updates and action endpoints (/:invoice, /:payment). "
                       "For payment registration, use params for query parameters, NOT body.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/invoice/123/:payment'"},
                "body": {"type": "object", "description": "JSON body (optional for action endpoints)"},
                "params": {"type": "object", "description": "Query params — use for payment registration"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "tripletex_delete",
        "description": "DELETE request for removing entities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee/123'"},
            },
            "required": ["path"],
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    today = date.today().isoformat()
    return f"""You are an expert AI accounting agent for Tripletex. Complete the given task by calling the Tripletex REST API using the provided tools.

Today's date is {today}.

## Rules
1. Minimize API calls — every extra call hurts your efficiency score.
2. Do NOT search before creating unless the task says "find" or "modify existing".
3. Use known constants directly — never look them up:
   - NOK currency: id=1
   - Norway country: id=162
   - VAT types vary per sandbox. Do NOT hardcode vatType IDs. If a product POST fails with "Ugyldig mva-kode", retry WITHOUT vatType — Tripletex assigns a valid default. For orderLines, vatType is optional.
4. Create entities in dependency order: department → employee, customer + product → order → invoice → payment.
5. Use response IDs from create calls directly — do not re-fetch.
6. Embed orderLines in the order POST body (saves a call).
7. For payment registration: PUT /invoice/{{id}}/:payment with QUERY PARAMS (paymentDate, paymentTypeId, paidAmount, paidAmountCurrency), NOT a JSON body.
8. Dates are always YYYY-MM-DD for the API.
9. Object references are always {{"id": <int>}}, never bare ints.
10. departmentNumber is a STRING, not an int.
11. On error: read the error message, fix the issue, retry ONCE. Never retry more than once.
12. When done, stop calling tools. Do not add verification GETs after successful creates.
13. If file attachments are provided, analyze them to extract relevant data (amounts, dates, names, line items) for use in API calls.

## Payment Registration (critical gotcha)
PUT /invoice/{{invoiceId}}/:payment?paymentDate=YYYY-MM-DD&paymentTypeId=N&paidAmount=X&paidAmountCurrency=1
Use params, NOT body. paymentTypeId: use GET /invoice/paymentType to find the right one, or use id=0 for default.

{TRIPLETEX_API_CHEAT_SHEET}
"""


# ---------------------------------------------------------------------------
# Gemini OCR (image text extraction only)
# ---------------------------------------------------------------------------

def gemini_ocr(file_contents: list[dict]) -> str:
    """Use Gemini to extract text from images. Returns OCR text or empty string."""
    image_parts = []
    for f in file_contents:
        for img in f.get("images", []):
            image_parts.append(types.Part.from_bytes(
                data=img["data"], mime_type=img["mime_type"]
            ))

    if not image_parts:
        return ""

    image_parts.append(types.Part.from_text(
        text="Extract all text, numbers, dates, names, and amounts from these images. "
             "Return the extracted data as structured text."
    ))

    config = types.GenerateContentConfig(temperature=0.0)
    response = _get_genai_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=image_parts)],
        config=config,
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: dict, client: TripletexClient) -> dict:
    """Execute a single tool call against the Tripletex API."""
    path = args.get("path", "")
    params = args.get("params")
    body = args.get("body")

    if name == "tripletex_get":
        return client.get(path, params=params)
    elif name == "tripletex_post":
        return client.post(path, body=body)
    elif name == "tripletex_put":
        return client.put(path, body=body, params=params)
    elif name == "tripletex_delete":
        return client.delete(path)
    else:
        return {"success": False, "error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(prompt: str, file_contents: list[dict], base_url: str, session_token: str) -> dict:
    """Route: OCR → parse → deterministic execution or tool-use fallback."""
    start_time = time.time()
    client = TripletexClient(base_url, session_token)
    path = "fallback"
    total_api_calls = 0
    llm_calls = 0

    # Step 0: OCR — extract text from images via Gemini
    ocr_text = gemini_ocr(file_contents)
    if ocr_text:
        llm_calls += 1
        # Append OCR text to file_contents as synthetic text entry
        file_contents.append({
            "filename": "_ocr_extracted.txt",
            "text_content": ocr_text,
            "images": [],
        })

    # Step 1: Parse prompt via Claude
    task_plan = parse_prompt(prompt, file_contents)
    llm_calls += 1

    # Step 2: Try deterministic path
    if task_plan and is_known_pattern(task_plan):
        result = execute_plan(client, task_plan)
        total_api_calls += result.get("api_calls", 0)
        if result["success"]:
            path = "deterministic"
            total_ms = int((time.time() - start_time) * 1000)
            logger.info(f"result: status=completed path={path} total_api_calls={total_api_calls} "
                       f"llm_calls={llm_calls} total_time_ms={total_ms}")
            return {"status": "completed", "path": path}
        fallback_ctx = result["fallback_context"]
        path = "deterministic+fallback"
    else:
        fallback_ctx = FallbackContext(task_plan=task_plan)

    # Step 3: Tool-use fallback via Claude
    loop_result = run_tool_loop(prompt, file_contents, client, fallback_ctx)
    total_ms = int((time.time() - start_time) * 1000)
    logger.info(f"result: status=completed path={path} total_api_calls={total_api_calls} "
               f"llm_calls={llm_calls} total_time_ms={total_ms}")
    return {"status": "completed", "path": path}


def run_tool_loop(prompt: str, file_contents: list[dict], client: TripletexClient,
                  fallback_context: FallbackContext | None = None) -> dict:
    """Run the Claude tool-use agent loop (fallback path)."""
    start_time = time.time()
    reason = "parse_failure"
    if fallback_context:
        if fallback_context.failed_action:
            reason = "execution_error"
        elif fallback_context.task_plan:
            reason = "pattern_mismatch"
    logger.info(f"fallback: reason={reason}")

    system_prompt = build_system_prompt()

    # Inject fallback context
    if fallback_context:
        extra = []
        if fallback_context.completed_refs:
            extra.append(f"These entities were already created: {json.dumps(fallback_context.completed_refs)}")
        if fallback_context.failed_action and fallback_context.error:
            extra.append(f"This action failed: {json.dumps(fallback_context.failed_action)}. "
                        f"Error: {fallback_context.error}. Fix and continue.")
        if fallback_context.task_plan:
            extra.append(f"Parsed task plan for context: {json.dumps(fallback_context.task_plan)}")
        if extra:
            system_prompt += "\n\n## Context from previous attempt\n" + "\n".join(extra)

    # Build user message (text only — images already OCR'd)
    text_parts = []
    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            text_parts.append(f"[Attached file: {f['filename']}]\n{text}")
    text_parts.append(f"Complete this accounting task:\n\n{prompt}")
    user_message = "\n\n".join(text_parts)

    messages = [{"role": "user", "content": user_message}]

    claude_client = get_claude_client()

    iteration = 0
    for iteration in range(MAX_ITERATIONS):
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            logger.warning(f"Timeout after {elapsed:.0f}s at iteration {iteration}")
            break

        logger.info(f"Agent iteration {iteration + 1}")

        response = claude_client.messages.create(
            model=CLAUDE_MODEL,
            system=system_prompt,
            messages=messages,
            tools=TOOLS,
            max_tokens=4096,
            temperature=0.0,
        )

        # Process response content blocks
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # Check for tool use
        tool_use_blocks = [b for b in assistant_content if b.type == "tool_use"]
        if not tool_use_blocks:
            logger.info(f"Agent completed after {iteration + 1} iterations")
            break

        # Execute tools and build results
        tool_results = []
        for block in tool_use_blocks:
            logger.info(f"  Tool: {block.name}({json.dumps(block.input, ensure_ascii=False)[:200]})")

            try:
                result = execute_tool(block.name, block.input, client)
            except Exception as e:
                logger.error(f"  Tool error: {e}")
                result = {"success": False, "error": str(e)}

            logger.info(f"  -> {result.get('status_code')} success={result.get('success')}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

    return {"status": "completed", "iterations": iteration + 1}
