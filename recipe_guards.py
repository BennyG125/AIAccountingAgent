# recipe_guards.py
"""Validation middleware for Tripletex API calls.

Loads .guard.json files from the recipes directory and validates/transforms
API requests before they reach Tripletex. Catches known field-name errors
that Claude's agentic loop tends to make.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class RecipeGuards:
    """Validates and transforms API calls against structured recipe rules."""

    def __init__(self, guards_dir: Path | None = None):
        if guards_dir is None:
            guards_dir = Path(__file__).parent / "recipes"
        self._guards_dir = guards_dir
        self._global_guards = self._load_guard_file("_global")
        self._task_guards: dict = {}
        self._active_guards: dict = {}  # merged guards for current task

        # Load all task-specific guard files
        for f in guards_dir.glob("*.guard.json"):
            if f.stem == "_global":
                continue
            guard = json.loads(f.read_text())
            task_type = guard.get("task_type", f.stem)
            self._task_guards[task_type] = guard

        # Default: only global guards active
        self._active_guards = self._global_guards

    def _load_guard_file(self, name: str) -> dict:
        path = self._guards_dir / f"{name}.guard.json"
        if path.exists():
            return json.loads(path.read_text())
        return {"task_type": name, "field_guards": {}}

    def set_active_task(self, task_type: str):
        """Merge global + task-specific guards. Task-specific extends global."""
        task = self._task_guards.get(task_type, {"field_guards": {}})
        merged_guards = {}

        for path, rules in self._global_guards.get("field_guards", {}).items():
            merged_guards[path] = dict(rules)

        for path, rules in task.get("field_guards", {}).items():
            if path in merged_guards:
                existing = merged_guards[path]
                for key in ("body_strip", "forbidden_fields_filter", "allowed_fields_filter"):
                    if key in rules:
                        existing[key] = list(set(existing.get(key, []) + rules[key]))
                if "body_rename" in rules:
                    existing.setdefault("body_rename", {}).update(rules["body_rename"])
            else:
                merged_guards[path] = dict(rules)

        self._active_guards = {"field_guards": merged_guards}

    def validate_request(
        self, method: str, path: str, body: dict | None, params: dict | None
    ) -> tuple[dict | None, dict | None, list[str]]:
        """Validate and transform a request. Returns (body, params, warnings)."""
        warnings: list[str] = []
        guard = self._find_matching_guard(path)
        if not guard:
            return body, params, warnings

        if params and "fields" in params:
            params, field_warnings = self._validate_fields_filter(params, guard)
            warnings.extend(field_warnings)

        if body:
            body, body_warnings = self._transform_body(body, guard)
            warnings.extend(body_warnings)

        return body, params, warnings

    def _find_matching_guard(self, path: str) -> dict | None:
        """Find the best matching guard for a path using longest-prefix match."""
        guards = self._active_guards.get("field_guards", {})
        if not guards:
            return None

        normalized = re.sub(r"/\d+(/|$)", r"\1", path).rstrip("/")

        if normalized in guards:
            return guards[normalized]

        best_match = None
        best_len = 0
        for guard_path in guards:
            if normalized.startswith(guard_path) and len(guard_path) > best_len:
                best_match = guard_path
                best_len = len(guard_path)

        return guards[best_match] if best_match else None

    def _validate_fields_filter(
        self, params: dict, guard: dict
    ) -> tuple[dict, list[str]]:
        """Remove forbidden fields from ?fields= param."""
        warnings: list[str] = []
        fields_str = params.get("fields", "")
        if not fields_str:
            return params, warnings

        fields = [f.strip() for f in fields_str.split(",")]
        forbidden = set(guard.get("forbidden_fields_filter", []))
        allowed = set(guard.get("allowed_fields_filter", []))

        filtered = []
        for f in fields:
            if f in forbidden:
                warnings.append(f"Removed forbidden field '{f}' from fields filter")
                continue
            if allowed and f not in allowed:
                warnings.append(f"Removed unknown field '{f}' from fields filter (not in allowed list)")
                continue
            filtered.append(f)

        params = dict(params)
        if filtered:
            params["fields"] = ",".join(filtered)
        else:
            del params["fields"]
            warnings.append("All fields were filtered out — removed fields param entirely")

        return params, warnings

    def _transform_body(self, body: dict, guard: dict) -> tuple[dict, list[str]]:
        """Apply body_strip and body_rename rules."""
        warnings: list[str] = []
        body = dict(body)

        strip_keys = set(guard.get("body_strip", []))
        if strip_keys:
            body, strip_warnings = self._strip_keys(body, strip_keys)
            warnings.extend(strip_warnings)

        renames = guard.get("body_rename", {})
        for path, new_key_suffix in renames.items():
            match = re.match(r"^(\w+)\[\]\.(\w+)$", path)
            if not match:
                continue
            array_key, old_key = match.groups()
            new_match = re.match(r"^(\w+)\[\]\.(\w+)$", new_key_suffix)
            if not new_match:
                logger.warning(f"Invalid body_rename target format: {new_key_suffix}")
                continue
            _, new_key = new_match.groups()

            if array_key in body and isinstance(body[array_key], list):
                for item in body[array_key]:
                    if isinstance(item, dict) and old_key in item:
                        item[new_key] = item.pop(old_key)
                        warnings.append(
                            f"Renamed '{old_key}' -> '{new_key}' in {array_key}[] item"
                        )

        return body, warnings

    def _strip_keys(self, obj: dict, keys: set) -> tuple[dict, list[str]]:
        """Recursively strip forbidden keys from a dict."""
        warnings: list[str] = []
        result = {}
        for k, v in obj.items():
            if k in keys:
                warnings.append(f"Stripped forbidden field '{k}' from request body")
                continue
            if isinstance(v, dict):
                v, sub_warnings = self._strip_keys(v, keys)
                warnings.extend(sub_warnings)
            elif isinstance(v, list):
                new_list = []
                for item in v:
                    if isinstance(item, dict):
                        item, sub_warnings = self._strip_keys(item, keys)
                        warnings.extend(sub_warnings)
                    new_list.append(item)
                v = new_list
            result[k] = v
        return result, warnings
