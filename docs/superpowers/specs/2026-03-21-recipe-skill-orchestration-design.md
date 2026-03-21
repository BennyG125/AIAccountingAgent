# Recipe Skill Orchestration — Design Spec

> Date: 2026-03-21
> Status: Draft
> Skills: agent-debugger (done), recipe-builder (new), recipe-validator (new)

## Problem

The AI Accounting Agent's recipes live inline in `prompts.py` (~300 lines, 20 recipes). Improving them requires manually reading logs, guessing at API sequences, editing prompts.py, redeploying, and hoping it works. There's no systematic workflow for:
- Analyzing why a recipe failed
- Discovering the optimal API call sequence through direct testing
- Verifying the deployed agent actually follows the recipe
- Iterating quickly on recipe improvements

## Solution

Three complementary skills that form a debugging-and-improvement pipeline:

| Skill | Purpose | Already exists? |
|-------|---------|-----------------|
| **agent-debugger** | Investigate what happened with a request (GCS + LangSmith) | Yes |
| **recipe-builder** | Explore Tripletex API, find optimal call sequence, write recipe file | New |
| **recipe-validator** | Deploy agent, send test request, verify agent follows recipe | New |

## Architecture

```
agent-debugger  →  recipe-builder  →  recipe-validator
"what happened?"   "what should happen?"  "did the agent do it?"
```

Typical flows:
- **Reactive (fix failure):** agent-debugger → recipe-builder → recipe-validator
- **Proactive (new task type):** recipe-builder → recipe-validator
- **Quick re-check after tweak:** recipe-validator alone
- **Investigation only:** agent-debugger alone

Each skill is self-contained. They don't invoke each other programmatically — each skill's output naturally feeds into the next skill's input (task_id, diagnosis, recipe file path).

## Containers and Environments

| Container | Purpose | LangSmith Project | GCS Bucket |
|-----------|---------|-------------------|------------|
| `ai-accounting-agent-det` | Dev/testing — ALL testing happens here | `ai-accounting-agent-dev` | `ai-nm26osl-1799-dev-logs` |
| `accounting-agent-comp` | Competition only — deploy after validation | `ai-accounting-agent-comp` | `ai-nm26osl-1799-competition-logs` |

Rules:
- **NEVER** send test requests to `accounting-agent-comp`
- All recipe-validator testing targets `ai-accounting-agent-det`
- Promote to `accounting-agent-comp` only after validation passes and user explicitly approves

## Recipe File Structure

### Directory layout

```
recipes/
├── 01_create_customer.md
├── 02_create_employee.md
├── 03_create_supplier.md
├── 04_create_departments.md
├── 05_create_product.md
├── 06_create_invoice.md
├── 07_register_payment.md
├── 08_create_project.md
├── 09_fixed_price_project.md
├── 10_run_salary.md
├── 11_register_supplier_invoice.md
├── 12_create_order.md
├── 13_custom_dimension_voucher.md
├── 14_reverse_payment_voucher.md
├── 15_credit_note.md
├── 16_register_hours.md
├── 17_travel_expense.md
├── 18_bank_reconciliation.md
├── 19_asset_registration.md
├── 20_year_end_corrections.md
```

### Recipe file format

```markdown
# Create Invoice (Tier 2)

## Task Pattern
Prompts that ask to create and optionally send an invoice for a customer
with one or more product lines.
Languages observed: NO, PT, ES

## File Handling (only for file-based tasks)
<If this task type involves attached files: what files the evaluator sends,
what data OCR/text extraction provides, how extracted values map to API fields.>

## Optimal API Sequence
1. POST /customer {name, organizationNumber} → customer_id                    [1 call]
2. POST /product {name, priceExcludingVatCurrency} × N products → product_ids [N calls]
3. POST /order {customer, orderDate, deliveryDate, orderLines: [...]} → order_id [1 call]
4. POST /invoice {invoiceDate, invoiceDueDate, orders: [{id}]} → invoice_id   [1 call]
5. (If "send"): PUT /invoice/{id}/:send {sendType: "EMAIL"}                   [1 call]

## Field Reference
<!-- Exact JSON bodies with all field names, types, required vs optional -->
POST /customer:
{
  "name": "<from prompt>",
  "organizationNumber": "<from prompt>",
  ...
}

POST /product:
{
  "name": "<from prompt>",
  "priceExcludingVatCurrency": <number>
}
NOTE: Do NOT include `number` (auto-assigned) or `vatType` (returns error).

## Known Gotchas
- Do NOT include vatType on products — returns "Ugyldig mva-kode"
- orderLines MUST be embedded in the order POST body — saves separate calls
- Do NOT make verification GETs after successful creates

## Expected Performance
- Calls: 4 + N products (+ 1 if send)
- Errors: 0
- Time: ~30s
```

### prompts.py integration

```python
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def _load_recipes() -> str:
    recipes_dir = Path(__file__).parent / "recipes"
    parts = []
    for f in sorted(recipes_dir.glob("*.md")):
        parts.append(f.read_text())
    if not parts:
        logger.error("No recipe files found in recipes/ — agent will have no recipes!")
        raise FileNotFoundError(f"No .md files in {recipes_dir}. Recipes are required.")
    logger.info(f"Loaded {len(parts)} recipes from {recipes_dir}")
    return "\n\n".join(parts)
```

Recipes are loaded on each call to `build_system_prompt()` and concatenated into the existing "Recipes for Known Task Types" section. The inline recipes in prompts.py are removed and replaced by `{_load_recipes()}`. Loading per-request (not at import time) supports local iteration without restart — recipe file changes are picked up immediately.

### Naming convention

Recipe filenames use **2-digit zero-padded** prefixes: `01_`, `02_`, ... `20_`. New recipes continue this pattern (`21_`, `22_`, etc.). This ensures `sorted()` produces the correct order. Never use unpadded numbers like `3_` — always `03_`.

### Recipe language

Recipes are written for the competition environment. They describe API behavior factually ("this endpoint returns 403, use X instead") without referencing "sandbox" or environment-specific framing. Workarounds are stated as facts about the API, not about a particular environment.

## File-Based Tasks

Some competition tasks include attached files (PDFs, images, CSVs). The agent processes these before the agentic loop:

```
Request with files → process_files() → gemini_ocr() → Claude agentic loop
```

**Processing pipeline (file_handler.py + agent.py):**
1. `process_files()`: decodes base64, extracts PDF text via pymupdf, renders PDF pages as PNG images
2. `gemini_ocr()`: sends images to Gemini for OCR text extraction
3. Both extracted text and OCR text are included in Claude's user message

**Impact on each skill:**

| Skill | File handling responsibility |
|-------|----------------------------|
| **agent-debugger** | Decode files from GCS to inspect originals. Check `gemini_ocr` LangSmith span for OCR quality. Identify if failures are caused by bad OCR vs bad recipe. |
| **recipe-builder** | For file-based task types: document what OCR extracts, how extracted values map to API fields. Include a "File Handling" section in the recipe. Test API calls using manually-provided data (curl works the same — the recipe-builder doesn't need to run OCR). |
| **recipe-validator** | Include base64-encoded test files in the validation payload. Verify `gemini_ocr` span ran and produced usable output. Check that the agent used OCR data correctly in API calls. |

**No file-based tasks have appeared in Tier 1-2 competition yet** (all 37 observed fixtures have `files: []`). However, Tier 3 (opens Saturday morning) is likely to include file-based tasks (bank reconciliation from CSV/PDF, supplier invoices with scanned attachments).

## Skill 1: recipe-builder

### Trigger
"build a recipe for X", "optimize the invoice recipe", "figure out how to handle this task type", pasting a competition prompt with "make this work", or any request to create/improve a recipe.

### Workflow

**Step 1: Understand the task**
- Reactive: Read the GCS log or competition fixture to get the exact prompt and what went wrong. If a task_id is provided, use agent-debugger techniques to pull the full trace.
- Proactive: Read the user's description or sample prompt. Identify which Tripletex entities and endpoints are likely involved.

**Step 2: Check existing recipe**
- Look in `recipes/` for an existing file for this task type
- If one exists, this is an optimization — compare the existing recipe against what actually happened

**Step 3: Explore the Tripletex API with curl**

Authentication:
```bash
source .env
export TRIPLETEX_BASE_URL  # from .env or environment
export TRIPLETEX_SESSION_TOKEN  # from .env or environment

curl -s -u "0:$TRIPLETEX_SESSION_TOKEN" "$TRIPLETEX_BASE_URL/<endpoint>" | python3 -m json.tool
```

API discovery approach:
1. Start with `api_knowledge/cheat_sheet.py` as a known baseline
2. Go beyond the cheat sheet — the full Tripletex API is much larger. Discover new endpoints by:
   - Trying logical paths based on the task (e.g., `/bank`, `/bank/reconciliation`)
   - Using `?fields=*` on any discovered endpoint to reveal its full structure
   - Checking Tripletex's public API documentation if available
3. Work through the task incrementally:
   - GET calls to understand entity structures
   - Build prerequisite entities (customer, department, etc.)
   - Execute the target action
   - Capture exact responses — note which fields are required vs optional
4. Track: number of calls, any errors, which fields worked

**Step 4: Optimize**
- Can any calls be eliminated? (e.g., embed sub-entities)
- Can parallel-safe calls be reordered for clarity?
- Verify zero 4xx errors in the final sequence
- Re-run the full optimized sequence from scratch to confirm it works clean

**Step 5: Clean up sandbox**
- DELETE created entities in reverse order (include `version` param from GET)
- Some entities cannot be deleted after state transitions (e.g., invoices after payment, posted vouchers). If DELETE returns 4xx, note the entity and move on — the sandbox resets between competition submissions anyway.
- Verify sandbox is clean enough for the next test

**Step 6: Write the recipe**
- Save to `recipes/<NN>_<task_type>.md` using the format from the "Recipe file format" section
- If this is a new task type, assign the next available 2-digit number (e.g., `21_`)
- If updating an existing recipe, preserve the existing number
- The recipe MUST include all required sections: Task Pattern, Optimal API Sequence, Field Reference, Known Gotchas, Expected Performance
- Enumerate ALL fields in Field Reference — no `...` placeholders
- Note any newly discovered endpoints for addition to `api_knowledge/cheat_sheet.py`

## Skill 2: recipe-validator

### Trigger
"test the recipe", "verify the agent works", "deploy and check", "does the agent follow the recipe", or after completing a recipe-builder session.

### Workflow

**Step 1: Deploy to dev container**
- Run the deploy command from CLAUDE.md for `ai-accounting-agent-det`
- Load `.env` first (required for LangSmith API keys)
- Wait for deployment to complete

**Step 2: Send test request to dev container**
- Read credentials from `.env`: `TRIPLETEX_BASE_URL` and `TRIPLETEX_SESSION_TOKEN`
- Build a competition-format payload:
  ```json
  {
    "prompt": "<the task prompt>",
    "files": [],
    "tripletex_credentials": {
      "base_url": "$TRIPLETEX_BASE_URL",
      "session_token": "$TRIPLETEX_SESSION_TOKEN"
    }
  }
  ```
- POST to the root path `/` (NOT `/solve`) to match evaluator behavior:
  ```bash
  curl -s -X POST https://ai-accounting-agent-det-590159115697.europe-north1.run.app/ \
    -H "Content-Type: application/json" \
    -d @payload.json
  ```
- Note: the response is just `{"status": "completed"}` — the task_id is NOT in the response

**Step 3: Find the trace**
The task_id is not returned in the HTTP response. To find it:
1. List the most recent GCS dev log entry (it was just created):
   ```bash
   gsutil ls gs://ai-nm26osl-1799-dev-logs/requests/ | tail -1
   ```
2. Extract task_id from the filename: `requests/{timestamp}_{task_id}_{prompt}.json`
3. Find the corresponding LangSmith trace:
   ```bash
   langsmith run list --project ai-accounting-agent-dev --metadata task_id=<task_id> --format json
   ```

**Step 4: Verify agent behavior via LangSmith**
- List all runs in the trace with full I/O
- Compare against the recipe's expected sequence:
  - **Call order**: Did the agent follow the recipe's steps in order?
  - **Call count**: Match expected number? Any extra/unnecessary calls?
  - **Errors**: Any 4xx responses? Which ones?
  - **Thinking**: Did the agent's reasoning reference the recipe?

**Step 5: Verify state via direct curl**
- Make GET calls against the sandbox to verify entities were created correctly
- Check field values match what the prompt asked for (customer name, amounts, etc.)

**Step 6: Report**
Present a comparison:
```
                    Expected (recipe)    Actual (agent)
API calls:          4                    6
Errors:             0                    1 (422 on POST /order)
Sequence match:     —                    Steps 1-2 ✓, step 3 deviated
State:              —                    Customer ✓, Products ✓, Invoice ✗
```

**Pass/fail criteria:**
- **Pass**: Zero 4xx errors AND call count matches expected (± 1 tolerance for edge cases) AND final sandbox state is correct
- **Marginal**: Zero errors but extra calls (agent deviated but got the right result)
- **Fail**: Any 4xx error, or final state is wrong

If the agent deviated:
- **Agent found a better path** → update the recipe (back to recipe-builder)
- **Agent didn't follow the recipe** → recipe wording needs to be clearer, adjust the recipe's language
- **Agent hit an error the recipe didn't anticipate** → add to Known Gotchas

**Step 7: Clean up sandbox**
- Delete test entities in reverse order (include `version` param)
- Some entities can't be deleted after state transitions — note and move on
- Reset for next validation run

**Step 8: Promote (optional, only on explicit user request)**
- Deploy to `accounting-agent-comp` using the competition deploy command
- NEVER do this automatically — always ask the user first

## Implementation Plan

### Phase 1a: Structural migration (recipes to files)
- Create `recipes/` directory
- Extract existing 20 recipes from `prompts.py` **verbatim** into individual .md files (no content changes)
- Add `_load_recipes()` to `prompts.py` with the error check for empty directory
- Replace inline recipes with `{_load_recipes()}`
- Deploy to dev and run smoke tests — verify zero regression before any content changes

### Phase 1b: Recipe language cleanup
- Rewrite recipe language: remove "sandbox" framing, state behaviors as facts
- Deploy to dev and run smoke tests again — isolate any regression to the language change, not the file migration

### Phase 2: recipe-builder skill
- Create `~/.claude/skills/recipe-builder/SKILL.md`
- Include: Tripletex auth pattern, curl format, API discovery guidance, recipe file format with required sections checklist, cleanup procedures
- Reference `api_knowledge/cheat_sheet.py` as starting point (not limit)

### Phase 3: recipe-validator skill
- Create `~/.claude/skills/recipe-validator/SKILL.md`
- Include: deploy commands, competition payload format (credentials from `.env`), task_id discovery via GCS, LangSmith verification, pass/fail criteria, comparison reporting, container distinction (dev vs comp)
- Reference agent-debugger techniques for LangSmith/GCS querying

### Phase 4: Test the skills
- Use recipe-builder to optimize the weakest recipe (create_invoice — 75% success, 4.2 avg errors)
- Use recipe-validator to verify the improvement
- Iterate until the recipe passes validation cleanly
