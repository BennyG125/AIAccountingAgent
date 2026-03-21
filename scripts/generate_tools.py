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

# Tags covering all accounting-relevant endpoints (~35 tags, ~248 operations)
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

MAX_DEPTH = 3


def _snake_case(name: str) -> str:
    """Convert operationId or tag to snake_case tool name."""
    s = re.sub(r"[/.]", "_", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
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
        return {"type": schema.get("type", "object")}

    result = {}
    for k, v in schema.items():
        if k == "readOnly" and v:
            return {}  # signal to caller to skip this property
        if k == "$ref":
            continue
        if k == "properties" and isinstance(v, dict):
            resolved_props = {}
            for prop_name, prop_schema in v.items():
                resolved = _resolve_schema(prop_schema, spec, depth + 1)
                if resolved:
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

            op_id = operation.get("operationId", "")
            if not op_id:
                tag = next(iter(op_tags), "unknown")
                op_id = f"{tag}_{method}"
            tool_name = _snake_case(op_id)

            if tool_name in seen_names:
                suffix = 2
                while f"{tool_name}_{suffix}" in seen_names:
                    suffix += 1
                tool_name = f"{tool_name}_{suffix}"
            seen_names.add(tool_name)

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

            body_schema = {}
            req_body = operation.get("requestBody", {})
            if req_body:
                content = req_body.get("content", {})
                json_content = content.get("application/json", {})
                raw_schema = json_content.get("schema", {})
                body_schema = _resolve_schema(raw_schema, spec)

                if "properties" in body_schema:
                    for prop_name, prop_def in body_schema["properties"].items():
                        if prop_name not in properties:
                            properties[prop_name] = prop_def

                for r in body_schema.get("required", []):
                    if r not in required and r in properties:
                        required.append(r)

            description = operation.get("summary", operation.get("description", tool_name))
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
    parser.add_argument("--dry-run", action="store_true", help="Print stats only")
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

    names = [t["name"] for t in tools]
    dupes = [n for n in names if names.count(n) > 1]
    if dupes:
        print(f"\nERROR: Duplicate tool names: {set(dupes)}")
        sys.exit(1)

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
