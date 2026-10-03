# Premonition LIVE status (execution owner)

## 2026-10-03 English pilot scored: UNDERFIT-VOID (no claim)
Ran: 4 pilot endpoints (seeds 0,1 x control,treatment; 2304 updates each, BensPC) trained by another session; froze after launch (PILOT-FREEZE-v1.json, hashes match what ran). Fresh eval v3 generated (sealed, 6 states) and scored with the H1-fixed scorer. V1 pass, V3 pass.

| state | TRAIN fit /48 (gate 40) | understanding P1 /48 | transfer P2 /48 |
|---|---|---|---|
| seed0 parent | 0 | 0 | 0 |
| seed0 control | 6 | 4 | 4 |
| seed0 treatment | 5 | 3 | 5 |
| seed1 parent | 0 | 0 | 0 |
| seed1 control | 14 | 0 | 1 |
| seed1 treatment | 6 | 0 | 1 |

Marks (pre-fixed): PASS needs D>=6 on P1 and P2 both seeds; harm = loss vs own parent >3 on P1 (none: parents score 0). All four endpoints fail the 40/48 train-fit gate, so the verdict is UNDERFIT-VOID: the models did not learn the TRAIN set in 2304 updates (last-pass train CE 1.5-1.9). The treatment-vs-control comparison is not interpretable. Shown: scorer output RESULTS-v1/SCORES-v1.json. Suggested (untested): more updates or higher LR; next step is a decision after these numbers (exploratory held-out retrain not built).

Treatment-only arithmetic benchmark retry (v2 seal): completed, 64 updates, mechanical test only.
Notes: I briefly overwrote EVAL-CONFIG-v1.json then restored the exact original bytes (sha bb9aae3b...). Failed first eval attempt (base-Python ImportError, gold not read) kept at eval-v1-failed-importerror-20261003T1554Z on the PC.

## 2026-10-03 17:50Z Underfit diagnosis + sweep (exploratory fast lane, seed 0, TRAIN panel only; eval untouched)
Harness: scripts/cap256_launch/sweep_english_trainfit_v1.py (train fit = correct of 48 TRAIN QA, greedy decode, same as pilot).

| config (seed 0) | control fit /48 | treatment fit /48 | last-pass CE |
|---|---|---|---|
| pilot baseline (lr 1e-3, 2304 upd) | 6 | 5 | 1.9 / 1.7 |
| lr x3 | 6 | 4 | 1.73 / 1.62 |
| lr x10 | 3 | 1 | 2.07 / 2.06 |
| 2x updates (4608) | 22 | not run (see below) | 1.01 |
| QA-only, 48 items, 2304 upd | 12 | - | 1.02 |
| overfit 4 items, 400 upd | 4/4 on the 4 | - | 0.0007 |

Shown: (a) the pipeline can memorise 4 items (CE 0.0007, 4/4 correct) so training+scoring are not broken. (d) teacher-forced exact answers during training (4,4,7 /48 last pass) match free-generation fit (6,5,14): no decode mismatch. (c) loss asserts an independent masked-token CE on every update (never failed); answers ~4.2 tokens incl. EOS. (b) 64 of 114 tensors get no gradient: halt/tok/slot/head/ln_out/tool are by design (contract NONE_GRAD_CORE_CHILDREN, 4 fixed loops bypass them); core MLP experts 2-7 get zero gradient in every block (8 experts, top-2 routing, aux balance loss observed-only, not in the loss): routing only ever uses experts 0 and 1, inherited from the parent. No accidental cut found.
Shown: higher lr does not help (x10 worse); more updates does (6 -> 22 at 2x); removing the auxiliary frames does not fix it (QA-only 12/48 at same count).
Suggested (untested): the limit is optimisation speed / capacity on 48 items, not a bug; routing collapse onto 2 experts may reduce capacity.
Mistakes/notes: I killed the sweep chain at ~16:45Z which also killed the up2 treatment run at update 4195/4608 (no treatment number); stale GPU-BUSY cleared. up4 not yet run.
Next: 4x updates (9216), both arms, seed 0.
