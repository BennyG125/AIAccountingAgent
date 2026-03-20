# Claude Migration — Design Spec

**Goal:** Replace Gemini with Claude Opus 4.6 (via Vertex AI) for prompt parsing and tool-use fallback. Keep Gemini for OCR only. Fixes the empty `fields`/`depends_on` parse bug caused by Gemini structured output treating `{"type": "object"}` without `properties` as an empty object.

**Context:** The deterministic execution layer (registry, executor, pattern matcher) works correctly. The bottleneck is parsing: Gemini returns `{}` for all nested objects in the TaskPlan. Claude returns correct JSON from instructions alone — no schema constraint needed. Verified: Claude Opus 4.6 on Vertex AI (`us-east5`) returns correct TaskPlan JSON in ~2.3s.

---

## 1. Architecture After Migration

```
Request → main.py → agent.run_agent()
  │
  ├── file_handler.py: extract text + page images from PDFs (PyMuPDF, no LLM)
  │
  ├── Gemini (google-genai): OCR only — images → text
  │     Called once if request has image attachments.
  │     Returns extracted text appended to prompt context.
  │
  ├── Claude (anthropic[vertex]): parse prompt → TaskPlan JSON
  │     Uses PARSE_SYSTEM_PROMPT + few-shot examples.
  │     Returns JSON text → json.loads() → TaskPlan dict.
  │
  ├── is_known_pattern(): validate TaskPlan (no LLM)
  │     ├── TRUE → executor.execute_plan() (deterministic, no LLM)
  │     │            └── success → return
  │     │            └── failure → FallbackContext → tool-use fallback
  │     └── FALSE → tool-use fallback
  │
  └── Claude (anthropic[vertex]): tool-use fallback loop
        4 HTTP tools (GET/POST/PUT/DELETE) → TripletexClient
        Max 25 iterations, 270s timeout.
```

**LLM usage per request:**
- 0-1 Gemini calls (OCR, only if images present)
- 1 Claude call (parse)
- 0-25 Claude calls (tool-use fallback, only if deterministic path fails)

**Behavioral change — image handling:** Previously, `parse_prompt()` and `build_user_content()` sent images directly to Gemini as multimodal parts. After migration, images are pre-processed by `gemini_ocr()` into text before Claude sees them. This means image-only PDFs (where PyMuPDF extracts zero text but produces page images) now depend on the OCR step extracting useful text. If `gemini_ocr()` returns empty text for an image, that data is lost to the parse step. This is an acceptable trade-off — Gemini OCR is reliable, and separating OCR from reasoning is cleaner.

---

## 2. Claude Client Setup

### AnthropicVertex client

Shared between planner.py and agent.py via a module-level client:

```python
# claude_client.py (new file — thin shared client)
import os
from anthropic import AnthropicVertex

CLAUDE_MODEL = "claude-opus-4-6"
CLAUDE_REGION = "us-east5"

_client: AnthropicVertex | None = None

def get_claude_client() -> AnthropicVertex:
    """Get cached AnthropicVertex client. Uses ADC on Cloud Run, gcloud locally."""
    global _client
    if _client is None:
        _client = AnthropicVertex(
            region=CLAUDE_REGION,
            project_id=os.getenv("GCP_PROJECT_ID"),
        )
    return _client
```

**Auth:**
- On Cloud Run: Application Default Credentials (service account) — same IAM that Gemini already uses. No new credentials needed.
- Locally: `gcloud auth application-default login` or the SDK falls back to `gcloud auth print-access-token`.

### Model

`claude-opus-4-6` for both parse and tool-use. Single model, no routing.

Verified working via live API call on 2026-03-20: `AnthropicVertex(region="us-east5", project_id="ai-nm26osl-1799")` with `model="claude-opus-4-6"` returned correct JSON in 2.3s. Response confirmed `"model": "claude-opus-4-6"`.

---

## 3. Parse — planner.py Changes

### What changes

1. **Remove:** `genai_client`, `genai` imports, `TASK_PLAN_SCHEMA`, `response_schema` usage
2. **Add:** `import json`, import `get_claude_client, CLAUDE_MODEL` from `claude_client.py`
3. **Rewrite:** `parse_prompt()` to use Claude messages API
4. **Update:** Module docstring to reference Claude instead of Gemini

### parse_prompt() — new implementation

```python
def parse_prompt(prompt: str, file_contents: list[dict]) -> dict | None:
    """Parse a task prompt into a structured TaskPlan via Claude."""
    start = time.time()

    # Build text context from files (images already OCR'd by this point)
    text_parts = []
    for f in file_contents:
        text = f.get("text_content", "").strip()
        if text:
            text_parts.append(f"[Attached file: {f['filename']}]\n{text}")

    user_message = "\n\n".join(text_parts + [prompt]) if text_parts else prompt

    try:
        client = get_claude_client()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            system=PARSE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=4096,
            temperature=0.0,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        # Claude returns JSON as text — parse it
        raw_text = response.content[0].text
        # Handle case where Claude wraps JSON in markdown code block
        import re
        raw_text = re.sub(r'^```\w*\n?', '', raw_text.strip())
        raw_text = raw_text.rsplit("```", 1)[0].strip()
        result = json.loads(raw_text)

        if isinstance(result, dict) and "actions" in result:
            actions = result["actions"]
            entities = [a.get("entity", "?") for a in actions]
            logger.info(f"parse: task_plan_actions={len(actions)} entities={entities} "
                       f"parse_time_ms={elapsed_ms}")
            for a in actions:
                logger.info(f"parse: action ref={a.get('ref')} action={a.get('action')} "
                           f"entity={a.get('entity')} fields={a.get('fields')} "
                           f"depends_on={a.get('depends_on')}")
            return result

        logger.warning(f"parse: unexpected format, parse_time_ms={elapsed_ms}")
        return None

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.warning(f"parse: error=\"{e}\" parse_time_ms={elapsed_ms}")
        return None
```

### PARSE_SYSTEM_PROMPT changes

Add one line at the end of the existing prompt:

```
Output ONLY the JSON object. No explanation, no markdown code fences, no other text.
```

Everything else stays identical — entity field names, action patterns, few-shot examples.

### What stays the same

- `PARSE_SYSTEM_PROMPT` content (entity names, actions, few-shot examples)
- `is_known_pattern()` — unchanged
- `DETERMINISTIC_ACTIONS` — unchanged
- `FallbackContext` — unchanged

### What gets removed

- `TASK_PLAN_SCHEMA` dict
- `genai_client` (Gemini client in planner.py)
- `from google import genai` / `from google.genai import types` imports

---

## 4. Tool-Use Fallback — agent.py Changes

### What changes

1. **Remove:** Gemini `FUNCTION_DECLARATIONS`, `TOOLS` (Gemini format), `build_user_content()`
2. **Rename:** `MODEL` → `GEMINI_MODEL` (clarity — Gemini kept for OCR only)
3. **Add:** Claude tool definitions (Anthropic format), Claude tool loop
4. **Add:** `gemini_ocr()` function for image pre-processing
5. **Add:** Import `get_claude_client, CLAUDE_MODEL` from `claude_client.py`
6. **Rewrite:** `run_tool_loop()` for Anthropic SDK message format
7. **Update:** Module docstring to reference Claude instead of Gemini

### Tool definitions — Anthropic format

Same 4 tools, same schemas, different wrapper:

```python
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
```

### Gemini OCR function

```python
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
    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=image_parts)],
        config=config,
    )
    return response.text or ""
```

### run_tool_loop() — Claude version

```python
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
```

### run_agent() — updated flow

```python
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
```

### What stays the same

- `execute_tool()` — unchanged (wraps TripletexClient)
- `build_system_prompt()` — unchanged content
- All Tripletex cheat sheet knowledge
- All rules (13 rules in system prompt)

### What gets removed

- `FUNCTION_DECLARATIONS` (Gemini format tool defs)
- `TOOLS` (Gemini `types.Tool` wrapper)
- `build_user_content()` (Gemini `Part` objects — replaced by text strings)
- Gemini tool loop code in `run_tool_loop()`

### Gemini retained for

- `gemini_ocr()` — image text extraction only
- `genai_client` stays in agent.py for OCR calls
- `google-genai` stays in requirements.txt

---

## 5. New File: claude_client.py

Small shared module to avoid duplicating client setup:

```python
# claude_client.py
"""Shared Claude client for Vertex AI."""

import os
from anthropic import AnthropicVertex

CLAUDE_MODEL = "claude-opus-4-6"
CLAUDE_REGION = "us-east5"

_client: AnthropicVertex | None = None

def get_claude_client() -> AnthropicVertex:
    """Get cached AnthropicVertex client.

    On Cloud Run: uses Application Default Credentials (service account).
    Locally: uses gcloud ADC or falls back to gcloud auth.
    """
    global _client
    if _client is None:
        _client = AnthropicVertex(
            region=CLAUDE_REGION,
            project_id=os.getenv("GCP_PROJECT_ID"),
        )
    return _client
```

---

## 6. Dependency Changes

### requirements.txt

```
fastapi
uvicorn[standard]
requests
google-genai>=1.51.0      # kept for Gemini OCR
anthropic[vertex]>=0.86.0  # new — Claude on Vertex AI
pymupdf
python-dotenv
```

### Environment variables

Existing (unchanged):
- `GCP_PROJECT_ID` — used by both Gemini and Claude
- `GCP_LOCATION` — Gemini only (OCR)

No new env vars needed. Claude region is hardcoded to `us-east5` (the only region with Opus 4.6).

---

## 7. File Changes Summary

| File | Action | What changes |
|------|--------|--------------|
| `claude_client.py` | **Create** | Shared cached AnthropicVertex client + model constant |
| `planner.py` | **Modify** | Replace Gemini parse with Claude, remove TASK_PLAN_SCHEMA, add `import json` |
| `agent.py` | **Modify** | Replace Gemini tool loop with Claude, add gemini_ocr(), rename MODEL→GEMINI_MODEL |
| `requirements.txt` | **Modify** | Add `anthropic[vertex]>=0.86.0` |
| `tests/test_planner.py` | **Modify (significant)** | Mock AnthropicVertex instead of google.genai, test JSON text parsing + code fence stripping |
| `tests/test_executor.py` | **Modify** | Remove or simplify genai mock (planner.py no longer instantiates genai.Client at import time) |
| `tests/test_agent.py` | **Modify (significant)** | Rewrite TestToolDefinitions (Gemini→Anthropic format), remove TestBuildUserContent (function removed), add OCR tests |
| `executor.py` | No change | |
| `task_registry.py` | No change | |
| `tripletex_api.py` | No change | |
| `file_handler.py` | No change | |
| `main.py` | No change | |
| `api_knowledge/cheat_sheet.py` | No change | |

---

## 8. Test Plan

### Parse tests (test_planner.py)
- Mock `AnthropicVertex.messages.create` to return JSON text
- Verify `parse_prompt()` extracts fields, depends_on, search_fields correctly
- Verify markdown code fence stripping works
- Verify error handling (invalid JSON, timeout, API error)

### Agent tests (test_agent.py — significant rewrite)
- **Remove:** `TestBuildUserContent` (function removed)
- **Rewrite:** `TestToolDefinitions` — validate Anthropic format dicts instead of Gemini FunctionDeclaration objects
- **Add:** Mock Claude tool-use responses (tool_use content blocks with `id` field)
- **Add:** Verify tool execution and result threading (`tool_use_id` matching)
- **Add:** Verify fallback context injection into system prompt
- **Add:** Verify timeout handling
- **Add:** Verify `gemini_ocr()` calls Gemini and appends text to file_contents

### Existing tests
- `test_executor.py` — remove or simplify genai mock (planner.py no longer runs `genai.Client()` at import time; if `agent.py` still does for OCR, update mock to target `agent.genai_client` only)
- `test_task_registry.py` — no change
- All pattern matcher tests — no change (is_known_pattern is LLM-independent)

### Smoke tests
- Deploy and run Tier 1 + Tier 2 smoke tests
- Check logs for `path=deterministic` (the whole point — fields should now be populated)
- Compare: before (all `deterministic+fallback`) vs after (should see pure `deterministic`)

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Claude returns JSON wrapped in markdown fences | Strip ```` ```json ``` ```` wrapper before json.loads() |
| Claude Opus 4.6 not available in all Vertex AI regions | Hardcode `us-east5` (verified working) |
| Cloud Run service account lacks Claude access | Same IAM as Gemini — Vertex AI API already enabled |
| Claude parse returns different field names than expected | Same system prompt with exact API field names + few-shot examples |
| Latency increase (two LLM providers) | OCR is conditional (only with images). Parse is ~2.3s. Net faster than Gemini structured output (~10s) |
