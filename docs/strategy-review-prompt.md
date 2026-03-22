# Strategy Review — Deterministic Executor vs Claude Agent

Use this prompt to start a fresh session reviewing our competition strategy.

---

## Prompt for new session:

I need you to review our competition strategy for the NM i AI 2026 Tripletex accounting agent. Read the following files to understand the current state, then help me decide whether to restructure our approach.

**Key files to read:**
1. `CLAUDE.md` — project overview, architecture, deploy commands
2. `real-requests/analysis-plan.md` — all 47 captured competition requests grouped by task type
3. `real-requests/api-audit.md` — API optimization audit
4. `deterministic_executor.py` — the deterministic execution pipeline
5. `execution_plans/_classifier.py` — keyword-based task classifier (the weakest link)
6. `main.py` — integration point (deterministic first, Claude fallback)
7. `agent.py` — the Claude agentic loop (fallback)
8. `prompts.py` — system prompt with recipes

**Check competition logs:**
- `real-requests/logs/` — 47 captured requests with results
- `real-requests/replay-results/` — replay test results
- `real-requests/optimal-sequence/` — researched optimal API sequences per task type

## What we built

A **deterministic executor** that sits in front of the existing Claude agent:

```
Request → Keyword classifier (instant) → Gemini param extraction (~5-10s) → Execute hardcoded plan → Result
                                                                                    ↓ (on any failure)
                                                                              Claude Opus 4.6 agentic fallback
```

- 21 execution plans covering all observed task types
- Keyword classifier with multilingual regex patterns
- Gemini Flash for parameter extraction from prompts
- Claude fallback catches everything the deterministic path misses

## Current results

**Replay against sandbox (41 requests):**
- 40/41 OK (98%), avg 63s
- The deterministic path handles ~60% of requests successfully
- ~40% fall back to Claude (misclassification, extraction failure, plan errors)

**Competition results (3 submissions so far):**
- Task 045 create_product: **7/7 (100%)** — deterministic, 14.5s
- Task 046 reverse_payment: **2/8 (25%)** — MISCLASSIFIED as register_payment
- Task 047 project_lifecycle: **4/11 (36%)** — MISCLASSIFIED as register_supplier_invoice

## The core problem

**The keyword classifier is brittle.** Every new prompt phrasing we haven't seen breaks it:
- "Consulting Hours" (product name) triggered `register_hours`
- "lønnsavsetning" (salary provision) triggered `run_salary` instead of `monthly_closing`
- "leverandørkostnad" (supplier cost) triggered `register_supplier_invoice` instead of `project_lifecycle`
- "zurückgebucht" (reversed) wasn't in `reverse_payment` patterns
- We keep patching — 6+ classifier fixes so far, each after a competition failure

**When misclassification happens, the deterministic plan runs the WRONG sequence** — creating wrong entities, wasting API calls, and scoring 25-36% instead of the ~95% Claude would have gotten.

**The fallback doesn't help for misclassification** — the plan "succeeds" (returns a result dict), so Claude never gets called. The deterministic executor only falls back on explicit failures (exceptions, timeouts, null params), not on "I ran the wrong plan."

## The strategic tension

| Approach | Speed | Accuracy | Risk |
|----------|-------|----------|------|
| **Deterministic only** | 10-30s | ~60% correct classification | Wrong plan = bad score |
| **Claude only** | 60-150s | ~95% task understanding | Slow, many API retries |
| **Current hybrid** | 10-30s when right, 60-300s on fallback | ~60% deterministic, ~95% fallback | Misclassification doesn't trigger fallback |
| **Claude guided by optimal sequences** | 30-60s | ~95% understanding + optimal sequences | Need to update recipes/prompts |

## Questions to answer

1. **Should we keep the deterministic-first approach?** The classifier keeps breaking on new phrasings. Every competition submission reveals new patterns we haven't seen.

2. **Should we use Claude for classification instead of regex?** A single Claude/Gemini call to classify the task type would be much more robust than regex, at the cost of ~5s latency.

3. **Should we convert the optimal sequences into better recipes for Claude instead of hardcoded plans?** The research we did (20 optimal sequence docs) is valuable regardless — the question is whether it should drive Python code or Claude's system prompt.

4. **Should we add a confidence check?** After the deterministic plan executes, verify that the result makes sense (e.g., did we create the right number of entities?) before returning. If not confident, fall back to Claude.

5. **Can we get the best of both worlds?** Use Claude for classification + parameter extraction (robust), then execute the deterministic plan (fast API calls). Only ~1 Claude call instead of 10-20 iterations.

## Deadline context

- Competition deadline: **Saturday March 22 at 15:00 CET** (tomorrow)
- Tier 3 opens Saturday morning (3x multiplier)
- 180 submissions/day
- Current agent with Claude fallback works for ~95% of tasks
- The deterministic path adds value when classification is correct but actively hurts when wrong
