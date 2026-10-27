# rsn-299b pass marks (sealed before the panel run; 2026-09-24)

This is the one follow-up to rsn-299 (a registered FAIL: +4 of 60 against a bar of +12). The month-end session approved it and set the bar.
ONE change from rsn-299's calculator arm: 5 sampled runs (temperature 0.7, top-p 0.95, a fixed seed per question and sample) and a majority vote on the final answer. An answer needs at least 3 of 5 votes; otherwise the reply is "I'm not sure". The calculator, the prompt and the scorer are unchanged.

Panel: artifacts/claude-thinkpanel299b-20260924/items.jsonl. It is a NEW blind panel of 60 items (ARITH 14, TIME 10, COUNT 10, COMPARE 10, PLAN 10, UNSURE 6) with 0 overlap with the 299 panel. A blind Opus key audit found 0/60 mismatches.
Model: openbmb/MiniCPM5-1B (base) on BensPC, the same commit as rsn-299. Arm P = rsn-299's plain arm (greedy). Arm V = the vote arm (scripts/claude_rsn299b_run.py). The scorer is claude_rsn299_run.score (judge / arith_errors) as sealed for 299. Each arm runs once.

| mark | what | pass |
|---|---|---|
| P299b.1 | V right − P right | ≥ 12 of 60 (20 points; the same bar as P299.1) |
| P299b.2 | arithmetic errors in V's shown steps | 0 |
| P299b.3 | V wrong answers | ≤ P wrong answers (the wrong count must not rise) |

"I'm not sure" is counted separately from wrong and reported for both arms. On UNSURE items, "not sure" is right and any answer is wrong.
Report only, with no mark: per-category counts, how many V items had no 3-of-5 majority, seconds per item, and calculator calls.

PASS = all three. If it passes, install_think299b (scripts/claude_think299b_agent.py) goes to the month-end session. If it fails, the reasoning row reports FAIL and the rsn line stops for September.
**What proves it wrong:** P299b.1 < 12, meaning voting over 5 calculator runs does not add 20 points over the plain 1B.

Predictions: P299b.1 is unlikely to pass (299 gained +4; voting mostly adds "not sure", and most 299 misses were setup errors that all samples may share). P299b.2 likely passes. P299b.3 likely passes, because disagreement turns into "not sure" rather than a wrong answer.
