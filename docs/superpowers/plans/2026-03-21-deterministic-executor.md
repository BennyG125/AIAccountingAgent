# Deterministic Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the download script, executor framework, and main.py integration so that once optimal sequences are researched, execution plans can be plugged in and immediately work.

**Architecture:** Comp container already logs requests to GCS (with results). Download script organizes them into `real-requests/logs/`. Executor framework provides base class, keyword classifier, plan registry, and Gemini param extractor. main.py tries deterministic execution first, falls back to existing Claude agent.

**Tech Stack:** Python 3.11, FastAPI, google-cloud-storage, google-genai (Gemini Flash), existing TripletexClient

**Spec:** `docs/superpowers/specs/2026-03-21-deterministic-executor-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/download_captures.py` | Create | Download GCS payloads → `real-requests/logs/NNN_name/` |
| `execution_plans/__init__.py` | Create | Package init — imports all plan modules |
| `execution_plans/_base.py` | Create | ExecutionPlan base class with timeout, safe_post, find_or_create |
| `execution_plans/_classifier.py` | Create | Keyword-based multilingual task classifier |
| `execution_plans/_registry.py` | Create | Plan registry with @register decorator |
| `execution_plans/create_customer.py` | Create | Example plan to validate end-to-end pipeline |
| `deterministic_executor.py` | Create | DeterministicExecutor: classify → extract → execute |
| `main.py` | Modify | Add deterministic path before Claude fallback |
| `tests/test_classifier.py` | Create | Tests for keyword classifier |
| `tests/test_executor.py` | Create | Tests for executor integration |
| `scripts/verify_plans.py` | Create | Verify all plans against sandbox |

---

### Task 1: Download Script

**Files:**
- Create: `scripts/download_captures.py`

- [ ] **Step 1: Create `scripts/download_captures.py`**

```python
#!/usr/bin/env python3
"""Download captured competition requests from GCS into real-requests/logs/.

Each request gets its own numbered folder with request.json and any decoded files.

Usage:
    python scripts/download_captures.py                    # all default buckets
    python scripts/download_captures.py --bucket my-bucket # specific bucket
"""
import argparse
import base64
import json
import os
import re

from google.cloud import storage

DEFAULT_BUCKETS = [
    "ai-nm26osl-1799-competition-logs",
    "ai-nm26osl-1799-dev-logs",
]
OUTPUT_DIR = "real-requests/logs"


def _safe_name(text: str, max_len: int = 40) -> str:
    """Convert text to a filesystem-safe directory name."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", text).strip("_")
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    return safe[:max_len]


def _extract_request(raw: dict) -> dict:
    """Extract the request payload from either format (direct or wrapped)."""
    if "request" in raw:
        return raw["request"]
    return raw


def download(buckets: list[str] | None = None):
    buckets = buckets or DEFAULT_BUCKETS
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    idx = 1
    seen_prompts = set()  # deduplicate across buckets

    for bucket_name in buckets:
        print(f"\n--- Scanning gs://{bucket_name} ---")
        try:
            client = storage.Client()
            bucket = client.bucket(bucket_name)
        except Exception as e:
            print(f"  Skipping (cannot access): {e}")
            continue

        prefixes = ["captured/", "requests/"]

        for prefix in prefixes:
            try:
                blobs = sorted(
                    bucket.list_blobs(prefix=prefix), key=lambda b: b.name
                )
            except Exception:
                continue

            for blob in blobs:
                try:
                    raw = json.loads(blob.download_as_text())
                except Exception:
                    continue

                data = _extract_request(raw)
                prompt = (
                    data.get("prompt") or data.get("task_prompt") or "unknown"
                )

                # Deduplicate by prompt text
                prompt_key = prompt.strip()[:200]
                if prompt_key in seen_prompts:
                    continue
                seen_prompts.add(prompt_key)

                prompt_preview = _safe_name(prompt)
                folder = os.path.join(OUTPUT_DIR, f"{idx:03d}_{prompt_preview}")
                os.makedirs(folder, exist_ok=True)

                # Save full raw payload
                with open(os.path.join(folder, "request.json"), "w") as f:
                    json.dump(raw, f, indent=2, ensure_ascii=False)

                # Decode and save attached files
                files = data.get("files") or data.get("attached_files") or []
                for file_idx, file_entry in enumerate(files):
                    filename = file_entry.get("filename", f"file_{file_idx}")
                    # Try all known base64 field names
                    content_b64 = (
                        file_entry.get("content")
                        or file_entry.get("data")
                        or file_entry.get("content_base64", "")
                    )
                    if content_b64:
                        try:
                            file_data = base64.b64decode(content_b64)
                            filepath = os.path.join(folder, filename)
                            with open(filepath, "wb") as f:
                                f.write(file_data)
                            print(f"  Decoded file: {filepath}")
                        except Exception as e:
                            print(f"  Warning: could not decode {filename}: {e}")

                print(f"  [{bucket_name}] {folder}")
                idx += 1

    print(f"\nDone. {idx - 1} requests saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download captured requests from GCS")
    parser.add_argument(
        "--bucket", action="append",
        help="GCS bucket to download from (can specify multiple). Defaults to all known buckets.",
    )
    args = parser.parse_args()
    download(args.bucket)
```

- [ ] **Step 2: Test script runs without errors (dry run)**

Run: `python scripts/download_captures.py --help`
Expected: Help text with `--bucket` option

- [ ] **Step 3: Commit**

```bash
git add scripts/download_captures.py
git commit -m "feat: add download script for organizing captured requests"
```

---

### Task 2: Execution Plan Base Class

**Files:**
- Create: `execution_plans/__init__.py`
- Create: `execution_plans/_base.py`
- Create: `execution_plans/_registry.py`
- Test: `tests/test_executor.py`

- [ ] **Step 1: Create package and base class**

Create `execution_plans/__init__.py`:
```python
"""Deterministic execution plans for known task types."""
```

Create `execution_plans/_registry.py`:
```python
"""Plan registry — maps task_type strings to ExecutionPlan instances."""

PLANS: dict[str, "ExecutionPlan"] = {}


def register(plan_class):
    """Class decorator that registers an execution plan by its task_type."""
    instance = plan_class()
    PLANS[instance.task_type] = instance
    return plan_class
```

Create `execution_plans/_base.py`:
```python
"""Base class for deterministic execution plans."""
import logging
import time

from tripletex_api import TripletexClient

logger = logging.getLogger(__name__)

EXECUTOR_TIMEOUT = 60  # seconds — leaves ~200s for Claude fallback


class ExecutionPlan:
    """Base class for all execution plans.

    Subclasses must set task_type and implement execute().
    """

    task_type: str = ""
    description: str = ""

    def execute(self, client: TripletexClient, params: dict, start_time: float) -> dict:
        """Execute the plan against the Tripletex API.

        Args:
            client: Authenticated TripletexClient
            params: Extracted parameters from the prompt
            start_time: time.time() when execution started

        Returns:
            Result dict with status, api_calls, api_errors, etc.

        Raises:
            RuntimeError: On unrecoverable API failure
            TimeoutError: If execution exceeds EXECUTOR_TIMEOUT
        """
        raise NotImplementedError

    def _check_timeout(self, start_time: float) -> None:
        """Raise TimeoutError if we've exceeded EXECUTOR_TIMEOUT."""
        elapsed = time.time() - start_time
        if elapsed > EXECUTOR_TIMEOUT:
            raise TimeoutError(
                f"Execution plan '{self.task_type}' timed out after {elapsed:.0f}s "
                f"(limit: {EXECUTOR_TIMEOUT}s)"
            )

    def _safe_post(
        self,
        client: TripletexClient,
        path: str,
        body: dict,
        retry_without: list[str] | None = None,
    ) -> dict:
        """POST with optional field removal on 422 failure.

        If the first POST returns 422 and retry_without is specified,
        retries with those fields removed from the body.
        Does NOT mutate the original body dict.
        """
        result = client.post(path, body=body)
        if (
            not result["success"]
            and retry_without
            and result.get("status_code") == 422
        ):
            cleaned = {k: v for k, v in body.items() if k not in retry_without}
            result = client.post(path, body=cleaned)
        return result

    def _find_or_create(
        self,
        client: TripletexClient,
        search_path: str,
        search_params: dict,
        create_path: str,
        create_body: dict,
    ) -> int:
        """Search for an entity; create if not found. Returns entity ID.

        Raises RuntimeError if both search and create fail.
        """
        result = client.get(search_path, params=search_params)
        if result["success"]:
            values = result["body"].get("values", [])
            if values:
                return values[0]["id"]

        # Not found — create
        result = client.post(create_path, body=create_body)
        if result["success"]:
            return result["body"]["value"]["id"]

        raise RuntimeError(
            f"Failed to find or create at {create_path}: "
            f"status={result.get('status_code')}, error={result.get('error')}"
        )

    def _make_result(
        self,
        api_calls: int,
        api_errors: int,
        time_ms: int = 0,
        error_details: list | None = None,
    ) -> dict:
        """Build a result dict matching run_agent() output shape."""
        return {
            "status": "completed",
            "iterations": 1,
            "time_ms": time_ms,
            "api_calls": api_calls,
            "api_errors": api_errors,
            "error_details": error_details,
            "executor": "deterministic",
        }
```

- [ ] **Step 2: Write tests for base class**

Create `tests/test_executor.py`:
```python
"""Tests for execution plan base class and registry."""
import time
import pytest
from unittest.mock import MagicMock

from execution_plans._base import ExecutionPlan, EXECUTOR_TIMEOUT
from execution_plans._registry import PLANS, register


class TestExecutionPlanBase:
    def test_check_timeout_within_limit(self):
        plan = ExecutionPlan()
        # Should not raise
        plan._check_timeout(time.time())

    def test_check_timeout_exceeded(self):
        plan = ExecutionPlan()
        # start_time far in the past
        with pytest.raises(TimeoutError):
            plan._check_timeout(time.time() - EXECUTOR_TIMEOUT - 1)

    def test_safe_post_success(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.post.return_value = {"success": True, "body": {"value": {"id": 1}}}
        result = plan._safe_post(client, "/test", {"name": "x"})
        assert result["success"]
        client.post.assert_called_once_with("/test", body={"name": "x"})

    def test_safe_post_retries_without_fields_on_422(self):
        plan = ExecutionPlan()
        client = MagicMock()
        # First call fails with 422, second succeeds
        client.post.side_effect = [
            {"success": False, "status_code": 422, "error": "bad field"},
            {"success": True, "body": {"value": {"id": 1}}},
        ]
        result = plan._safe_post(
            client, "/test", {"name": "x", "vatType": "bad"}, retry_without=["vatType"]
        )
        assert result["success"]
        assert client.post.call_count == 2
        # Second call should not have vatType
        second_call_body = client.post.call_args_list[1][1].get("body") or client.post.call_args_list[1][0][1]
        assert "vatType" not in second_call_body

    def test_safe_post_does_not_mutate_original_body(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.post.side_effect = [
            {"success": False, "status_code": 422, "error": "bad"},
            {"success": True, "body": {"value": {"id": 1}}},
        ]
        original = {"name": "x", "vatType": "bad"}
        plan._safe_post(client, "/test", original, retry_without=["vatType"])
        assert "vatType" in original  # original unchanged

    def test_find_or_create_finds_existing(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.get.return_value = {
            "success": True,
            "body": {"values": [{"id": 42, "name": "existing"}]},
        }
        result = plan._find_or_create(
            client, "/search", {"name": "x"}, "/create", {"name": "x"}
        )
        assert result == 42
        client.post.assert_not_called()

    def test_find_or_create_creates_when_not_found(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.get.return_value = {"success": True, "body": {"values": []}}
        client.post.return_value = {"success": True, "body": {"value": {"id": 99}}}
        result = plan._find_or_create(
            client, "/search", {"name": "x"}, "/create", {"name": "x"}
        )
        assert result == 99

    def test_find_or_create_raises_on_failure(self):
        plan = ExecutionPlan()
        client = MagicMock()
        client.get.return_value = {"success": True, "body": {"values": []}}
        client.post.return_value = {
            "success": False, "status_code": 500, "error": "server error"
        }
        with pytest.raises(RuntimeError, match="Failed to find or create"):
            plan._find_or_create(
                client, "/search", {}, "/create", {"name": "x"}
            )

    def test_make_result_shape(self):
        plan = ExecutionPlan()
        result = plan._make_result(api_calls=3, api_errors=1, time_ms=500)
        assert result == {
            "status": "completed",
            "iterations": 1,
            "time_ms": 500,
            "api_calls": 3,
            "api_errors": 1,
            "error_details": None,
            "executor": "deterministic",
        }


class TestRegistry:
    def test_register_decorator(self):
        @register
        class TestPlan(ExecutionPlan):
            task_type = "test_task_for_registry"

        assert "test_task_for_registry" in PLANS
        assert isinstance(PLANS["test_task_for_registry"], TestPlan)
        # Cleanup
        del PLANS["test_task_for_registry"]
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_executor.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add execution_plans/__init__.py execution_plans/_base.py execution_plans/_registry.py tests/test_executor.py
git commit -m "feat: add execution plan base class, registry, and tests"
```

---

### Task 3: Keyword Classifier

**Files:**
- Create: `execution_plans/_classifier.py`
- Test: `tests/test_classifier.py`

- [ ] **Step 1: Write classifier tests**

Create `tests/test_classifier.py`:
```python
"""Tests for keyword-based task classifier."""
import pytest
from execution_plans._classifier import classify_task


class TestClassifier:
    """Test classification across task types and languages."""

    @pytest.mark.parametrize("prompt,expected", [
        # create_customer
        ("Create the customer Brightstone Ltd with organization number 853284882", "create_customer"),
        ("Opprett kunden Fjordkraft AS med organisasjonsnummer 843216285", "create_customer"),
        ("Crie o cliente Montanha Lda com número de organização 986713344", "create_customer"),

        # create_employee
        ("Create an employee named Per Olsen with email per.olsen@firma.no", "create_employee"),
        ("Tenemos un nuevo empleado llamado Diego Rodriguez", "create_employee"),
        ("Temos um novo funcionário chamado Rita Almeida", "create_employee"),

        # create_supplier
        ("Registrer leverandøren Nordhav AS med organisasjonsnummer 923456910", "create_supplier"),
        ("Enregistrez le fournisseur Lumiere SARL avec le numéro d'organisation 879852439", "create_supplier"),

        # create_departments (batch)
        ("Opprett tre avdelingar i Tripletex: Logistikk, Innkjop og IT", "create_departments"),
        ("Erstellen Sie drei Abteilungen in Tripletex", "create_departments"),

        # create_invoice
        ("Opprett og send en faktura til kunden Lysgard AS", "create_invoice"),
        ("Crea una factura para el cliente Dorada SL", "create_invoice"),
        ("Crie uma fatura para o cliente Oceano Lda", "create_invoice"),

        # register_supplier_invoice — must match BEFORE create_supplier
        ("Wir haben die Rechnung vom Lieferanten Nordlicht GmbH", "register_supplier_invoice"),
        ("Enregistrez la facture du fournisseur Lumiere SARL", "register_supplier_invoice"),

        # register_payment
        ("Le paiement de Riviere SARL pour la facture Design web", "register_payment"),
        ("O pagamento de Cascata Lda referente a fatura", "register_payment"),

        # run_salary
        ("Kjør lønn for Erik Nilsen for denne måneden", "run_salary"),
        ("Processe o salário de Sofia Sousa para este mês", "run_salary"),

        # fixed_price_project — must match BEFORE create_project
        ("Establezca un precio fijo de 152400 NOK en el proyecto", "fixed_price_project"),
        ("Set a fixed price of 100000 NOK on the project", "fixed_price_project"),

        # create_project
        ("Crie o projeto Migracao Montanha vinculado ao cliente", "create_project"),
        ("Create the project Upgrade Windmill linked to the customer", "create_project"),

        # create_order
        ("Créez une commande pour le client Colline SARL", "create_order"),

        # custom_dimension
        ("Create a custom accounting dimension Produktlinje", "custom_dimension"),

        # travel_expense
        ("Registrer ei reiserekning for Svein Berg", "travel_expense"),
        ("Erfassen Sie eine Reisekostenabrechnung", "travel_expense"),

        # credit_note
        ("Issue a full credit note that reverses the entire invoice", "credit_note"),

        # reverse_payment
        ("Reverse the payment for invoice 12345", "reverse_payment"),

        # register_hours
        ("Register 8 hours for the project", "register_hours"),

        # bank_reconciliation
        ("Rapprochez le relevé bancaire CSV ci-joint", "bank_reconciliation"),

        # unknown
        ("Do something completely unrelated", None),
    ])
    def test_classify(self, prompt, expected):
        assert classify_task(prompt) == expected

    def test_specific_before_general(self):
        """register_supplier_invoice must match before create_supplier."""
        prompt = "Register the supplier invoice from Nordlicht GmbH"
        assert classify_task(prompt) == "register_supplier_invoice"

    def test_fixed_price_before_project(self):
        """fixed_price_project must match before create_project."""
        prompt = "Set a fixed price on the project Infrastructure Upgrade"
        assert classify_task(prompt) == "fixed_price_project"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_classifier.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create `execution_plans/_classifier.py`**

```python
"""Keyword-based multilingual task classifier.

Classifies accounting task prompts into known task types using regex patterns.
Patterns are ordered most-specific-first so that e.g. "register_supplier_invoice"
matches before "create_supplier" and "fixed_price_project" before "create_project".
"""
import re

# (task_type, [regex_patterns]) — ordered most specific first
TASK_PATTERNS: list[tuple[str, list[str]]] = [
    # Composite / specific patterns first
    ("register_supplier_invoice", [
        r"leverandør.*faktura", r"supplier.*invoice", r"proveedor.*factura",
        r"fornecedor.*fatura", r"lieferant.*rechnung", r"fournisseur.*facture",
    ]),
    ("fixed_price_project", [
        r"fast\s*pris", r"fixed\s*price", r"precio\s*fijo", r"preço\s*fixo",
        r"festpreis", r"prix\s*fixe",
    ]),
    ("reverse_payment", [
        r"reverser.*betaling", r"reverse.*payment", r"revertir.*pago",
        r"reverter.*pagamento", r"stornierung", r"annuler.*paiement",
    ]),
    ("credit_note", [
        r"kreditnota", r"credit\s*note", r"nota\s*de\s*crédito", r"gutschrift",
        r"note\s*de\s*crédit",
    ]),
    ("bank_reconciliation", [
        r"bank.*avstemming", r"bank.*reconcil", r"concilia.*banc",
        r"rapproch.*bancaire",
    ]),
    ("employee_onboarding", [
        r"arbeidskontrakt", r"employment.*contract", r"contrat.*travail",
        r"contrato.*trabajo",
    ]),
    ("travel_expense", [
        r"reise", r"travel.*expense", r"gastos.*viaje", r"despesas.*viagem",
        r"reisekosten", r"frais.*voyage", r"reiserekning", r"reiseregning",
    ]),
    ("register_hours", [
        r"timer", r"hours", r"horas", r"stunden", r"heures", r"timeføring",
    ]),
    ("custom_dimension", [
        r"dimensjon", r"dimension", r"dimensión", r"dimensão",
    ]),
    ("run_salary", [
        r"l[øo]nn", r"salary", r"salario", r"salário", r"gehalt", r"salaire",
    ]),
    ("register_payment", [
        r"betal", r"payment", r"pago", r"pagamento", r"zahlung", r"paiement",
    ]),
    ("create_invoice", [
        r"faktura", r"invoice", r"factura", r"fatura", r"rechnung", r"facture",
    ]),
    ("create_order", [
        r"bestilling", r"order", r"pedido", r"encomenda", r"bestellung", r"commande",
    ]),
    ("create_project", [
        r"prosjekt", r"project", r"proyecto", r"projeto", r"projekt", r"projet",
    ]),
    ("create_departments", [
        r"avdeling", r"department", r"departamento", r"abteilung", r"département",
    ]),
    ("create_employee", [
        r"ansatt", r"employee", r"empleado", r"funcionário", r"mitarbeiter", r"employé",
    ]),
    ("create_customer", [
        r"kunde", r"customer", r"cliente", r"client",
    ]),
    ("create_supplier", [
        r"leverandør", r"supplier", r"proveedor", r"fornecedor",
        r"lieferant", r"fournisseur",
    ]),
    ("create_product", [
        r"produkt", r"product", r"producto", r"produto", r"produit",
    ]),
]


def classify_task(prompt: str) -> str | None:
    """Classify a task prompt into a known task type.

    Returns the task_type string or None if no pattern matches.
    """
    prompt_lower = prompt.lower()
    for task_type, patterns in TASK_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return task_type
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_classifier.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add execution_plans/_classifier.py tests/test_classifier.py
git commit -m "feat: add keyword-based multilingual task classifier with tests"
```

---

### Task 4: Example Execution Plan (create_customer)

**Files:**
- Create: `execution_plans/create_customer.py`
- Test: `tests/test_executor.py` (add to existing)

- [ ] **Step 1: Write test for create_customer plan**

Append to `tests/test_executor.py`:
```python
from execution_plans.create_customer import CreateCustomerPlan


class TestCreateCustomerPlan:
    def test_execute_simple(self):
        plan = CreateCustomerPlan()
        client = MagicMock()
        client.post.return_value = {
            "success": True,
            "status_code": 201,
            "body": {"value": {"id": 1, "name": "Test AS"}},
        }
        result = plan.execute(
            client,
            {"name": "Test AS", "org_number": "123456789"},
            start_time=time.time(),
        )
        assert result["status"] == "completed"
        assert result["api_calls"] == 1
        assert result["api_errors"] == 0
        assert result["executor"] == "deterministic"

    def test_execute_with_address(self):
        plan = CreateCustomerPlan()
        client = MagicMock()
        client.post.return_value = {
            "success": True,
            "status_code": 201,
            "body": {"value": {"id": 1}},
        }
        result = plan.execute(
            client,
            {
                "name": "Test AS",
                "org_number": "123456789",
                "email": "test@test.no",
                "phone": "12345678",
                "address": {
                    "street": "Storgata 1",
                    "postal_code": "0001",
                    "city": "Oslo",
                },
            },
            start_time=time.time(),
        )
        assert result["status"] == "completed"
        # Verify the POST body included the address
        call_body = client.post.call_args[1].get("body") or client.post.call_args[0][1]
        assert "physicalAddress" in call_body

    def test_execute_raises_on_failure(self):
        plan = CreateCustomerPlan()
        client = MagicMock()
        client.post.return_value = {
            "success": False,
            "status_code": 500,
            "error": "server error",
        }
        with pytest.raises(RuntimeError, match="Failed to create customer"):
            plan.execute(
                client,
                {"name": "Test AS"},
                start_time=time.time(),
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_executor.py::TestCreateCustomerPlan -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create `execution_plans/create_customer.py`**

```python
"""Execution plan: Create Customer (Tier 1)."""
from execution_plans._base import ExecutionPlan
from execution_plans._registry import register


@register
class CreateCustomerPlan(ExecutionPlan):
    task_type = "create_customer"
    description = "Create a customer with all provided fields"

    def execute(self, client, params, start_time):
        self._check_timeout(start_time)

        body = {"name": params["name"]}

        if params.get("org_number"):
            body["organizationNumber"] = params["org_number"]
        if params.get("email"):
            body["email"] = params["email"]
        if params.get("phone"):
            body["phoneNumber"] = params["phone"]

        if params.get("address"):
            addr = params["address"]
            body["physicalAddress"] = {
                "addressLine1": addr.get("street"),
                "postalCode": addr.get("postal_code"),
                "city": addr.get("city"),
                "country": {"id": 162},  # Norway
            }

        result = client.post("/customer", body=body)
        if not result["success"]:
            raise RuntimeError(
                f"Failed to create customer: "
                f"status={result.get('status_code')}, error={result.get('error')}"
            )

        return self._make_result(api_calls=1, api_errors=0)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_executor.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add execution_plans/create_customer.py tests/test_executor.py
git commit -m "feat: add create_customer execution plan with tests"
```

---

### Task 5: Deterministic Executor

**Files:**
- Create: `deterministic_executor.py`

- [ ] **Step 1: Create `deterministic_executor.py`**

```python
"""Deterministic executor — classify, extract params, execute plan.

Tries to handle the request deterministically. Returns result dict on success,
or None to signal that the caller should fall back to the Claude agentic loop.
"""
import json
import logging
import re
import time

from tripletex_api import TripletexClient
from execution_plans._classifier import classify_task
from execution_plans._registry import PLANS
from observability import traceable

logger = logging.getLogger(__name__)

# Import all plan modules to trigger @register decorators
import execution_plans.create_customer  # noqa: F401
# Add imports here as plans are implemented:
# import execution_plans.create_invoice  # noqa: F401
# import execution_plans.run_salary  # noqa: F401
# ... etc

# ---------------------------------------------------------------------------
# Extraction schemas — defines what fields to pull from the prompt per task type.
# These are populated as optimal sequences are researched.
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMAS: dict[str, dict] = {
    "create_customer": {
        "name": "string (customer name)",
        "org_number": "string (organization number)",
        "email": "string or null",
        "phone": "string or null",
        "address": {
            "street": "string (street address)",
            "postal_code": "string",
            "city": "string",
        },
    },
    # Add schemas here as optimal sequences are researched
}


def extract_params(prompt: str, task_type: str) -> dict | None:
    """Extract task parameters from the prompt using Gemini Flash.

    Returns a dict of extracted params, or None if extraction fails.
    """
    schema = EXTRACTION_SCHEMAS.get(task_type)
    if not schema:
        logger.warning(f"No extraction schema for task_type='{task_type}'")
        return None

    extraction_prompt = (
        f"Extract parameters from this accounting task prompt.\n"
        f"Task type: {task_type}\n"
        f"Expected fields: {json.dumps(schema)}\n\n"
        f"Prompt: {prompt}\n\n"
        f"Return ONLY a valid JSON object with the extracted fields. No explanation."
    )

    try:
        from agent import _get_genai_client
        from google.genai import types

        client = _get_genai_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Content(role="user", parts=[
                types.Part.from_text(text=extraction_prompt)
            ])],
            config=types.GenerateContentConfig(temperature=0.0),
        )

        text = (response.text or "").strip()
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"JSON parse failed for '{task_type}' extraction")
        return None
    except Exception as e:
        logger.warning(f"Param extraction error for '{task_type}': {e}")
        return None


class DeterministicExecutor:
    """Tries deterministic execution for known task types.

    Usage:
        executor = DeterministicExecutor(base_url, session_token)
        result = executor.try_execute(prompt, files)
        if result is None:
            # Fall back to Claude agent
    """

    def __init__(self, base_url: str, session_token: str):
        self.client = TripletexClient(base_url, session_token)

    @traceable(name="deterministic_execute")
    def try_execute(self, prompt: str, files: list) -> dict | None:
        """Try deterministic execution.

        Returns result dict on success, or None to trigger fallback.
        """
        start_time = time.time()

        # 1. OCR if files present
        ocr_text = ""
        if files:
            try:
                from file_handler import process_files
                from agent import gemini_ocr

                file_contents = process_files(files)
                ocr_text = gemini_ocr(file_contents)
            except Exception as e:
                logger.warning(f"OCR failed in deterministic executor: {e}")

        full_prompt = f"{prompt}\n\n{ocr_text}" if ocr_text else prompt

        # 2. Classify (keyword — instant, no LLM)
        task_type = classify_task(full_prompt)
        if task_type is None:
            logger.info("Deterministic: no classifier match, falling back")
            return None

        # 3. Check if we have an execution plan
        plan = PLANS.get(task_type)
        if plan is None:
            logger.info(f"Deterministic: no plan for '{task_type}', falling back")
            return None

        logger.info(f"Deterministic: matched '{task_type}'")

        # 4. Extract parameters (single Gemini Flash call)
        params = extract_params(full_prompt, task_type)
        if params is None:
            logger.warning(
                f"Deterministic: param extraction failed for '{task_type}', falling back"
            )
            return None

        # 5. Execute plan
        logger.info(
            f"Deterministic: executing '{task_type}' with "
            f"params={json.dumps(params, ensure_ascii=False)[:200]}"
        )
        try:
            result = plan.execute(self.client, params, start_time)
            result["time_ms"] = int((time.time() - start_time) * 1000)
            logger.info(
                f"Deterministic: '{task_type}' completed in {result['time_ms']}ms, "
                f"{result['api_calls']} calls, {result['api_errors']} errors"
            )
            return result
        except TimeoutError:
            logger.warning(f"Deterministic: '{task_type}' timed out, falling back")
            return None
        except Exception as e:
            logger.warning(
                f"Deterministic: '{task_type}' failed ({e}), falling back"
            )
            return None
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `python -c "from deterministic_executor import DeterministicExecutor; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add deterministic_executor.py
git commit -m "feat: add deterministic executor with classify + extract + execute pipeline"
```

---

### Task 6: Integrate into main.py

**Files:**
- Modify: `main.py:112-152` (the `solve` endpoint)

- [ ] **Step 1: Modify `main.py` — move bank pre-config and add deterministic path**

In `main.py`, replace the `solve` function (lines 112-152) with:

```python
@app.post("/")
@app.post("/solve")
async def solve(request: Request):
    if API_KEY:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()

    # Handle both payload formats (official + competitor-observed)
    prompt = body.get("prompt") or body.get("task_prompt", "")
    files = body.get("files") or body.get("attached_files", [])
    creds = body.get("tripletex_credentials") or {}
    base_url = creds.get("base_url") or body.get("tripletex_base_url", "")
    session_token = creds.get("session_token") or body.get("session_token", "")

    logger.info(f"Task received. Prompt: {prompt}")
    logger.info(f"Files: {len(files)}, Base URL: {base_url}")

    # Correlation ID — links GCS request log to LangSmith trace
    task_id = uuid.uuid4().hex[:12]
    logger.info(f"task_id={task_id}")

    # Bank pre-config runs before BOTH execution paths
    _preconfigure_bank_account(base_url, session_token)

    result = None

    # Priority path: deterministic execution
    try:
        from deterministic_executor import DeterministicExecutor
        executor = DeterministicExecutor(base_url, session_token)
        result = executor.try_execute(prompt, files)
        if result:
            logger.info(f"Deterministic executor succeeded: task_id={task_id}")
    except Exception as e:
        logger.warning(f"Deterministic executor error: {e}")
        result = None

    # Fallback: full Claude agentic loop
    if result is None:
        try:
            metadata = {
                "task_id": task_id,
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:8],
                "prompt_preview": prompt[:80],
                "file_count": len(files),
            }
            result = _handle_task(prompt, files, base_url, session_token, metadata=metadata)
            logger.info(f"Agent: {result}")
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)

    # Save full request+result to GCS (synchronous — Cloud Run freezes CPU after response)
    _save_request_to_gcs(body, result, task_id=task_id)

    return JSONResponse({"status": "completed"})
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import main; print('OK')"`
Expected: `OK` (or import warnings that are non-fatal)

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All existing tests still pass

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: integrate deterministic executor into main.py with Claude fallback"
```

---

### Task 7: Verification Script

**Files:**
- Create: `scripts/verify_plans.py`

- [ ] **Step 1: Create `scripts/verify_plans.py`**

```python
#!/usr/bin/env python3
"""Verify execution plans against the Tripletex sandbox.

For each implemented plan:
1. Loads a test fixture from real-requests/logs/ or tests/competition_tasks/
2. Runs the keyword classifier
3. Runs Gemini param extraction
4. Executes the plan against the sandbox
5. Reports success/failure

Usage:
    source .env && export TRIPLETEX_SESSION_TOKEN
    python scripts/verify_plans.py                      # all plans
    python scripts/verify_plans.py --task create_customer  # single plan
"""
import argparse
import json
import logging
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from deterministic_executor import DeterministicExecutor, extract_params
from execution_plans._classifier import classify_task
from execution_plans._registry import PLANS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SANDBOX_BASE_URL = os.getenv("TRIPLETEX_BASE_URL", "https://kkpqfuj-amager.tripletex.dev/v2")
SANDBOX_TOKEN = os.getenv("TRIPLETEX_SESSION_TOKEN", "")

# Test prompts for each task type (simple, English)
TEST_PROMPTS = {
    "create_customer": (
        "Create the customer VerifyTest AS with organization number 999888777. "
        "The address is Testveien 1, 0001 Oslo. Email: verify@test.no"
    ),
    # Add test prompts for each task type as plans are implemented
}


def verify_plan(task_type: str, prompt: str | None = None) -> bool:
    """Verify a single execution plan. Returns True on success."""
    prompt = prompt or TEST_PROMPTS.get(task_type)
    if not prompt:
        logger.warning(f"  No test prompt for '{task_type}', skipping")
        return False

    # Step 1: Classify
    classified = classify_task(prompt)
    if classified != task_type:
        logger.error(f"  Classifier returned '{classified}', expected '{task_type}'")
        return False
    logger.info(f"  Classifier: OK ({task_type})")

    # Step 2: Extract params
    params = extract_params(prompt, task_type)
    if params is None:
        logger.error(f"  Param extraction failed")
        return False
    logger.info(f"  Params: {json.dumps(params, ensure_ascii=False)[:200]}")

    # Step 3: Execute against sandbox
    if not SANDBOX_TOKEN:
        logger.warning("  No TRIPLETEX_SESSION_TOKEN set, skipping sandbox execution")
        return True  # classifier + extraction verified

    executor = DeterministicExecutor(SANDBOX_BASE_URL, SANDBOX_TOKEN)
    plan = PLANS.get(task_type)
    if plan is None:
        logger.error(f"  No plan registered for '{task_type}'")
        return False

    try:
        start = time.time()
        result = plan.execute(executor.client, params, start)
        elapsed = time.time() - start
        logger.info(
            f"  Executed: {result['api_calls']} calls, "
            f"{result['api_errors']} errors, {elapsed:.1f}s"
        )
        return True
    except Exception as e:
        logger.error(f"  Execution failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verify execution plans against sandbox")
    parser.add_argument("--task", help="Verify single task type")
    parser.add_argument("--list", action="store_true", help="List registered plans")
    args = parser.parse_args()

    if args.list:
        for task_type in sorted(PLANS.keys()):
            has_prompt = "+" if task_type in TEST_PROMPTS else "-"
            print(f"  [{has_prompt}] {task_type}: {PLANS[task_type].description}")
        return

    task_types = [args.task] if args.task else sorted(PLANS.keys())
    results = {}

    for task_type in task_types:
        if task_type not in PLANS:
            logger.error(f"Unknown task type: {task_type}")
            results[task_type] = False
            continue

        logger.info(f"\nVerifying: {task_type}")
        results[task_type] = verify_plan(task_type)

    # Summary
    print(f"\n{'='*60}")
    print(f"Results: {sum(results.values())}/{len(results)} passed")
    for task_type, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {task_type}")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script runs**

Run: `python scripts/verify_plans.py --list`
Expected: Shows registered plans (at least `create_customer`)

- [ ] **Step 3: Commit**

```bash
git add scripts/verify_plans.py
git commit -m "feat: add plan verification script for sandbox testing"
```

---

## What Comes Next (after comp submission)

The comp container (`accounting-agent-comp`) already logs every request + result to
`gs://ai-nm26osl-1799-competition-logs`. After submitting to the evaluator we get both
the request payloads AND the agent's performance per task (success/fail, API calls, errors).

1. **Run download script** — `python scripts/download_captures.py` populates `real-requests/logs/`
   (pulls from competition-logs bucket which has both request and result data)
2. **Analysis session** — Claude Code reads all requests + results, groups by task type,
   notes which tasks succeeded/failed and why, writes `real-requests/analysis-plan.md`
3. **Parallel research** — one agent per task type tests against sandbox, writes
   `real-requests/optimal-sequence/<task_type>.md`
4. **Build plans** — convert each optimal sequence into an `execution_plans/<task_type>.py`,
   add extraction schema to `deterministic_executor.py`
5. **Verify & deploy** — run `scripts/verify_plans.py`, smoke test, deploy

Each of these is a separate planning/execution session that depends on the captured data.
