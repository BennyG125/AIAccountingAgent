# agent.py
"""Pure Claude agentic loop for Tripletex accounting tasks.

Single code path: OCR (Gemini) → Claude tool-use loop → done.
No deterministic path, no pattern matching, no executor.
"""

import json
import logging
import os
import time

from google import genai
from google.genai import types

from claude_client import get_claude_client, CLAUDE_MODEL
from prompts import build_system_prompt
from tripletex_api import TripletexClient
import claude_client as claude_client_mod
from observability import traceable, trace_llm_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (retained for OCR only — lazy init, NOT module-level)
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
MAX_ITERATIONS = 20
TIMEOUT_SECONDS = 270  # 30s buffer before 300s competition hard limit

# ---------------------------------------------------------------------------
# Tool definitions (Anthropic format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "tripletex_get",
        "description": "GET request to Tripletex API. Use for searching/listing entities.",
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
        "description": "POST request to create entities. Include body with JSON payload.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "API path e.g. '/employee'"},
                "body": {"type": "object", "description": "JSON request body"},
                "params": {"type": "object", "description": "Query params (rare for POST)"},
            },
            "required": ["path", "body"],
        },
    },
    {
        "name": "tripletex_put",
        "description": "PUT request for updates and action endpoints. "
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
# Gemini OCR
# ---------------------------------------------------------------------------

@traceable(run_type="llm", name="gemini_ocr")
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

@traceable(run_type="tool", name="execute_tool")
def execute_tool(name: str, args: dict, client: TripletexClient) -> dict:
    """Execute a single tool call against the Tripletex API."""
    try:
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
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Message building
# ---------------------------------------------------------------------------

def _serialize_content(content: list) -> list[dict]:
    """Serialize response content blocks for message history.

    Only include fields the API accepts — model_dump() adds internal Pydantic
    fields (parsed_output, caller) that Anthropic rejects on the next request.
    """
    result = []
    for block in content:
        if block.type == "thinking":
            result.append({
                "type": "thinking",
                "thinking": block.thinking,
                "signature": block.signature,
            })
        elif block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
        else:
            result.append(block.model_dump())
    return result


def build_user_message(prompt: str, file_contents: list[dict]) -> str:
    """Build the user message from prompt and file contents."""
    parts = []

    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            parts.append(f"[Attached file: {f['filename']}]\n{text}")

    parts.append(prompt)

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

@traceable(name="run_agent")
def run_agent(prompt: str, file_contents: list[dict], base_url: str, session_token: str) -> dict:
    """Run the pure Claude agentic loop.

    Flow: OCR (if images) → Claude tool-use loop → done.
    """
    start_time = time.time()
    client = TripletexClient(base_url, session_token)

    # Step 1: OCR — extract text from images via Gemini
    ocr_text = gemini_ocr(file_contents)
    if ocr_text:
        logger.info(f"OCR extracted {len(ocr_text)} chars")
        file_contents.append({
            "filename": "_ocr_extracted.txt",
            "text_content": ocr_text,
            "images": [],
        })

    # Step 2: Build messages
    system_prompt = build_system_prompt()
    user_message = build_user_message(prompt, file_contents)
    messages = [{"role": "user", "content": user_message}]

    claude_client = get_claude_client()

    # Step 3: Agentic loop
    iteration = 0
    for iteration in range(MAX_ITERATIONS):
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            logger.warning(f"Timeout after {elapsed:.0f}s at iteration {iteration}")
            break

        logger.info(f"Iteration {iteration + 1}/{MAX_ITERATIONS} ({elapsed:.0f}s elapsed)")

        stream_kwargs = dict(
            model=CLAUDE_MODEL,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=messages,
            tools=TOOLS,
            max_tokens=16000,
            thinking={"type": "adaptive"},
        )

        if claude_client_mod.LANGSMITH_LLM_WRAPPED:
            # wrap_anthropic succeeded — LLM call is auto-traced
            with claude_client.messages.stream(**stream_kwargs) as stream:
                response = stream.get_final_message()
        else:
            # Manual LLM tracing — wrap_anthropic failed on AnthropicVertex
            with trace_llm_call(f"claude_iteration_{iteration+1}", inputs={"iteration": iteration + 1}):
                with claude_client.messages.stream(**stream_kwargs) as stream:
                    response = stream.get_final_message()

        # Check if agent is done
        if response.stop_reason == "end_turn":
            logger.info(f"Agent completed after {iteration + 1} iterations")
            break

        # Append assistant response — strip internal Pydantic fields
        messages.append({
            "role": "assistant",
            "content": _serialize_content(response.content),
        })

        # Execute tool calls
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            logger.info(f"No tool calls, stopping after {iteration + 1} iterations")
            break

        tool_results = []
        for block in tool_use_blocks:
            logger.info(f"  Tool: {block.name}({json.dumps(block.input, ensure_ascii=False)[:200]})")

            result = execute_tool(block.name, block.input, client)

            status = result.get("status_code", "?")
            logger.info(f"  -> {status} success={result.get('success')}")

            content = json.dumps(result)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                **({"is_error": True} if not result.get("success") else {}),
            })

        messages.append({"role": "user", "content": tool_results})

    total_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Agent done: {iteration + 1} iterations, {total_ms}ms total")

    return {"status": "completed", "iterations": iteration + 1, "time_ms": total_ms}
