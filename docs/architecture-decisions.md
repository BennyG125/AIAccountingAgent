# Architecture Decision Records

Tracks key architectural decisions for the AI Accounting Agent. Each ADR explains what was decided, why, and what trade-offs were accepted.

---

## ADR-001: Two-Path Execution Model

**Decision:** Requests go through a deterministic execution path first, falling back to a Gemini tool-use loop if the deterministic path can't handle it or fails.

**Why:** The competition scores efficiency (fewer API calls, zero 4xx errors). The deterministic path executes known patterns in pure code — no LLM iteration, no guessing, no retries. For patterns we haven't registered, the tool-use loop provides full coverage.

**Trade-off:** Maintaining two execution paths adds complexity. The deterministic path needs a registry of every entity type it handles. Unknown patterns always fall back, so coverage depends on registry completeness.

---

## ADR-002: Single LLM Parse Call

**Decision:** Gemini structured output parses the prompt into a TaskPlan JSON in exactly 1 LLM call. The pattern matcher and executor run in code with zero additional LLM calls.

**Why:** Every LLM call adds ~3-5 seconds of latency. The tool-use fallback needs 3-15 LLM calls per task. The deterministic path needs exactly 1 (the parse), saving 10-40 seconds per request and improving the efficiency score.

**Trade-off:** The parse must extract all necessary information in one shot. Complex or ambiguous prompts may produce incomplete plans, triggering fallback.

---

## ADR-003: Static Entity Registry

**Decision:** All entity schemas, field requirements, defaults, constants, and dependencies are hardcoded in `task_registry.py`. No runtime API discovery.

**Why:** API discovery wastes calls (hurts efficiency). The Tripletex API schema doesn't change between competition submissions. Hardcoding makes the system deterministic and fully testable.

**Trade-off:** New entity types require code changes. If Tripletex changes an endpoint or field, the registry must be updated manually.

---

## ADR-004: Generic REST Tools for Fallback

**Decision:** The tool-use fallback uses 4 generic tools (`tripletex_get`, `tripletex_post`, `tripletex_put`, `tripletex_delete`) rather than entity-specific typed tools.

**Why:** 4 generic tools cover every Tripletex endpoint without maintaining 30+ tool definitions. The LLM has full flexibility to call any endpoint with any parameters. The cheat sheet in the system prompt provides the domain knowledge.

**Trade-off:** The model must compose raw API paths and payloads. Entity-specific tools would reduce model errors but limit flexibility and increase maintenance burden.

---

## ADR-005: FallbackContext Handoff

**Decision:** When the deterministic executor fails mid-execution (e.g., 422 on the third of five actions), it passes a `FallbackContext` to the tool-use loop containing: completed entity IDs, the failed action, and the error message.

**Why:** Without handoff, the fallback would re-create entities that already exist (causing 422 duplicates) and wouldn't know what went wrong. FallbackContext lets the tool-use loop pick up where the deterministic path left off.

**Trade-off:** The fallback must interpret the context correctly. If the tool-use loop ignores the context, it may still duplicate work.

---

## ADR-006: Pre-Lookups for Runtime Constants

**Decision:** Entity types that need runtime IDs (costCategory, paymentType, rateCategory, rateType) declare them as `pre_lookups` in the registry. The executor GETs these once per request and caches them.

**Why:** These IDs vary per sandbox instance — they can't be hardcoded like VAT rates. But they're the same for all actions within a single request, so one GET per lookup type suffices.

**Trade-off:** Each pre-lookup adds 1 API call. For travel expense tasks this means 1-2 extra GETs. This is still far fewer than the fallback's iterative approach.

---

## ADR-007: Search-Then-Act for Update/Delete/Action Patterns

**Decision:** The deterministic executor handles update, delete, and named actions (send invoice, reverse voucher, etc.) by first searching for the entity via GET, then executing the action.

**Why:** The competition includes modification and correction tasks (Tier 2-3). Without this, all update/delete/action tasks fall to the tool-use loop, losing the efficiency advantage.

**Trade-off:** Search may return wrong results if search_fields are ambiguous. The executor takes the first result — if multiple entities match, it may act on the wrong one. Fallback handles these edge cases.

---

## ADR-008: Few-Shot Examples Over Explicit Field Schemas

**Decision:** The parse prompt uses 3 few-shot examples (Norwegian simple, English multi-step, German single) rather than defining all 200+ field properties in the JSON schema.

**Why:** Gemini structured output has schema size limits. 200+ property definitions would exceed them or degrade quality. Few-shot examples are more token-efficient (~300 tokens) and teach the output format through demonstration.

**Trade-off:** The model may still miss field names that aren't in the examples. The system prompt lists all field names per entity as a reference, and the examples show the extraction pattern.

---

## ADR-009: Separate Cloud Run Service

**Decision:** The deterministic execution layer deploys as `ai-accounting-agent-det`, separate from the teammate's `ai-accounting-agent`.

**Why:** We accidentally overwrote the teammate's deployment. Separate services allow independent development and deployment without interference.

**Trade-off:** Two services to manage. Eventually these should be merged once the deterministic layer is proven.

---

## ADR-010: Known Constants Hardcoded

**Decision:** VAT rates (25%=id 3, 15%=id 5, 0%=id 6), NOK currency (id 1), and Norway country (id 162) are hardcoded as `KNOWN_CONSTANTS` in the registry, never looked up via API.

**Why:** These IDs are the same across all Tripletex sandbox instances and never change. Looking them up wastes API calls and hurts the efficiency score.

**Trade-off:** If Tripletex ever changes these IDs, the hardcoded values would be wrong. This is extremely unlikely for a competition sandbox.

---

## ADR-011: Static Registry Over RAG/SQL for Endpoint Discovery

**Decision:** Endpoint schemas are stored as Python dicts in `task_registry.py`, not in SQLite, a vector store, or a graph database. Gemini's parse call handles prompt → entity mapping using the system prompt as context.

**Why:** The competition has a fixed API surface (~99 cheat sheet endpoints, ~200+ in the full OpenAPI spec). The parse step already correctly identifies entity types and actions — the bottleneck is execution quality (empty fields, retry loops), not endpoint discovery. A static registry is O(1) lookup, zero latency, fully deterministic, and trivially testable. Adding RAG (embed prompt → vector search → retrieve endpoints) would add ~2s latency per request and a dependency (embedding model + vector store) to solve a problem we don't have.

**Alternatives considered:**
- **SQLite + embeddings (RAG):** Store endpoint descriptions with vector embeddings, semantic search on each prompt. Rejected for now — adds latency and complexity without improving accuracy for known competition patterns.
- **GraphRAG:** Model entity relationships as a knowledge graph (entity → endpoint → dependencies → constants). Could improve multi-step planning by traversing the graph. Rejected for now — the dependency graph in `DEPENDENCIES` already captures this in a simpler form.
- **Hybrid (static + RAG fallback):** Use static registry for known patterns, fall back to RAG for unknown ones. Most promising future option if Tier 3 tasks involve unexpected endpoints.

**Revisit trigger:** If smoke tests reveal tasks that require endpoints not in the cheat sheet, or if the competition adds new API categories, revisit RAG/GraphRAG as a discovery layer on top of the static registry.

---

## ADR-012: Bulk Create Auto-Batching

**Decision:** When the executor detects multiple create actions of the same entity type with no cross-dependencies, it automatically batches them into a single `POST /*/list` call instead of N individual POST calls.

**Why:** The competition scores efficiency by API call count. Creating 5 employees via `POST /employee/list` is 1 call instead of 5 — directly improving the efficiency bonus. Six entity types support bulk creates: employee, customer, contact, product, order/orderline, project/participant.

**Trade-off:** Batch creates return a different response format (`{"values": [...]}` vs `{"value": {...}}`). The executor must extract multiple IDs and map them back to their respective refs. If one entity in the batch fails validation, the entire batch may fail — the executor must handle partial failures by falling back to individual creates.

---

## ADR-013: Complete Endpoint Catalog in Parse System Prompt

**Decision:** The full endpoint catalog (all entity types, field names, action patterns) is included in Gemini's parse system prompt. Gemini acts as both the "RAG retrieval" and the "structured extraction" in a single LLM call.

**Why:** With unlimited credits, the cost of a larger system prompt (~4K tokens) is irrelevant. Gemini already understands accounting terminology in 7 languages. Giving it the complete catalog means it can map any prompt to the right endpoint without a separate retrieval step. This is simpler and faster than a two-step RAG pipeline (embed → retrieve → parse).

**Trade-off:** The system prompt is larger, which slightly increases parse latency (~1-2s). If the catalog grows beyond ~10K tokens, response quality may degrade — at that point, RAG pre-filtering would help reduce the context window.
