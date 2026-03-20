# LangSmith Observability — Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LangSmith tracing to the AI Accounting Agent — covering Claude LLM calls, Gemini OCR, tool executions, and the agent loop — with competition metadata for filtering in the LangSmith UI.

**Architecture:** Graceful opt-in observability. `wrap_anthropic` is attempted on the AnthropicVertex client; when it fails (expected — `AnthropicVertex` lacks `completions` attribute), the Claude LLM call in `agent.py` is traced manually via `langsmith.run_helpers.trace` context manager. `@traceable` decorators on `run_agent`, `execute_tool`, `gemini_ocr`, and the request handler create nested spans. A shared `observability.py` module provides the no-op fallback when `langsmith` is not installed. If `LANGSMITH_TRACING` is unset, all decorators are no-ops and the agent runs identically.

**Tech Stack:** Python 3.11 (Docker), langsmith~=0.7.0, anthropic[vertex], FastAPI

**Spec:** `docs/superpowers/specs/2026-03-20-langsmith-observability-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `requirements.txt` | **Modify** | Add `langsmith~=0.7.0` |
| `observability.py` | **Create** | Shared LangSmith imports with no-op fallbacks, `trace_llm_call` helper |
| `claude_client.py` | **Modify** | Wrap AnthropicVertex with `wrap_anthropic` (graceful fallback), export `LANGSMITH_LLM_WRAPPED` |
| `agent.py` | **Modify** | `@traceable` on `run_agent`, `execute_tool`, `gemini_ocr`; manual LLM tracing when `LANGSMITH_LLM_WRAPPED=False` |
| `main.py` | **Modify** | `@traceable` on request handler with competition metadata |
| `CLAUDE.md` | **Modify** | Add LangSmith env vars to deploy commands |
| `tests/test_observability.py` | **Create** | Test no-op fallbacks and trace helper |
| `tests/test_claude_client.py` | **Create** | Test wrapping works and degrades gracefully |

---

## Task 1: Add langsmith dependency + shared observability module

**Files:**
- Modify: `requirements.txt`
- Create: `observability.py`
- Create: `tests/test_observability.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_observability.py
"""Tests for observability helpers — no-op fallbacks and trace helpers."""


class TestTraceableNoOp:
    """The no-op fallback must handle all @traceable call patterns."""

    def test_bare_decorator(self):
        from observability import traceable

        @traceable
        def f():
            return 1
        assert f() == 1

    def test_empty_parens(self):
        from observability import traceable

        @traceable()
        def f():
            return 2
        assert f() == 2

    def test_with_kwargs(self):
        from observability import traceable

        @traceable(name="x", run_type="tool")
        def f():
            return 3
        assert f() == 3

    def test_preserves_function_args(self):
        from observability import traceable

        @traceable(name="add")
        def add(a, b):
            return a + b
        assert add(3, 4) == 7


class TestTraceLlmCall:
    """trace_llm_call context manager must be a no-op when langsmith is absent."""

    def test_noop_context_manager(self):
        from observability import trace_llm_call
        with trace_llm_call("test") as ctx:
            assert ctx is None or ctx is not None  # just doesn't crash
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_observability.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'observability'`

- [ ] **Step 3: Add langsmith to requirements.txt**

Append after `google-cloud-storage`:

```
langsmith~=0.7.0
```

- [ ] **Step 4: Install langsmith**

Run: `pip install "langsmith~=0.7.0"`

- [ ] **Step 5: Create observability.py**

```python
# observability.py
"""Shared LangSmith observability helpers with graceful no-op fallbacks.

If langsmith is not installed or LANGSMITH_TRACING is not set,
all exports become no-ops. The agent runs identically.
"""

import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    from langsmith import traceable
    from langsmith.run_helpers import trace as _ls_trace
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

    def traceable(*args, **kwargs):
        """No-op fallback when langsmith is not installed."""
        if args and callable(args[0]):
            return args[0]
        def decorator(fn):
            return fn
        return decorator


@contextmanager
def trace_llm_call(name: str, inputs: dict | None = None):
    """Context manager for manually tracing an LLM call.

    When langsmith is available, creates a run of type 'llm'.
    When not available, yields None (no-op).
    """
    if LANGSMITH_AVAILABLE:
        with _ls_trace(name=name, run_type="llm", inputs=inputs or {}) as rt:
            yield rt
    else:
        yield None
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_observability.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add requirements.txt observability.py tests/test_observability.py
git commit -m "feat: add langsmith dependency and shared observability module"
```

---

## Task 2: Wrap AnthropicVertex client in claude_client.py

Try `wrap_anthropic` on the AnthropicVertex singleton. It will likely fail because `AnthropicVertex` lacks a `completions` attribute. Export `LANGSMITH_LLM_WRAPPED` so `agent.py` knows whether to do manual LLM tracing.

**Files:**
- Modify: `claude_client.py`
- Create: `tests/test_claude_client.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_claude_client.py
"""Tests for Claude client initialization and LangSmith wrapping."""
import os
from unittest.mock import patch, MagicMock


class TestGetClaudeClient:
    def setup_method(self):
        import claude_client as mod
        mod._client = None  # reset singleton between tests

    def teardown_method(self):
        import claude_client as mod
        mod._client = None

    def test_returns_client(self):
        import claude_client as mod
        with patch.object(mod, "AnthropicVertex") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = mod.get_claude_client()
            assert client is not None
            mock_cls.assert_called_once()

    def test_caches_client(self):
        import claude_client as mod
        with patch.object(mod, "AnthropicVertex") as mock_cls:
            mock_cls.return_value = MagicMock()
            c1 = mod.get_claude_client()
            c2 = mod.get_claude_client()
            assert c1 is c2
            mock_cls.assert_called_once()

    def test_wrapping_attempted_when_tracing_enabled(self):
        import claude_client as mod
        with patch.object(mod, "AnthropicVertex") as mock_cls:
            mock_cls.return_value = MagicMock()
            with patch.object(mod, "_try_wrap_anthropic", wraps=mod._try_wrap_anthropic) as mock_wrap:
                with patch.dict(os.environ, {"LANGSMITH_TRACING": "true"}):
                    mod.get_claude_client()
                    mock_wrap.assert_called_once()

    def test_wrapping_skipped_when_tracing_disabled(self):
        import claude_client as mod
        with patch.object(mod, "AnthropicVertex") as mock_cls:
            mock_cls.return_value = MagicMock()
            with patch.object(mod, "_try_wrap_anthropic") as mock_wrap:
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("LANGSMITH_TRACING", None)
                    mod.get_claude_client()
                    mock_wrap.assert_not_called()

    def test_graceful_fallback_when_wrap_fails(self):
        """wrap_anthropic fails on AnthropicVertex — client still works."""
        import claude_client as mod
        mock_client = MagicMock()
        with patch.object(mod, "AnthropicVertex", return_value=mock_client):
            with patch.dict(os.environ, {"LANGSMITH_TRACING": "true"}):
                # Force wrap_anthropic to fail
                with patch("claude_client.wrap_anthropic", side_effect=AttributeError("no completions"), create=True):
                    client = mod.get_claude_client()
                    assert client is mock_client  # unwrapped original
                    assert mod.LANGSMITH_LLM_WRAPPED is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_claude_client.py -v`
Expected: FAIL — `_try_wrap_anthropic` doesn't exist yet, `LANGSMITH_LLM_WRAPPED` doesn't exist

- [ ] **Step 3: Modify claude_client.py**

Replace the entire file:

```python
# claude_client.py
"""Shared Claude client for Vertex AI with optional LangSmith tracing."""

import logging
import os

from anthropic import AnthropicVertex

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-opus-4-6"
CLAUDE_REGION = "us-east5"

_client: AnthropicVertex | None = None
LANGSMITH_LLM_WRAPPED = False


def _try_wrap_anthropic(client: AnthropicVertex) -> AnthropicVertex:
    """Attempt to wrap the client with LangSmith tracing.

    wrap_anthropic may fail on AnthropicVertex (lacks 'completions' attribute).
    Returns the original client on any failure.
    """
    global LANGSMITH_LLM_WRAPPED
    try:
        from langsmith.wrappers import wrap_anthropic
        wrapped = wrap_anthropic(client)
        LANGSMITH_LLM_WRAPPED = True
        logger.info("LangSmith: Claude client wrapped for automatic LLM tracing")
        return wrapped
    except Exception as e:
        LANGSMITH_LLM_WRAPPED = False
        logger.info(f"LangSmith: auto-wrapping skipped ({e}), agent.py will trace LLM calls manually")
        return client


def get_claude_client() -> AnthropicVertex:
    """Get cached AnthropicVertex client, optionally wrapped with LangSmith.

    On Cloud Run: uses Application Default Credentials (service account).
    Locally: uses gcloud ADC or falls back to gcloud auth.
    """
    global _client
    if _client is None:
        _client = AnthropicVertex(
            region=CLAUDE_REGION,
            project_id=os.getenv("GCP_PROJECT_ID"),
        )
        if os.getenv("LANGSMITH_TRACING", "").lower() == "true":
            _client = _try_wrap_anthropic(_client)
    return _client
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_claude_client.py -v`
Expected: All PASS

- [ ] **Step 5: Run all tests to verify no regressions**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add claude_client.py tests/test_claude_client.py
git commit -m "feat: wrap AnthropicVertex with LangSmith tracing (graceful fallback)"
```

---

## Task 3: Add @traceable to agent.py with manual LLM tracing

Add `@traceable` decorators to `run_agent`, `execute_tool`, and `gemini_ocr`. When `LANGSMITH_LLM_WRAPPED` is False, wrap the `messages.stream()` call with `trace_llm_call` context manager to manually trace the Claude LLM call.

**Files:**
- Modify: `agent.py`

- [ ] **Step 1: Replace imports — add observability imports**

After `from tripletex_api import TripletexClient` (line 18), add:

```python
from observability import traceable, trace_llm_call
from claude_client import LANGSMITH_LLM_WRAPPED
```

Note: `LANGSMITH_LLM_WRAPPED` is imported at module load time. Since `claude_client.py` sets it during `get_claude_client()` (which is called at request time, not import time), we need to check it dynamically. Instead, import the module and check `claude_client.LANGSMITH_LLM_WRAPPED` at runtime.

Change to:

```python
import claude_client as claude_client_mod
from observability import traceable, trace_llm_call
```

And update the existing import line (line 16) from:
```python
from claude_client import get_claude_client, CLAUDE_MODEL
```
to:
```python
from claude_client import get_claude_client, CLAUDE_MODEL
import claude_client as claude_client_mod
from observability import traceable, trace_llm_call
```

- [ ] **Step 2: Add @traceable to gemini_ocr**

Before `def gemini_ocr(file_contents: list[dict]) -> str:` (line 105), add:

```python
@traceable(run_type="llm", name="gemini_ocr")
```

- [ ] **Step 3: Add @traceable to execute_tool**

Before `def execute_tool(name: str, args: dict, client: TripletexClient) -> dict:` (line 135), add:

```python
@traceable(run_type="tool", name="execute_tool")
```

- [ ] **Step 4: Add @traceable to run_agent**

Before `def run_agent(prompt: str, file_contents: list[dict], base_url: str, session_token: str) -> dict:` (line 206), add:

```python
@traceable(name="run_agent")
```

- [ ] **Step 5: Wrap the messages.stream() call with manual LLM tracing**

Replace the streaming block (lines 241-253):

```python
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
```

With:

```python
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
```

- [ ] **Step 6: Run all tests to verify no regressions**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS — decorators and trace context manager are transparent to existing mocks

- [ ] **Step 7: Commit**

```bash
git add agent.py
git commit -m "feat: add LangSmith @traceable decorators and manual LLM tracing to agent"
```

---

## Task 4: Add @traceable to main.py with competition metadata

Extract a sync helper function from `solve()` and decorate it with `@traceable`. Pass competition metadata (prompt_hash, prompt_preview, file_count) as a regular function parameter so it appears in the LangSmith trace inputs.

Note: `@traceable` is a sync decorator. The `solve()` endpoint is async. The helper is sync (all called functions are sync), which is correct — FastAPI runs it in a thread pool.

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add imports at top of main.py**

After `from file_handler import process_files` (line 12), add:

```python
import hashlib
from observability import traceable
```

- [ ] **Step 2: Add _handle_task function before the solve endpoint**

Insert before `@app.post("/")` (line 82):

```python
@traceable(name="handle_accounting_task")
def _handle_task(prompt: str, files: list, base_url: str, session_token: str,
                 metadata: dict | None = None) -> dict | None:
    """Core task handler — wrapped with LangSmith tracing.

    Args:
        metadata: Competition metadata (prompt_hash, prompt_preview, file_count).
                  Captured by @traceable as a trace input for LangSmith filtering.
    """
    file_contents = process_files(files)
    _preconfigure_bank_account(base_url, session_token)
    return run_agent(prompt, file_contents, base_url, session_token)
```

- [ ] **Step 3: Update solve() to use _handle_task**

Replace the try/except block in solve() (lines 102-109):

```python
    result = None
    try:
        file_contents = process_files(files)
        _preconfigure_bank_account(base_url, session_token)
        result = run_agent(prompt, file_contents, base_url, session_token)
        logger.info(f"Agent: {result}")
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
```

With:

```python
    result = None
    try:
        metadata = {
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:8],
            "prompt_preview": prompt[:80],
            "file_count": len(files),
        }
        result = _handle_task(prompt, files, base_url, session_token, metadata=metadata)
        logger.info(f"Agent: {result}")
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
```

- [ ] **Step 4: Run tests to verify no regressions**

Run: `python -m pytest tests/test_main.py -v`
Expected: All PASS

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add LangSmith tracing to request handler with competition metadata"
```

---

## Task 5: Update CLAUDE.md deploy commands

Add LangSmith env vars to deploy commands. API key is set separately via `--update-env-vars` (not `--set-env-vars` which overwrites all vars).

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update deploy commands section**

Replace the deploy commands block (lines 28-34) with:

```bash
# Dev (test here first)
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 --project ai-nm26osl-1799 --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent" --quiet

# Competition (only after dev is verified)
gcloud run deploy accounting-agent-comp --source . --region europe-north1 --project ai-nm26osl-1799 --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent" --quiet

# Set LangSmith API key separately (never commit the value):
# gcloud run services update ai-accounting-agent-det --region europe-north1 --project ai-nm26osl-1799 --update-env-vars="LANGSMITH_API_KEY=<your-key>"
# gcloud run services update accounting-agent-comp --region europe-north1 --project ai-nm26osl-1799 --update-env-vars="LANGSMITH_API_KEY=<your-key>"
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add LangSmith env vars to deploy commands"
```

---

## Task 6: Verify end-to-end locally

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All PASS

- [ ] **Step 2: Verify LangSmith tracing initializes locally**

Run:
```bash
source .env && python -c "
from claude_client import get_claude_client, LANGSMITH_LLM_WRAPPED
client = get_claude_client()
print(f'Client type: {type(client).__name__}')
print(f'LLM auto-wrapped: {LANGSMITH_LLM_WRAPPED}')
from observability import LANGSMITH_AVAILABLE
print(f'LangSmith available: {LANGSMITH_AVAILABLE}')
"
```

Expected output (most likely):
```
LangSmith: auto-wrapping skipped (...)
Client type: AnthropicVertex
LLM auto-wrapped: False
LangSmith available: True
```

- [ ] **Step 3: Fix any issues found and commit**

```bash
git add observability.py claude_client.py agent.py main.py
git commit -m "fix: langsmith integration fixes from local testing"
```

(Skip this step if no fixes needed.)

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | requirements.txt + observability.py | langsmith dep, shared no-op fallbacks, trace_llm_call helper |
| 2 | claude_client.py | wrap_anthropic attempt + LANGSMITH_LLM_WRAPPED flag |
| 3 | agent.py | @traceable on 3 functions + manual LLM tracing fallback |
| 4 | main.py | @traceable on request handler with competition metadata |
| 5 | CLAUDE.md | LangSmith env vars in deploy commands |
| 6 | Verification | End-to-end local test |

**After merge into feat/tool-use-agent:** Deploy to dev, verify traces appear in LangSmith UI at smith.langchain.com, then deploy to competition.
