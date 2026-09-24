# rsn-299 pass marks (sealed before the panel run; 2026-09-24)

Panel: artifacts/claude-thinkpanel299-20260924/items.jsonl. It has 60 blind items (ARITH 14, TIME 10, COUNT 10, COMPARE 10, PLAN 10, UNSURE 6) and a blind Opus key audit found 0/60 mismatches.
Model: openbmb/MiniCPM5-1B (base) on BensPC. Arms P (plain) and T (calculator) come from scripts/claude_rsn299_run.py, with an identical prompt and greedy decoding. The scorer is `claude_rsn299_run.py score` (judge / arith_errors as sealed). Each arm runs once.

| mark | what | pass |
|---|---|---|
| P299.1 | T right − P right | ≥ 12 of 60 (20 points) |
| P299.2 | arithmetic errors in T's shown steps | 0 |
| P299.3 | T wrong answers | ≤ P wrong answers |

"I'm not sure" is counted separately from wrong. On UNSURE items, "not sure" is right and any answer is wrong.
Report only, with no mark: per-category counts, seconds per item, calculator calls, and how many panel questions install_think299's router would send to the think path.

PASS = all three.
**What proves it wrong:** P299.1 < 12, meaning an exact calculator does not add 20 points for a 1B that writes its steps.

Predictions:
- P299.1 is uncertain. On dev it was +5 of 28 (18 points), with 0 items worse.
- P299.2 likely passes.
- P299.3 likely passes.
