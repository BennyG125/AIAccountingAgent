---
name: save-and-replay
description: Save competition requests locally and replay them against the dev container. Use this skill when the user wants to save a competition request, replay a saved request after a recipe fix, or says "save this request", "save the competition request", "replay the task", "test locally", "try it again". Also trigger after an agent-debugger session when a failure needs to be saved for reproduction. Even "save it" or "replay it" in the context of a competition task should trigger this skill.
---

# Save & Replay

Save competition requests locally (stripped of credentials) and replay them against the dev container to verify fixes.

## When to use

- **After debugging**: Save the failing request so you have a reproducible test case
- **After fixing a recipe**: Replay the saved request to verify the fix before deploying to competition

## Save a Request

### Check if already saved
```bash
ls competition/requests/
```
If the task_id already exists, tell the user it's already saved and offer to replay it.

### Save from competition logs (default)
```bash
# Save all competition requests
python scripts/save_competition_requests.py

# Save a specific task
python scripts/save_competition_requests.py --task-id <task_id>
```

### Save from dev logs
```bash
python scripts/save_competition_requests.py --env dev
```

Saved requests go to `competition/requests/{task_id}.json` — prompt, files, and result summary. Credentials are stripped (injected from `.env` at replay time).

### Saved file format
```json
{
  "task_id": "752c1e06d0c3",
  "timestamp": "2026-03-21T07:40:32Z",
  "prompt": "Opprett ein faktura...",
  "files": [],
  "result_summary": {
    "status": "completed",
    "api_calls": 9,
    "api_errors": 3,
    "time_ms": 49200,
    "error_details": [...]
  }
}
```

## Replay a Request

Replays the exact prompt + files against the dev container, injecting credentials from `.env`.

```bash
source .env && export TRIPLETEX_BASE_URL TRIPLETEX_SESSION_TOKEN
python scripts/replay_request.py competition/requests/<task_id>.json
```

The script shows:
- Previous error count (from the saved result_summary)
- Response status and time
- You can then use agent-debugger to check the LangSmith trace for the replay

### Replay against a different URL
```bash
python scripts/replay_request.py competition/requests/<task_id>.json --url https://other-container.run.app
```

## Typical Workflow

```
agent-debugger           →  "Found 3 errors on task X. Save it for replay?"
save-and-replay (save)   →  "Saved. Fix the recipe?"  (invoke recipe-builder)
recipe-builder           →  "Recipe updated. Replay to verify?"
save-and-replay (replay) →  "Replay shows 0 errors (was 3). Deploy to validate?"  (invoke recipe-validator)
recipe-validator         →  "Deploy + full verification"
```

## Next Steps

After saving, recommend the user invoke **recipe-builder** to fix the identified issue:
> "Request saved to competition/requests/{task_id}.json. Want me to fix the recipe? (invoke recipe-builder)"

After replaying, recommend **recipe-validator** if the replay shows improvement:
> "Replay shows {N} errors (was {M}). Want me to deploy and validate fully? (invoke recipe-validator)"
