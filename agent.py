"""Agentic loop using Gemini function calling to complete Tripletex accounting tasks."""

import json
import logging
import os
import time
from datetime import date

from google import genai
from google.genai import types

from api_knowledge.cheat_sheet import TRIPLETEX_API_CHEAT_SHEET
from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
MAX_TURNS = 25
TIMEOUT_BUFFER_SECONDS = 45


def _create_genai_client():
    """Create Gemini client. Returns None if GCP credentials unavailable."""
    try:
        return genai.Client(
            vertexai=True,
            project=os.getenv("GCP_PROJECT_ID"),
            location=os.getenv("GCP_LOCATION", "global"),
        )
    except Exception as e:
        logger.warning(f"Could not initialize Gemini client: {e}")
        return None


genai_client = _create_genai_client()

TRIPLETEX_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="tripletex_api",
            description=(
                "Make a request to the Tripletex v2 REST API. "
                "Use to create, read, update, or delete accounting entities."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "method": types.Schema(
                        type="STRING",
                        description="HTTP method",
                        enum=["GET", "POST", "PUT", "DELETE"],
                    ),
                    "endpoint": types.Schema(
                        type="STRING",
                        description="API path, e.g. /employee or /customer/123",
                    ),
                    "body_json": types.Schema(
                        type="STRING",
                        description='JSON body for POST/PUT. Example: \'{"firstName":"Ola"}\'',
                    ),
                    "query_params_json": types.Schema(
                        type="STRING",
                        description='JSON query params for GET. Example: \'{"fields":"id,name"}\'',
                    ),
                },
                required=["method", "endpoint"],
            ),
        )
    ]
)


def build_system_prompt() -> str:
    """Build the system prompt with API reference and today's date."""
    today = date.today().isoformat()
    return f"""You are an expert accounting agent for Tripletex. You receive tasks in any of 7 languages (Norwegian, English, Spanish, Portuguese, Nynorsk, German, French) and complete them via API calls.

{TRIPLETEX_API_CHEAT_SHEET}

## Rules
1. Today's date: {today}. Use for all date fields unless the prompt says otherwise.
2. Account starts EMPTY. Create prerequisites before dependent entities.
3. MINIMIZE API calls — every call and error affects your score.
4. POST responses include the created entity's ID. Use it directly — don't GET to find it.
5. body_json and query_params_json must be valid JSON strings.
6. Read error messages carefully. Fix the specific issue in one retry.
7. When done, stop calling tools and respond with a brief summary.
8. Do NOT make verification GETs unless absolutely necessary.
9. Dates: YYYY-MM-DD. IDs: integers. Text: UTF-8."""


def run_agent(
    client: TripletexClient,
    prompt: str,
    file_contents: list[dict],
    deadline: float,
) -> dict:
    """Run the agentic loop to complete an accounting task.

    Args:
        client: Initialized TripletexClient
        prompt: The task prompt in any of 7 languages
        file_contents: Processed file attachments from file_handler
        deadline: Unix timestamp when we must stop

    Returns:
        {"success": bool, "summary": str, "api_calls": int, "errors": int}
    """
    if genai_client is None:
        raise RuntimeError("Gemini client not initialized. Set GCP_PROJECT_ID env var.")

    system_prompt = build_system_prompt()
    user_text = f"{system_prompt}\n\n## Task\n{prompt}"
    content_parts = [types.Part.from_text(text=user_text)]

    for f in file_contents:
        if "text_content" in f:
            content_parts.append(
                types.Part.from_text(text=f"\n## File: {f['filename']}\n{f['text_content']}")
            )
        if f.get("mime_type", "").startswith("image/") and "raw_bytes" in f:
            content_parts.append(
                types.Part.from_bytes(data=f["raw_bytes"], mime_type=f["mime_type"])
            )

    history = [types.Content(role="user", parts=content_parts)]
    config = types.GenerateContentConfig(
        tools=[TRIPLETEX_TOOL],
        temperature=0.0,
        max_output_tokens=4096,
    )

    for turn in range(MAX_TURNS):
        remaining = deadline - time.time()
        if remaining < TIMEOUT_BUFFER_SECONDS:
            logger.warning(f"Timeout: {remaining:.0f}s left, stopping")
            break

        logger.info(f"Turn {turn + 1}/{MAX_TURNS} ({remaining:.0f}s left)")

        try:
            response = genai_client.models.generate_content(
                model=MODEL, contents=history, config=config,
            )
        except Exception as e:
            logger.error(f"Gemini error on turn {turn + 1}: {e}")
            break

        model_content = response.candidates[0].content
        history.append(model_content)

        function_calls = [
            p for p in model_content.parts
            if getattr(p, "function_call", None)
        ]

        if not function_calls:
            text_parts = [
                p.text for p in model_content.parts
                if getattr(p, "text", None)
            ]
            summary = " ".join(text_parts) if text_parts else "Completed"
            logger.info(f"Done on turn {turn + 1}: {summary[:200]}")
            return {
                "success": True,
                "summary": summary,
                "api_calls": client.call_count,
                "errors": client.error_count,
            }

        fn_response_parts = []
        for part in function_calls:
            fc = part.function_call
            logger.info(f"Tool: {fc.name} args={dict(fc.args)}")
            result = _execute_tool(client, fc.name, dict(fc.args))
            fn_response_parts.append(
                types.Part.from_function_response(name=fc.name, response={"result": result})
            )

        history.append(types.Content(role="user", parts=fn_response_parts))

    return {
        "success": False,
        "summary": "Loop ended without completion",
        "api_calls": client.call_count,
        "errors": client.error_count,
    }


def _execute_tool(client: TripletexClient, name: str, args: dict) -> dict:
    """Execute a tool call against the Tripletex API."""
    if name != "tripletex_api":
        return {"error": f"Unknown tool: {name}"}

    method = args.get("method", "GET").upper()
    endpoint = args.get("endpoint", "")
    body = _parse_json_arg(args.get("body_json"))
    params = _parse_json_arg(args.get("query_params_json"))

    if method == "GET":
        return client.get(endpoint, params=params)
    elif method == "POST":
        return client.post(endpoint, body=body)
    elif method == "PUT":
        return client.put(endpoint, body=body)
    elif method == "DELETE":
        return client.delete(endpoint)
    return {"success": False, "error": f"Unknown method: {method}"}


def _parse_json_arg(value) -> dict | None:
    """Parse a JSON argument that may be a string, dict, or None."""
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON arg: {value[:200]}")
            return None
    return None
