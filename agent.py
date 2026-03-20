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
from observability import traceable, trace_child

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

        # --- LLM call span ---
        with trace_child(f"claude_{iteration + 1}", run_type="llm", inputs={
            "model": CLAUDE_MODEL,
            "messages": messages,
            "tools": [t["name"] for t in TOOLS],
            "max_tokens": 16000,
            "thinking": "adaptive",
        }) as llm_span:
            with claude_client.messages.stream(
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
            ) as stream:
                response = stream.get_final_message()

            # Capture response metadata for LangSmith
            if llm_span:
                usage = getattr(response, "usage", None)
                output_content = _serialize_content(response.content)
                llm_span.end(
                    outputs={
                        "stop_reason": response.stop_reason,
                        "content": output_content,
                    },
                    **({"metadata": {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
                        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
                    }} if usage else {}),
                )

        # Check if agent is done
        if response.stop_reason == "end_turn":
            logger.info(f"Agent completed after {iteration + 1} iterations")
            break

        # Append assistant response — strip internal Pydantic fields
        serialized = _serialize_content(response.content)
        messages.append({"role": "assistant", "content": serialized})

        # Execute tool calls
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            logger.info(f"No tool calls, stopping after {iteration + 1} iterations")
            break

        tool_results = []
        for block in tool_use_blocks:
            logger.info(f"  Tool: {block.name}({json.dumps(block.input, ensure_ascii=False)[:200]})")

            # --- Tool execution span ---
            with trace_child(block.name, run_type="tool", inputs={
                "tool": block.name,
                "args": block.input,
            }) as tool_span:
                result = execute_tool(block.name, block.input, client)

                status = result.get("status_code", "?")
                success = result.get("success", False)
                logger.info(f"  -> {status} success={success}")

                if tool_span:
                    tool_span.end(outputs={
                        "status_code": status,
                        "success": success,
                        "body": result.get("body", {}),
                        **({"error": result.get("error")} if not success else {}),
                    })

            content = json.dumps(result)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                **({"is_error": True} if not success else {}),
            })

        messages.append({"role": "user", "content": tool_results})

    total_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Agent done: {iteration + 1} iterations, {total_ms}ms total")

    return {"status": "completed", "iterations": iteration + 1, "time_ms": total_ms}
