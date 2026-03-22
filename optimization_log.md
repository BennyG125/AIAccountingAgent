# Optimization Log — AI Accounting Agent

Automated findings from sequential review of execution plans, optimal sequences, and recipes against real Tripletex API documentation (swagger.json).

**Goal:** Reduce API calls per task type through bulk endpoints, skip-search patterns, sub-resource embedding, and eliminating redundant lookups.

**Process:** 10 parallel agents per cycle, each analyzing one task type. Rotates through all 26 task types.

---

## Cycle 1 — 2026-03-22 ~14:00

**Task types analyzed:** bank_reconciliation, cost_analysis_projects, create_customer, create_departments, create_employee, create_invoice, create_order, create_product, create_project, create_supplier

**Total findings:** 42
**Total potential savings:** 30-45 API calls across all analyzed task types

---

### PRIORITY SUMMARY — Highest-Impact Findings

| Rank | Task Type | Current Calls | Proposed Calls | Savings | Key Optimization |
|------|-----------|--------------|----------------|---------|-----------------|
| 1 | bank_reconciliation | 38-43 | 19-23 | **16-20** | Skip all searches, bulk create, combine invoice+payment |
| 2 | cost_analysis_projects | 12 | 5-8 | **4-7** | Skip activity search, bulk /activity/list, embed in project |
| 3 | create_order | 7 | 4-5 | **2-3** | Remove product number, skip customer search, hardcode paymentTypeId |
| 4 | create_invoice | 4-11 | 3-4 | **1-7** | Fix bulk product fallback cascade, skip customer search |
| 5 | create_employee | 3-4 | 2-3 | **1-2** | Remove entitlements, skip dept search, add employment |
| 6 | create_departments | 2 | 1 | **1** | Remove GET /department (sandbox empty) |
| 7 | create_project | 5 | 4 | **1** | Pre-configure department in main.py |
| 8 | create_customer | 1 | 1 | 0 | Already optimal |
| 9 | create_product | 1 | 1 | 0 | Already optimal |
| 10 | create_supplier | 1 | 1 | 0 | Already optimal |

### CROSS-CUTTING FINDING: Pre-configure department in main.py

**Confidence:** HIGH | **Impact:** Saves 1 call across 7+ task types (create_project, create_employee, employee_onboarding, register_hours, travel_expense, project_lifecycle, run_salary)

`main.py` already runs `_preconfigure_bank_account()` before every execution. Adding `_preconfigure_department()` alongside it would cache the department ID and pass it to execution plans, eliminating the GET/POST department pattern repeated across many task types.

**Files:** `main.py` lines 64-85

---

## bank_reconciliation — 38-43 calls → 19-23 calls (41-51% reduction)

### Finding: Skip search before creating customers
- **Component:** execution_plan
- **Optimization Type:** skip_search
- **Current API Calls:** 2 per unique customer (GET + POST)
- **Proposed API Calls:** 1 per unique customer (POST only)
- **Savings:** 3-5 calls
- **Confidence:** HIGH
- **Details:** `_find_or_create()` does `GET /customer?name=X` before `POST /customer`. Sandbox starts EMPTY — search always returns 0 results.
- **Files:** `execution_plans/bank_reconciliation.py` lines 181-196

### Finding: Skip search before creating suppliers
- **Component:** execution_plan
- **Optimization Type:** skip_search
- **Current API Calls:** 2 per unique supplier (GET + POST)
- **Proposed API Calls:** 1 per unique supplier (POST only)
- **Savings:** 2-3 calls
- **Confidence:** HIGH
- **Files:** `execution_plans/bank_reconciliation.py` lines 199-218

### Finding: Eliminate invoice search per customer row
- **Component:** execution_plan
- **Optimization Type:** eliminate_lookup
- **Current API Calls:** 1 GET per customer payment row (5 calls typically)
- **Proposed API Calls:** 0
- **Savings:** 5 calls
- **Confidence:** HIGH
- **Details:** `GET /invoice?customerId=X` always returns empty on fresh sandbox. Recipe and optimal sequence both skip this.
- **Files:** `execution_plans/bank_reconciliation.py` lines 254-267

### Finding: Eliminate product search
- **Component:** execution_plan
- **Optimization Type:** skip_search
- **Savings:** 1 call
- **Confidence:** HIGH
- **Details:** `GET /product?name=Service` always returns empty. POST directly.
- **Files:** `execution_plans/bank_reconciliation.py` lines 272-289

### Finding: Bulk create customers via POST /customer/list
- **Component:** execution_plan
- **Optimization Type:** bulk_endpoint
- **Current API Calls:** 3-5 individual POSTs
- **Proposed API Calls:** 1 bulk POST
- **Savings:** 2-4 calls
- **Confidence:** MEDIUM
- **API Reference:** `POST /customer/list` confirmed in swagger.json
- **Files:** `execution_plans/bank_reconciliation.py` lines 181-196

### Finding: Bulk create suppliers via POST /supplier/list
- **Component:** execution_plan
- **Optimization Type:** bulk_endpoint
- **Savings:** 1-2 calls
- **Confidence:** MEDIUM
- **Files:** `execution_plans/bank_reconciliation.py` lines 199-218

### Finding: Combine invoice+payment in single PUT /order/:invoice call
- **Component:** execution_plan
- **Optimization Type:** eliminate_lookup
- **Current API Calls:** 2 per customer payment (PUT /order/:invoice + PUT /invoice/:payment)
- **Proposed API Calls:** 1 per customer payment
- **Savings:** 5 calls
- **Confidence:** HIGH
- **Details:** `PUT /order/{id}/:invoice` accepts `paymentTypeId` and `paidAmount` as query params. Confirmed in OpenAPI spec.
- **Risk:** `paidAmount` on `:invoice` might behave as "prepayment" — needs testing.
- **Files:** `execution_plans/bank_reconciliation.py` lines 315-343

### Finding: Voucher posting sign inconsistency
- **Component:** inconsistency
- **Confidence:** MEDIUM
- **Details:** Execution plan and recipe use opposite signs for supplier voucher postings (2400 account). Both claim "paying a supplier" but signs reversed. Execution plan: positive for 2400, negative for 1920. Recipe: negative for 2400, positive for 1920.
- **Files:** `execution_plans/bank_reconciliation.py` line 369, `recipes/18_bank_reconciliation.md` line 79

### Finding: Account lookup already optimized (doc gap)
- **Confidence:** HIGH
- **Details:** Plan already batches `_get_accounts(client, "1920", "2400", "7770")` into 1 call. Recipe and optimal sequence incorrectly show 3 separate calls.
- **Files:** `recipes/18_bank_reconciliation.md` lines 35-37, `real-requests/optimal-sequence/bank_reconciliation.md` lines 87-89

---

## cost_analysis_projects — 12 calls → 5-8 calls (33-58% reduction)

### Finding: Include account name in posting fields to eliminate separate lookup
- **Component:** execution_plan
- **Optimization Type:** eliminate_lookup
- **Savings:** 1 call
- **Confidence:** HIGH
- **Details:** Change `fields=account(number),amount` to `fields=account(number,name),amount` in GET /ledger/posting. Eliminates separate `GET /ledger/account` for account names.
- **Files:** `execution_plans/cost_analysis_projects.py`

### Finding: Eliminate 3x GET /activity search-before-create
- **Component:** execution_plan
- **Optimization Type:** skip_search
- **Savings:** 3 calls
- **Confidence:** HIGH
- **Details:** Sandbox starts empty — activities never exist. Search always returns 0 results.
- **Files:** `execution_plans/cost_analysis_projects.py` lines 251-253

### Finding: Use POST /activity/list bulk endpoint
- **Component:** execution_plan
- **Optimization Type:** bulk_endpoint
- **Current API Calls:** 3 individual POSTs
- **Proposed API Calls:** 1 bulk POST
- **Savings:** 2 calls
- **Confidence:** MEDIUM
- **API Reference:** `POST /activity/list` confirmed in swagger.json
- **Files:** `execution_plans/cost_analysis_projects.py`

### Finding: Embed activities via projectActivities in POST /project/list
- **Component:** execution_plan
- **Optimization Type:** embed_subresource
- **Savings:** 3 calls (replaces all activity creation)
- **Confidence:** MEDIUM
- **Details:** POST /project accepts `projectActivities` inline. Could embed activities directly in the bulk project creation call. Risk: evaluator may expect GENERAL_ACTIVITY type vs PROJECT_SPECIFIC_ACTIVITY.
- **Files:** `execution_plans/cost_analysis_projects.py`, cheat_sheet.py line 375

### Finding: Recipe/optimal sequence inconsistencies
- **Confidence:** HIGH
- **Details:** (1) Recipe shows 3 individual POST /project but plan uses bulk POST /project/list. (2) Recipe shows separate employee creation but plan reuses existing employee. (3) Recipe suggests 3 separate account lookups but plan batches them.
- **Files:** `recipes/28_cost_analysis_projects.md`, `real-requests/optimal-sequence/cost_analysis_projects.md`

---

## create_customer — 1 call (already optimal)

- Execution plan achieves theoretical minimum: single `POST /customer`.
- No search-before-create waste.
- **Gap:** Missing optimal sequence doc at `real-requests/optimal-sequence/create_customer.md`.
- **Gap:** Recipe too terse — should warn against unnecessary GET /country (hardcode 162 for Norway).
- **Risk:** Hardcoded country ID 162 (Norway) — non-Norwegian addresses would be wrong.
- **Files:** `execution_plans/create_customer.py`, `recipes/01_create_customer.md`

---

## create_departments — 2 calls → 1 call (50% reduction)

### Finding: Remove unnecessary GET /department lookup
- **Component:** execution_plan
- **Optimization Type:** skip_search
- **Savings:** 1 call (50% reduction)
- **Confidence:** HIGH
- **Details:** Plan calls `GET /department?count=1000` to find highest departmentNumber. Sandbox starts EMPTY — max_num is always 0. Optimal sequence doc already says "No GET lookup before POST."
- **Proposed Change:** Hardcode starting number at 100, increment by 100. Skip GET entirely.
- **Files:** `execution_plans/create_departments.py` lines 34-42

### Finding: Cheat sheet missing POST /department/list
- **Confidence:** HIGH
- **Details:** Endpoint exists (confirmed in OpenAPI spec line 6207) but not documented in cheat_sheet.py. Claude agent can't use what it doesn't know about.
- **Files:** `api_knowledge/cheat_sheet.py`

### Finding: Recipe doesn't mention POST /department/list
- **Confidence:** MEDIUM
- **Details:** Recipe says "one POST /department per department" — should use bulk endpoint.
- **Files:** `recipes/04_create_departments.md`

---

## create_employee — 3-4 calls → 2-3 calls

### Finding: Remove unnecessary entitlements call
- **Component:** execution_plan
- **Optimization Type:** eliminate_lookup
- **Savings:** 1 call (25-33% reduction)
- **Confidence:** HIGH
- **Details:** `PUT /employee/entitlement/:grantEntitlementsByTemplate` is not scored for basic Tier 1 create_employee. Entitlements are for project managers, not basic employees.
- **Files:** `execution_plans/create_employee.py` lines 102-108

### Finding: Skip GET /department on empty sandbox
- **Component:** execution_plan
- **Optimization Type:** skip_search
- **Savings:** 1 call
- **Confidence:** MEDIUM-HIGH
- **Details:** POST /department directly, handle 422 with fallback GET.
- **Files:** `execution_plans/create_employee.py` lines 32-61

### Finding: Missing employment/startDate handling — losing scored points
- **Component:** execution_plan
- **Optimization Type:** accuracy (feature gap)
- **Confidence:** HIGH
- **Details:** All 4 real competition prompts include start dates, but EXTRACTION_SCHEMA lacks `start_date`. Plan creates no employment record. POST /employee accepts inline `employments` array — embed employment in the same call.
- **Files:** `execution_plans/create_employee.py` lines 9-15

### Finding: Recipe missing employment step + division warning
- **Confidence:** HIGH
- **Details:** Recipe omits employment creation. Should also warn "NEVER POST /division" (one request hit 422 on this).
- **Files:** `recipes/02_create_employee.md`

### Finding: Missing optimal sequence doc
- **Confidence:** HIGH
- **Files:** `real-requests/optimal-sequence/create_employee.md` does not exist

---

## create_invoice — 4-11 calls → 3-4 calls (up to 64% reduction)

### Finding: Skip customer search on fresh sandbox
- **Savings:** 1 call
- **Confidence:** HIGH
- **Files:** `execution_plans/create_invoice.py` lines 40-58

### Finding: Fix bulk product create fallback cascade (CRITICAL)
- **Component:** execution_plan
- **Optimization Type:** bulk_endpoint fix
- **Current API Calls (worst case, 3 products):** 7 (bulk fail + 3 individual fails + 3 searches)
- **Proposed API Calls:** 1 (bulk succeeds)
- **Savings:** Up to 6 calls
- **Confidence:** HIGH
- **Details:** Evidence: requests 37fe7effbefc and d7a4af2123ab show 11 API calls — signature of bulk-success-but-empty-ids fallback. The `if not product_ids` check falls through even when bulk succeeded, because response structure parsing may be wrong.
- **Files:** `execution_plans/create_invoice.py` lines 83-118

### Finding: Guard strips vatType from order lines — breaks multi-VAT invoices
- **Component:** recipe guard
- **Optimization Type:** inconsistency (BUG)
- **Confidence:** HIGH
- **Details:** `06_create_invoice.guard.json` has `"/order/orderline": {"body_strip": ["vatType"]}` which silently removes vatType from order lines in the Claude agentic loop. Multi-VAT-rate invoices get wrong VAT.
- **Files:** `recipes/06_create_invoice.guard.json`

### Finding: sendToCustomer contradicts prompts.py gotcha
- **Confidence:** MEDIUM
- **Details:** Execution plan uses `sendToCustomer=true` query param on POST /invoice. prompts.py explicitly says "NEVER use sendToCustomer query param."
- **Files:** `execution_plans/create_invoice.py` lines 140-142, `prompts.py` line 147

### Finding: Optimal sequence doc outdated
- **Confidence:** HIGH
- **Details:** Shows separate POST /order + POST /invoice (2 calls) but execution plan already uses inline order in POST /invoice (1 call).
- **Files:** `real-requests/optimal-sequence/create_invoice.md`

---

## create_order — 7 calls → 4-5 calls (29-43% reduction)

### Finding: Skip customer search (sandbox empty)
- **Savings:** 1 call
- **Confidence:** HIGH
- **Files:** `execution_plans/create_order.py` lines 35-44

### Finding: Hardcode paymentTypeId=1 — eliminate GET /invoice/paymentType
- **Savings:** 1 call
- **Confidence:** HIGH
- **Details:** register_payment optimal sequence already documents: "Use paymentTypeId=1 directly." Current code defaults to 1 anyway (line 165).
- **Files:** `execution_plans/create_order.py` lines 162-169

### Finding: Remove product `number` field — eliminates 422 errors
- **Optimization Type:** accuracy (BUG FIX)
- **Savings:** Up to 2 extra calls per product on error path
- **Confidence:** HIGH
- **Details:** Including `number` from prompt causes 422 "Validering feilet" or "Produktnummeret X er i bruk". create_invoice optimal sequence says "NEVER include number on POST /product."
- **Files:** `execution_plans/create_order.py` lines 59-66, 79-84

### Finding: Merge order+invoice into single POST /invoice with inline order
- **Savings:** 1 call
- **Confidence:** MEDIUM-HIGH
- **Details:** create_invoice plan already does this successfully. Risk: evaluator may check for standalone Order entity.
- **Files:** `execution_plans/create_order.py` lines 116-148

### Finding: Recipe missing invoice+payment steps
- **Confidence:** MEDIUM
- **Details:** Recipe only shows 3 steps (customer, products, order). Execution plan has 5 steps (adds invoice + payment).
- **Files:** `recipes/12_create_order.md`

---

## create_product — 1 call (already optimal)

- Single `POST /product` achieves theoretical minimum.
- All 9 competition requests: 1 call, 0 errors.
- Minor note: `_safe_post` retry may undercount api_calls metric (reports 1 when 2 were made on 422 retry).
- **Files:** `execution_plans/create_product.py`

---

## create_project — 5 calls → 4 calls (20% reduction)

### Finding: Pre-configure department (cross-cutting, see above)
- **Savings:** 1 call
- **Confidence:** HIGH

### Finding: Recipe mentions participants but execution plan ignores them
- **Confidence:** MEDIUM
- **Details:** Recipe says "If prompt mentions participants: POST /project/participant". Plan doesn't handle this.
- **Files:** `recipes/08_create_project.md` line 6, `execution_plans/create_project.py`

### Finding: Optimal sequence tier label wrong
- **Confidence:** HIGH
- **Details:** Doc says "Tier 2" but real requests tagged as Tier 1.
- **Files:** `real-requests/optimal-sequence/create_project.md` line 3

---

## create_supplier — 1 call (already optimal)

- Single `POST /supplier` achieves theoretical minimum.
- All 12 competition requests: 1 call, 0 errors.
- **Gap:** Missing optimal sequence doc at `real-requests/optimal-sequence/create_supplier.md`.
- **Gap:** Hardcoded country ID 162 (Norway) — same risk as create_customer.
- **Files:** `execution_plans/create_supplier.py`, `recipes/03_create_supplier.md`

---

## Documentation Gaps Identified

| Missing File | Task Type | Priority |
|---|---|---|
| `real-requests/optimal-sequence/create_customer.md` | create_customer | LOW (already optimal) |
| `real-requests/optimal-sequence/create_employee.md` | create_employee | HIGH (needs employment docs) |
| `real-requests/optimal-sequence/create_supplier.md` | create_supplier | LOW (already optimal) |
| `real-requests/optimal-sequence/create_order.md` | create_order | MEDIUM |

---

## Cycle 2 — 2026-03-22 ~14:30

**Task types analyzed:** credit_note, custom_dimension, employee_onboarding, fixed_price_project, forex_payment, monthly_closing, overdue_invoice_reminder, project_lifecycle, register_hours, register_payment

**Total findings:** 55+
**Total potential savings:** 40-60 API calls across all analyzed task types

---

### PRIORITY SUMMARY — Cycle 2 Highest-Impact Findings

| Rank | Task Type | Current Calls | Proposed Calls | Savings | Key Optimization |
|------|-----------|--------------|----------------|---------|-----------------|
| 1 | project_lifecycle | 20-21 | 14-15 | **6-7** | Skip 5 search-before-create, batch accounts |
| 2 | register_hours | 13 | 6-8 | **5-7** | Skip 4 searches, inline hourlyRates in project |
| 3 | forex_payment | 9-13 | 6-7 | **3-7** | Remove fast path, skip product, hardcode paymentTypeId |
| 4 | fixed_price_project | 10 | 6 | **4** | Skip customer/employee/product search |
| 5 | overdue_invoice_reminder | 11 | 7 | **4** | Batch accounts, skip product, skip EMAIL send |
| 6 | employee_onboarding | 5-6 | 2-3 | **3** | Embed employments inline, pre-cache division |
| 7 | register_payment | 4-6 | 3 | **1-3** | Hardcode paymentTypeId=1, skip searches |
| 8 | custom_dimension | 7 | 5 | **2** | Skip 2 search-before-create on empty sandbox |
| 9 | monthly_closing | 3-4 | 3-4 | **0** | Already optimal; bug fix (early return blocks salary voucher) |
| 10 | credit_note | 3 | 3 | **0** | Already optimal; recipe has bugs to fix |

---

### CROSS-CUTTING FINDINGS (Cycle 2)

**Pre-cache division ID in main.py**: GET /company/divisions always returns the same result. Cache it alongside `_preconfigure_bank_account()`. Saves 1 call in employee_onboarding, project_lifecycle, register_hours, and more.

**Hardcode paymentTypeId=1**: Confirmed across ALL payment-related tasks (register_payment, forex_payment, overdue_invoice_reminder, create_order, bank_reconciliation). Every plan already falls back to ID 1. The GET /invoice/paymentType call is universally wasted.

**Description-only order lines**: Both forex_payment and overdue_invoice_reminder recipes confirm that order lines can use `description` instead of `product: {id}`, eliminating product creation entirely.

---

## credit_note — 3 calls (already optimal)

- Sequential dependency chain (customer→invoice→createCreditNote) cannot be shortened.
- **Recipe bug**: Uses `customerName` param on GET /invoice (doesn't exist) and missing customer lookup step. Would cause errors if Claude fallback triggers.
- **Doc fix**: Optimal sequence says 3-4 calls, should say 3 (order line fetch never needed).
- **Minor**: Unused `orders` field in GET /invoice response — remove for smaller payload.
- **Files**: `recipes/15_credit_note.md`, `real-requests/optimal-sequence/credit_note.md`

---

## custom_dimension — 7 calls → 5 calls (29% reduction)

### Finding: Skip GET /ledger/accountingDimensionName search
- **Savings:** 1 call | **Confidence:** HIGH
- Sandbox starts empty — dimension never exists. POST directly.
- **Files:** `execution_plans/custom_dimension.py` lines 67-81

### Finding: Skip GET /ledger/accountingDimensionValue search
- **Savings:** 1 call | **Confidence:** HIGH
- Same reasoning — values never exist on fresh sandbox.
- **Files:** `execution_plans/custom_dimension.py` lines 104-113

### Finding: No bulk POST /accountingDimensionValue/list exists
- **Confirmed** via OpenAPI spec — only PUT /list (update), not POST /list (create).

### Finding: Recipe applies dimension to both voucher rows, plan only to row 1
- **Confidence:** MEDIUM — need to verify which the evaluator expects.
- **Files:** `recipes/13_custom_dimension_voucher.md` vs `execution_plans/custom_dimension.py`

### Finding: Optimal sequence doc claims "4 minimum" but correct is 5
- Account lookups are essential and can't be eliminated.
- **Files:** `real-requests/optimal-sequence/custom_dimension.md` line 4

---

## employee_onboarding — 5-6 calls → 2-3 calls (up to 60% reduction)

### Finding: Embed employments + employmentDetails inline in POST /employee
- **Savings:** 2 calls | **Confidence:** MEDIUM-HIGH
- OpenAPI spec confirms POST /employee accepts `employments` array, each with `employmentDetails`.
- Requires knowing division_id BEFORE POST /employee (reorder steps).
- **Risk:** Must test — nested embedding depth may not work in practice.
- **Files:** `execution_plans/employee_onboarding.py` lines 104-194

### Finding: Skip department search — POST first, GET on conflict
- **Savings:** 1 call | **Confidence:** MEDIUM
- **Files:** `execution_plans/employee_onboarding.py` lines 92-100

### Finding: Pre-cache division ID in main.py
- **Savings:** 1 call | **Confidence:** HIGH
- Divisions are system-level, not task-specific. Cache once, reuse everywhere.
- **Files:** `main.py`, `execution_plans/employee_onboarding.py` lines 144-151

### Finding: api_calls counter always adds 2 for _find_or_create (should be 1 or 2)
- **Confidence:** HIGH — bookkeeping fix, no call savings.
- **Files:** `execution_plans/employee_onboarding.py` line 100

---

## fixed_price_project — 10 calls → 6 calls (40% reduction)

### Finding: Skip customer search (sandbox empty)
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/fixed_price_project.py` lines 52-109

### Finding: Skip employee search (sandbox empty)
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/fixed_price_project.py` lines 113-189

### Finding: Skip product search (sandbox empty)
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/fixed_price_project.py` lines 256-302

### Finding: Recipe uses wasteful GET+PUT pattern for fixed price
- **Savings:** 2 calls in Claude fallback path
- Recipe says: create project, GET version, PUT isFixedPrice. Plan already sets isFixedPrice at POST time.
- **Files:** `recipes/09_fixed_price_project.md`

### Finding: Missing project link on invoice order (SCORING BUG)
- **Confidence:** HIGH — plan omits `project: {id}` in inline order. Evaluator may check.
- **Files:** `execution_plans/fixed_price_project.py` line 312

---

## forex_payment — 9-13 calls → 6-7 calls (up to 46% reduction)

### Finding: Hardcode paymentTypeId=1
- **Savings:** 1 call | **Confidence:** HIGH
- Code already falls back to 1 (line 318).
- **Files:** `execution_plans/forex_payment.py` lines 316-322

### Finding: Use description-only order lines (eliminate product creation)
- **Savings:** 1-2 calls | **Confidence:** HIGH
- Recipe explicitly says "no product needed." Plan still creates one.
- **Files:** `execution_plans/forex_payment.py` lines 190-214

### Finding: Remove entire fast path (invoice search futile on empty sandbox)
- **Savings:** 1-2 calls | **Confidence:** HIGH
- Fast path searches for existing customer+invoice. Never exist in competition.
- **Files:** `execution_plans/forex_payment.py` lines 109-138

### Finding: Optimistic customer create (POST first, GET on conflict)
- **Savings:** 1 call | **Confidence:** HIGH
- Double customer search in fast+full path wastes calls.
- **Files:** `execution_plans/forex_payment.py` lines 41-46, 144-165

### Finding: Optimal sequence doc lists account 1920 but code never uses it
- **Confidence:** HIGH — documentation error, 1920 is irrelevant for forex voucher.
- **Files:** `real-requests/optimal-sequence/forex_payment.md`

---

## monthly_closing — 3-4 calls (already near optimal)

### Finding: EARLY RETURN BUG blocks salary voucher (SCORING FIX)
- **Confidence:** HIGH | **Impact:** Prevents salary provision from posting
- If depreciation account lookup fails, `return` prevents salary voucher.
- **Fix:** Replace `return` with skip, let execution continue to salary voucher.
- **Files:** `execution_plans/monthly_closing.py` lines 207-210

### Finding: Recipe uses 6 individual account GETs, plan batches into 1
- **Savings:** 5 calls in Claude fallback path
- **Files:** `recipes/23_monthly_closing.md` lines 29-41

### Finding: Optimal sequence doc claims 9 calls, plan achieves 3-4
- **Confidence:** HIGH — documentation is stale.
- **Files:** `real-requests/optimal-sequence/monthly_closing.md`

---

## overdue_invoice_reminder — 11 calls → 7 calls (36% reduction)

### Finding: Merge 2 account lookups via _get_accounts()
- **Savings:** 1 call | **Confidence:** HIGH
- `GET /ledger/account?number=1500,3400` instead of 2 separate calls.
- **Files:** `execution_plans/overdue_invoice_reminder.py` lines 146-172

### Finding: Eliminate product search/create — use description-only orderLine
- **Savings:** 1-2 calls | **Confidence:** HIGH
- Recipe and optimal sequence both confirm: description-only orderLine works.
- **Files:** `execution_plans/overdue_invoice_reminder.py` lines 231-254

### Finding: Skip EMAIL send — go directly to MANUAL
- **Savings:** 1 call + 1 error | **Confidence:** MEDIUM-HIGH
- EMAIL always fails with 422 (customer has no email). MANUAL always works.
- **Files:** `execution_plans/overdue_invoice_reminder.py` lines 294-310

### Finding: Hardcode paymentTypeId=1
- **Savings:** 1 call | **Confidence:** MEDIUM
- **Files:** `execution_plans/overdue_invoice_reminder.py` lines 323-329

### Finding: `:send` uses body but API requires query params
- **Confidence:** MEDIUM — correctness fix, cheat_sheet says "Query params (NOT body)."
- **Files:** `execution_plans/overdue_invoice_reminder.py` lines 295-304

---

## project_lifecycle — 20-21 calls → 14-15 calls (33% reduction)

### Finding: Skip GET /project search before POST /project
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/project_lifecycle.py` lines 318-349

### Finding: Batch 2 account lookups via _get_accounts("7000", "2400")
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/project_lifecycle.py` lines 751-772

### Finding: Skip GET /customer search (sandbox empty)
- **Savings:** 1 call | **Confidence:** HIGH
- Recipe says POST first, plan does GET first.
- **Files:** `execution_plans/project_lifecycle.py` lines 165-204

### Finding: Skip GET /employee search (per employee)
- **Savings:** 2 calls (PM + consultant) | **Confidence:** HIGH
- Recipe says POST first, plan does GET first.
- **Files:** `execution_plans/project_lifecycle.py` lines 566-616

### Finding: Skip GET /supplier search
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/project_lifecycle.py` lines 705-747

### Finding: Skip GET /activity search
- **Savings:** 0-1 call | **Confidence:** MEDIUM
- Activities might pre-exist more often than other entities.
- **Files:** `execution_plans/project_lifecycle.py` lines 362-402

### Finding: Remove futile sub-project search before close
- **Savings:** 1 call | **Confidence:** HIGH
- Plan never creates sub-projects. Search always returns empty.
- **Files:** `execution_plans/project_lifecycle.py` lines 504-530

### Finding: Skip entitlement grant for consultant employees
- **Savings:** 1 call per consultant | **Confidence:** MEDIUM
- Recipe only grants to PM. Plan grants to all employees.
- **Files:** `execution_plans/project_lifecycle.py` lines 301-310

---

## register_hours — 13 calls → 6-8 calls (38-54% reduction)

### Finding: Skip search-before-create for customer, employee, activity, project
- **Savings:** 4 calls | **Confidence:** HIGH
- All 4 entities: sandbox starts empty, search always returns nothing.
- **Files:** `execution_plans/register_hours.py` lines 58-228

### Finding: Inline projectHourlyRates in POST /project
- **Savings:** 3 calls (replaces GET check + POST hourlyRates + saves project search) | **Confidence:** MEDIUM-HIGH
- POST /project accepts `projectHourlyRates` array inline (cheat_sheet.py line 376).
- **Files:** `execution_plans/register_hours.py` lines 174-256

### Finding: Pre-configure department in main.py
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/register_hours.py` lines 95-111, `main.py`

### Finding: Recipe missing customerId filter on project search
- **Confidence:** HIGH — could match wrong project in fallback.
- **Files:** `recipes/16_register_hours.md` Step 5

---

## register_payment — 4-6 calls → 3 calls (25-50% reduction)

### Finding: Hardcode paymentTypeId=1 (skip GET /invoice/paymentType)
- **Savings:** 1 call | **Confidence:** HIGH
- Optimal sequence already documents this. Code falls back to 1 anyway.
- **Files:** `execution_plans/register_payment.py` lines 228-235

### Finding: Skip customer search in full path (sandbox empty)
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/register_payment.py` lines 138-159

### Finding: Skip product search in full path (sandbox empty)
- **Savings:** 1 call | **Confidence:** HIGH
- **Files:** `execution_plans/register_payment.py` lines 164-182

### Finding: paidAmountCurrency inconsistency across plans
- **Confidence:** MEDIUM-HIGH — register_payment sends amount, create_order sends "1". Need standardization.
- **Files:** `execution_plans/register_payment.py` line 243, `execution_plans/create_order.py` line 178

### Finding: Recipe outdated — doesn't reflect fast path or inline order
- **Confidence:** HIGH
- **Files:** `recipes/07_register_payment.md`

---

## BUGS FOUND IN CYCLE 2

| Bug | Task Type | Impact | Files |
|-----|-----------|--------|-------|
| Early return blocks salary voucher | monthly_closing | Scoring loss | `execution_plans/monthly_closing.py` lines 207-210 |
| Missing project link on invoice order | fixed_price_project | Scoring loss | `execution_plans/fixed_price_project.py` line 312 |
| Recipe uses wrong endpoint param (`customerName` on /invoice) | credit_note | Claude fallback fails | `recipes/15_credit_note.md` |
| `:send` uses body but API requires query params | overdue_invoice_reminder | Potential silent failure | `execution_plans/overdue_invoice_reminder.py` |
| Product `number` field causes 422 cascades | create_order/register_payment | Extra error calls | `execution_plans/create_order.py` lines 59-66 |
| paidAmountCurrency inconsistency | register_payment vs create_order | Scoring inconsistency | Multiple files |

---

## Cycle 3 — 2026-03-22 ~15:00

**Task types analyzed:** register_supplier_invoice, reverse_payment, run_salary, travel_expense, year_end_close, year_end_corrections

**ALL 26 TASK TYPES NOW COVERED.**

**Total findings:** 40+
**Total potential savings:** 20-30 API calls across analyzed task types

---

### PRIORITY SUMMARY — Cycle 3

| Rank | Task Type | Current Calls | Proposed Calls | Savings | Key Optimization |
|------|-----------|--------------|----------------|---------|-----------------|
| 1 | run_salary | 7-16 | 3-6 | **4-10** | Remove fallback retries, inline employments |
| 2 | year_end_corrections | 7 | 5 | **2** | Skip vatType lookup, fix _safe_post bug |
| 3 | travel_expense | 3-8 | 3-5 | **0-3** | Conditional lookups (skip when unused) |
| 4 | register_supplier_invoice | 4-5 | 3-4 | **1** | Skip supplier search on empty sandbox |
| 5 | reverse_payment | 8 | 7 | **1** | Hardcode paymentTypeId=1 |
| 6 | year_end_close | ~6 | ~6 | **0** | Bug fixes + recipe alignment |

---

### CROSS-CUTTING FINDINGS (Cycle 3)

**`_safe_post` retry_without bug is systemic**: Confirmed in BOTH `register_supplier_invoice` and `year_end_corrections`. The `retry_without=["vatType"]` parameter strips from the top-level body dict, but `vatType` is nested inside `postings[]` array. The retry is identical to the original call and always fails again. This wastes 1 call every time it triggers. Affects any plan using `_safe_post` with nested field names.

**Recipe salary calculation bug**: `recipes/10_run_salary.md` says monthly salary = annual/12, but prompts give monthly amounts directly. Plan correctly uses the value as-is.

---

## register_supplier_invoice — 4-5 calls → 3-4 calls

### Finding: Skip supplier GET on empty sandbox
- **Savings:** 1 call | **Confidence:** HIGH
- POST /supplier directly, handle 422 with fallback GET.
- **Files:** `execution_plans/register_supplier_invoice.py` lines 93-124

### Finding: _safe_post retry_without=["vatType"] is a no-op (BUG)
- **Confidence:** HIGH
- vatType is nested in `postings[0]`, not at body top level. Retry is identical to original.
- **Fix:** Either use direct `client.post` with manual nested-field retry, or skip vatType entirely.
- **Files:** `execution_plans/register_supplier_invoice.py` lines 199-205, `execution_plans/_base.py` lines 74-95

### Finding: Supplier ref on wrong row (CORRECTNESS BUG)
- **Confidence:** HIGH
- Plan puts supplier on row 2 (liability). Recipe and optimal sequence put it on row 1 (expense).
- **Files:** `execution_plans/register_supplier_invoice.py` lines 172-196

### Finding: Row 2 includes forbidden amountGross/amountGrossCurrency fields
- **Confidence:** HIGH
- Recipe and optimal sequence say row 2 should ONLY have amount + amountCurrency.
- **Files:** `execution_plans/register_supplier_invoice.py` lines 186-195

### Finding: Recipe shows 3 separate account GETs, plan already batches into 1
- **Confidence:** HIGH — recipe needs updating to match plan.
- **Files:** `recipes/11_register_supplier_invoice.md` lines 16-20

---

## reverse_payment — 8 calls → 7 calls

### Finding: Hardcode paymentTypeId=1
- **Savings:** 1 call | **Confidence:** HIGH
- Code already falls back to 1. Skip the lookup.
- **Files:** `execution_plans/reverse_payment.py` lines 146-151

### Finding: Recipe voucher lookup uses non-existent `invoiceId` param
- **Confidence:** HIGH
- Cheat sheet does NOT list `invoiceId` as valid for GET /ledger/voucher.
- **Files:** `recipes/14_reverse_payment_voucher.md` Step 7

### Finding: Recipe dateTo=today bug causes 422
- **Confidence:** HIGH
- dateTo must be strictly after dateFrom. Recipe should use tomorrow.
- Competition request 3373928e56bf hit exactly this: 12 calls, 3 errors.
- **Files:** `recipes/14_reverse_payment_voucher.md` Step 7

---

## run_salary — 7-16 calls → 3-6 calls (up to 63% reduction)

### Finding: Remove 4 redundant salary type fallback searches
- **Savings:** up to 4 calls | **Confidence:** HIGH
- Initial GET returns all types. Fallback searches query the same data.
- **Files:** `execution_plans/run_salary.py` lines 200-236

### Finding: Remove division retry logic (wasted 2 calls)
- **Savings:** 2 calls | **Confidence:** HIGH
- Second GET /company/divisions identical to first. Retry of POST /employment also wastes a call.
- **Files:** `execution_plans/run_salary.py` lines 126-134

### Finding: Remove employment details retry
- **Savings:** 1 call | **Confidence:** MEDIUM-HIGH
- Retry without annualSalary changes semantics. Original failure cause is rarely the salary field.
- **Files:** `execution_plans/run_salary.py` lines 152-164

### Finding: Inline employments in POST /employee
- **Savings:** 3 calls | **Confidence:** MEDIUM
- Embed employment + details in POST /employee body. Needs dev testing.
- **Files:** `execution_plans/run_salary.py` lines 83-165

### Finding: Batch account lookups in voucher fallback
- **Savings:** 1 call | **Confidence:** HIGH
- Use `_get_accounts("5000", "1920")` instead of 2 separate GETs.
- **Files:** `execution_plans/run_salary.py` lines 289-299

### Finding: Recipe says annual/12 but prompts give monthly salary (BUG)
- **Confidence:** HIGH — plan correctly uses base_salary directly.
- **Files:** `recipes/10_run_salary.md` Step 7

---

## travel_expense — 3-8 calls → 3-5 calls (conditional optimization)

### Finding: Skip rateCategory lookup when no per diem
- **Savings:** 1 call for receipt-only tasks | **Confidence:** HIGH
- rate_categories only consumed inside `if per_diem_days:` block.
- **Files:** `execution_plans/travel_expense.py` lines 177-184

### Finding: Skip costCategory lookup when no costs
- **Savings:** 1 call for per-diem-only tasks | **Confidence:** HIGH
- cost_categories only consumed in `for expense in costs_input` loop.
- **Files:** `execution_plans/travel_expense.py` lines 165-172

### Finding: Skip paymentType lookup when no costs
- **Savings:** 1 call for per-diem-only tasks | **Confidence:** HIGH
- paymentType only used inside cost items.
- **Files:** `execution_plans/travel_expense.py` lines 152-160

### Finding: POST-first department on empty sandbox
- **Savings:** 1 call in new-employee path | **Confidence:** MEDIUM
- **Files:** `execution_plans/travel_expense.py` lines 69-84

### Finding: Missing `purpose: "work"` in travelDetails
- **Confidence:** MEDIUM — recipe and optimal sequence include it, plan omits it.
- **Files:** `execution_plans/travel_expense.py` lines 291-302

---

## year_end_close — ~6 calls (near optimal, but critical bugs)

### Finding: NameError bug — tax_provision_amount used before defined (CRITICAL)
- **Confidence:** HIGH
- Lines 237-246 reference `tax_provision_amount` which isn't defined until line 367.
- **Files:** `execution_plans/year_end_close.py` lines 237-246

### Finding: Missing accountNumberFrom/To filter on GET /ledger/posting
- **Confidence:** HIGH
- Recipe already uses the filter. Plan fetches ALL postings, wastes bandwidth.
- **Files:** `execution_plans/year_end_close.py` lines 357-363

### Finding: Recipe shows 6-9 individual account GETs, plan batches into 1
- **Confidence:** HIGH — recipe needs updating.
- **Files:** `recipes/22_year_end_close.md` lines 22-38

### Finding: /balanceSheet endpoint contradictions across docs
- Plan says "returns 404". Cheat sheet documents it. Optimal sequence uses it.
- Need empirical verification.
- **Files:** Multiple

---

## year_end_corrections — 7 calls → 5 calls (29% reduction)

### Finding: Skip GET /ledger/vatType — use simple 2-row voucher
- **Savings:** 1-2 calls | **Confidence:** HIGH
- Recipe documents the fallback approach as the preferred one. vatType adds complexity + potential 422.
- **Files:** `execution_plans/year_end_corrections.py` lines 196-345

### Finding: _safe_post retry_without=["vatType"] is a no-op (same bug as supplier invoice)
- **Savings:** 1 wasted call on failure path | **Confidence:** HIGH
- vatType nested in postings, not at body top level.
- **Files:** `execution_plans/year_end_corrections.py` lines 328-345

### Finding: Optimal sequence claims 12 calls, reality is 5-7
- **Confidence:** HIGH — docs massively overshoot.
- **Files:** `real-requests/optimal-sequence/year_end_corrections.md` line 269

### Finding: Docstring says GET /ledger/posting Step 3 but code skips it
- **Confidence:** HIGH — plan correctly skips, but docs are inconsistent.
- **Files:** `execution_plans/year_end_corrections.py` docstring, `recipes/20_year_end_corrections.md`

---

## ALL BUGS FOUND ACROSS ALL 3 CYCLES

| Bug | Task Type | Severity | Files |
|-----|-----------|----------|-------|
| NameError: tax_provision_amount before definition | year_end_close | **CRITICAL** | `execution_plans/year_end_close.py` L237 |
| Early return blocks salary voucher | monthly_closing | **HIGH** | `execution_plans/monthly_closing.py` L207-210 |
| Missing project link on invoice order | fixed_price_project | **HIGH** | `execution_plans/fixed_price_project.py` L312 |
| Supplier ref on wrong voucher row | register_supplier_invoice | **HIGH** | `execution_plans/register_supplier_invoice.py` L172-196 |
| Row 2 has forbidden amountGross fields | register_supplier_invoice | **HIGH** | `execution_plans/register_supplier_invoice.py` L186-195 |
| _safe_post retry doesn't work for nested fields | register_supplier_invoice, year_end_corrections | **MEDIUM** | `execution_plans/_base.py` L74-95 |
| Guard strips vatType from order lines (breaks multi-VAT) | create_invoice | **HIGH** | `recipes/06_create_invoice.guard.json` |
| Product number field causes 422 cascades | create_order | **HIGH** | `execution_plans/create_order.py` L59-66 |
| Recipe uses wrong endpoint param (customerName on /invoice) | credit_note | **MEDIUM** | `recipes/15_credit_note.md` |
| Recipe dateTo=today causes 422 | reverse_payment | **MEDIUM** | `recipes/14_reverse_payment_voucher.md` |
| `:send` uses body but API requires query params | overdue_invoice_reminder | **MEDIUM** | `execution_plans/overdue_invoice_reminder.py` |
| Recipe salary annual/12 but prompts give monthly | run_salary | **MEDIUM** | `recipes/10_run_salary.md` |
| paidAmountCurrency inconsistency across plans | register_payment, create_order | **LOW** | Multiple files |

---

## FULL COVERAGE SUMMARY — ALL 26 TASK TYPES

| Task Type | Current | Proposed | Savings | Status |
|-----------|---------|----------|---------|--------|
| bank_reconciliation | 38-43 | 19-23 | **16-20** | Major wins |
| cost_analysis_projects | 12 | 5-8 | **4-7** | Major wins |
| create_customer | 1 | 1 | 0 | Optimal |
| create_departments | 2 | 1 | **1** | Easy win |
| create_employee | 3-4 | 2-3 | **1-2** | Easy win |
| create_invoice | 4-11 | 3-4 | **1-7** | Critical bug fix |
| create_order | 7 | 4-5 | **2-3** | Bug fix + optimize |
| create_product | 1 | 1 | 0 | Optimal |
| create_project | 5 | 4 | **1** | Easy win |
| create_supplier | 1 | 1 | 0 | Optimal |
| credit_note | 3 | 3 | 0 | Optimal (recipe bugs) |
| custom_dimension | 7 | 5 | **2** | Easy win |
| employee_onboarding | 5-6 | 2-3 | **3** | Embed employments |
| fixed_price_project | 10 | 6 | **4** | Skip searches |
| forex_payment | 9-13 | 6-7 | **3-7** | Major wins |
| monthly_closing | 3-4 | 3-4 | 0 | Optimal (bug fix) |
| overdue_invoice_reminder | 11 | 7 | **4** | Batch + skip product |
| project_lifecycle | 20-21 | 14-15 | **6-7** | Major wins |
| register_hours | 13 | 6-8 | **5-7** | Inline hourlyRates |
| register_payment | 4-6 | 3 | **1-3** | Hardcode paymentTypeId |
| register_supplier_invoice | 4-5 | 3-4 | **1** | Skip search + bug fixes |
| reverse_payment | 8 | 7 | **1** | Hardcode paymentTypeId |
| run_salary | 7-16 | 3-6 | **4-10** | Remove retries |
| travel_expense | 3-8 | 3-5 | **0-3** | Conditional lookups |
| year_end_close | ~6 | ~6 | 0 | Critical bug fix |
| year_end_corrections | 7 | 5 | **2** | Skip vatType |

**TOTAL ESTIMATED SAVINGS: 55-100 API calls across all task types**

---
