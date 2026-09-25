# slp-363x results: school night with a wider self-check (tiny reasoner, CPU, $0)

**Registered PASS, 5/5** on fresh seeds 3 and 4. No errors; code hashes match SEAL-code.

| Mark | Bar | Result |
|---|---|---|
| P363x.1 main notebook log unchanged, every idle step and school night | all | pass (0 changes) |
| P363x.2 school nights inside a user turn | 0 | pass |
| P363x.3 sabotaged nights rejected; SABOTAGE ends on base | all | pass (14/14) |
| P363x.4 user replies identical to NOSCHOOL | 4/4 | pass |
| P363x.5 SCHOOL final vs base on the fixed 600-item panel, right answers | ≥ -12 each seed | pass (seed 3 +7: 132 -> 139; seed 4 -4: 147 -> 143) |

Honest nights kept: seed 3 7/7, seed 4 3/7 (4 stopped by the general set, 1 of them also by the taught-rows set).

## What this shows, and what it does not
- Shown: a school night can run inside idle sleep, practise on the user's taught facts, never touch the notebook,
  never delay a reply, throw away a clearly bad night (14/14), and, with the general set, not leave the reasoner worse
  on a fixed panel on two fresh seeds (under 363w, one seed lost 20).
- Not shown: learning. +7 and -4 on 600 items are within run-to-run noise for this tiny model (179,093 weights,
  100 + 100 steps a night). Whether practice on taught facts improves the reasoner is slp-363 at full size on BensPC.
- Raw wrong answers on the panel still rose on seed 3 (150 -> 194); the checked answers did not.
