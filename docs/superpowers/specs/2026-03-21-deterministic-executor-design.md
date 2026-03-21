# Deterministic Executor — Capture, Analyze, Execute

> **Goal:** Maximize competition score by executing known task types deterministically
> (keyword classification + 1 LLM call for param extraction + hardcoded API sequences),
> falling back to the existing Claude agentic loop for unknown tasks.

## Context

- **Competition deadline:** 2026-03-22 at 15:00 CET
- **Submissions:** 180/day, Tier 3 opens Saturday morning
- **Current agent:** Claude Opus 4.6 agentic loop, 20 iterations max, 270s timeout
- **Current recipes:** 21 markdown files guiding Claude's reasoning
- **Observed task types:** 12 in competition, ~20 total including test-only types
- **Current success rate:** ~96% on known tasks, but slow (avg 60s) and API-inefficient
- **Existing data:** 43 task fixtures in `tests/competition_tasks/`, 6 real competition captures, ground truth doc

## Principle

**Diligence over efficiency.** Every task type gets a thoroughly researched, tested, and verified
execution plan. The compound effect of bulletproof plans across all task types and tiers is the
real competitive advantage. We do not cut corners or skip task types.

## Strategy

Four phases:

1. **Capture** — Deploy minimal container to intercept ALL evaluator requests (especially Tier 3)
2. **Parallel Analysis** — For each captured task type, spawn a research agent that discovers the optimal API sequence by testing against the sandbox
3. **Build Plans** — Convert each research output into a hardcoded execution plan
4. **Integrate** — Wire up: classify → extract → execute → fallback

---

## Phase 1: Capture Container

### Scope

We already have fixtures and captures for Tier 1 and 2 tasks. The capture container's primary purpose is to **intercept Tier 3 requests** when they open Saturday morning. We use 1 submission to capture, not 3.

### What

A minimal FastAPI app that:
1. Receives POST requests from the evaluator
2. Saves the full request body to GCS (bucket: `ai-nm26osl-1799-capture-logs`)
3. Returns `{"status": "completed"}` immediately

### Why minimal

No agent imports, no Tripletex client, no Claude/Gemini dependencies. Just `fastapi`, `google-cloud-storage`, and `uvicorn`. This ensures:
- Fast cold start (< 2s)
- Zero chance of timeout or crash
- Every request captured reliably

### Implementation

**New file: `capture_main.py`** (~30 lines)

```python
import json, logging, os
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
app = FastAPI()
logger = logging.getLogger(__name__)
BUCKET = os.getenv("REQUEST_LOG_BUCKET", "ai-nm26osl-1799-capture-logs")

@app.post("/")
@app.post("/solve")
async def capture(request: Request):
    body = await request.json()
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(BUCKET)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")
        prompt = (body.get("prompt") or "")[:40]
        safe = "".join(c if c.isalnum() or c in " -_" else "" for c in prompt).strip().replace(" ", "_")
        blob = bucket.blob(f"captured/{ts}_{safe}.json")
        blob.upload_from_string(json.dumps(body, ensure_ascii=False, default=str))
        logger.info(f"Captured to gs://{BUCKET}/{blob.name}")
    except Exception as e:
        logger.error(f"Capture failed: {e}")
    return JSONResponse({"status": "completed"})

@app.get("/health")
def health():
    return {"status": "ok"}
```

**New file: `Dockerfile.capture`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn google-cloud-storage
COPY capture_main.py .
CMD ["uvicorn", "capture_main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Deploy

```bash
# Create GCS bucket for captures (one-time, may already exist)
gsutil mb -l europe-north1 gs://ai-nm26osl-1799-capture-logs 2>/dev/null || true

# Deploy capture container
gcloud run deploy accounting-agent-capture \
  --source . \
  --dockerfile Dockerfile.capture \
  --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="REQUEST_LOG_BUCKET=ai-nm26osl-1799-capture-logs" \
  --allow-unauthenticated \
  --quiet
```

### Usage

1. Point evaluator at the capture container URL
2. Submit once when Tier 3 opens Saturday morning
3. Download captured payloads

### Cost

- 1 submission = 1 of 180 daily quota
- Score: 0 on this submission (acceptable — investing to discover Tier 3 task types)

---

## Phase 2: Download & Parallel Analysis

### Download script

**New file: `scripts/download_captures.py`**

Downloads all captured payloads from GCS into `tests/captured_tasks/`.

```python
"""Download captured competition requests from GCS."""
import json, os
from google.cloud import storage

BUCKET = "ai-nm26osl-1799-capture-logs"
OUTPUT_DIR = "tests/captured_tasks"

def download():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    for blob in bucket.list_blobs(prefix="captured/"):
        data = json.loads(blob.download_as_text())
        prompt = (data.get("prompt") or "unknown")[:60]
        safe = "".join(c if c.isalnum() or c in " -_" else "" for c in prompt).strip().replace(" ", "_")
        path = os.path.join(OUTPUT_DIR, f"{safe}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved: {path}")

if __name__ == "__main__":
    download()
```

### Parallel research agents

Once captured tasks are downloaded, we **spawn one research agent per task type in parallel**.
Each agent receives:

1. The captured prompt(s) for that task type
2. The existing recipe (if one exists)
3. Access to the Tripletex sandbox (base_url + session_token)
4. The API cheat sheet (`api_knowledge/cheat_sheet.py`)

Each agent's job:

1. **Parse the prompt** — identify all required fields the evaluator expects
2. **Read the existing recipe** — understand the current approach and known gotchas
3. **Test against the sandbox** — make real API calls to discover:
   - The exact minimal set of API calls needed
   - Which fields are required vs optional
   - What error responses look like and how to recover
   - Field name quirks (e.g., `priceExcludingVatCurrency` not `price`)
4. **Document the optimal sequence** — write a research report with:
   - Exact API calls in order (method, path, body, params)
   - Required vs optional fields per call
   - Error recovery strategies (tested, not guessed)
   - The extraction schema (what to pull from the prompt)

**Output:** One research report per task type saved to `execution_plans/research/<task_type>.md`

```
execution_plans/research/
  create_customer.md
  create_employee.md
  create_supplier.md
  create_product.md
  create_departments.md
  create_invoice.md
  create_order.md
  create_project.md
  fixed_price_project.md
  register_payment.md
  register_supplier_invoice.md
  run_salary.md
  custom_dimension.md
  reverse_payment.md
  credit_note.md
  register_hours.md
  travel_expense.md
  bank_reconciliation.md
  employee_onboarding.md
  asset_registration.md
  year_end_corrections.md
  # ... plus any new Tier 3 task types discovered via capture
```

### Why parallel

- Each task type is independent — agents don't need to coordinate
- Sandbox can handle concurrent API calls (separate entities don't conflict)
- Running 20 agents in parallel instead of sequentially saves massive time
- Each agent can be thorough (5-10 min of real API testing) without blocking others

### Analysis checklist per task type

Each research agent must answer:

- [ ] What is the minimum number of API calls?
- [ ] What are the exact required fields per API call?
- [ ] What fields should NEVER be included (cause errors)?
- [ ] What order do calls need to happen in (dependencies)?
- [ ] If a call fails with 422, what field should be removed and retried?
- [ ] If an entity already exists, how to find it (which search endpoint + params)?
- [ ] What does the prompt look like across all 6 languages for this task?
- [ ] What parameters need to be extracted from the prompt?

### Phase 2 output: execution plan files

After research, each task type gets an execution plan:

```
execution_plans/
  __init__.py
  _base.py            # Base class, shared utilities, timeout
  _registry.py        # Task type → plan mapping
  _classifier.py      # Keyword classifier + Gemini param extractor
  research/           # Research reports from parallel agents
  create_customer.py
  create_employee.py
  create_supplier.py
  create_product.py
  create_departments.py
  create_invoice.py
  create_order.py
  create_project.py
  fixed_price_project.py
  register_payment.py
  register_supplier_invoice.py
  run_salary.py
  custom_dimension.py
  reverse_payment.py
  credit_note.py
  register_hours.py
  travel_expense.py
  bank_reconciliation.py
  employee_onboarding.py
  asset_registration.py
  year_end_corrections.py
  # ... plus any new Tier 3 task types
```

**Every task type gets a plan.** No scoping down. The Claude fallback exists as a safety net,
not as an excuse to skip task types.

---

## Phase 3: Deterministic Executor

### Architecture

```
POST / → main.py
  ├── _save_request_to_gcs()               (unchanged)
  ├── _preconfigure_bank_account()          ← moved BEFORE executor
  ├── DeterministicExecutor.try_execute()   ← NEW, priority path
  │     ├── 1. OCR if files present (reuse existing gemini_ocr)
  │     ├── 2. Keyword classification → task_type
  │     ├── 3. Single Gemini Flash call → extract params as JSON
  │     ├── 4. Look up execution plan for task_type
  │     ├── 5. Execute API calls with error handling + 60s timeout
  │     └── Returns result dict OR None (triggers fallback)
  └── run_agent()                           ← EXISTING, fallback
```

### Integration point in main.py

```python
@app.post("/")
async def solve(request: Request):
    # ... existing request parsing (prompt, files, creds, base_url, session_token) ...
    # ... task_id generation ...

    # Bank pre-config runs before BOTH paths
    _preconfigure_bank_account(base_url, session_token)

    result = None
    try:
        from deterministic_executor import DeterministicExecutor
        executor = DeterministicExecutor(base_url, session_token)
        result = executor.try_execute(prompt, files)
        if result:
            logger.info(f"Deterministic executor succeeded: {result}")
    except Exception as e:
        logger.warning(f"Deterministic executor failed, falling back to agent: {e}")
        result = None

    if result is None:
        # Fallback: full Claude agentic loop (existing behavior)
        metadata = {
            "task_id": task_id,
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:8],
            "prompt_preview": prompt[:80],
            "file_count": len(files),
        }
        result = _handle_task(prompt, files, base_url, session_token, metadata=metadata)

    _save_request_to_gcs(body, result, task_id=task_id)
    return JSONResponse({"status": "completed"})
```

### Core components

#### 3a. Task Classifier (keyword-based, no LLM)

Classification uses keyword matching — task types have very distinct trigger patterns across all 6 languages. This avoids an extra LLM call, is instant, and has no failure mode.

**Implementation: `execution_plans/_classifier.py`**

```python
import re

# Keyword patterns per task type (multilingual)
TASK_PATTERNS = [
    ("create_invoice", [
        r"faktura", r"invoice", r"factura", r"fatura", r"rechnung", r"facture",
    ]),
    ("run_salary", [
        r"l[øo]nn", r"salary", r"salario", r"salário", r"gehalt", r"salaire",
    ]),
    ("register_payment", [
        r"betal", r"payment", r"pago", r"pagamento", r"zahlung", r"paiement",
    ]),
    ("register_supplier_invoice", [
        r"leverandør.*faktura", r"supplier.*invoice", r"proveedor.*factura",
        r"fornecedor.*fatura", r"lieferant.*rechnung", r"fournisseur.*facture",
    ]),
    ("create_order", [
        r"bestilling", r"order", r"pedido", r"encomenda", r"bestellung", r"commande",
    ]),
    ("fixed_price_project", [
        r"fast\s*pris", r"fixed\s*price", r"precio\s*fijo", r"preço\s*fixo",
        r"festpreis", r"prix\s*fixe",
    ]),
    ("custom_dimension", [
        r"dimensjon", r"dimension", r"dimensión", r"dimensão",
    ]),
    ("credit_note", [
        r"kreditnota", r"credit\s*note", r"nota\s*de\s*crédito", r"gutschrift",
        r"note\s*de\s*crédit",
    ]),
    ("reverse_payment", [
        r"reverser.*betaling", r"reverse.*payment", r"revertir.*pago",
        r"reverter.*pagamento", r"stornierung", r"annuler.*paiement",
    ]),
    ("register_hours", [
        r"timer", r"hours", r"horas", r"stunden", r"heures", r"timeføring",
    ]),
    ("travel_expense", [
        r"reise", r"travel.*expense", r"gastos.*viaje", r"despesas.*viagem",
        r"reisekosten", r"frais.*voyage", r"reiserekning", r"reiseregning",
    ]),
    ("bank_reconciliation", [
        r"bank.*avstemming", r"bank.*reconcil", r"concilia.*banc",
        r"rapproch.*bancaire",
    ]),
    ("employee_onboarding", [
        r"arbeidskontrakt", r"employment.*contract", r"contrat.*travail",
        r"contrato.*trabajo",
    ]),
    ("create_project", [
        r"prosjekt", r"project", r"proyecto", r"projeto", r"projekt", r"projet",
    ]),
    ("create_departments", [
        r"avdeling", r"department", r"departamento", r"abteilung", r"département",
    ]),
    ("create_employee", [
        r"ansatt", r"employee", r"empleado", r"funcionário", r"mitarbeiter",
        r"employé",
    ]),
    ("create_customer", [
        r"kunde", r"customer", r"cliente", r"client", r"kund",
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
    """Classify task type from prompt using keyword matching.

    Returns task_type string or None if no match.
    More specific patterns (e.g., register_supplier_invoice) are checked
    before general ones (e.g., create_supplier) due to list ordering.
    """
    prompt_lower = prompt.lower()
    for task_type, patterns in TASK_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return task_type
    return None
```

#### 3b. Parameter Extractor (single Gemini Flash call)

Only the parameter extraction uses an LLM call. Uses the existing Gemini client with `gemini-2.0-flash` for speed.

```python
# In deterministic_executor.py
import json
import re

def extract_params(prompt: str, task_type: str) -> dict | None:
    """Extract task parameters using Gemini Flash. Returns dict or None."""
    schema = EXTRACTION_SCHEMAS.get(task_type)
    if not schema:
        return None

    extraction_prompt = f"""Extract parameters from this accounting task prompt.
Task type: {task_type}
Expected fields: {json.dumps(schema)}

Prompt: {prompt}

Return ONLY a valid JSON object with the extracted fields. No explanation."""

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
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
```

#### 3c. Execution Plan Base

```python
# execution_plans/_base.py
import logging
import time

logger = logging.getLogger(__name__)

EXECUTOR_TIMEOUT = 60  # seconds — leave room for Claude fallback within 270s total

class ExecutionPlan:
    """Base class for deterministic execution plans."""
    task_type: str = ""
    description: str = ""

    def execute(self, client, params: dict, start_time: float) -> dict:
        """Execute the plan. Returns result dict or raises on unrecoverable failure.

        Args:
            client: TripletexClient instance
            params: Extracted parameters from the prompt
            start_time: time.time() when execution started (for timeout checking)
        """
        raise NotImplementedError

    def _check_timeout(self, start_time: float):
        """Raise TimeoutError if we've exceeded EXECUTOR_TIMEOUT."""
        if time.time() - start_time > EXECUTOR_TIMEOUT:
            raise TimeoutError(f"Execution plan timed out after {EXECUTOR_TIMEOUT}s")

    def _safe_post(self, client, path, body, retry_without=None):
        """POST with optional field removal on 422 failure."""
        result = client.post(path, body=body)
        if not result["success"] and retry_without and result.get("status_code") == 422:
            cleaned_body = {k: v for k, v in body.items() if k not in retry_without}
            result = client.post(path, cleaned_body)
        return result

    def _find_or_create(self, client, search_path, search_params, create_path, create_body):
        """Search for entity; create if not found. Returns entity ID."""
        result = client.get(search_path, params=search_params)
        if result["success"]:
            values = result["body"].get("values", [])
            if values:
                return values[0]["id"]
        # Not found — create
        result = client.post(create_path, body=create_body)
        if result["success"]:
            return result["body"]["value"]["id"]
        raise RuntimeError(f"Failed to find or create at {create_path}: {result}")

    def _make_result(self, api_calls: int, api_errors: int, time_ms: int,
                     error_details: list | None = None) -> dict:
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

#### 3d. Example: Create Customer Plan

```python
# execution_plans/create_customer.py
from execution_plans._base import ExecutionPlan

class CreateCustomerPlan(ExecutionPlan):
    task_type = "create_customer"
    description = "Create a customer with all provided fields"

    def execute(self, client, params, start_time):
        body = {
            "name": params["name"],
        }
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
        errors = []
        if not result["success"]:
            errors.append({"path": "/customer", "status": result.get("status_code"),
                          "error": result.get("error", "")})
            raise RuntimeError(f"Failed to create customer: {result}")

        return self._make_result(api_calls=1, api_errors=0, time_ms=0)
```

#### 3e. Example: Create Invoice Plan (highest-impact Tier 2 task)

```python
# execution_plans/create_invoice.py
from datetime import date, timedelta
from execution_plans._base import ExecutionPlan

class CreateInvoicePlan(ExecutionPlan):
    task_type = "create_invoice"
    description = "Create invoice with products, order, and optional send"

    def execute(self, client, params, start_time):
        today = date.today().isoformat()
        due_date = (date.today() + timedelta(days=30)).isoformat()
        api_calls = 0
        api_errors = 0

        # 1. Find or create customer
        customer_id = self._find_or_create(
            client,
            "/customer", {"organizationNumber": params["customer_org"]},
            "/customer", {"name": params["customer_name"],
                         "organizationNumber": params["customer_org"]},
        )
        api_calls += 1
        self._check_timeout(start_time)

        # 2. Create products (NEVER include vatType or number)
        order_lines = []
        for product in params.get("products", []):
            self._check_timeout(start_time)
            result = self._safe_post(client, "/product", {
                "name": product["name"],
                "priceExcludingVatCurrency": product["price"],
            }, retry_without=["vatType", "number"])
            api_calls += 1

            if result["success"]:
                product_id = result["body"]["value"]["id"]
            else:
                api_errors += 1
                # Product may already exist — search by name
                search = client.get("/product", params={"name": product["name"]})
                api_calls += 1
                values = search["body"].get("values", [])
                if values:
                    product_id = values[0]["id"]
                else:
                    raise RuntimeError(f"Cannot create or find product: {product['name']}")

            order_lines.append({
                "product": {"id": product_id},
                "count": product.get("quantity", 1),
                "unitPriceExcludingVatCurrency": product["price"],
            })

        # 3. Create order
        self._check_timeout(start_time)
        order_result = client.post("/order", body={
            "customer": {"id": customer_id},
            "orderDate": today,
            "deliveryDate": today,
            "orderLines": order_lines,
        })
        api_calls += 1
        if not order_result["success"]:
            api_errors += 1
            raise RuntimeError(f"Failed to create order: {order_result}")
        order_id = order_result["body"]["value"]["id"]

        # 4. Create invoice from order
        self._check_timeout(start_time)
        invoice_result = client.post("/invoice", body={
            "invoiceDate": today,
            "invoiceDueDate": due_date,
            "orders": [{"id": order_id}],
        })
        api_calls += 1
        if not invoice_result["success"]:
            api_errors += 1
            raise RuntimeError(f"Failed to create invoice: {invoice_result}")
        invoice_id = invoice_result["body"]["value"]["id"]

        # 5. Send if requested
        if params.get("send", False):
            self._check_timeout(start_time)
            send_result = client.put(f"/invoice/{invoice_id}/:send",
                                     body={"sendType": "EMAIL"})
            api_calls += 1
            if not send_result["success"]:
                api_errors += 1

        return self._make_result(api_calls=api_calls, api_errors=api_errors, time_ms=0)
```

#### 3f. Plan Registry

```python
# execution_plans/_registry.py
from execution_plans.create_customer import CreateCustomerPlan
from execution_plans.create_invoice import CreateInvoicePlan
# ... import all implemented plans ...

_ALL_PLANS = [
    CreateCustomerPlan(),
    CreateInvoicePlan(),
    # ... all implemented plans ...
]

PLANS = {plan.task_type: plan for plan in _ALL_PLANS}
```

#### 3g. Main Executor

```python
# deterministic_executor.py
import json
import logging
import time

from file_handler import process_files
from agent import gemini_ocr
from tripletex_api import TripletexClient
from execution_plans._classifier import classify_task
from execution_plans._registry import PLANS
from observability import traceable, trace_child

logger = logging.getLogger(__name__)

# Extraction schemas per task type
EXTRACTION_SCHEMAS = {
    "create_customer": {
        "name": "string", "org_number": "string", "email": "string|null",
        "phone": "string|null",
        "address": {"street": "string", "postal_code": "string", "city": "string"},
    },
    "create_invoice": {
        "customer_name": "string", "customer_org": "string",
        "products": [{"name": "string", "price": "number", "quantity": "number"}],
        "send": "boolean",
    },
    # ... schemas for all implemented task types ...
}


class DeterministicExecutor:
    def __init__(self, base_url: str, session_token: str):
        self.client = TripletexClient(base_url, session_token)

    @traceable(name="deterministic_execute")
    def try_execute(self, prompt: str, files: list) -> dict | None:
        """Try deterministic execution. Returns result dict or None for fallback."""
        start_time = time.time()

        # 1. OCR if files present
        ocr_text = ""
        if files:
            file_contents = process_files(files)
            ocr_text = gemini_ocr(file_contents)

        full_prompt = f"{prompt}\n\n{ocr_text}" if ocr_text else prompt

        # 2. Classify (keyword — instant, no LLM)
        task_type = classify_task(full_prompt)
        if task_type is None:
            logger.info("Classifier: no match, falling back to agent")
            return None

        # 3. Check if we have an execution plan
        plan = PLANS.get(task_type)
        if plan is None:
            logger.info(f"No execution plan for '{task_type}', falling back to agent")
            return None

        logger.info(f"Deterministic: {task_type} — extracting params")

        # 4. Extract parameters (single Gemini Flash call)
        params = extract_params(full_prompt, task_type)
        if params is None:
            logger.warning(f"Param extraction failed for '{task_type}', falling back")
            return None

        # 5. Execute plan
        logger.info(f"Deterministic: executing {task_type} with params={params}")
        try:
            result = plan.execute(self.client, params, start_time)
            result["time_ms"] = int((time.time() - start_time) * 1000)
            return result
        except TimeoutError:
            logger.warning(f"Deterministic plan timed out for '{task_type}', falling back")
            return None
        except Exception as e:
            logger.warning(f"Deterministic plan failed for '{task_type}': {e}, falling back")
            return None
```

### Extraction schemas per task type

| Task Type | Extracted Fields |
|-----------|-----------------|
| create_customer | name, org_number, email, phone, address{street, postal_code, city} |
| create_employee | name, date_of_birth, email, start_date, department, occupation_code, national_id |
| create_supplier | name, org_number, email, phone |
| create_product | name, price |
| create_departments | departments[]{name} |
| create_invoice | customer_name, customer_org, products[]{name, price, quantity}, send (bool) |
| create_order | customer_name, customer_org, products[]{name, price, quantity}, delivery_date |
| create_project | name, customer_name, customer_org, manager_name, start_date, end_date |
| fixed_price_project | project_name, customer_name, customer_org, fixed_price, start_date, end_date |
| register_payment | customer_name, customer_org, invoice_description, amount, payment_date |
| register_supplier_invoice | supplier_name, supplier_org, invoice_number, amount, date, due_date, account |
| run_salary | employee_email, base_salary, additions[]{type, amount}, month, year |
| custom_dimension | dimension_name, values[], voucher_details |

### Error handling per plan

Each plan includes specific error recovery:

1. **Entity already exists** → `_find_or_create()` searches first, then creates
2. **vatType invalid (422)** → `_safe_post()` retries without vatType field
3. **Product number in use** → Search by name, use existing product ID
4. **403 proxy expired** → RuntimeError propagates → fallback to agent
5. **Timeout (>60s)** → `_check_timeout()` raises → fallback to agent (still has ~200s for Claude)
6. **Any unhandled error** → Caught in `try_execute()` → returns None → fallback

### Partial execution and fallback

If the deterministic executor partially completes (e.g., creates a customer but fails on the invoice), the Claude fallback runs the entire task from scratch. The existing recipes guide Claude to search for existing entities before creating, so duplicate creation is avoided. This is acceptable because:
- The fallback agent already handles "entity exists" gracefully
- Partial state is rare (most failures happen on the first API call)
- The alternative (passing partial state) adds complexity for minimal gain

### Observability

Both paths (deterministic and fallback) use LangSmith tracing. The deterministic path adds `"executor": "deterministic"` to the result, making it easy to filter and compare in LangSmith.

---

## Testing Strategy

### Local verification

**New file: `scripts/verify_plans.py`**

For each implemented task type:
1. Load a fixture from `tests/competition_tasks/`
2. Run the keyword classifier → verify correct task_type
3. Run Gemini param extraction → verify correct params
4. Execute plan against Tripletex sandbox → verify entity created

```bash
# Verify all plans against sandbox
source .env && export TRIPLETEX_SESSION_TOKEN
python scripts/verify_plans.py

# Verify single plan
python scripts/verify_plans.py --task create_invoice
```

### Smoke test integration

Extend `smoke_test.py` with `--mode deterministic` flag:

```bash
python smoke_test.py --mode deterministic --tier 1
python smoke_test.py --mode deterministic --tier 2
```

---

## File Summary

| File | Action | Purpose |
|------|--------|---------|
| `capture_main.py` | Create | Minimal capture container (~30 lines) |
| `Dockerfile.capture` | Create | Dockerfile for capture container |
| `scripts/download_captures.py` | Create | Download captured tasks from GCS |
| `scripts/verify_plans.py` | Create | Verify plans against sandbox |
| `deterministic_executor.py` | Create | Classifier + extractor + plan orchestration |
| `execution_plans/__init__.py` | Create | Package init |
| `execution_plans/_base.py` | Create | Base class with timeout, safe_post, find_or_create |
| `execution_plans/_classifier.py` | Create | Keyword-based task classifier |
| `execution_plans/_registry.py` | Create | Task type → plan mapping |
| `execution_plans/research/<task>.md` | Create | Research report per task type (from parallel agents) |
| `execution_plans/<task>.py` | Create | One per task type (ALL types, no scoping down) |
| `main.py` | Modify | Add deterministic path before Claude fallback, move bank pre-config |
| `smoke_test.py` | Modify | Add --mode deterministic option |

---

## Execution Order

### Step 1 — Framework + Capture Container

1. Deploy capture container
2. Implement the executor framework: `_base.py`, `_classifier.py`, `_registry.py`, `deterministic_executor.py`
3. Implement + test 1 simple plan (e.g., create_customer) to validate the full pipeline end-to-end
4. Integrate into `main.py` with Claude fallback

### Step 2 — Capture Tier 3

1. When Tier 3 opens: submit once via capture container
2. Download all captured payloads

### Step 3 — Parallel Research

1. Combine captured tasks with existing fixtures (`tests/competition_tasks/`)
2. Group by task type
3. Spawn parallel research agents — one per task type
4. Each agent tests against sandbox and produces a research report
5. Review research reports for completeness

### Step 4 — Build ALL Execution Plans

1. Convert each research report into a hardcoded Python execution plan
2. Every task type gets a plan — no exceptions
3. Each plan is tested against the sandbox before moving on

### Step 5 — Verification

1. Run `scripts/verify_plans.py` — verifies every plan against the sandbox
2. Run smoke tests in deterministic mode
3. Fix any failures

### Step 6 — Deploy

1. Deploy to dev container, run full smoke test
2. Deploy to comp container
3. Submit scored runs
