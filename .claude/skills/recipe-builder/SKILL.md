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
<Numbered steps. Each step: METHOD /endpoint {fields} -> capture_var [N calls]>

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
Request with files -> process_files() -> gemini_ocr() -> Claude agentic loop
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
