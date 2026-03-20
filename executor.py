# executor.py

import logging
import re
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


# ---------------------------------------------------------------------------
# Variable substitution
# ---------------------------------------------------------------------------


def _substitute_value(value: Any, variables: dict) -> Any:
    """Recursively substitute {variable_name} placeholders in a value.

    - Whole-string placeholders preserve the captured type.
    - Embedded placeholders produce a string via str().
    - Dicts: recurse on values only, never keys.
    - Lists: recurse on each element.
    - Scalars (int, float, bool, None): returned as-is.
    - Missing variable: raises ValueError.
    - Invalid placeholder-like text (e.g. "{123bad}"): left literal.
    """
    if isinstance(value, str):
        # Whole-string placeholder: "{var_name}" exactly
        match = _PLACEHOLDER_RE.fullmatch(value)
        if match:
            var_name = match.group(1)
            if var_name not in variables:
                raise ValueError(
                    f"Missing variable '{var_name}'. "
                    f"Available: {sorted(variables.keys())}"
                )
            return variables[var_name]

        # Embedded placeholders: replace all occurrences with str(value)
        def _replacer(m: re.Match) -> str:
            var_name = m.group(1)
            if var_name not in variables:
                raise ValueError(
                    f"Missing variable '{var_name}'. "
                    f"Available: {sorted(variables.keys())}"
                )
            return str(variables[var_name])

        return _PLACEHOLDER_RE.sub(_replacer, value)

    if isinstance(value, dict):
        return {k: _substitute_value(v, variables) for k, v in value.items()}

    if isinstance(value, list):
        return [_substitute_value(item, variables) for item in value]

    # int, float, bool, None — return as-is
    return value


# ---------------------------------------------------------------------------
# Capture path resolution
# ---------------------------------------------------------------------------


def _resolve_capture_path(body: Any, path: str) -> Any:
    """Traverse a dot-separated path into the API response body.

    - Dict segments: key lookup.
    - List segments: non-negative integer index (only when current is a list).
    - Numeric segment on a dict: treated as normal string key.
    - Negative indices: forbidden.
    """
    current = body
    segments = path.split(".")

    for segment in segments:
        if isinstance(current, dict):
            if segment not in current:
                available = sorted(current.keys()) if isinstance(current, dict) else str(current)
                raise ValueError(
                    f"Capture path '{path}': key '{segment}' not found. "
                    f"Available keys: {available}"
                )
            current = current[segment]
        elif isinstance(current, list):
            try:
                idx = int(segment)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Capture path '{path}': segment '{segment}' is not a valid "
                    f"integer index for list of length {len(current)}"
                )
            if idx < 0:
                raise ValueError(
                    f"Capture path '{path}': negative index {idx} is forbidden"
                )
            if idx >= len(current):
                raise ValueError(
                    f"Capture path '{path}': index {idx} out of range for "
                    f"list of length {len(current)}"
                )
            current = current[idx]
        else:
            raise ValueError(
                f"Capture path '{path}': cannot traverse into "
                f"{type(current).__name__} with segment '{segment}'"
            )

    return current


# ---------------------------------------------------------------------------
# API dispatch
# ---------------------------------------------------------------------------


def _validate_client_response(response: Any) -> None:
    """Validate that a client response has the expected shape.

    Raises ValueError if malformed.
    """
    if not isinstance(response, dict):
        raise ValueError(f"Client returned {type(response).__name__}, expected dict")

    missing = []
    for key in ("success", "status_code", "body"):
        if key not in response:
            missing.append(key)
    if missing:
        raise ValueError(f"Client response missing keys: {missing}")

    if not isinstance(response["success"], bool):
        raise ValueError(
            f"Client response 'success' must be bool, got {type(response['success']).__name__}"
        )
    if not isinstance(response["status_code"], int):
        raise ValueError(
            f"Client response 'status_code' must be int, got {type(response['status_code']).__name__}"
        )


def _dispatch(
    client: Any,
    method: str,
    endpoint: str,
    body: dict | None,
    params: dict | None,
) -> dict:
    """Route to the correct TripletexClient method."""
    if method == "GET":
        return client.get(endpoint, params=params)
    elif method == "POST":
        return client.post(endpoint, body=body)
    elif method == "PUT":
        return client.put(endpoint, body=body)
    elif method == "DELETE":
        if params:
            qs = urlencode(params, doseq=True)
            endpoint = f"{endpoint}?{qs}"
            logger.info(f"DELETE with params encoded as query string: {endpoint}")
        return client.delete(endpoint)
    else:
        raise ValueError(f"Unknown method: {method}")


# ---------------------------------------------------------------------------
# Normalized result builder
# ---------------------------------------------------------------------------


def _build_result(
    step_index: int,
    method: str,
    endpoint: str,
    success: bool,
    status_code: int = 0,
    body: Any = None,
    error: str | None = None,
) -> dict:
    """Build a normalized per-step result entry."""
    return {
        "step_index": step_index,
        "method": method,
        "endpoint": endpoint,
        "success": success,
        "status_code": status_code,
        "body": body if body is not None else {},
        "error": error,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def execute_plan(client: Any, plan: dict) -> dict:
    """Execute a structured plan step by step.

    Returns a dict with success/failure status, captured variables,
    completed step indices, normalized per-step results, and on failure,
    the failed step index, error message, and remaining raw steps.
    """
    if not isinstance(plan, dict):
        raise ValueError(f"Plan must be a dict, got {type(plan).__name__}")
    if "steps" not in plan:
        raise ValueError("Plan missing required key 'steps'")
    steps = plan["steps"]
    if not isinstance(steps, list):
        raise ValueError(f"'steps' must be a list, got {type(steps).__name__}")

    variables: dict[str, Any] = {}
    completed_steps: list[int] = []
    results: list[dict] = []

    for i, step in enumerate(steps):
        method = step.get("method", "UNKNOWN")
        raw_endpoint = step.get("endpoint", "")

        # -- 1-3: Substitute variables --
        try:
            endpoint = _substitute_value(raw_endpoint, variables)
            body = _substitute_value(step.get("body"), variables) if "body" in step else None
            params = _substitute_value(step.get("params"), variables) if "params" in step else None
        except ValueError as e:
            logger.error(f"Step {i}: substitution error: {e}")
            # Use raw endpoint if substitution failed before endpoint resolved
            ep = endpoint if "endpoint" in dir() and isinstance(endpoint, str) else raw_endpoint
            results.append(_build_result(i, method, ep, False, error=str(e)))
            return {
                "success": False,
                "variables": variables,
                "completed_steps": completed_steps,
                "results": results,
                "failed_step": i,
                "error": str(e),
                "remaining_steps": steps[i:],
            }

        logger.info(f"Step {i}: {method} {endpoint}")

        # -- 4: Dispatch API call --
        try:
            response = _dispatch(client, method, endpoint, body, params)
            _validate_client_response(response)
        except (ValueError, Exception) as e:
            logger.error(f"Step {i}: dispatch/validation error: {e}")
            results.append(_build_result(i, method, endpoint, False, error=str(e)))
            return {
                "success": False,
                "variables": variables,
                "completed_steps": completed_steps,
                "results": results,
                "failed_step": i,
                "error": str(e),
                "remaining_steps": steps[i:],
            }

        # -- 5: Build normalized result and append --
        result_entry = _build_result(
            i,
            method,
            endpoint,
            response["success"],
            response["status_code"],
            response["body"],
            response.get("error"),
        )
        results.append(result_entry)

        # -- 6: Check API success --
        if not response["success"]:
            error_msg = response.get("error", f"HTTP {response['status_code']}")
            logger.warning(f"Step {i}: API failure: {error_msg}")
            return {
                "success": False,
                "variables": variables,
                "completed_steps": completed_steps,
                "results": results,
                "failed_step": i,
                "error": error_msg,
                "remaining_steps": steps[i:],
            }

        # -- 7: Process captures --
        capture = step.get("capture", {})
        try:
            for var_name, dot_path in capture.items():
                if var_name in variables:
                    logger.info(f"Step {i}: capture '{var_name}' overwritten")
                captured_value = _resolve_capture_path(response["body"], dot_path)
                variables[var_name] = captured_value
                logger.info(
                    f"Step {i}: captured '{var_name}' "
                    f"(type={type(captured_value).__name__})"
                )
        except ValueError as e:
            logger.error(f"Step {i}: capture error: {e}")
            # Mutate the already-appended result entry
            result_entry["success"] = False
            result_entry["error"] = str(e)
            return {
                "success": False,
                "variables": variables,
                "completed_steps": completed_steps,
                "results": results,
                "failed_step": i,
                "error": str(e),
                "remaining_steps": steps[i:],
            }

        # -- 8: Mark step completed --
        completed_steps.append(i)

    return {
        "success": True,
        "variables": variables,
        "completed_steps": completed_steps,
        "results": results,
    }
