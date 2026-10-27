# 381b pass marks (month-end line, fixed 2026-09-25 ~03:55 UTC, before the new set is judged)

Change (one follow-up to 381, VERIFY-381.md): scripts/claude_e2e381b_harness.py:confirm_answer381b = 381 plus alias
groups (boss/manager, sibling, nan), relation head words, relation-word owners, two family chains for the user, a
shorter tail value, and every relation/value split of a "Just to check" question. Built on 381's 73 held-out
questions (now dev): wrong yes 0, right yes 42/43 (the miss: a gerbil asked about as a hamster).

Held-out set: 120 items written blind by a separate agent that never saw any code or this file's rules
(scratchpad j381b/items.jsonl, copied here as holdout381b_items.jsonl after judging), mixing true claims and wrong or
unanswerable ones in the agent's two confirm forms. Two fresh blind Opus judges answer each as the user; a third
decides splits. Marks, same as 381:
| Mark | What | Bar |
|---|---|---|
| H1 | 381b says yes where the judges say no | 0 |
| H2 | 381b says yes where the judges say yes, over the judges' yes | >= 95% |
Report only: 381 and the old 336 harness on the same set.
If 381b passes, it is the harness for banks C and D (0.2 and 0.2b). If it fails, C and D use the old harness and
report 381b's answers alongside (no third follow-up before Sept 30).
