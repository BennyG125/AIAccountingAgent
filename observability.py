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
    from langsmith.run_helpers import trace as _ls_trace, get_current_run_tree
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

    def get_current_run_tree():
        return None


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


@contextmanager
def trace_child(name: str, run_type: str = "chain", inputs: dict | None = None):
    """Context manager that creates a child span under the current run tree.

    Usage:
        with trace_child("iteration_1", "chain", {"messages": [...]}) as span:
            # do work
            if span:
                span.end(outputs={"result": ...})

    When langsmith is not available, yields None (no-op).
    """
    if not LANGSMITH_AVAILABLE:
        yield None
        return

    rt = get_current_run_tree()
    if rt is None:
        # No parent run — create a standalone trace
        with _ls_trace(name=name, run_type=run_type, inputs=inputs or {}) as child:
            yield child
        return

    child = rt.create_child(name=name, run_type=run_type, inputs=inputs or {})
    child.post()
    try:
        yield child
    except Exception as e:
        child.end(error=str(e))
        child.patch()
        raise
    else:
        # If caller didn't call .end(), end with no outputs
        if child.end_time is None:
            child.end()
        child.patch()
