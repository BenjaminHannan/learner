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
  never start inside a user turn, leave replies unchanged, throw away a clearly bad night (14/14; one of them only the
  general set caught), and not leave the reasoner more than 12 worse on a fixed panel on two fresh seeds.
- Suggested, not shown: that the general set is what prevents 363w's drift. On seed 3 it rejected nothing (so +7 is
  what 363w alone would give); on seed 4 the 363w-only result was not measured. The only same-seed comparison is the
  unregistered dev run on seed 1 (-5 vs -20).
- Not measured: reply delay (no timing data).
- Not shown: learning. +7 and -4 on 600 items are probably within run-to-run noise (not measured here) for this tiny model (179,093 weights per 363w's train_summary,
  100 + 100 steps a night). Whether practice on taught facts improves the reasoner is slp-363 at full size on BensPC.
- Raw wrong answers on the panel still rose on seed 3 (150 -> 194); the checked answers did not.
- Oddity (untested): on seed 3, nights 2-5 left the self-check and general scores unchanged, so those trained copies
  may have barely changed.
