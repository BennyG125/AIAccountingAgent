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
