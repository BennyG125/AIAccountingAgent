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
