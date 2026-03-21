# Tool Search Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add hybrid tool search mode that gives Claude on-demand access to ~248 per-endpoint Tripletex API tools with exact schemas, while keeping the current 4 generic tools as always-loaded fallback.

**Architecture:** Generate Anthropic tool definitions from the Tripletex OpenAPI spec at build time. Use `defer_loading: true` + BM25 tool search so Claude discovers and loads only the tools it needs per task. Mode switching via `AGENT_MODE` env var (generic/hybrid).

**Tech Stack:** Python 3.13, anthropic SDK 0.86+, Tripletex OpenAPI 3.x spec, FastAPI

**Spec:** `docs/superpowers/specs/2026-03-21-tool-search-architecture-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `scripts/generate_tools.py` | NEW — Fetches OpenAPI spec, filters, resolves refs, outputs tool defs |
| `api_knowledge/generated_tools.py` | NEW — Generated output: GENERATED_TOOLS list + GENERATED_TOOLS_META dict |
| `agent.py` | MODIFY — Tool router, content serialization, mode switching, tool list assembly |
| `prompts.py` | MODIFY — Add `_slim_prompt()`, parameterize `build_system_prompt(mode)` |
| `tests/test_generate_tools.py` | NEW — Tests for the OpenAPI parser/generator |
| `tests/test_agent.py` | MODIFY — Tests for tool router, serialization, mode switching |
| `tests/test_prompts.py` | MODIFY — Test slim prompt mode |
| `CLAUDE.md` | MODIFY — Document AGENT_MODE |

---

### Task 1: OpenAPI Tool Generator Script

**Files:**
- Create: `scripts/generate_tools.py`
- Create: `tests/test_generate_tools.py`

- [ ] **Step 1: Write test for OpenAPI spec fetching and ref resolution**

```python
# tests/test_generate_tools.py
"""Tests for the OpenAPI tool generator."""
import json
import pytest

# Minimal OpenAPI fragment for testing
MINI_SPEC = {
    "paths": {
        "/employee": {
            "post": {
                "tags": ["employee"],
                "summary": "Create employee",
                "operationId": "Employee_post",
                "parameters": [],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "firstName": {"type": "string", "description": "First name"},
                                    "lastName": {"type": "string", "description": "Last name"},
                                    "userType": {
                                        "type": "string",
                                        "enum": ["STANDARD", "EXTENDED", "NO_ACCESS"],
                                    },
                                    "id": {"type": "integer", "readOnly": True},
                                },
                                "required": ["firstName", "lastName"],
                            }
                        }
                    }
                },
            }
        },
        "/employee/entitlement/:grantEntitlementsByTemplate": {
            "put": {
                "tags": ["employee/entitlement"],
                "summary": "Grant entitlements by template",
                "operationId": "EmployeeEntitlement_grant",
                "parameters": [
                    {"name": "employeeId", "in": "query", "required": True,
                     "schema": {"type": "integer"}},
                    {"name": "template", "in": "query", "required": True,
                     "schema": {"type": "string", "enum": ["ALL_PRIVILEGES", "NONE_PRIVILEGES"]}},
                ],
            }
        },
        "/invoice/{id}/:payment": {
            "put": {
                "tags": ["invoice"],
                "summary": "Register payment",
                "operationId": "Invoice_payment",
                "parameters": [
                    {"name": "id", "in": "path", "required": True,
                     "schema": {"type": "integer"}},
                    {"name": "paymentDate", "in": "query", "required": True,
                     "schema": {"type": "string"}},
                    {"name": "paidAmount", "in": "query", "required": True,
                     "schema": {"type": "number"}},
                ],
            }
        },
        "/unrelated/endpoint": {
            "get": {
                "tags": ["unrelated_tag"],
                "summary": "Should be filtered out",
                "operationId": "Unrelated_get",
                "parameters": [],
            }
        },
    },
    "components": {"schemas": {}},
}

ACCOUNTING_TAGS = {"employee", "employee/entitlement", "invoice"}


def test_generate_tools_from_spec():
    from scripts.generate_tools import generate_tools_from_spec
    tools, meta = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)

    assert len(tools) == 3
    names = {t["name"] for t in tools}
    assert "employee_post" in names
    assert "employee_entitlement_grant" in names
    assert "invoice_payment" in names
    # unrelated_tag should be filtered out
    assert not any("unrelated" in t["name"] for t in tools)


def test_readonly_fields_stripped():
    from scripts.generate_tools import generate_tools_from_spec
    tools, _ = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    emp = next(t for t in tools if t["name"] == "employee_post")
    props = emp["input_schema"]["properties"]
    assert "firstName" in props
    assert "id" not in props  # readOnly stripped


def test_enums_preserved():
    from scripts.generate_tools import generate_tools_from_spec
    tools, _ = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    emp = next(t for t in tools if t["name"] == "employee_post")
    assert emp["input_schema"]["properties"]["userType"]["enum"] == ["STANDARD", "EXTENDED", "NO_ACCESS"]


def test_query_params_become_input_properties():
    from scripts.generate_tools import generate_tools_from_spec
    tools, meta = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    ent = next(t for t in tools if t["name"] == "employee_entitlement_grant")
    props = ent["input_schema"]["properties"]
    assert "employeeId" in props
    assert "template" in props
    assert ent["input_schema"]["required"] == ["employeeId", "template"]
    # Meta has query_params
    assert meta["employee_entitlement_grant"]["query_params"] == ["employeeId", "template"]
    assert meta["employee_entitlement_grant"]["method"] == "PUT"


def test_path_params_in_meta():
    from scripts.generate_tools import generate_tools_from_spec
    tools, meta = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    assert meta["invoice_payment"]["path_params"] == ["id"]
    assert "paymentDate" in meta["invoice_payment"]["query_params"]


def test_all_tools_have_defer_loading():
    from scripts.generate_tools import generate_tools_from_spec
    tools, _ = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    for t in tools:
        assert t.get("defer_loading") is True


def test_no_duplicate_names():
    from scripts.generate_tools import generate_tools_from_spec
    tools, _ = generate_tools_from_spec(MINI_SPEC, ACCOUNTING_TAGS)
    names = [t["name"] for t in tools]
    assert len(names) == len(set(names)), f"Duplicate tool names: {[n for n in names if names.count(n) > 1]}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_generate_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts'`

- [ ] **Step 3: Create scripts directory**

Run: `mkdir -p scripts && touch scripts/__init__.py`

- [ ] **Step 4: Implement the generator**

```python
# scripts/generate_tools.py
"""Generate Anthropic tool definitions from the Tripletex OpenAPI spec.

Usage:
    python scripts/generate_tools.py                           # fetch from sandbox + generate
    python scripts/generate_tools.py --spec /tmp/openapi.json  # use cached spec
    python scripts/generate_tools.py --dry-run                 # print stats only
"""

import argparse
import json
import logging
import os
import re
import sys

import requests

logger = logging.getLogger(__name__)

# Tags covering all accounting-relevant endpoints (35 tags, ~248 operations)
ACCOUNTING_TAGS = {
    "employee", "employee/employment", "employee/employment/details",
    "employee/entitlement",
    "customer", "customer/category", "contact",
    "supplier",
    "product", "product/unit",
    "order", "order/orderline",
    "invoice",
    "department",
    "project", "project/participant", "project/hourlyRates",
    "project/hourlyRates/projectSpecificRates", "project/orderline",
    "ledger/voucher", "ledger/account", "ledger/posting", "ledger/vatType",
    "salary", "salary/type",
    "travelExpense", "travelExpense/cost", "travelExpense/costCategory",
    "travelExpense/paymentType", "travelExpense/perDiemCompensation",
    "travelExpense/rateCategory", "travelExpense/rate",
    "travelExpense/mileageAllowance", "travelExpense/accommodationAllowance",
    "timesheet/entry",
    "activity",
    "bank/reconciliation", "bank/reconciliation/match",
    "balanceSheet",
    "asset",
    "company",
    "currency", "country",
    "division",
    "inventory", "inventory/location",
    "supplierInvoice",
    "incomingInvoice",
    "purchaseOrder", "purchaseOrder/orderline",
    "deliveryAddress",
    "municipality",
}

MAX_DEPTH = 3  # limit nested object resolution


def _snake_case(name: str) -> str:
    """Convert operationId or tag to snake_case tool name."""
    # Replace / and . with _
    s = re.sub(r"[/.]", "_", name)
    # Insert _ before uppercase runs
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s).strip("_").lower()
    return s


def _resolve_ref(ref: str, spec: dict) -> dict:
    """Resolve a $ref string like '#/components/schemas/Foo' to its schema."""
    parts = ref.lstrip("#/").split("/")
    node = spec
    for p in parts:
        node = node.get(p, {})
    return node


def _resolve_schema(schema: dict, spec: dict, depth: int = 0) -> dict:
    """Recursively resolve $ref and strip readOnly fields. Limits depth."""
    if not schema:
        return {}

    if "$ref" in schema:
        schema = _resolve_ref(schema["$ref"], spec)

    if depth >= MAX_DEPTH:
        # At max depth, return a simplified version
        return {"type": schema.get("type", "object")}

    result = {}
    for k, v in schema.items():
        if k == "readOnly" and v:
            return {}  # signal to caller to skip this property
        if k == "$ref":
            continue  # already resolved
        if k == "properties" and isinstance(v, dict):
            resolved_props = {}
            for prop_name, prop_schema in v.items():
                resolved = _resolve_schema(prop_schema, spec, depth + 1)
                if resolved:  # skip readOnly
                    resolved_props[prop_name] = resolved
            result[k] = resolved_props
        elif k == "items" and isinstance(v, dict):
            result[k] = _resolve_schema(v, spec, depth + 1)
        else:
            result[k] = v

    return result


def generate_tools_from_spec(
    spec: dict, tags: set[str] | None = None
) -> tuple[list[dict], dict]:
    """Generate Anthropic tool definitions from an OpenAPI spec.

    Returns:
        (tools, meta) where tools is a list of tool defs and meta maps
        tool names to {method, path, path_params, query_params}.
    """
    if tags is None:
        tags = ACCOUNTING_TAGS

    tools = []
    meta = {}
    seen_names = set()

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in ("get", "post", "put", "delete"):
                continue

            op_tags = set(operation.get("tags", []))
            if not op_tags & tags:
                continue

            # Build tool name from operationId
            op_id = operation.get("operationId", "")
            if not op_id:
                tag = next(iter(op_tags), "unknown")
                op_id = f"{tag}_{method}"
            tool_name = _snake_case(op_id)

            # Deduplicate
            if tool_name in seen_names:
                suffix = 2
                while f"{tool_name}_{suffix}" in seen_names:
                    suffix += 1
                tool_name = f"{tool_name}_{suffix}"
            seen_names.add(tool_name)

            # Collect parameters
            params = operation.get("parameters", [])
            path_params = []
            query_params = []
            properties = {}
            required = []

            for p in params:
                p_name = p["name"]
                p_schema = _resolve_schema(p.get("schema", {}), spec)
                if not p_schema:
                    p_schema = {"type": "string"}

                p_schema["description"] = p.get("description", p_name)
                properties[p_name] = p_schema

                if p.get("in") == "path":
                    path_params.append(p_name)
                    required.append(p_name)
                elif p.get("in") == "query":
                    query_params.append(p_name)
                    if p.get("required"):
                        required.append(p_name)

            # Collect request body
            body_schema = {}
            req_body = operation.get("requestBody", {})
            if req_body:
                content = req_body.get("content", {})
                json_content = content.get("application/json", {})
                raw_schema = json_content.get("schema", {})
                body_schema = _resolve_schema(raw_schema, spec)

                # Merge body properties into tool properties
                if "properties" in body_schema:
                    for prop_name, prop_def in body_schema["properties"].items():
                        if prop_name not in properties:  # query/path params take precedence
                            properties[prop_name] = prop_def

                # Merge required from body
                for r in body_schema.get("required", []):
                    if r not in required and r in properties:
                        required.append(r)

            # Build tool definition
            description = operation.get("summary", operation.get("description", tool_name))
            # Trim long descriptions
            if len(description) > 150:
                description = description[:147] + "..."

            input_schema = {"type": "object", "properties": properties}
            if required:
                input_schema["required"] = required

            tool = {
                "name": tool_name,
                "description": description,
                "input_schema": input_schema,
                "defer_loading": True,
            }
            tools.append(tool)

            meta[tool_name] = {
                "method": method.upper(),
                "path": path,
                "path_params": path_params,
                "query_params": query_params,
            }

    return tools, meta


def fetch_openapi_spec(base_url: str, token: str) -> dict:
    """Fetch the OpenAPI spec from a Tripletex sandbox."""
    resp = requests.get(
        f"{base_url}/openapi.json",
        auth=("0", token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def write_generated_tools(tools: list[dict], meta: dict, output_path: str):
    """Write generated tools to a Python module."""
    with open(output_path, "w") as f:
        f.write('# api_knowledge/generated_tools.py\n')
        f.write('"""Auto-generated Tripletex API tool definitions.\n\n')
        f.write(f'Generated from OpenAPI spec. {len(tools)} tools across ')
        f.write(f'{len(set(m["method"] for m in meta.values()))} HTTP methods.\n')
        f.write('DO NOT EDIT MANUALLY — regenerate with: python scripts/generate_tools.py\n')
        f.write('"""\n\n')
        f.write(f'GENERATED_TOOLS = {json.dumps(tools, indent=2, ensure_ascii=False)}\n\n')
        f.write(f'GENERATED_TOOLS_META = {json.dumps(meta, indent=2, ensure_ascii=False)}\n')


def main():
    parser = argparse.ArgumentParser(description="Generate Tripletex API tool definitions")
    parser.add_argument("--spec", help="Path to cached openapi.json (skip fetch)")
    parser.add_argument("--output", default="api_knowledge/generated_tools.py",
                        help="Output path (default: api_knowledge/generated_tools.py)")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only, don't write")
    args = parser.parse_args()

    if args.spec:
        with open(args.spec) as f:
            spec = json.load(f)
    else:
        from dotenv import load_dotenv
        load_dotenv()
        base_url = os.getenv("TRIPLETEX_BASE_URL", "")
        token = os.getenv("TRIPLETEX_SESSION_TOKEN", "")
        if not base_url or not token:
            print("ERROR: Set TRIPLETEX_BASE_URL and TRIPLETEX_SESSION_TOKEN in .env")
            sys.exit(1)
        print(f"Fetching OpenAPI spec from {base_url}...")
        spec = fetch_openapi_spec(base_url, token)

    tools, meta = generate_tools_from_spec(spec)

    # Stats
    total_chars = sum(len(json.dumps(t)) for t in tools)
    est_tokens = total_chars // 4
    methods = {}
    for m in meta.values():
        methods[m["method"]] = methods.get(m["method"], 0) + 1

    print(f"\nGenerated {len(tools)} tools:")
    for method, count in sorted(methods.items()):
        print(f"  {method}: {count}")
    print(f"Estimated tokens (full schemas): ~{est_tokens:,}")
    print(f"Estimated tokens (deferred, names+descriptions only): ~{len(tools) * 35:,}")

    # Check for name collisions
    names = [t["name"] for t in tools]
    dupes = [n for n in names if names.count(n) > 1]
    if dupes:
        print(f"\nERROR: Duplicate tool names: {set(dupes)}")
        sys.exit(1)

    # Check for long names
    long_names = [n for n in names if len(n) > 64]
    if long_names:
        print(f"\nWARNING: {len(long_names)} tool names exceed 64 chars:")
        for n in long_names[:5]:
            print(f"  {n} ({len(n)} chars)")

    if args.dry_run:
        print("\n--dry-run: not writing output file")
        return

    write_generated_tools(tools, meta, args.output)
    print(f"\nWritten to {args.output}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

Also create `scripts/__init__.py`:
```python
# scripts/__init__.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_generate_tools.py -v`
Expected: all 7 tests PASS

- [ ] **Step 6: Run generator against real spec**

Run: `source .env && python scripts/generate_tools.py --dry-run`
Expected: prints stats showing ~248 tools, no duplicate names, estimated tokens

- [ ] **Step 7: Generate the tools file**

Run: `source .env && python scripts/generate_tools.py`
Expected: `api_knowledge/generated_tools.py` created with ~248 tool definitions

- [ ] **Step 8: Commit**

```bash
git add scripts/ tests/test_generate_tools.py api_knowledge/generated_tools.py
git commit -m "feat: OpenAPI tool generator + 248 generated Tripletex tools"
```

---

### Task 2: Agent Tool Router and Content Serialization

**Files:**
- Modify: `agent.py:44-99` (TOOLS section) and `agent.py:137-187` (execute_tool, _serialize_content)
- Modify: `tests/test_agent.py`

- [ ] **Step 1: Write tests for path param resolution**

Add to `tests/test_agent.py`:
```python
class TestResolvePathParams:
    def test_simple_path_param(self):
        result = agent_module._resolve_path_params("/invoice/{id}/:payment", ["id"], {"id": 123})
        assert result == "/invoice/123/:payment"

    def test_no_path_params(self):
        result = agent_module._resolve_path_params("/employee", [], {})
        assert result == "/employee"

    def test_multiple_path_params(self):
        result = agent_module._resolve_path_params("/a/{x}/b/{y}", ["x", "y"], {"x": 1, "y": 2})
        assert result == "/a/1/b/2"

    def test_action_segments_preserved(self):
        result = agent_module._resolve_path_params(
            "/employee/entitlement/:grantEntitlementsByTemplate", [], {}
        )
        assert result == "/employee/entitlement/:grantEntitlementsByTemplate"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_agent.py::TestResolvePathParams -v`
Expected: FAIL with `AttributeError: module 'agent' has no attribute '_resolve_path_params'`

- [ ] **Step 3: Write tests for generated tool execution routing**

Add to `tests/test_agent.py`:
```python
class TestGeneratedToolRouting:
    def test_routes_generated_put_with_query_params(self):
        mock_client = MagicMock()
        mock_client.put.return_value = {"success": True, "status_code": 200, "body": {}}
        # Temporarily inject a generated tool meta entry
        agent_module.GENERATED_TOOLS_META["test_entitlement_grant"] = {
            "method": "PUT",
            "path": "/employee/entitlement/:grantEntitlementsByTemplate",
            "path_params": [],
            "query_params": ["employeeId", "template"],
        }
        try:
            result = agent_module.execute_tool(
                "test_entitlement_grant",
                {"employeeId": 123, "template": "ALL_PRIVILEGES"},
                mock_client,
            )
            mock_client.put.assert_called_once_with(
                "/employee/entitlement/:grantEntitlementsByTemplate",
                body=None, params={"employeeId": 123, "template": "ALL_PRIVILEGES"},
            )
            assert result["success"]
        finally:
            del agent_module.GENERATED_TOOLS_META["test_entitlement_grant"]

    def test_routes_generated_post_with_body(self):
        mock_client = MagicMock()
        mock_client.post.return_value = {"success": True, "status_code": 201, "body": {}}
        agent_module.GENERATED_TOOLS_META["test_employee_post"] = {
            "method": "POST",
            "path": "/employee",
            "path_params": [],
            "query_params": [],
        }
        try:
            result = agent_module.execute_tool(
                "test_employee_post",
                {"firstName": "Test", "lastName": "User"},
                mock_client,
            )
            mock_client.post.assert_called_once_with(
                "/employee", body={"firstName": "Test", "lastName": "User"},
            )
        finally:
            del agent_module.GENERATED_TOOLS_META["test_employee_post"]

    def test_routes_generated_put_with_path_params(self):
        mock_client = MagicMock()
        mock_client.put.return_value = {"success": True, "status_code": 200, "body": {}}
        agent_module.GENERATED_TOOLS_META["test_invoice_payment"] = {
            "method": "PUT",
            "path": "/invoice/{id}/:payment",
            "path_params": ["id"],
            "query_params": ["paymentDate", "paidAmount"],
        }
        try:
            agent_module.execute_tool(
                "test_invoice_payment",
                {"id": 456, "paymentDate": "2026-03-21", "paidAmount": 1000},
                mock_client,
            )
            mock_client.put.assert_called_once_with(
                "/invoice/456/:payment",
                body=None,
                params={"paymentDate": "2026-03-21", "paidAmount": 1000},
            )
        finally:
            del agent_module.GENERATED_TOOLS_META["test_invoice_payment"]

    def test_generic_tools_still_work(self):
        mock_client = MagicMock()
        mock_client.get.return_value = {"success": True, "status_code": 200, "body": {}}
        agent_module.execute_tool("tripletex_get", {"path": "/employee"}, mock_client)
        mock_client.get.assert_called_once()
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_agent.py::TestGeneratedToolRouting -v`
Expected: FAIL

- [ ] **Step 5: Implement _resolve_path_params, GENERATED_TOOLS_META, and update execute_tool**

In `agent.py`, add after the TOOLS list (around line 99):
```python
# ---------------------------------------------------------------------------
# Generated tools (loaded when AGENT_MODE != "generic")
# ---------------------------------------------------------------------------

AGENT_MODE = os.getenv("AGENT_MODE", "generic")

if AGENT_MODE != "generic":
    from api_knowledge.generated_tools import GENERATED_TOOLS, GENERATED_TOOLS_META
else:
    GENERATED_TOOLS = []
    GENERATED_TOOLS_META = {}
```

Add `_resolve_path_params` function and update `execute_tool` per the spec.

Rename existing `TOOLS` to `GENERIC_TOOLS` and add `_build_tools()`:
```python
GENERIC_TOOLS = [...]  # existing 4 tools

def _build_tools():
    if AGENT_MODE == "generic":
        return list(GENERIC_TOOLS)
    tools = list(GENERIC_TOOLS)
    tools.append({"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"})
    tools.extend(GENERATED_TOOLS)
    if AGENT_MODE == "tool_search":
        tools = [{**t, "defer_loading": True} for t in tools[:4]] + tools[4:]
    return tools

TOOLS = _build_tools()
```

Update `execute_tool` to route generated tools INSIDE the existing try/except:
```python
def execute_tool(name: str, args: dict, client: TripletexClient) -> dict:
    """Execute a single tool call against the Tripletex API."""
    try:
        # Generic tools (existing behavior)
        if name.startswith("tripletex_"):
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
                return client.delete(path, params=params)

        # Generated endpoint tools
        meta = GENERATED_TOOLS_META.get(name)
        if meta:
            path = _resolve_path_params(meta["path"], meta.get("path_params", []), args)
            query = {k: args[k] for k in meta["query_params"] if k in args}
            body_keys = [k for k in args if k not in meta["query_params"]
                         and k not in meta.get("path_params", [])]
            body = {k: args[k] for k in body_keys} if body_keys else None
            method = meta["method"]
            if method == "GET":
                return client.get(path, params=query or None)
            elif method == "POST":
                return client.post(path, body=body)
            elif method == "PUT":
                return client.put(path, body=body, params=query or None)
            elif method == "DELETE":
                return client.delete(path, params=query or None)

        return {"success": False, "error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

Also update references in these existing tests to use `GENERIC_TOOLS` instead of `TOOLS`:
- `test_post_requires_path_and_body`: `next(t for t in agent_module.GENERIC_TOOLS if ...)`
- `test_put_has_params`: same
- `test_all_tools_have_input_schema`: same

- [ ] **Step 6: Write test for content serialization of new block types**

Add to `tests/test_agent.py`:
```python
class TestSerializeToolSearchBlocks:
    def test_server_tool_use_block(self):
        block = MagicMock()
        block.type = "server_tool_use"
        block.id = "tool_123"
        block.name = "employee_post"
        block.input = {"firstName": "Test"}
        block.caller = None
        result = agent_module._serialize_content([block])
        assert result[0]["type"] == "server_tool_use"
        assert result[0]["name"] == "employee_post"
        assert "caller" not in result[0]  # None caller omitted

    def test_server_tool_use_with_caller(self):
        caller_mock = MagicMock()
        caller_mock.model_dump.return_value = {"type": "direct"}
        block = MagicMock()
        block.type = "server_tool_use"
        block.id = "tool_123"
        block.name = "employee_post"
        block.input = {}
        block.caller = caller_mock
        result = agent_module._serialize_content([block])
        assert result[0]["caller"] == {"type": "direct"}

    def test_tool_search_tool_result_block(self):
        content_mock = MagicMock()
        content_mock.model_dump.return_value = {"tools": [{"name": "employee_post"}]}
        block = MagicMock()
        block.type = "tool_search_tool_result"
        block.tool_use_id = "search_123"
        block.content = content_mock
        result = agent_module._serialize_content([block])
        assert result[0]["type"] == "tool_search_tool_result"
        assert result[0]["tool_use_id"] == "search_123"
        assert result[0]["content"] == {"tools": [{"name": "employee_post"}]}
```

- [ ] **Step 7: Implement content serialization updates**

In `agent.py`, update `_serialize_content` to add after the `tool_use` block:
```python
elif block.type == "server_tool_use":
    entry = {"type": "server_tool_use", "id": block.id, "name": block.name, "input": block.input}
    if hasattr(block, "caller") and block.caller is not None:
        entry["caller"] = block.caller.model_dump(exclude_none=True)
    result.append(entry)
elif block.type == "tool_search_tool_result":
    result.append({
        "type": "tool_search_tool_result",
        "tool_use_id": block.tool_use_id,
        "content": block.content.model_dump(exclude_none=True),
    })
```

- [ ] **Step 8: Update existing test_has_four_tools for mode awareness**

Update `TestToolDefinitions.test_has_four_tools`:
```python
def test_has_four_tools(self):
    # In generic mode (default), TOOLS has exactly 4 generic tools
    generic_names = [t["name"] for t in agent_module.GENERIC_TOOLS]
    assert sorted(generic_names) == ["tripletex_delete", "tripletex_get", "tripletex_post", "tripletex_put"]
```

Update other tests that reference `agent_module.TOOLS` to use `agent_module.GENERIC_TOOLS`.

- [ ] **Step 9: Run all tests**

Run: `python -m pytest tests/test_agent.py -v`
Expected: all tests PASS

- [ ] **Step 10: Commit**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: tool router, content serialization, mode switching in agent.py"
```

---

### Task 3: Slim System Prompt

**Files:**
- Modify: `prompts.py`
- Modify: `tests/test_prompts.py`

- [ ] **Step 1: Write test for slim prompt mode**

Add to `tests/test_prompts.py`:
```python
class TestSlimPrompt:
    def test_slim_prompt_has_no_cheat_sheet(self):
        prompt = build_system_prompt(mode="hybrid")
        assert "## Tripletex v2 API" not in prompt  # cheat sheet header absent

    def test_slim_prompt_has_recipes(self):
        prompt = build_system_prompt(mode="hybrid")
        assert "Create Customer" in prompt
        assert "Create Employee" in prompt

    def test_slim_prompt_has_fallback_guidance(self):
        prompt = build_system_prompt(mode="hybrid")
        assert "tripletex_get" in prompt or "generic" in prompt.lower()

    def test_generic_mode_unchanged(self):
        prompt = build_system_prompt(mode="generic")
        assert "## Tripletex v2 API" in prompt  # cheat sheet present

    def test_default_mode_is_generic(self):
        prompt = build_system_prompt()
        assert "## Tripletex v2 API" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_prompts.py::TestSlimPrompt -v`
Expected: FAIL with `TypeError: build_system_prompt() got an unexpected keyword argument 'mode'`

- [ ] **Step 3: Implement mode parameter in build_system_prompt**

In `prompts.py`:

1. Rename `build_system_prompt` to `_full_prompt` (keep all existing content)
2. Create new `build_system_prompt` that dispatches by mode
3. Create `_slim_prompt` that copies everything EXCEPT the final `{TRIPLETEX_API_CHEAT_SHEET}` line, replacing it with fallback guidance

```python
def build_system_prompt(mode: str = "generic") -> str:
    """Build the system prompt. Mode controls cheat sheet inclusion."""
    if mode == "generic":
        return _full_prompt()
    return _slim_prompt()


def _full_prompt() -> str:
    """Full prompt with cheat sheet — used in generic mode."""
    today = date.today().isoformat()
    # ... (entire existing prompt body, unchanged)


def _slim_prompt() -> str:
    """Slim prompt without cheat sheet — used in hybrid/tool_search modes.

    Keeps: scoring rules, known constants, critical gotchas, all 20 recipes.
    Drops: the 941-line TRIPLETEX_API_CHEAT_SHEET (endpoint details come from tool schemas).
    Adds: fallback guidance for using generic tools.
    """
    today = date.today().isoformat()
    # Copy the entire f-string from _full_prompt() but replace the last line:
    #   {TRIPLETEX_API_CHEAT_SHEET}
    # with:
    #   ## Using Tools
    #   You have access to specific Tripletex API tools discovered via search. Each tool has
    #   exact parameter schemas with enums and required fields — use them directly.
    #   If a searched tool does not exist or fails, fall back to the generic
    #   tripletex_get/post/put/delete tools with the API path and body directly.
```

The key change: `_slim_prompt` is identical to `_full_prompt` except the last line before the closing `"""` replaces `{TRIPLETEX_API_CHEAT_SHEET}` with the fallback guidance text above.

- [ ] **Step 4: Run all prompt tests**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add prompts.py tests/test_prompts.py
git commit -m "feat: add slim prompt mode for hybrid tool search"
```

---

### Task 4: Wire AGENT_MODE Through main.py

**Files:**
- Modify: `agent.py:265-267` (run_agent calling build_system_prompt)
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update run_agent to pass mode to build_system_prompt**

In `agent.py`, change:
```python
system_prompt = build_system_prompt()
```
to:
```python
system_prompt = build_system_prompt(mode=AGENT_MODE)
```

No changes needed in `main.py` — `AGENT_MODE` is read from env var directly in `agent.py`.

- [ ] **Step 2: Update CLAUDE.md with AGENT_MODE documentation**

Add to the Deploy commands section:
```markdown
### Agent Mode

Set `AGENT_MODE` env var to control tool behavior:
- `generic` (default): 4 generic tools + full cheat sheet. Current battle-tested mode.
- `hybrid`: 4 generic tools + 248 deferred endpoint tools + BM25 tool search. Requires `api_knowledge/generated_tools.py`.

To deploy hybrid mode to dev for testing:
```bash
gcloud run deploy ai-accounting-agent-det ... --set-env-vars="...,AGENT_MODE=hybrid" --quiet
```
```

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add agent.py CLAUDE.md
git commit -m "feat: wire AGENT_MODE through agent, document in CLAUDE.md"
```

---

### Task 5: Integration Test — Deploy Hybrid Mode to Dev

**Files:** No code changes — deploy and test

- [ ] **Step 1: Deploy hybrid mode to dev**

```bash
source .env
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-dev,LANGSMITH_API_KEY=$LANGSMITH_API_KEY,AGENT_MODE=hybrid" \
  --quiet
```

- [ ] **Step 2: Test with create_product fixture (Tier 1)**

```bash
source .env && curl -s -X POST "$DEV_URL/" -H "Content-Type: application/json" \
  -d "$(jq --arg base "$TRIPLETEX_BASE_URL" --arg token "$TRIPLETEX_SESSION_TOKEN" \
    '.tripletex_credentials.base_url = $base | .tripletex_credentials.session_token = $token' \
    tests/competition_tasks/39_create_product_pt.json)" | python3 -m json.tool
```

Expected: `{"status": "completed"}`

- [ ] **Step 3: Check LangSmith traces for tool search usage**

```bash
source .env && python3 -c "
from langsmith import Client
c = Client(api_key='$LANGSMITH_API_KEY')
runs = list(c.list_runs(project_name='ai-accounting-agent-dev', filter='eq(name, \"run_agent\")', limit=1))
for r in runs:
    meta = r.metadata or {}
    print(f'errors={meta.get(\"api_errors\")} calls={meta.get(\"api_calls\")} iters={meta.get(\"iterations\")}')
"
```

Expected: fewer errors than generic mode on the same task

- [ ] **Step 4: Test with register_hours fixture (Tier 2 — previously failed)**

```bash
source .env && curl -s -X POST "$DEV_URL/" -H "Content-Type: application/json" \
  -d "$(jq --arg base "$TRIPLETEX_BASE_URL" --arg token "$TRIPLETEX_SESSION_TOKEN" \
    '.tripletex_credentials.base_url = $base | .tripletex_credentials.session_token = $token' \
    tests/competition_tasks/32_register_hours_no.json)" | python3 -m json.tool
```

Expected: `{"status": "completed"}` — verify via LangSmith that entitlement grant uses correct enum

- [ ] **Step 5: If tests pass, commit any fixes. If tests fail, investigate and fix before proceeding.**

---

### Task 6: Verify Generic Mode Is Unaffected

**Files:** No code changes — verification only

- [ ] **Step 1: Deploy generic mode (default) to verify no regression**

```bash
source .env
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-dev,LANGSMITH_API_KEY=$LANGSMITH_API_KEY,AGENT_MODE=generic" \
  --quiet
```

- [ ] **Step 2: Run same test fixtures and verify identical behavior to before**

- [ ] **Step 3: If all good, deploy hybrid to dev and generic to comp**

```bash
# Keep comp on generic (battle-tested) for competition
source .env
gcloud run deploy accounting-agent-comp --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-comp,LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP,AGENT_MODE=generic" \
  --quiet
```
