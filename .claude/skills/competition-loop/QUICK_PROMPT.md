# Competition Loop — Quick Prompt

Copy-paste this into a new Claude Code session after submitting a batch:

```
Run the competition loop. I just submitted a batch.

1. Save & tag new requests:
   python scripts/save_competition_requests.py

2. Coverage report:
   python scripts/coverage_report.py
   python scripts/coverage_report.py --gaps

3. Analyze logs:
   python .claude/skills/competition-loop/scripts/analyze_logs.py --hours 2

4. Cross-reference coverage gaps with log errors.
   Prioritize fixes by: Tier 3 first (3x multiplier), then Tier 2, then Tier 1.
   Within a tier, fix highest-request-count task types first.

5. For each issue found:
   - Classifier miss → fix _classifier.py
   - No optimal sequence → write real-requests/optimal-sequence/<task>.md
   - No execution plan → create execution_plans/<task>.py, register in whitelist
   - Deterministic errors → fix the plan
   - Claude errors → fix recipes/*.md and prompts.py gotchas

6. After fixing, replay a tagged request to verify:
   grep -l '"task_type": "<fixed_type>"' competition/requests/*.json
   python scripts/replay_request.py competition/requests/<id>.json

7. Run tests, deploy dev first, then comp. Push.
```
