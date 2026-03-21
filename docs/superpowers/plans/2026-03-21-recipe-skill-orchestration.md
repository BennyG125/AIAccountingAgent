# Recipe Skill Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract recipes from prompts.py into modular files, then create recipe-builder and recipe-validator skills for systematic recipe development and testing.

**Architecture:** 20 recipe files in `recipes/` loaded by `prompts.py` at runtime. Two new Claude Code skills guide the workflow: recipe-builder (explore API, write recipes) and recipe-validator (deploy, test, verify via LangSmith).

**Tech Stack:** Python 3.13, FastAPI, Claude Code skills (SKILL.md), gsutil, langsmith CLI, curl

**Spec:** `docs/superpowers/specs/2026-03-21-recipe-skill-orchestration-design.md`

---

### Task 1: Create `_load_recipes()` with tests (TDD)

**Files:**
- Create: `tests/test_load_recipes.py`
- Create: `recipes/` directory (empty initially)
- Modify: `prompts.py` (add function only, don't wire up yet)

- [ ] **Step 1: Create recipes/ directory**

```bash
mkdir -p recipes
```

- [ ] **Step 2: Write failing tests for `_load_recipes()`**

```python
# tests/test_load_recipes.py
"""Tests for recipe file loading."""
import os
import tempfile
from pathlib import Path

import pytest


class TestLoadRecipes:
    def test_loads_md_files_sorted_by_name(self, tmp_path):
        """Recipes load in filename order."""
        (tmp_path / "02_b.md").write_text("# Recipe B\nContent B")
        (tmp_path / "01_a.md").write_text("# Recipe A\nContent A")

        from prompts import _load_recipes
        result = _load_recipes(recipes_dir=tmp_path)

        assert "# Recipe A" in result
        assert "# Recipe B" in result
        assert result.index("Recipe A") < result.index("Recipe B")

    def test_raises_on_empty_directory(self, tmp_path):
        """Must fail loudly if no recipe files found."""
        from prompts import _load_recipes
        with pytest.raises(FileNotFoundError, match="No .md files"):
            _load_recipes(recipes_dir=tmp_path)

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "01_a.md").write_text("# Recipe A")
        (tmp_path / "notes.txt").write_text("not a recipe")

        from prompts import _load_recipes
        result = _load_recipes(recipes_dir=tmp_path)

        assert "Recipe A" in result
        assert "not a recipe" not in result

    def test_replaces_today_placeholder(self, tmp_path):
        """Recipe files use {today} as a placeholder for the current date."""
        from datetime import date
        (tmp_path / "01_test.md").write_text('orderDate: "{today}"')

        from prompts import _load_recipes
        result = _load_recipes(recipes_dir=tmp_path)

        assert date.today().isoformat() in result
        assert "{today}" not in result

    def test_concatenates_with_separator(self, tmp_path):
        (tmp_path / "01_a.md").write_text("# A")
        (tmp_path / "02_b.md").write_text("# B")

        from prompts import _load_recipes
        result = _load_recipes(recipes_dir=tmp_path)

        assert "# A\n\n# B" in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_load_recipes.py -v`
Expected: FAIL — `_load_recipes` does not exist yet

- [ ] **Step 4: Implement `_load_recipes()` in prompts.py**

Add this function to `prompts.py` (above `build_system_prompt`, do NOT change `build_system_prompt` yet):

```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _load_recipes(recipes_dir: Path | None = None) -> str:
    """Load all recipe .md files from the recipes/ directory.

    Args:
        recipes_dir: Override directory for testing. Defaults to recipes/ next to this file.
    """
    if recipes_dir is None:
        recipes_dir = Path(__file__).parent / "recipes"

    parts = []
    for f in sorted(recipes_dir.glob("*.md")):
        parts.append(f.read_text())

    if not parts:
        logger.error(f"No recipe files found in {recipes_dir} — agent will have no recipes!")
        raise FileNotFoundError(f"No .md files in {recipes_dir}. Recipes are required.")

    logger.info(f"Loaded {len(parts)} recipes from {recipes_dir}")

    today = date.today().isoformat()
    combined = "\n\n".join(parts)
    return combined.replace("{today}", today)
```

Note: `date` is already imported at the top of prompts.py. Add `logging` and `Path` imports.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_load_recipes.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Run existing tests to verify no regression**

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: All existing tests still PASS (we haven't changed `build_system_prompt` yet)

- [ ] **Step 7: Commit**

```bash
git add recipes/ tests/test_load_recipes.py prompts.py
git commit -m "feat: add _load_recipes() for modular recipe files (TDD)"
```

---

### Task 2: Extract recipes from prompts.py into individual files

**Files:**
- Create: `scripts/extract_recipes.py`
- Create: `recipes/01_create_customer.md` through `recipes/20_year_end_corrections.md`

The recipes in prompts.py are inside an f-string, so `{{` represents literal `{` and `}}` represents literal `}`. The extraction script handles this conversion.

- [ ] **Step 1: Write the extraction script**

```python
# scripts/extract_recipes.py
"""Extract recipes from prompts.py into individual .md files.

Reads the f-string content, splits by recipe headings,
converts f-string escaping ({{ → {, }} → }) and writes
each recipe to recipes/<NN>_<name>.md.

The {today} placeholder is kept as-is — _load_recipes() handles it at runtime.
"""
import re
from pathlib import Path

# Recipe number → filename mapping
RECIPE_FILES = {
    1: "01_create_customer",
    2: "02_create_employee",
    3: "03_create_supplier",
    4: "04_create_departments",
    5: "05_create_product",
    6: "06_create_invoice",
    7: "07_register_payment",
    8: "08_create_project",
    9: "09_fixed_price_project",
    10: "10_run_salary",
    11: "11_register_supplier_invoice",
    12: "12_create_order",
    13: "13_custom_dimension_voucher",
    14: "14_reverse_payment_voucher",
    15: "15_credit_note",
    16: "16_register_hours",
    17: "17_travel_expense",
    18: "18_bank_reconciliation",
    19: "19_asset_registration",
    20: "20_year_end_corrections",
}

def unescape_fstring(text: str) -> str:
    """Convert f-string escaping to plain text.

    {{ → {  and  }} → }
    But preserve {today} as a literal placeholder.
    """
    # First, temporarily protect {today}
    text = text.replace("{today}", "___TODAY___")
    # Unescape doubled braces
    text = text.replace("{{", "{")
    text = text.replace("}}", "}")
    # Restore {today} placeholder
    text = text.replace("___TODAY___", "{today}")
    return text


def extract():
    project_root = Path(__file__).parent.parent
    prompts_file = project_root / "prompts.py"
    recipes_dir = project_root / "recipes"
    recipes_dir.mkdir(exist_ok=True)

    content = prompts_file.read_text()

    # Find the recipes section: starts at "## Recipes for Known Task Types"
    # and ends at "## Handling Unknown Tasks"
    recipes_start = content.index("## Recipes for Known Task Types")
    recipes_end = content.index("## Handling Unknown Tasks")
    recipes_section = content[recipes_start:recipes_end]

    # Split by ### headings (recipe numbers)
    # Pattern: ### N. Title or ### NN. Title
    parts = re.split(r'(?=^### \d+\.)', recipes_section, flags=re.MULTILINE)

    # First part is the section header — skip it
    # Also skip the "### Tier 3 Recipes (anticipated — opens Saturday)" line
    recipe_parts = []
    for part in parts[1:]:
        part = part.strip()
        if part and re.match(r'^### \d+\.', part):
            recipe_parts.append(part)

    print(f"Found {len(recipe_parts)} recipes")

    for part in recipe_parts:
        # Extract recipe number from "### N. Title"
        match = re.match(r'^### (\d+)\.\s+(.+?)$', part, re.MULTILINE)
        if not match:
            print(f"WARNING: Could not parse recipe heading: {part[:80]}")
            continue

        num = int(match.group(1))
        title = match.group(2).strip()

        if num not in RECIPE_FILES:
            print(f"WARNING: Unknown recipe number {num}: {title}")
            continue

        filename = RECIPE_FILES[num]
        # Convert ### heading to # heading for standalone file
        md_content = part.replace(f"### {num}.", f"#", 1)
        md_content = unescape_fstring(md_content)

        filepath = recipes_dir / f"{filename}.md"
        filepath.write_text(md_content.strip() + "\n")
        print(f"  Wrote {filepath.name} ({len(md_content)} chars)")

    # Handle the "Tier 3 Recipes" separator line — skip it, recipes 18-20 are extracted above


if __name__ == "__main__":
    extract()
```

- [ ] **Step 2: Run the extraction**

```bash
python scripts/extract_recipes.py
```

Expected: 20 files created in `recipes/`, one per recipe.

- [ ] **Step 3: Verify recipe files were created**

```bash
ls -la recipes/
```

Expected: 20 .md files, `01_create_customer.md` through `20_year_end_corrections.md`

- [ ] **Step 4: Spot-check a recipe file**

Read `recipes/06_create_invoice.md` and verify:
- Heading starts with `#` (single `#`, not `###`)
- Content has single `{` not doubled `{{`
- `{today}` placeholders are preserved as literal `{today}`
- Recipe number is preserved in the heading text

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_recipes.py recipes/
git commit -m "feat: extract 20 recipes from prompts.py into individual files"
```

---

### Task 3: Wire up prompts.py to use `_load_recipes()`

**Files:**
- Modify: `prompts.py:88-305` (replace inline recipes with `_load_recipes()` call)

- [ ] **Step 1: Update `build_system_prompt()` to use `_load_recipes()`**

In `prompts.py`, replace the entire section from `## Recipes for Known Task Types` (line 88) through `## Handling Unknown Tasks` (line 293, exclusive) with a call to `_load_recipes()`.

The f-string in `build_system_prompt()` should change from:

```python
## Recipes for Known Task Types

### 1. Create Customer (Tier 1)
...
### 20. Year-End / Ledger Corrections
...

## Handling Unknown Tasks
```

To:

```python
## Recipes for Known Task Types

{_load_recipes()}

## Handling Unknown Tasks
```

Important: Since `_load_recipes()` already handles `{today}` substitution, remove any remaining `{today}` references that were inside the recipes section. The `{today}` references in the non-recipe parts of the prompt (e.g., the Known Constants section) should remain as f-string interpolation.

- [ ] **Step 2: Run existing tests — verify zero regression**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: ALL tests PASS. The prompt content should be identical to before.

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: ALL tests PASS.

- [ ] **Step 3: Verify the full prompt is equivalent**

Quick sanity check — the built prompt should still contain all recipe keywords:

```python
python -c "
from prompts import build_system_prompt
p = build_system_prompt()
checks = ['POST /customer', 'orderLines', 'paymentTypeId', 'isFixedPrice',
          'grantEntitlementsByTemplate', 'POST /ledger/voucher', 'reconciliation']
for c in checks:
    assert c in p, f'MISSING: {c}'
print(f'All checks passed. Prompt length: {len(p)} chars')
"
```

- [ ] **Step 4: Remove the extraction script (no longer needed)**

```bash
rm scripts/extract_recipes.py
rmdir scripts 2>/dev/null  # Remove if empty
```

- [ ] **Step 5: Commit**

```bash
git add prompts.py
git rm scripts/extract_recipes.py 2>/dev/null
git commit -m "refactor: load recipes from files instead of inline in prompts.py"
```

- [ ] **Step 6: Deploy to dev and smoke test (spec Phase 1a gate)**

This is the critical regression gate: verify the structural migration didn't break anything in production before making content changes.

```bash
source .env
gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-dev,LANGSMITH_API_KEY=$LANGSMITH_API_KEY" \
  --quiet
```

After deploy completes, run a quick smoke test:
```bash
source .env && export TRIPLETEX_SESSION_TOKEN
python smoke_test.py --task create_department
```

Expected: Task completes successfully. If it fails, STOP — the structural migration broke something. Revert Task 3 changes and investigate before proceeding.

---

### Task 4: Recipe language cleanup — remove sandbox references

**Files:**
- Modify: `recipes/*.md` (multiple files)
- Modify: `prompts.py:39-86` (Known Constants and Critical Gotchas sections)

This is Phase 1b from the spec — separate from the structural migration so regressions can be isolated.

- [ ] **Step 1: Find all sandbox references**

```bash
grep -rn "sandbox" recipes/ prompts.py
```

Document each occurrence and its replacement. The rule: state behaviors as facts, don't reference the environment.

Examples:
- "the sandbox does NOT support setting vatType" → "Setting vatType on products is not supported (returns 'Ugyldig mva-kode')"
- "not enabled in sandbox" → "This endpoint returns 403"
- "sandbox rejects it" → "This is rejected by the API"
- "This is a sandbox limitation, not a bug" → remove this sentence entirely
- "IDs vary per sandbox" → "IDs vary per environment"

- [ ] **Step 2: Apply replacements to recipe files**

Go through each file in `recipes/` and `prompts.py` (the non-recipe sections: Known Constants at line 39, Critical Gotchas at line 47). Replace sandbox-specific language with factual statements.

- [ ] **Step 3: Run tests to verify no regression**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: ALL tests PASS

Run: `python -m pytest tests/ -v --ignore=tests/integration`
Expected: ALL tests PASS

- [ ] **Step 4: Commit**

```bash
git add recipes/ prompts.py
git commit -m "refactor: remove sandbox-specific language from recipes and prompts"
```

---

### Task 5: Create recipe-builder skill

**Files:**
- Create: `~/.claude/skills/recipe-builder/SKILL.md`

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p ~/.claude/skills/recipe-builder
```

- [ ] **Step 2: Write SKILL.md**

Create `~/.claude/skills/recipe-builder/SKILL.md` with this content:

```markdown
---
name: recipe-builder
description: Build and optimize Tripletex API recipes for the AI Accounting Agent. Use this skill whenever the user wants to create a new recipe, improve an existing recipe, figure out the optimal API call sequence for a task type, or says "build a recipe", "optimize the recipe", "make this work", or pastes a competition prompt. Also trigger when the user mentions API exploration, endpoint discovery, or testing API calls against the Tripletex sandbox. Even if the user just says "fix the invoice recipe" or "the agent is wasting calls", use this skill.
---

# Recipe Builder

Build and optimize Tripletex API recipes by exploring the API with curl, finding the minimal call sequence with zero errors, and writing a recipe file the agent can follow.

## When to use

- **Reactive**: A competition task failed or scored poorly — analyze what went wrong (optionally using agent-debugger first) and build a better recipe
- **Proactive**: A new task type is expected — discover the optimal API sequence before the agent sees it

## Environment Setup

```bash
source .env
export TRIPLETEX_BASE_URL    # e.g., https://kkpqfuj-amager.tripletex.dev/v2
export TRIPLETEX_SESSION_TOKEN
```

All curl commands use Basic Auth:
```bash
curl -s -u "0:$TRIPLETEX_SESSION_TOKEN" "$TRIPLETEX_BASE_URL/<endpoint>" | python3 -m json.tool
```

POST/PUT pattern:
```bash
curl -s -u "0:$TRIPLETEX_SESSION_TOKEN" \
  -X POST "$TRIPLETEX_BASE_URL/<endpoint>" \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}' | python3 -m json.tool
```

## Workflow

### Step 1: Understand the task

**If reactive (fixing a failure):**
- Read the GCS log or competition fixture to get the exact prompt
- If a task_id is provided, use agent-debugger techniques to pull the LangSmith trace
- Identify: what API calls did the agent make? Where did it fail? How many errors?

**If proactive (new task type):**
- Read the user's description or sample prompt
- Identify which Tripletex entities and endpoints are likely needed

### Step 2: Check existing recipe

Look in `recipes/` for an existing file for this task type:
```bash
ls recipes/
```

If one exists, read it and compare against what actually happened in the logs. This is an optimization, not a fresh build.

### Step 3: Explore the Tripletex API

Start with `api_knowledge/cheat_sheet.py` as a known baseline, but go beyond it — the full Tripletex API is much larger.

**Discovery approach:**
1. Try logical endpoint paths based on the task (e.g., `/bank`, `/bank/reconciliation`, `/bank/statement`)
2. Use `?fields=*` on any discovered endpoint to reveal its full structure
3. Try GET on collection endpoints to see what entities exist
4. Check Tripletex's public API documentation if available online

**Build incrementally:**
1. GET calls first — understand entity structures and discover field names
2. Create prerequisite entities (customer, department, employee, etc.)
3. Execute the target action (invoice, voucher, salary, etc.)
4. Capture each response — note exactly which fields were required vs optional
5. Track: total calls made, any errors, which fields caused problems

**Track your progress:**
After each curl call, note:
- Endpoint and method
- Response status code
- Whether it was necessary or wasted
- Any error message (exact text — these go into Known Gotchas)

### Step 4: Optimize

- Can any calls be eliminated? (e.g., embed orderLines in order POST)
- Are there unnecessary GET lookups? (e.g., use known constants instead)
- Can prerequisite creation be avoided? (e.g., entity already exists)
- Verify zero 4xx errors in the final sequence
- **Re-run the full optimized sequence from scratch** on a clean state to confirm it works

### Step 5: Clean up sandbox

Delete created entities in reverse order:
```bash
# Get entity with version
curl -s -u "0:$TRIPLETEX_SESSION_TOKEN" "$TRIPLETEX_BASE_URL/<endpoint>/<id>" | python3 -m json.tool
# Delete with version
curl -s -u "0:$TRIPLETEX_SESSION_TOKEN" -X DELETE "$TRIPLETEX_BASE_URL/<endpoint>/<id>?version=N"
```

Some entities cannot be deleted after state transitions (invoices after payment, posted vouchers). If DELETE returns 4xx, note it and move on.

### Step 6: Write the recipe

Save to `recipes/<NN>_<task_type>.md`. Use 2-digit zero-padded prefix. New task types get the next available number.

**Required sections** (every recipe MUST have all of these):

```markdown
# <Task Name> (Tier N)

## Task Pattern
<What prompts look like for this task type. Languages observed.>
<If file-based: what files are typically attached, what data the OCR extracts.>

## File Handling (include ONLY if this task type involves attached files)
<Describe: what files the evaluator sends (PDF invoice, CSV bank statement, etc.),
what data the OCR/text extraction provides, and how the agent should use that data
to populate API call fields. This is critical — the agent needs to know which OCR-extracted
values map to which API fields.>

## Optimal API Sequence
<Numbered steps. Each step: METHOD /endpoint {fields} → capture_var [N calls]>

## Field Reference
<Exact JSON bodies for each API call. ALL fields listed, no "..." placeholders.>

## Known Gotchas
<Specific errors encountered and how to avoid them. Exact error messages.>

## Expected Performance
- Calls: N
- Errors: 0
- Time: ~Ns
```

After writing, verify the recipe loads correctly:
```python
python -c "from prompts import build_system_prompt; p = build_system_prompt(); print('OK' if '<unique text from recipe>' in p else 'MISSING')"
```

### Step 7: Update cheat sheet (if new endpoints discovered)

If you discovered endpoints not in `api_knowledge/cheat_sheet.py`, add them following the existing format.

## File-Based Tasks

Some tasks include attached files (PDFs, images, CSVs). The agent processes them before the agentic loop:

```
Request with files → process_files() → gemini_ocr() → Claude agentic loop
```

**Processing pipeline:**
1. `process_files()` (file_handler.py): decodes base64, extracts PDF text via pymupdf, renders PDF pages as PNG images
2. `gemini_ocr()` (agent.py): sends images to Gemini for OCR text extraction
3. Both extracted text and OCR text are included in Claude's user message

**When building a recipe for a file-based task:**
- Note in the "Task Pattern" section that files are attached and what type (PDF invoice, CSV statement, etc.)
- Add a "File Handling" section documenting:
  - What the OCR typically extracts (invoice number, amounts, dates, supplier name, etc.)
  - How extracted values map to API call fields
  - What to do if OCR output is incomplete or ambiguous
- The curl-based API testing (Step 3) still works normally — you manually provide the data that OCR would have extracted
- Include a sample of what OCR output looks like for this task type

**To get a real OCR sample** (if a GCS log with files exists):
```bash
# Decode the file from GCS
gsutil cat gs://<bucket>/requests/<filename>.json | python3 -c "
import json, sys, base64
data = json.load(sys.stdin)
for f in data['request'].get('files', []):
    name = f['filename']
    raw = base64.b64decode(f['content_base64'])
    with open(name, 'wb') as out:
        out.write(raw)
    print(f'Saved {name} ({len(raw)} bytes)')
"
# Then check the LangSmith gemini_ocr span for what text was extracted
```

## Scoring Rules (context for optimization)

The competition scores on:
1. Correct field values (tier multipliers: 1x/2x/3x)
2. Fewer API calls = higher efficiency bonus
3. Every 4xx error reduces score
4. 270-second timeout — agent must finish within this

The ideal recipe: minimum calls, zero errors, all fields correct.
```

- [ ] **Step 3: Verify skill is recognized**

Start a new Claude Code conversation in the project directory and check that `recipe-builder` appears in the available skills list.

- [ ] **Step 4: Verify skill file exists**

Skills live in `~/.claude/skills/`, outside the project git repo — no git commit needed.

```bash
cat ~/.claude/skills/recipe-builder/SKILL.md | head -5
```

Expected: Shows the YAML frontmatter with `name: recipe-builder`.

---

### Task 6: Create recipe-validator skill

**Files:**
- Create: `~/.claude/skills/recipe-validator/SKILL.md`

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p ~/.claude/skills/recipe-validator
```

- [ ] **Step 2: Write SKILL.md**

Create `~/.claude/skills/recipe-validator/SKILL.md` with this content:

```markdown
---
name: recipe-validator
description: Validate that the deployed AI Accounting Agent follows recipes correctly. Use this skill whenever the user wants to test a recipe, verify agent behavior, deploy and check, see if the agent follows the expected API sequence, or says "test the recipe", "deploy and verify", "does the agent work", "check the agent". Also trigger after a recipe-builder session when the user wants to validate the new recipe end-to-end. Even "run a test" or "try it against dev" should trigger this skill.
---

# Recipe Validator

Deploy the agent and verify it follows the recipe's expected API call sequence.

## Containers

| Container | Purpose | Use for |
|-----------|---------|---------|
| `ai-accounting-agent-det` | Dev/testing | ALL validation testing |
| `accounting-agent-comp` | Competition | Deploy ONLY after validation passes, ONLY on explicit user request |

**NEVER send test requests to `accounting-agent-comp`.**

## Environment Setup

```bash
source .env
export TRIPLETEX_BASE_URL
export TRIPLETEX_SESSION_TOKEN
export LANGSMITH_API_KEY=$LANGSMITH_API_KEY  # dev key
export LANGSMITH_PROJECT=ai-accounting-agent-dev
export PATH="/Users/torbjornbeining/.local/bin:$PATH"  # for langsmith CLI
```

## Workflow

### Step 1: Deploy to dev container

Load .env first (required for LangSmith API keys — omitting them silently breaks tracing):

```bash
source .env

gcloud run deploy ai-accounting-agent-det --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-dev-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-dev,LANGSMITH_API_KEY=$LANGSMITH_API_KEY" \
  --quiet
```

Wait for deployment to complete (typically 2-3 minutes).

### Step 2: Send test request

Read credentials from `.env` and build a competition-format payload.

**For text-only tasks:**
```bash
curl -s -X POST https://ai-accounting-agent-det-590159115697.europe-north1.run.app/ \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"<the task prompt>\",
    \"files\": [],
    \"tripletex_credentials\": {
      \"base_url\": \"$TRIPLETEX_BASE_URL\",
      \"session_token\": \"$TRIPLETEX_SESSION_TOKEN\"
    }
  }"
```

POST to the root path `/` (NOT `/solve`) — this matches the competition evaluator's behavior.

**For file-based tasks** (PDF, image, CSV attachments):
Build the payload with base64-encoded files using a script:

```bash
python3 -c "
import json, base64, sys, os

# Encode the test file
filepath = '<path-to-test-file.pdf>'
with open(filepath, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

payload = {
    'prompt': '<the task prompt>',
    'files': [{
        'filename': os.path.basename(filepath),
        'mime_type': 'application/pdf',  # or image/png, text/csv, etc.
        'content_base64': b64
    }],
    'tripletex_credentials': {
        'base_url': os.environ['TRIPLETEX_BASE_URL'],
        'session_token': os.environ['TRIPLETEX_SESSION_TOKEN']
    }
}
with open('/tmp/test_payload.json', 'w') as f:
    json.dump(payload, f)
print(f'Payload written ({len(b64)} base64 chars for file)')
"

curl -s -X POST https://ai-accounting-agent-det-590159115697.europe-north1.run.app/ \
  -H "Content-Type: application/json" \
  -d @/tmp/test_payload.json
```

To get a test file from a previous GCS log:
```bash
gsutil cat gs://ai-nm26osl-1799-dev-logs/requests/<filename>.json | python3 -c "
import json, sys, base64
data = json.load(sys.stdin)
for f in data['request'].get('files', []):
    raw = base64.b64decode(f['content_base64'])
    with open(f['filename'], 'wb') as out:
        out.write(raw)
    print(f'Saved {f[\"filename\"]} ({len(raw)} bytes)')
"
```

The response is just `{"status": "completed"}` — the task_id is NOT in the HTTP response.

### Step 3: Find the trace

The task_id is in GCS and LangSmith, not the HTTP response. Find it:

```bash
# 1. List the most recent GCS dev log entry (just created)
gsutil ls gs://ai-nm26osl-1799-dev-logs/requests/ | tail -1
# Filename format: requests/{timestamp}_{task_id}_{prompt_preview}.json

# 2. Extract task_id from the filename (the 12-char hex between timestamp and prompt)

# 3. Find the LangSmith trace
langsmith run list --project ai-accounting-agent-dev --metadata task_id=<task_id> --format json
```

### Step 4: Verify agent behavior via LangSmith

```bash
# Get the trace tree
langsmith trace get <trace-id> --project ai-accounting-agent-dev --format pretty

# List all runs with full I/O
langsmith run list --project ai-accounting-agent-dev --trace-ids <trace-id> \
  --include-io --include-metadata --format json
```

Compare against the recipe's expected sequence. Check:
- **Call order**: Did the agent follow the recipe's steps in order?
- **Call count**: Match expected number? Any extra/unnecessary calls?
- **Errors**: Any 4xx responses? Which endpoints?
- **Thinking**: Did the agent's reasoning reference the recipe?

**For file-based tasks — also verify OCR:**
The `gemini_ocr` span is the first child of `run_agent`. Check its outputs:
- `ocr_text`: what Gemini extracted — does it contain the key data (invoice number, amounts, dates)?
- `chars_extracted`: if 0, OCR failed or no images were in the file
- Did the agent use the OCR data correctly in subsequent API calls?

```bash
# Find the gemini_ocr run specifically
langsmith run list --project ai-accounting-agent-dev --trace-ids <trace-id> \
  --include-io --format json
# Look for run with name "gemini_ocr" — check outputs.ocr_text
```

### Step 5: Verify sandbox state via direct curl

Make GET calls to verify entities were created correctly:

```bash
# Example: verify customer was created
curl -s -u "0:$TRIPLETEX_SESSION_TOKEN" "$TRIPLETEX_BASE_URL/customer?name=<expected>" | python3 -m json.tool

# Example: verify invoice exists
curl -s -u "0:$TRIPLETEX_SESSION_TOKEN" "$TRIPLETEX_BASE_URL/invoice?fields=*" | python3 -m json.tool
```

Check that field values match what the prompt asked for.

### Step 6: Report

Present a comparison table:

```
                    Expected (recipe)    Actual (agent)
API calls:          N                    M
Errors:             0                    K
Sequence match:     —                    ✓/✗ (detail which steps matched)
Sandbox state:      —                    Entity ✓/✗ per entity
```

**Pass/fail criteria:**
- **Pass**: Zero 4xx errors AND call count within ±1 of expected AND sandbox state correct
- **Marginal**: Zero errors but extra calls (agent deviated but got right result)
- **Fail**: Any 4xx error, or final state is wrong

**If the agent deviated:**
- Agent found a better path → update the recipe (back to recipe-builder)
- Agent didn't follow the recipe → recipe wording needs to be clearer
- Agent hit an unexpected error → add to recipe's Known Gotchas

### Step 7: Clean up sandbox

Delete test entities to reset for the next validation run:

```bash
curl -s -u "0:$TRIPLETEX_SESSION_TOKEN" "$TRIPLETEX_BASE_URL/<endpoint>/<id>?version=N" -X DELETE
```

Some entities can't be deleted after state transitions — note and move on.

### Step 8: Promote to competition (ONLY on explicit user request)

If validation passes and the user explicitly asks to deploy to competition:

```bash
source .env

gcloud run deploy accounting-agent-comp --source . --region europe-north1 \
  --project ai-nm26osl-1799 \
  --set-env-vars="GCP_PROJECT_ID=ai-nm26osl-1799,GCP_LOCATION=global,REQUEST_LOG_BUCKET=ai-nm26osl-1799-competition-logs,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=ai-accounting-agent-comp,LANGSMITH_API_KEY=$LANGSMITH_API_KEY_COMP" \
  --quiet
```

NEVER do this automatically. Always confirm with the user first.

## Reading a recipe's expected behavior

Before validating, read the recipe file to know what to expect:

```bash
cat recipes/<NN>_<task_type>.md
```

The "Optimal API Sequence" section lists the expected calls. The "Expected Performance" section lists the target call count and error count.

## Cross-referencing with GCS

For the full request payload (prompt, files, credentials, result summary):

```bash
gsutil cat gs://ai-nm26osl-1799-dev-logs/requests/<filename>.json | python3 -m json.tool
```

The GCS log includes `result.api_calls`, `result.api_errors`, and `result.error_details` — useful for a quick check without diving into LangSmith.
```

- [ ] **Step 3: Verify skill is recognized**

Start a new Claude Code conversation in the project directory and check that `recipe-validator` appears in the available skills list.

- [ ] **Step 4: Commit**

Note: Skills are in `~/.claude/skills/`, outside the project git repo. No project commit needed, but verify the skill file exists:

```bash
cat ~/.claude/skills/recipe-validator/SKILL.md | head -5
```

---

### Task 7: End-to-end verification

**Files:** None (verification only)

- [ ] **Step 1: Run all project tests**

```bash
python -m pytest tests/ -v --ignore=tests/integration
```

Expected: ALL tests pass, including the new `test_load_recipes.py` and existing `test_prompts.py`.

- [ ] **Step 2: Verify prompt equivalence**

```python
python -c "
from prompts import build_system_prompt
p = build_system_prompt()
# All recipe keywords must be present
checks = [
    'POST /customer', 'POST /employee', 'POST /supplier',
    'POST /department', 'POST /product', 'POST /order',
    'POST /invoice', 'POST /project', 'POST /ledger/voucher',
    'orderLines', 'paymentTypeId', 'isFixedPrice',
    'grantEntitlementsByTemplate', 'reconciliation',
    'POST /asset', 'POST /timesheet/entry',
]
missing = [c for c in checks if c not in p]
if missing:
    print(f'MISSING: {missing}')
else:
    print(f'All {len(checks)} checks passed. Prompt: {len(p)} chars, ~{len(p)//4} tokens')
"
```

- [ ] **Step 3: Verify all 3 skills are available**

```bash
ls ~/.claude/skills/agent-debugger/SKILL.md
ls ~/.claude/skills/recipe-builder/SKILL.md
ls ~/.claude/skills/recipe-validator/SKILL.md
```

- [ ] **Step 4: Final commit (project changes only)**

```bash
git add recipes/ prompts.py tests/test_load_recipes.py
git status  # Verify only expected files are staged
git commit -m "feat: recipe skill orchestration — modular recipes, builder, and validator skills"
```

Note: The skill files in `~/.claude/skills/` are outside the project repo and not tracked by git.
