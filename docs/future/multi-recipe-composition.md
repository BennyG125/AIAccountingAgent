# Future Investigation: Multi-Recipe Composition

> Saved: 2026-03-21. Use this prompt to resume in a future session.

## The Question

Some competition tasks may require the agent to combine multiple recipes in a single request. For example:
- "Create a customer, then create an invoice for that customer" (recipes 01 + 06)
- "Create an employee, grant entitlements, create a project, register hours" (recipes 02 + 08 + 16)
- "Create a supplier and register a supplier invoice" (recipes 03 + 11)

Currently each recipe is written as a standalone sequence. The agent is smart enough to chain them (it reads all 20 recipes in the system prompt), but we haven't explicitly tested or optimized for multi-recipe tasks.

## Potential Issues

1. **Redundant prerequisites**: Recipe 06 (invoice) includes "POST /customer" as step 1. If the task already created the customer via recipe 01, the agent might create a duplicate customer.
2. **ID passing between recipes**: The agent needs to carry entity IDs from one recipe's output into the next recipe's input. This works naturally in the agentic loop, but the recipes don't explicitly say "if a customer was already created, use that ID".
3. **Call count optimization**: A composed task should use fewer total calls than summing the individual recipes, since prerequisites are shared.

## Session Prompt

Paste this into a new Claude Code session to resume:

```
I need to investigate whether our AI Accounting Agent handles multi-recipe composition well.

Context: Our agent has 20 recipes in recipes/*.md, each describing the optimal API sequence for a single task type. Some competition tasks require combining multiple recipes (e.g., "create customer + invoice" uses recipes 01 + 06).

Questions to answer:
1. Read the current recipes and identify which ones share prerequisites (customer, employee, department creation)
2. Check competition ground truth in tests/competition_tasks/ for tasks that span multiple recipes
3. Look at LangSmith traces (use agent-debugger skill) for multi-step tasks to see if the agent handles composition well or wastes calls on redundant prerequisites
4. If there's a problem: should we add "composition hints" to recipes (e.g., "if customer already created, skip step 1"), or is the agent already smart enough?

Start by reading CLAUDE.md for project context, then check the recipes and ground truth fixtures.
```
