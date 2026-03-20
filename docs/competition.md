# NM i AI 2026 — Tripletex Challenge

## Scoring

correctness = points_earned / max_points (normalized 0–1)
final_score = correctness × tier_multiplier × (1 + efficiency_bonus)

| Tier | Multiplier | Perfect + best efficiency |
|------|-----------|--------------------------|
| 1 | ×1 | up to 2.0 |
| 2 | ×2 | up to 4.0 |
| 3 | ×3 | up to 6.0 |

**Efficiency bonus** (only on perfect correctness = 1.0):
- Call efficiency: fewer API calls vs benchmark = higher bonus
- Error cleanliness: every 4xx error reduces the bonus
- Benchmarks recalculated periodically — bar rises as teams improve

**Tier 2 examples:** Failed=0.0, 80% correct=1.6, perfect+many errors≈2.1, perfect+few errors≈2.6, perfect+best efficiency=4.0

**Best score tracking:** Per-task all-time best. Bad runs never lower your score. Recalculated every 12 hours.

## Rate Limits

- Verified teams: 3 concurrent, 10 per task daily
- Unverified: 1 concurrent, 3 per task daily

## Tasks

- **30 tasks** across 3 tiers, **56 variants per task** (7 languages × 8 data sets)
- **7 categories:** Employees, Customers & Products, Invoicing, Travel Expenses, Projects, Corrections, Departments
- **Languages:** `nb`, `nn`, `en`, `es`, `pt`, `de`, `fr`
- **Timeout:** 300 seconds (5 minutes)

## Task Patterns

| Pattern | Example | Optimal Flow |
|---------|---------|-------------|
| Create single entity | "Create employee" | POST /employee (1 call) |
| Create with linking | "Create invoice for customer" | GET → POST /order → POST /invoice |
| Modify existing | "Add phone to contact" | GET → PUT |
| Delete/reverse | "Delete travel expense" | GET → DELETE |
| Multi-step setup | "Register payment" | POST chain → PUT /:payment |

## Payload

```json
{
  "prompt": "<task in any of 7 languages>",
  "files": [{"filename": "...", "content_base64": "...", "mime_type": "..."}],
  "tripletex_credentials": {"base_url": "https://...tripletex.dev/v2", "session_token": "..."}
}
```

Response: `{"status": "completed"}` with HTTP 200.

## Optimization Rules

1. Minimize API calls — directly affects efficiency bonus
2. Zero 4xx errors — each error reduces bonus
3. Don't GET-verify after successful creates — wastes calls
4. Embed orderLines in order POST — saves separate calls
5. Use known constants (VAT ids, currency, country) — never look up
6. Sandbox starts EMPTY each submission — create prerequisites as needed
