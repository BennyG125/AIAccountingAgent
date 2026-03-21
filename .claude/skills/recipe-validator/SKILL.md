---
name: recipe-validator
description: Validate that the deployed AI Accounting Agent follows recipes correctly. Use this skill whenever the user wants to test a recipe, verify agent behavior, deploy and check, see if the agent follows the expected API sequence, or says "test the recipe", "deploy and verify", "does the agent work", "check the agent", "try the fix against dev". Also trigger after a recipe-builder session when the user wants to validate the new recipe end-to-end. Even "run a test", "try it against dev", or "verify the fix" should trigger this skill.
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
Sequence match:     —                    yes/no (detail which steps matched)
Sandbox state:      —                    Entity yes/no per entity
```

**Pass/fail criteria:**
- **Pass**: Zero 4xx errors AND call count within +/-1 of expected AND sandbox state correct
- **Marginal**: Zero errors but extra calls (agent deviated but got right result)
- **Fail**: Any 4xx error, or final state is wrong

**If the agent deviated, recommend the appropriate next action:**

| Deviation | Recommendation |
|-----------|----------------|
| Agent found a better path (fewer calls, same result) | "Agent found a better sequence. Want me to update the recipe? (invoke recipe-builder)" |
| Agent didn't follow the recipe (wording unclear) | "Recipe wording needs to be clearer. Want me to improve it? (invoke recipe-builder)" |
| Agent hit an unexpected error | "New gotcha discovered. Want me to add it to the recipe? (invoke recipe-builder)" |
| Agent passed cleanly | "Validation passed. Ready to deploy to competition on your say-so." |

Do NOT automatically invoke recipe-builder. Present the comparison and let the user decide.

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
