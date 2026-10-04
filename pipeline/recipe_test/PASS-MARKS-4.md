# Round 4: more composed two-step training wording (2026-10-04, fast lane). Marks fixed before training

Base = round-3 TWO (copy path + half composed wording + contextual reader, real modules, fresh weights, 4 loops, 3000 x 16, chain labels). Ordered read stays out.
ONE change: two-step training wording. Arm COMP = the same fixed 3,378 frames PLUS about 11,000 composed frames (`gen_two_v.py`): narrative / question-first / table / distance layouts
built from interchangeable parts (6 openers, 6+6 gain/loss clauses, 6 links, 6 questions, 5 question stems, 4 table headers x 5 separators x 5+5 row verbs, distance objects x units x clauses).
Frames sharing a sentence or word 6-gram with any eval frame are dropped. Nothing else differs (same seeds 0-5, same optimiser, same 30% one-step items).
Baseline: the six TWO runs from round 3 (`results3/two-copy-ctx-mix-seed0..5`), same eval, same seeds, so the comparison is paired and costs nothing to re-run.

## Eval = round 3's 192 fresh two-step questions (unchanged; `gen_two_r3.build_eval`, seed 20261301, `fits` cap 49 tokens). Eval frames never used for any training choice.
## HEADLINE: chain rate on all 192, paired gain COMP minus TWO (6 seeds, t = 2.571).
PASS: mean gain >= +10 AND interval lower bound > 0. FAILS: mean gain < +4. Otherwise partial, no claim.
Gate: COMP train fit (last 192 two-step training items, chain) >= 70%, else UNDERFIT-VOID.
Reported with no mark: table-layout and question-first chain, call 1 right, call 2 given call 1, seed SD.
Wrong-if: gain <= 0 would say wording variety is not what limits two-step (then suspects are the 4-loop depth or the 3000-update budget).
Budget: <= $1.2 (credit $2.56 at 12:50 UTC 10-04; ~$1 stays for two stopped disks).
