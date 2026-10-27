# slp-363w pass marks (registered 2026-09-25 ~11:35 UTC, before the seed 1-2 run)

Ben 11:03 UTC: "Switch to learning, but I think as long as sleep improves the model, it's fine."
Change (one): scripts/claude_slp363w_night.py, a school night after every idle sleep. It builds practice and a
separate self-check set from the loop's own taught rows, trains a copy of the reasoner checkpoint on the practice, and
keeps the copy only if the self-check did not get worse (right -2% / wrong +2% / answers-without-a-fact +2% of the set);
otherwise the copy is moved aside and the old checkpoint stays.
This is the PLUMBING for the practice school, on a tiny reasoner on CPU (100 copy + 100 practice steps per night).
It makes no learning claim: whether practice on taught facts makes the reasoner better is slp-363 (full size, BensPC).
Test: scripts/claude_slp363w_test.py, seeds 1 and 2, arms NOSCHOOL / SCHOOL / SABOTAGE (all with 360 + 367 + 368 + 369).
SABOTAGE is a test fixture: every practice grade replaced by a legal wrong answer, all practice from the night file.

| Mark | Bar |
|---|---|
| P363w.1 main notebook log unchanged on every idle step and every school night | all |
| P363w.2 school nights that start inside a user turn | 0 |
| P363w.3 sabotaged nights rejected, and the SABOTAGE arm ends on the base checkpoint | all (≥ 2 per seed ran) |
| P363w.4 user replies in SCHOOL and SABOTAGE identical to NOSCHOOL | 4/4 |
| P363w.5 SCHOOL final checkpoint on a fixed 600-item panel (363 dry world 9001, never trained on) vs base | right not lower by more than 12 |

Proved wrong if: the notebook changes, a school night starts inside a turn, or any sabotaged night is kept.
Reported, not a mark: honest nights kept, panel gain. The self-check shares facts with the practice (the model
checking itself), and it is noisy: one honest night in dev dropped 16 of 400.

## Disclosures written at seal time
- Dev on seed 9. Run 1 (sabotage = wrong grades at mix 0.5, self-check 200): only 1/7 sabotaged nights rejected; the
  fixture was too weak to hurt the tiny model. Run 2 (sabotage at mix 1.0, self-check 400): 7/7 rejected, all other
  marks pass; SCHOOL kept 6/7 honest nights; panel right 139 base vs 136 school (-3, i.e. no gain at this size).
