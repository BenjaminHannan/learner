# slp-363w results: school night inside idle sleep (tiny reasoner, CPU, $0)

**Registered FAIL** on P363w.5: on seed 1 the SCHOOL arm's final reasoner got 20 fewer right answers than its base on
the fixed 600-item panel (bar: not more than 12 fewer). Seed 2: 5 fewer. Not "proved wrong" (the notebook never
changed, no night started inside a turn, and every sabotaged night was rejected). No errors; code hashes match SEAL-code.

| Mark | Bar | Result |
|---|---|---|
| P363w.1 main notebook log unchanged, every idle step and school night | all | pass (26 school nights, 0 changes) |
| P363w.2 school nights inside a user turn | 0 | pass (0) |
| P363w.3 sabotaged nights rejected; SABOTAGE ends on base | all | pass (13/13; both seeds end on base) |
| P363w.4 user replies identical to NOSCHOOL | 4/4 | pass |
| P363w.5 SCHOOL final vs base, fixed panel, right answers | ≥ -12 | **FAIL: seed 1 -20 (156 -> 136), seed 2 -5 (139 -> 134)** |

What happened: the self-check kept all 13 honest nights (7 + 6). Each night's change on the self-check was small
(-5 to +11 of 400), but across the day the reasoner drifted. On the fixed panel it answered more and got more wrong:
raw wrong 167 -> 197 (seed 1) and 109 -> 193 (seed 2); checked wrong 113 -> 139 (seed 1), 43 -> 48 (seed 2).

## Reading (inferred, not tested)
1. ~~The self-check compares each night only with the night before, so small allowed drops add up.~~ [Edit after the
   blind recount: the data do not fit this. Summed over the nights the self-check went UP (right +5 / +10, wrong -5 / -10),
   while the panel fell. Each night used a different self-check set, so the sums are rough.]
2. (Fits the data better.) The self-check is built from the same taught facts as the practice (seven person relations only). It cannot see
   the reasoner getting worse at other kinds of question (places, jobs, counts, pets), which the panel has.
3. At this size (179k parameters, 100 + 100 steps a night) practice on taught facts did not help on the panel.
   Whether it helps at full size is slp-363's question (BensPC, 6th in the queue).
Side note: base seed 2 and the dev base seed 9 have different weights but identical checked panel totals (139/43/418);
the checked totals of a weak model seem to be set mostly by the code fact-check, so raw totals are also reported.

## Suggested next single change (363x, not started)
The self-check also asks a fixed set of general items (another invented world, never the panel), and a night is kept
only if neither set is worse than the reasoner was BEFORE THE FIRST NIGHT (not just the night before).
