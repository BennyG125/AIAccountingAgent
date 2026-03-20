# Competition Request Format — Tripletex AI Agent

## Endpoint Requirements

- **URL**: Your Cloud Run service URL (must be publicly accessible)
- **Method**: `POST /` (root path, NOT `/solve`)
- **Content-Type**: `application/json`
- **Timeout**: 300 seconds (5 minutes)
- **Response**: Must return `{"status": "completed"}` with HTTP 200

## Request Payload

```json
{
  "prompt": "Opprett en avdeling med navn Salg og avdelingsnummer 200",
  "files": [],
  "tripletex_credentials": {
    "base_url": "https://<sandbox>.tripletex.dev/v2",
    "session_token": "<session-token>"
  }
}
```

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `prompt` | string | Yes | Task in any language (nb, nn, en, es, pt, de, fr) |
| `files` | array | No | May be `[]`, `null`, or absent |
| `files[].filename` | string | Yes | Original filename |
| `files[].content_base64` | string | Yes | Base64-encoded file bytes |
| `files[].mime_type` | string | Yes | e.g. `application/pdf`, `image/png` |
| `tripletex_credentials` | object | Yes | May be `null` — handle gracefully |
| `tripletex_credentials.base_url` | string | Yes | Proxy URL (includes `/v2`) |
| `tripletex_credentials.session_token` | string | Yes | For Basic Auth (username=`0`) |

### Alternative payload format (observed from some evaluators)

```json
{
  "task_prompt": "...",
  "attached_files": [],
  "tripletex_base_url": "https://...",
  "session_token": "..."
}
```

Our `main.py` handles both formats.

## Authentication

- **Tripletex API**: Basic Auth with `username=0`, `password=session_token`
- **Your endpoint**: Optionally set API key during submission. Evaluator sends `Authorization: Bearer <key>`
- **Cloud Run**: Must allow unauthenticated invocations (`allUsers` → `roles/run.invoker`)

## Evaluation

- Each submission gets a **fresh Tripletex sandbox** (no pre-existing data)
- 30 unique task variants across 3 tiers (1x/2x/3x multiplier)
- **Field-by-field verification** against expected values
- Efficiency bonus for low API call count (only with perfect correctness)

## Key gotchas

1. Evaluator hits `POST /` (root path), not `POST /solve`
2. Fresh sandbox = no departments, no employees, no bank account on ledger 1920
3. vatType IDs vary per sandbox (don't hardcode — retry without if rejected)
4. Cloud Run must be publicly accessible (not `--no-allow-unauthenticated`)
