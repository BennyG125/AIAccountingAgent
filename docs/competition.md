# NM i AI 2026 — Tripletex Challenge

## Scoring

| Component | How |
|-----------|-----|
| **Correctness** | Field-by-field API verification after agent runs. Normalized 0–1. |
| **Tier multiplier** | Tier 1 = 1.0x, Tier 2 = 2.0x, Tier 3 = 3.0x |
| **Efficiency bonus** | Only on perfect correctness. Fewer API calls + zero 4xx errors = bonus above 1.0 |
| **Max score per task** | Tier 3 perfect = up to 6.0 |

## Tasks

- **30 tasks** across 3 tiers
- **56 variants per task** (7 languages × 8 data sets)
- **7 categories:** Employees, Customers & Products, Invoicing, Travel Expenses, Projects, Corrections, Departments

## Languages

`nb` (Bokmål), `nn` (Nynorsk), `en`, `es`, `pt`, `de`, `fr`

## Payload Format

```json
{
  "prompt": "<task text in any of the 7 languages>",
  "files": [{"filename": "...", "content_base64": "...", "mime_type": "..."}],
  "tripletex_credentials": {
    "base_url": "https://....tripletex.dev/v2",
    "session_token": "..."
  }
}
```

Response: `{"status": "completed"}`

## Verification

After agent responds, competition queries Tripletex API to check what was created/modified. Field-by-field comparison. Partial credit for partial completion.

## Key Optimization Rules

1. Minimize API calls — every extra call reduces efficiency bonus
2. Zero 4xx errors — each error reduces efficiency bonus
3. Don't verify with GET after successful creates — wastes calls
4. Plan calls in dependency order — avoid retries
5. Sandbox starts EMPTY each submission — create prerequisites as needed
