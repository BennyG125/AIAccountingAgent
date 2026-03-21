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

Five phases:

1. **Capture** — Deploy minimal container to intercept ALL evaluator requests (especially Tier 3)
2. **Download & Organize** — Deterministic script stores each request + files in `real-requests/logs/`
3. **Analyze & Plan** — Claude Code reads all requests, groups by task type, creates analysis plan. Then parallel research agents test each task type against the sandbox
4. **Build Plans** — Convert each optimal sequence into a hardcoded execution plan
5. **Integrate** — Wire up: classify → extract → execute → fallback

---

## Phase 1: Capture Container

### Scope

We already have fixtures and captures for Tier 1 and 2 tasks. The capture container's primary
purpose is to **intercept Tier 3 requests** when they open Saturday morning. We also capture
Tier 1+2 to get complete, untruncated prompts (existing fixtures have truncated prompts).

### What

A minimal FastAPI app that:
1. Receives POST requests from the evaluator
2. Saves the full request body to GCS (bucket: `ai-nm26osl-1799-capture-logs`)
3. Returns `{"status": "completed"}` immediately

### Why minimal

No agent imports, no Tripletex client, no Claude/Gemini dependencies. Just `fastapi`,
`google-cloud-storage`, and `uvicorn`. This ensures:
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
2. Submit once per tier
3. Download captured payloads via Phase 2

---

## Phase 2: Download & Organize

### Directory structure

```
real-requests/
  logs/                              # Raw captured requests, each in its own folder
    001_Create_the_customer_Brightsto/
      request.json                   # Full evaluator payload (prompt, credentials)
    002_Crea_una_factura_para_el_clie/
      request.json
      file_0.pdf                     # Attached files decoded from base64 (if any)
      file_1.csv
    003_Opprett_og_send_en_faktura_ti/
      request.json
    ...
  analysis-plan.md                   # Claude Code's grouping + research plan (Phase 3)
  optimal-sequence/                  # One optimal sequence doc per task type (Phase 3 output)
    create_customer.md
    create_invoice.md
    run_salary.md
    ...
```

### Download script

**New file: `scripts/download_captures.py`**

Deterministic script that:
1. Downloads all captured payloads from GCS (capture bucket + existing dev/comp buckets)
2. Creates a numbered folder per request with a descriptive name
3. Saves `request.json` (the full evaluator payload)
4. Decodes and saves any attached files (base64 → actual files on disk)

```python
"""Download captured competition requests from GCS into real-requests/logs/."""
import argparse
import base64
import json
import os
import re
from google.cloud import storage

DEFAULT_BUCKETS = [
    "ai-nm26osl-1799-capture-logs",
    "ai-nm26osl-1799-dev-logs",
    "ai-nm26osl-1799-competition-logs",
]
OUTPUT_DIR = "real-requests/logs"

def _safe_name(text: str, max_len: int = 40) -> str:
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', text).strip('_')
    return safe[:max_len]

def download(buckets: list[str] | None = None):
    buckets = buckets or DEFAULT_BUCKETS
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    idx = 1
    for bucket_name in buckets:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        prefixes = ["captured/", "requests/"]  # capture container + existing logging

        for prefix in prefixes:
            blobs = sorted(bucket.list_blobs(prefix=prefix), key=lambda b: b.name)
            for blob in blobs:
                try:
                    raw = json.loads(blob.download_as_text())
                except Exception:
                    continue

                # Handle both formats: direct payload or wrapped {request: payload}
                data = raw.get("request", raw) if "request" in raw else raw
                prompt = data.get("prompt") or data.get("task_prompt") or "unknown"
                prompt_preview = _safe_name(prompt)

                folder = os.path.join(OUTPUT_DIR, f"{idx:03d}_{prompt_preview}")
                os.makedirs(folder, exist_ok=True)

                # Save full raw payload as request.json
                with open(os.path.join(folder, "request.json"), "w") as f:
                    json.dump(raw, f, indent=2, ensure_ascii=False)

                # Decode and save attached files
                files = data.get("files") or data.get("attached_files") or []
                for file_idx, file_entry in enumerate(files):
                    filename = file_entry.get("filename", f"file_{file_idx}")
                    content_b64 = (file_entry.get("content")
                                   or file_entry.get("data")
                                   or file_entry.get("content_base64", ""))
                    if content_b64:
                        try:
                            file_data = base64.b64decode(content_b64)
                            with open(os.path.join(folder, filename), "wb") as f:
                                f.write(file_data)
                        except Exception as e:
                            print(f"  Warning: could not decode {filename}: {e}")

                print(f"[{bucket_name}] {folder}")
                idx += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", action="append", help="GCS bucket(s) to download from")
    args = parser.parse_args()
    download(args.bucket)
```

---

## Phase 3: Analyze & Plan Optimal Sequences

### The problem

`real-requests/logs/` now contains many requests. Some are the same task type in different
languages (e.g., create_invoice in NO, ES, PT). Others may be unique Tier 3 tasks we've
never seen. We need a structured approach.

### Step 1: Claude Code creates the analysis plan

Claude Code reads every `request.json` in `real-requests/logs/` and produces
`real-requests/analysis-plan.md`:

1. **Groups requests by task type** — identifies which requests are the same kind of operation
   (e.g., "create customer" in EN, NO, ES, PT are all `create_customer`)
2. **Notes cross-language patterns** — what fields appear in all languages, what's language-specific
3. **Identifies unknowns** — Tier 3 tasks that don't match any existing recipe
4. **Maps each group to its existing recipe** (if any)
5. **Produces a research assignment per task type** with:
   - Which request folders belong to this group
   - What the existing recipe says
   - What questions the research agent should answer
   - What to test against the sandbox

Example structure for `real-requests/analysis-plan.md`:

```markdown
# Request Analysis Plan

## Task Type Groups

### Group 1: create_customer (Tier 1, 1x multiplier)
- **Requests:** 001_Create_the_customer, 007_Opprett_kunden, 019_Opprett_kunden
- **Languages:** EN, NO
- **Has files:** No
- **Existing recipe:** recipes/01_create_customer.md
- **Complexity:** Low — single POST /customer
- **Research focus:** Verify all fields the evaluator checks. Current recipe is minimal.

### Group 2: create_invoice (Tier 2, 2x multiplier)
- **Requests:** 002_Crea_una_factura, 012_Opprett_og_send, 015_Opprett_en_faktura, 017_Crie_uma_fatura
- **Languages:** ES, NO, PT
- **Has files:** No
- **Existing recipe:** recipes/06_create_invoice.md
- **Complexity:** High — customer + N products + order + invoice + optional send
- **Known issues:** vatType errors, product number conflicts, slow (avg 127s)
- **Research focus:** Find the minimum-call sequence. Test vatType handling.

### Group N: [new_tier3_task] (Tier 3, 3x multiplier)
- **Requests:** 030_..., 031_...
- **Languages:** ...
- **Has files:** Yes (PDF)
- **Existing recipe:** None
- **Complexity:** Unknown
- **Research focus:** Full discovery — what API endpoints, what fields, what sequence.
```

### Step 2: Parallel research agents

For each task type group in the analysis plan, spawn a research agent. Each agent receives:

1. **All `request.json` files** for that task type group
2. **The existing recipe** (if one exists in `recipes/`)
3. **The API cheat sheet** (`api_knowledge/cheat_sheet.py`)
4. **Tripletex sandbox credentials** for live API testing

Each agent's job:

1. **Study all prompt variations** across languages — understand what fields appear, what varies
2. **Read the existing recipe** — understand current approach and known gotchas
3. **Test against the Tripletex sandbox** — make real API calls to discover:
   - The exact minimal set of API calls needed
   - Which fields are required vs optional vs harmful
   - What error responses look like and how to recover
   - Exact field names the API expects (e.g., `priceExcludingVatCurrency` not `price`)
4. **Write the optimal sequence** to `real-requests/optimal-sequence/<task_type>.md`

### Optimal sequence document format

Each document in `real-requests/optimal-sequence/` follows this structure:

```markdown
# Optimal Sequence: create_invoice

## Summary
- API calls: 5 (1 customer + N products + 1 order + 1 invoice + 1 send)
- Expected time: < 5s
- Error rate: 0 (all failure modes handled)

## Parameters to Extract from Prompt
| Field | Type | Required | Example (NO) | Example (ES) | Example (PT) |
|-------|------|----------|-------------|-------------|-------------|
| customer_name | string | yes | "Lysgard AS" | "Dorada SL" | "Oceano Lda" |
| customer_org | string | yes | "883939832" | "929580206" | "825975497" |
| products | array | yes | [{name, price}] | [{name, price}] | [{name, price}] |
| send | boolean | no | "send"→true | "enviar"→true | "enviar"→true |

## API Sequence

### Step 1: Find or create customer
GET /customer?organizationNumber={customer_org}&fields=id,name
- If found: use existing ID
- If not found: POST /customer {name, organizationNumber}

### Step 2: Create products (for each product)
POST /product {name: "...", priceExcludingVatCurrency: N}
- NEVER include: vatType, number
- On 422 "Produktnummeret X er i bruk": GET /product?name=X → use existing ID

### Step 3: Create order
POST /order {customer: {id}, orderDate, deliveryDate, orderLines: [...]}

### Step 4: Create invoice
POST /invoice {invoiceDate, invoiceDueDate, orders: [{id}]}

### Step 5: Send (if requested)
PUT /invoice/{id}/:send {sendType: "EMAIL"}

## Error Recovery
| Error | Cause | Recovery |
|-------|-------|----------|
| 422 vatType | Included vatType | Retry without vatType |
| 422 Produktnummeret | Product number exists | GET by name, use existing |
| 404 customer | Customer not found | Create first |

## Sandbox Verification
- Tested: YES
- Test date: 2026-03-22
- All steps verified against kkpqfuj-amager.tripletex.dev
```

### Research checklist per task type

Each research agent must answer ALL of these:

- [ ] What is the minimum number of API calls?
- [ ] What are the exact required fields per API call (verified against sandbox)?
- [ ] What fields should NEVER be included (cause errors)?
- [ ] What order do calls need to happen in (dependencies)?
- [ ] If a call fails with 422, what field should be removed and retried?
- [ ] If an entity already exists, how to find it (which search endpoint + params)?
- [ ] What does the prompt look like across all observed languages for this task?
- [ ] What parameters need to be extracted from the prompt?
- [ ] Has the full sequence been verified against the sandbox end-to-end?

### Why parallel research

- Each task type is independent — agents don't need to coordinate
- Sandbox can handle concurrent API calls (separate entities don't conflict)
- Each agent can be thorough without blocking others

---

## Phase 4: Build Execution Plans

Convert each `real-requests/optimal-sequence/<task_type>.md` into a Python execution plan.
Each plan is a direct translation of the optimal sequence document — no guesswork, every
step verified against the sandbox.

### Execution plan structure

```
execution_plans/
  __init__.py
  _base.py            # Base class, shared utilities, timeout
  _registry.py        # Task type → plan mapping
  _classifier.py      # Keyword classifier
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
  # ... plus any new Tier 3 task types discovered
```

**Every task type gets a plan.** No scoping down.

### Core components

#### 4a. Task Classifier (keyword-based, no LLM)

Classification uses keyword matching — task types have very distinct trigger patterns across
all 6 languages. Instant, no failure mode. More specific patterns (e.g., `register_supplier_invoice`)
are checked before general ones (e.g., `create_supplier`) due to list ordering.

**File: `execution_plans/_classifier.py`**

```python
import re

TASK_PATTERNS = [
    # Most specific patterns first
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
    """Classify task type from prompt using keyword matching.
    Returns task_type string or None if no match.
    """
    prompt_lower = prompt.lower()
    for task_type, patterns in TASK_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return task_type
    return None
```

#### 4b. Parameter Extractor (single Gemini Flash call)

Only parameter extraction uses an LLM. Uses existing Gemini client with `gemini-2.0-flash`.

```python
# In deterministic_executor.py
import json, re

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
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
```

#### 4c. Execution Plan Base

```python
# execution_plans/_base.py
import logging
import time

logger = logging.getLogger(__name__)
EXECUTOR_TIMEOUT = 60  # seconds — leaves ~200s for Claude fallback

class ExecutionPlan:
    """Base class for deterministic execution plans."""
    task_type: str = ""
    description: str = ""

    def execute(self, client, params: dict, start_time: float) -> dict:
        """Execute the plan. Returns result dict or raises on failure."""
        raise NotImplementedError

    def _check_timeout(self, start_time: float):
        if time.time() - start_time > EXECUTOR_TIMEOUT:
            raise TimeoutError(f"Timed out after {EXECUTOR_TIMEOUT}s")

    def _safe_post(self, client, path, body, retry_without=None):
        """POST with optional field removal on 422."""
        result = client.post(path, body=body)
        if not result["success"] and retry_without and result.get("status_code") == 422:
            cleaned = {k: v for k, v in body.items() if k not in retry_without}
            result = client.post(path, cleaned)
        return result

    def _find_or_create(self, client, search_path, search_params, create_path, create_body):
        """Search for entity; create if not found. Returns entity ID."""
        result = client.get(search_path, params=search_params)
        if result["success"]:
            values = result["body"].get("values", [])
            if values:
                return values[0]["id"]
        result = client.post(create_path, body=create_body)
        if result["success"]:
            return result["body"]["value"]["id"]
        raise RuntimeError(f"Failed to find or create at {create_path}: {result}")

    def _make_result(self, api_calls: int, api_errors: int, time_ms: int = 0,
                     error_details: list | None = None) -> dict:
        """Build result dict matching run_agent() output shape."""
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

#### 4d. Plan Registry

```python
# execution_plans/_registry.py
# Imports are added as plans are implemented
PLANS = {}

def register(plan_class):
    """Decorator to register an execution plan."""
    instance = plan_class()
    PLANS[instance.task_type] = instance
    return plan_class
```

Each plan file uses the decorator:
```python
from execution_plans._registry import register
from execution_plans._base import ExecutionPlan

@register
class CreateCustomerPlan(ExecutionPlan):
    task_type = "create_customer"
    # ... execute() method based on optimal-sequence/create_customer.md
```

#### 4e. Main Executor

```python
# deterministic_executor.py
import json, logging, time
from file_handler import process_files
from agent import gemini_ocr
from tripletex_api import TripletexClient
from execution_plans._classifier import classify_task
from execution_plans._registry import PLANS
from observability import traceable

logger = logging.getLogger(__name__)

# Import all plan modules to trigger @register decorators
import execution_plans.create_customer
import execution_plans.create_invoice
# ... all plan modules ...

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
            logger.info(f"No plan for '{task_type}', falling back to agent")
            return None

        logger.info(f"Deterministic: {task_type}")

        # 4. Extract parameters (single Gemini Flash call)
        params = extract_params(full_prompt, task_type)
        if params is None:
            logger.warning(f"Param extraction failed for '{task_type}', falling back")
            return None

        # 5. Execute plan
        logger.info(f"Executing {task_type} with params={json.dumps(params, ensure_ascii=False)[:200]}")
        try:
            result = plan.execute(self.client, params, start_time)
            result["time_ms"] = int((time.time() - start_time) * 1000)
            return result
        except TimeoutError:
            logger.warning(f"Plan timed out for '{task_type}', falling back")
            return None
        except Exception as e:
            logger.warning(f"Plan failed for '{task_type}': {e}, falling back")
            return None
```

---

## Phase 5: Integrate & Deploy

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

### Error handling & fallback

1. **Entity already exists** → `_find_or_create()` searches first
2. **vatType invalid (422)** → `_safe_post()` retries without the field
3. **Product number in use** → Search by name, use existing ID
4. **403 proxy expired** → RuntimeError propagates → fallback to agent
5. **Timeout (>60s)** → `_check_timeout()` raises → fallback (still ~200s for Claude)
6. **Any unhandled error** → Caught in `try_execute()` → returns None → fallback

If the deterministic executor partially succeeds then fails, the Claude fallback runs the
full task. The existing recipes guide Claude to search before creating, so duplicates are
avoided.

### Observability

Both paths use LangSmith tracing. The deterministic path includes `"executor": "deterministic"`
in the result for easy filtering.

---

## Testing Strategy

### Local verification

**New file: `scripts/verify_plans.py`**

For each task type:
1. Load a real request from `real-requests/logs/`
2. Run the keyword classifier → verify correct task_type
3. Run Gemini param extraction → verify correct params
4. Execute plan against Tripletex sandbox → verify entity created

```bash
source .env && export TRIPLETEX_SESSION_TOKEN
python scripts/verify_plans.py                      # all plans
python scripts/verify_plans.py --task create_invoice # single plan
```

### Smoke test integration

Extend `smoke_test.py` with `--mode deterministic`:

```bash
python smoke_test.py --mode deterministic --tier 1
python smoke_test.py --mode deterministic --tier 2
```

---

## File Summary

| File | Action | Purpose |
|------|--------|---------|
| `capture_main.py` | Create | Minimal capture container |
| `Dockerfile.capture` | Create | Dockerfile for capture container |
| `scripts/download_captures.py` | Create | Download + organize requests from GCS |
| `scripts/verify_plans.py` | Create | Verify all plans against sandbox |
| `real-requests/logs/` | Generated | Raw requests, each in numbered folder with files |
| `real-requests/analysis-plan.md` | Generated | Claude Code's grouping + research assignments |
| `real-requests/optimal-sequence/*.md` | Generated | One optimal sequence per task type |
| `deterministic_executor.py` | Create | Classifier + extractor + plan orchestration |
| `execution_plans/__init__.py` | Create | Package init |
| `execution_plans/_base.py` | Create | Base class with timeout, safe_post, find_or_create |
| `execution_plans/_classifier.py` | Create | Keyword-based task classifier |
| `execution_plans/_registry.py` | Create | Task type → plan registry |
| `execution_plans/<task>.py` | Create | One per task type (ALL types) |
| `main.py` | Modify | Add deterministic path before Claude fallback |
| `smoke_test.py` | Modify | Add --mode deterministic option |

---

## Execution Order

### Step 1 — Capture Container + Framework

1. Create and deploy capture container
2. Implement executor framework: `_base.py`, `_classifier.py`, `_registry.py`, `deterministic_executor.py`
3. Implement + test 1 simple plan (create_customer) to validate the full pipeline
4. Integrate into `main.py` with Claude fallback

### Step 2 — Capture Requests

1. Point evaluator at capture container
2. Submit once per tier (including Tier 3 when it opens)
3. Run `scripts/download_captures.py` to pull everything into `real-requests/logs/`

### Step 3 — Analyze & Create Research Plan

1. Claude Code reads all `request.json` files in `real-requests/logs/`
2. Groups by task type across languages
3. Produces `real-requests/analysis-plan.md` with research assignments

### Step 4 — Parallel Research

1. Spawn one research agent per task type group
2. Each agent tests against the Tripletex sandbox
3. Each agent writes its optimal sequence to `real-requests/optimal-sequence/<task_type>.md`
4. Review all optimal sequences for completeness

### Step 5 — Build ALL Execution Plans

1. Convert each optimal sequence into a Python execution plan
2. Every task type gets a plan — no exceptions
3. Each plan tested against sandbox

### Step 6 — Verification

1. Run `scripts/verify_plans.py` against the sandbox
2. Run smoke tests in deterministic mode
3. Fix any failures

### Step 7 — Deploy

1. Deploy to dev container, full smoke test
2. Deploy to comp container
3. Submit scored runs
