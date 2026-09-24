# 339: learns how you like to be talked to. Marks fixed 2026-09-24 ~13:10 UTC; panel never seen by the builder

Written by the month-end thread. Plan: design/v3/30-modes/330r-rebalance-2026-09-24.md (item 3).
Code: scripts/claude_style339_agent.py (install_style339, StyledGen339, detect, apply_prefs), builders and scorer
scripts/claude_style339_run.py, unit tests scripts/claude_style339_test.py (6/6 on the cloud CPU, stub reader and
stub generator).

One change on the 338 agent: feedback about the assistant's replies is saved as a style preference (a separate
kind from facts) in <state_dir>/style339.json and applied to every later reply: one sentence per preference in
338's chat prompt, plus a post-filter on every reply except confirm questions (banned nickname removed, emoji
removed, closing question dropped, "shorter" keeps 2 sentences). Detection = fixed rules (RULES339) that need the
turn to be addressed to the assistant.

Dev evidence before sealing (builder's own hand-written turns, never the panel):
- A 1B label-scoring detector: 15/20 right, leaning to one label; dropped.
- Rules: 36/36 on the 36 turns they were written against (so this number is not a fair estimate), 16/18 on 18
  fresh turns written afterwards with 0/8 false saves, and 0 detections on the 194-turn DEV bank.
- The two fresh misses (a "shorter" wish phrased as "your messages are like paragraphs", and "stop ending
  everything with a question") were NOT patched, so the fresh number stays honest.

## Panel
stylepanel339 (TEST-ONLY, written blind from design/v3/30-modes/339-style-panel-spec.md, audited blind, sealed):
60 three-day lives, 768 turns. 40 feedback lives (5 per preference: shorter, longer, no_nickname, no_emoji,
casual, formal, no_questions, name), 20 control lives with look-alike wording that is not feedback.

## Arms (BensPC, the 336 harness: one sleep per day, kill and restart from the same state dir)
- P = 330a + 334 + 333 + 338 + 339 (claude_style339_run:build_P).
- B = the same without 339 (claude_chat338_run:build_P).
- T = the plain twin (whole chat in its prompt, so it sees the feedback too).

## Marks (P)
| Mark | Bar |
|---|---|
| P339.1 feedback lives where exactly the right preference (and word or name) is saved, and nothing else | ≥ 32/40 |
| P339.2 control lives where any preference is saved | 0/20 |
| P339.3 day-3 replies a blind judge says follow the preference, among the replies where it applies | ≥ 80% |
| P339.4 preferences saved on the 194-turn DEV bank (report of the DEV rehearsal run with P) | 0 |

Report only: P vs B and P vs T pairwise on day 3 (blind, shuffled with seed 339), per-preference results,
"name" lives where the name is used at least once on day 3, fixed-acknowledgement counts.
**Proved wrong if** P339.3 is below 60% (a saved preference is not really followed after a sleep and a restart)
or P339.2 is above 1. Judges are blind Opus agents that see only the preference in words and the replies; never Ben.
