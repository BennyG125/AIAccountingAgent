---
name: optimize-sequences
description: Analyze execution plans, optimal sequences, and recipes against real Tripletex API docs to find optimization opportunities. Logs findings to optimization_log.md without modifying code.
user_invocable: true
---

# Optimize Sequences

Systematically review execution plans, optimal sequences, and recipes to find ways to reduce API calls. Cross-reference against the real Tripletex API documentation. **DO NOT modify any code** — only log findings to `optimization_log.md`.

## Step 1: Read State

Read `optimization_state.json` in the project root. If it doesn't exist, treat offset as 0.

```json
{"offset": 0, "reviewed": [], "cycle": 1}
```

## Step 2: Determine Task Types for This Cycle

The full task type list (alphabetical):
```
bank_reconciliation, cost_analysis_projects, create_customer, create_departments,
create_employee, create_invoice, create_order, create_product, create_project,
create_supplier, credit_note, custom_dimension, employee_onboarding,
fixed_price_project, forex_payment, monthly_closing, overdue_invoice_reminder,
project_lifecycle, register_hours, register_payment, register_supplier_invoice,
reverse_payment, run_salary, travel_expense, year_end_close, year_end_corrections
```

Pick the next 10 task types starting from `offset`. Wrap around if needed.

## Step 3: Dispatch 10 Parallel Agents

Launch 10 agents in parallel using the Agent tool (subagent_type: "general-purpose"). Each agent analyzes ONE task type. Provide each agent with this prompt template (fill in the task type):

---

### Agent Prompt Template

```
You are an API optimization analyst for a Tripletex accounting agent. Your job is to find ways to REDUCE API CALLS for the task type: **{TASK_TYPE}**.

## Your Inputs (read these files):
1. Execution plan: `execution_plans/{task_type}.py`
2. Optimal sequence: `real-requests/optimal-sequence/{task_type}.md`
3. Recipe: Find the matching file in `recipes/` (numbered, e.g. `01_create_customer.md`)
4. Sample real requests: Read 2-3 JSON files from `competition/requests/` where task_type matches
5. API cheat sheet: `api_knowledge/cheat_sheet.py`

## Real Tripletex API Bulk/Batch Endpoints (from swagger.json):
These CONFIRMED bulk endpoints exist:
- POST /product/list — bulk create products (array body)
- POST /customer/list — bulk create customers (array body)
- POST /employee/list — bulk create employees (array body)
- POST /contact/list — bulk create contacts (array body)
- POST /order/orderline/list — bulk create order lines (array body)
- POST /project/participant/list — bulk add project participants (array body)
- POST /project/import — bulk import projects
- POST /activity/list — bulk create activities (array body)

These sub-resource embedding patterns are confirmed:
- POST /order accepts `orderLines` array inline (already used by some plans)
- POST /travelExpense accepts `costs` and `perDiemCompensations` arrays inline
- POST /project accepts `participants`, `projectActivities`, `projectHourlyRates` inline
- POST /employee accepts `employments` array inline

## What to Look For:

### 1. UNNECESSARY SEARCH-BEFORE-CREATE
The sandbox starts EMPTY on each competition submission. If a plan uses _find_or_create()
or does GET before POST, the GET will ALWAYS return empty results on a fresh sandbox.
Consider: Can we just POST directly and only fall back to GET on 422/conflict?
NOTE: Be careful — some GETs are for REFERENCE DATA (departments, vatTypes, accounts)
that DO exist in fresh sandboxes. Only flag GETs for ENTITIES we're about to create.

### 2. BULK ENDPOINT USAGE
Can multiple sequential POST calls be replaced with a single POST /xxx/list call?
Example: Creating 3 products individually (3 calls) vs POST /product/list (1 call).

### 3. SUB-RESOURCE EMBEDDING
Can child resources be embedded in the parent POST instead of separate calls?
Example: orderLines in POST /order, costs in POST /travelExpense.

### 4. REDUNDANT LOOKUPS
Are there GET calls that could be eliminated by:
- Hardcoding known constants (country ID 162 for Norway, currency ID 1 for NOK)
- Caching results from a previous step
- Using the response from a POST (which returns the created entity with ID)

### 5. PARALLEL CALL OPPORTUNITIES
Are there sequential API calls that have no data dependency and could be made in parallel?
(Note: The deterministic executor is synchronous Python, so "parallel" means identifying
calls that COULD be parallelized if we add async support.)

### 6. RECIPE vs EXECUTION PLAN INCONSISTENCIES
Does the recipe describe a different sequence than what the execution plan implements?
Are there optimizations in one that aren't reflected in the other?

### 7. OPTIMAL SEQUENCE ACCURACY
Does the optimal sequence document accurately reflect the CURRENT execution plan code?
Are the call counts still correct?

## Output Format

Return your findings as a structured report. For EACH finding:

```
### Finding: [SHORT_TITLE]
- **Task Type:** {task_type}
- **Component:** execution_plan | optimal_sequence | recipe | cross-cutting
- **Optimization Type:** skip_search | bulk_endpoint | embed_subresource | eliminate_lookup | parallelize | inconsistency | accuracy
- **Current API Calls:** N
- **Proposed API Calls:** M
- **Savings:** N-M calls
- **Confidence:** HIGH | MEDIUM | LOW
- **Details:** [Specific description of the optimization]
- **Current Code/Sequence:** [Quote the relevant lines]
- **Proposed Change:** [Describe what would change]
- **Risk:** [What could go wrong]
- **Files Affected:** [List of files]
- **API Reference:** [Relevant endpoint from swagger/cheat_sheet]
```

If you find NO optimizations, still return a report saying the task type is already optimal
and why.

IMPORTANT: Read ALL the files before making recommendations. Do NOT guess — verify against
the actual code and API docs.
```

---

## Step 4: Collect Results and Log

After all 10 agents complete, append their findings to `optimization_log.md` in the project root. Use this format:

```markdown
---

## Cycle {N} — {YYYY-MM-DD HH:MM}

**Task types analyzed:** [list]
**Total findings:** N
**Total potential savings:** M API calls

{paste each agent's findings here}
```

## Step 5: Update State

Update `optimization_state.json`:
- Increment offset by 10 (wrap around at 26)
- Add analyzed task types to `reviewed` list
- Increment cycle count

## Important Rules

1. **NEVER modify execution plans, recipes, optimal sequences, or any code**
2. **ALWAYS read the actual files** before dispatching agents — don't assume content
3. **Include ALL metadata** in log entries — timestamps, file paths, line numbers
4. **Cross-reference the real API docs** — the swagger confirms which bulk endpoints exist
5. If an agent fails or times out, log that too — don't silently skip
