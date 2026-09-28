# T2 pass marks: does it help when the model picks which 16 old puzzles go into its sleep?

Written 2026-09-28 22:13 UTC (`date -u`) by Director helper "sleep tests sealer" (Claude). Sealed before any sleep of this test has run:
`ls artifacts/claude-dir-t2-selfpick-20260928/` holds no `sleeps/` folder, and no `s*-k*-PICK-*.json`, `-HARD-` or `-R16b-` record exists anywhere in the
repo (grep at 22:13 UTC). Marks are never changed after a score is seen. Marks as code: `scripts/claude_dir_t12_marks.py` (selftest: 12 cases pass).
Reasons for every number: DESIGN.md. Seal hashes: SEAL.md and SEAL-code.sha256.txt.

Scope: the practised 1.6M-weight loop reasoner of the fewex harness (the distill and keep-old-skills tests' net), code-made sums and Latin grids as the
old kinds, dev maze panels as the day's new kind. It is not the small card experiments and not the village model. Training data: code-made only.
Cells: 4 = seed {0, 1} x maze day k {64, 16,384}. Every cell, every arm: 3 sleep draws (draw seeds seed + k + 0 / 101 / 202, as the distill and ks tests).
Counts are "x of 200" (fixed old panels `D.old_panels()`: 200 sums4, 200 grids5) and "x of 300" (9x9 dev mazes).

## The one change
Which 16 stored puzzles per kind go into the sleep store. Everything else is the harness's own sleep (512 updates, 4 stored sums + 4 stored grids + 8 day
mazes per update, loss .25/.25/.5, same optimizer, same round draws, same maze draws). All arms run from the same start net in the same code path
(`claude_fewex_distill_sleep.sleep`, mode R), so arms differ in the store only.

| arm | store per kind (from the 128-puzzle pool of `D.replay_old()`, which is code-made and i.i.d.) |
|---|---|
| R16 (= "A", the fair comparator) | the first 16: today's small-store sleep, a random 16 |
| R16b (noise measure, no verdict) | items 16 to 31: a second random 16 |
| PICK (= "B", the change) | the model's own choice: the 8 highest-loss and the 8 lowest-loss pool items by the post-maze net's own cross-entropy at round 16 |
| HARD (= "C", control) | the 16 highest-loss pool items (tells "picks failures" from "picks something") |

Why not "8 wrong and 8 right" as first drafted: after a maze day the net gets **0 of 200** on both old kinds in all 4 cells (shown: `artifacts/claude-distill-20260928/rebuild/loop-s*-pre/rebuild-k*.json`
`old.after_*`, and the committed `artifacts/claude-fewex-20260927/eq-runs/loop-s*-pre/adapt.json`). There are no "right" answers to pick. The per-item loss still orders the puzzles, so PICK uses that; whether it got each
item right at its learned stop is recorded (report only). This is a disclosed change from the draft TESTS.md.

## Comparator (the fair one)
The higher of (no sleep after the maze day) and (R16). No sleep scores 0 of 200 on both kinds in every cell, so the comparator is R16 (3 draws, same nets, same code). R16b is not a comparator; it measures how far
the score moves when only "which 16" changes. R128 (128 stored, the deployed sleep) is not run here; it is an upper reference (distill: 42 to 174 of 200) and, if the keep-old-skills jobs wrote R128 records on the same nets, the report table shows them.

## Marks (kinds are judged separately; d = mean of PICK's 3 draws minus mean of R16's 3 draws in a cell)
Per cell and kind: margin = max(6, 2 x SE), SE = sqrt((var of PICK's draws + var of R16's draws) / 3).
- **M1 (the gain, both kinds):** mean of d over the 4 cells >= **12 of 200 on sums4 and >= 16 of 200 on grids5**, AND that mean >= 2 x (the mean over cells of |R16b - R16|, the "which 16" spread, measured in this run), AND d > margin in at least 3 of 4 cells.
- **M2 (not memorising 16 puzzles):** in every cell and both kinds, PICK's score on the fresh old panels (200 + 200, never stored, `fresh_panel()`) >= its score on the fixed panels - 20.
- **M3 (F_few row, its own required row; the sleep runs at k = 64 in the few-example range, so this row is scored at k = 64 only):** at both k = 64 cells, PICK's 9x9 dev maze count (mean of 3 draws) >= R16's - margin AND >= (the committed plain practised net's own sleep at k = 64: 14 of 300 on seed 0, 9 on seed 1) + 30. A plain net cannot pass the second half.
- **M4 (F_eq row, its own required row; stand-in at the large-day rung k = 16,384):** at both k = 16,384 cells, PICK's 9x9 (mean of 3 draws) >= R16's - margin.
Labels: M3 and M4 are one-rung stand-ins for F_few (rungs 1 to 64) and F_eq (all 8 rungs); a sleep exists only at k = 64 and k = 16,384, so a full F_few or F_eq is not measured. This is the precedent the keep-old-skills marks set.

**PASS = M1 on both kinds, and M2, M3, M4.** It says: choosing the 16 by the net's own loss beats a random 16 by more than sleep-draw noise and "which 16" noise, keeps the maze skill, and is not memorisation. It does not say PICK matches the 128-store.
**PROVED WRONG (the every-seed reading):** for BOTH seeds, the mean of d over that seed's two branches is below +5 of 200 on BOTH kinds. A seed that gains but breaks M2 to M4 is not "wrong": it is NOT SHOWN.
**NOT SHOWN:** anything else, with the verdict line naming which part missed.
**VOID:** any arm PICK, R16 or R16b has fewer than 3 draws in a cell. A dead job is re-run unchanged and its crash reported; a cell is never dropped or replaced.

## Control reading (fixed now, decides nothing)
HARD is scored the same way against R16. If PICK passes and HARD's mean gain is within 12 (sums) / 16 (grids) of PICK's: "picking the failures is enough; the 8 easy ones add nothing" (suggested). If PICK passes and HARD is more than that below: "the mix matters" (suggested). If HARD passes and PICK does not: "hardest-only helps, the mixed pick does not". Literature warns that a hardest-only tiny buffer can overfit (`design/research/standing/06-...md` Q2, tags A), so HARD failing M2 is an expected way for it to lose.

## Report only (no mark)
Every arm, cell and draw: old (200), fresh old (200), 9x9, 7x7 and 11x11 maze counts; the start net's old scores (should be 0); the picked indices, their losses, the pool's loss range, how many pool items were right at the learned stop, overlap of PICK's picks with the first 16; R16b - R16; PICK - HARD; PICK against R128 if present; seconds; sha256 of start nets and teacher.

## What this does not license
Nothing about the card experiments or the village model; nothing about stores larger than 16; nothing about who should choose (a person, a critic head, the model over more days). A PASS is a reason to build a "the model writes its own store" step, which needs Ben's yes. The pick here reads the store's own true labels (as every arm does); it tests choosing, not labelling.

## Marks self-check (Ben's list, one line each; H8 checklist)
1. **Bars above the measured run-to-run noise.** Three-draw sleep spread (SD across draws), recounted by me from `artifacts/claude-distill-20260928/sleeps/*.json` (60 records): R16 old kinds: sums4 SD 1.5 to 3.8 (mean 3.0), grids5 0.6 to 5.3 (mean 2.8), 9x9 14.6 to 35.2 of 300 (mean 22.0); D16: up to 7.0 and 9.5; R128: up to 20.1 (sums4). Bars 12 and 16 are 3 x the largest R16 SD (3.8, 5.3), rounded up, so above every measured cell SD by 3 times. "H6's S re-run spread": **no such re-run exists yet** (`ls artifacts/claude-dir-h6-sleeplen-20260928/` at 22:13 UTC: no `runs/`, no dirh6 JSON; its arm B and re-runs have not run). The nearest measured spread of the nights harness, recounted from `artifacts/claude-slp358n3-20260927/runs/s13..s16/*.json`: the same arm on different nights SD 11.2 (sums) and 11.7 (grids) of 400; arms that should barely differ (R minus N, 12 cells) SD 10.3 and 19.7. Those are about the 3-night reasoner (T3), not this sleep. This test measures its own "which 16" spread (R16b) and the rule above uses it.
2. **Every-seed reading:** PROVED WRONG only if both seeds are below +5 on both kinds; a non-win is NOT SHOWN. Yes.
3. **Fair comparator:** R16 = the higher of R16 and no-sleep (no-sleep is 0 of 200). R128 shown as an upper reference, not required (it stores 8 times more). Yes.
4. **A row a plain same-size net cannot pass, and not just memorising:** M3's plain floor (14 and 9 of 300 committed; loop must be >= plain + 30) and M2 (fresh panels). Disclosed limit: no plain net is re-run with a 16-store; the committed plain sleeps use the 128-store, where the plain net keeps 198 / 133 and 196 / 110 of 200 (sums4 / grids5, `eq-runs/plain-s*-pre/adapt.json`), so an old-kind row a plain net cannot pass does not exist at this store size and is not claimed.
5. **F_few beside F_eq:** M3 and M4, each its own required row (stand-ins, labelled above).
6. **Sleep gates use the mean of 3 sleep draws, margin max(6, 2 x SE):** yes (M1, M3, M4).

## Predictions (before any run; guesses, not results)
PASS 15%. PROVED WRONG 45%. NOT SHOWN 40%. The largest single risk: after a maze day the net has forgotten the old kinds entirely, so its loss ordering of the pool may be near-random (then PICK, HARD and R16 tie).

## Blind recount
A separate step, given only this file and the raw `sleeps/*.json` (and R16 from the same folder), recounts every mark before RESULTS.md is written. `python3 scripts/claude_dir_t12_marks.py report t2` is the same rules as code; the recount must not read it first.
