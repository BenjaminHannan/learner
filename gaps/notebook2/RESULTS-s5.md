# Notebook-2 Stage 0, arm S5 (fact cards), Amendment C

Labels: **shown** = measured on this sample, with Haiku (claude-haiku-5-5, effort low, Message Batches) as stand-in card writer; **untested** = anything beyond (local writer model, other datasets, roll-up cards, answer accuracy).

Setup: 9,256 unique sessions (sha1 of session JSON) across 217 questions, 190,859 cards (188,162 with a valid U-tag; 2,697 mapped to turn 0). Rankings: BM25 + bge-small over raw pairs and over cards, fused by RRF k=60, context = raw pairs only, 8k budget. S2 reused from stage0_rows.jsonl where present, else recomputed.
Actual writer cost: $4.53 (34.3M in / 11.3M out tokens; the $1.96 plan estimate assumed 300 output tokens/session, real mean was about 1,200). Under the $5 cap.

## Results (shown)
| set | n | S2 AllHit | S5 AllHit | S2 EvRecall % | S5 EvRecall % | S5 wins / losses vs S2 |
|---|---|---|---|---|---|---|
| (a) overall | 111 | 101 (91.0%) | 98 (88.3%) | 93.2 | 91.4 | 5 / 8 |
| (a) knowledge-update | 19 | 19 (100.0%) | 14 (73.7%) | 100.0 | 86.8 | 0 / 5 |
| (a) multi-session | 15 | 8 (53.3%) | 11 (73.3%) | 75.4 | 84.3 | 3 / 0 |
| (a) single-session-assistant | 20 | 20 (100.0%) | 19 (95.0%) | 100.0 | 95.0 | 0 / 1 |
| (a) single-session-preference | 20 | 17 (85.0%) | 18 (90.0%) | 80.8 | 86.7 | 2 / 1 |
| (a) single-session-user | 18 | 18 (100.0%) | 18 (100.0%) | 100.0 | 100.0 | 0 / 0 |
| (a) temporal-reasoning | 19 | 19 (100.0%) | 18 (94.7%) | 100.0 | 94.7 | 0 / 1 |
| (b) multi-session | 121 | 81 (66.9%) | 90 (74.4%) | 82.2 | 87.6 | 16 / 7 |

Deltas (S5 - S2, AllHit count): (a) overall -3 of 111; (b) multi-session +9 of 121
Amendment C pass (b >= +15 AND a >= +2): FAIL
Amendment C wrong-if (b <= +3): not triggered

## Verdicts (shown, this sample)
- Pass rule NOT met: (b) multi-session +9 (needs +15) and (a) overall -3 (needs +2).
- Wrong-if NOT triggered: (b) +9 is above +3. So S5 is neither a pass nor refuted; it helps multi-session (16 wins / 7 losses on (b); (a) multi-session 8 -> 11) but hurts (a) overall.
- Where it hurts (a): knowledge-update 19 -> 14 (0 wins, 5 losses). Suggested, not tested: card hits crowd out the raw pairs that BM25/dense over pairs would have ranked first, and the extra two rankings dilute the fused order for questions where S2 was already at ceiling.
- Roll-up cards (the step conditional on a pass) were not run.
