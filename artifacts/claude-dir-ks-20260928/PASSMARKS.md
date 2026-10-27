# Keep old skills after a maze day: PASS MARKS (Lead 0, blend, Lead 2)

Written 2026-09-28 (`date -u` at sealing is in the commit), before any run of these tests. Helper: Director helper "keep old skills", Claude. Code: `scripts/claude_dir_ks_run.py` (runner), `scripts/claude_dir_ks_net.py` (Lead 2 plug-in), `scripts/claude_dir_ks_marks.py` (this file's rules as code, self-tested). Sealed files (`claude_fewex_bench.py`, `claude_fewex_eq_bench.py`, `claude_fewex_data.py`, `claude_fewex_net.py`) are imported and never edited. Serves finish-line items 5 and 4 (sleep keeps old skills; skills learned first help). Not H6 (sleep length): every sleep here is the harness's 512 updates.

**Scope.** Practised loop only, seeds 0 and 1, dev panels only (the ruler's holdout is never opened). The small card experiments and the village model are out of every claim. Counts are "x of 200" (fixed old panels `D.old_panels()`), "x of 300" (9x9 dev mazes), "x of 32" / "x of 128" (the store).

**Cells.** 4 cells = seed {0,1} x maze day {k = 64 mazes, k = 16,384 mazes}. P = the pre-maze net (`k0.pt`, the qualified source). A = the adapted net after the maze day (`k64.pt` or `k16384.pt`).

## Start points
Ruler checkpoints on the Mac are used only if their dev 9x9 count equals the committed `eq-runs/loop-s{seed}-pre/adapt.json` count for that rung. Otherwise `prep` rebuilds rung 64 and 16,384 with the harness's own functions (same route as `claude_fewex_distill_sleep.py rebuild`); rebuilt nets are labelled and every comparison in this test uses the same nets for every arm. Rungs 1, 4, 16, 256, 1024, 4096 are only needed for the F rows; if they are missing the F rows are "not measured" and the blend cannot PASS (below). `prep/s{seed}.json` records the origin and hash of each net.

## Lead 0 (diagnostic, eval only, no training)
One change: revert one parameter group of A to P's weights, score. Groups (every tensor in exactly one; checked by the selftest): E (token and slot embeddings), B0, B1 (the two shared blocks), RD (output norm + answer head), ST (state norm + stop head). Report-only split of the blocks: ATT (attention, biases, their norms) and MLP. Report-only "only-g" rows (P with just g taken from A).
For each cell and group: `rec_kind` = revert score minus A's score on that kind (of 200); `loss` = A's 9x9 minus the revert's 9x9 (of 300); `room` = max(10% of (A9 - P9), 17).
A group is **localised** in a cell if `rec_sums4 >= 20` and `rec_grids5 >= 20` and `loss <= room`.
- **LOCALISED**: one partition group (E, B0, B1, RD or ST) is localised in at least 3 of the 4 cells. Reading: forgetting sits somewhere the maze skill does not; that group is where to protect or freeze.
- **ENTANGLED (the result that proves the lead wrong)**: in all 4 cells, no group (including ATT and MLP) has `rec_sums4 >= 20` and `rec_grids5 >= 20` with `loss <= room`.
- Anything else: **MIXED, not shown** either way.
Lead 0 makes no skill-gain claim, so checklist rows 4 to 6 do not apply to it; it only says where to look.

## Blend (eval only, no sleep, no training)
One change: weights = (1 - a) x P + a x A, a = 0, 0.1, ..., 1.0 (a = 0 is P, a = 1 is A, exactly; selftest). Per cell all 11 points are scored on the fixed old panels and the dev 9x9 (report).
**Picking a uses the store only.** Store = the first 16 stored sums and 16 grids (`D.replay_old()[kind][:16]`, scored as x of 32) and the first 128 layouts of the seed's maze pool (x of 128), all disjoint from every panel. Rule, fixed now: eligible a = store-maze score >= (store-maze at a = 1) - max(10% of (store-maze at 1 - store-maze at 0), 11); among eligible pick the highest store-old score; ties go to the larger a. The pick is written before any panel score is used for anything (the store scores are in the same record; `pick_alpha` reads only `store`).
At a* (per cell) the gates on the dev panels are:
- G_old: sums4 >= 100 and grids5 >= 100 (half of P's >= 190 of 200; V1 guard).
- G_maze: 9x9 >= A9 - max(10% of (A9 - P9), 17).
- G_fresh (not memorising the store): fresh old panels (200 + 200, `fresh_panel()`, disjoint from store and fixed panel) each >= the fixed-panel score - 20.
A cell is **kept** if all three hold.
**Comparator (fair one).** The blend uses no more than the 16-per-kind store, so the required comparator is the 16-store sleep R16 (harness sleep, store 16, same nets, 3 draws), or A itself if higher: required old-kind bar per kind = max(mean of R16's 3 draws, A) + max(6, 2 x SE), SE = SD of R16's 3 draws / sqrt(3). R128 (128-store, 3 draws, same nets) is reported next to it as the deployed upper reference; it is not required because it sees 8 times more stored puzzles.
**F rows (required, both seeds).** The same store rule is applied at every rung 1, 4, ..., 16384 (its own a*), and the dev 9x9 of the blended net is scored. F_few = mean over rungs 1, 4, 16, 64; F_eq = mean over all 8 rungs (as fractions of 300). Row passes for a seed if F_few(blend) >= max(0.9 x F_few(unblended), 0.08) and F_eq(blend) >= max(0.9 x F_eq(unblended), 0.40). The absolute floors are rows a plain net cannot pass: committed plain practised dev F_eq is 34.04% (seed 0) and 32.62% (seed 1), F_few 2.9% and 1.3%.
- **PASS**: kept in >= 3 of 4 cells, and beats the comparator (both kinds) in >= 3 of 4 cells, and both seeds' F rows pass.
- **PROVED WRONG**: in all 4 cells no a on the whole grid satisfies G_old and G_maze (the research note's own "wrong if").
- Anything else: **NOT SHOWN** (the verdict line names which part missed). A missed pick where some other a would have kept is NOT SHOWN, never wrong.

## Lead 2 (sleep replays the small store weakest-first; run after the blend result)
One change, in `claude_dir_ks_net.py` (harness lines 213-214 replaced): each sleep update draws its 4 stored sums and 4 stored grids from the 16-store with probability proportional to current per-item loss (table refreshed every 16 updates, loss floor 0.001), instead of uniformly. Same 512 updates, same store, same optimizer, same maze and round draws (selftest: with the switch off the plug-in equals the harness sleep bit for bit, and the switch on gives different weights). Arms: WF16 (weakest first, store 16), R16 (uniform, store 16, the fair comparator), R128 (report). 3 draws each, the distill test's draw seeds (seed + k + 0/101/202), all arms share draws. 36 sleeps.
Per cell and kind: d = mean(WF16) - mean(R16) over 3 draws; margin = max(6, 2 x SE), SE = sqrt((var_WF + var_R16) / 3).
- **PASS**: mean d over 4 cells >= 20 on each kind (the distill bar), and d > margin in >= 3 of 4 cells on each kind, and 9x9 after sleep >= R16's - margin in >= 3 of 4 cells, and fresh old panels >= fixed - 20 on both kinds in every cell, and the plain row: 9x9 dev of WF16 at k = 64 >= plain practised net's own sleep64 9x9 dev + 30 (committed adapt.json: 23 and 14) on both seeds.
- **PROVED WRONG**: in both seeds, the mean of d over the two branches is below +5 on both kinds.
- Anything else: **NOT SHOWN**.
F_few / F_eq are not measured for sleep arms (sleep exists only at rungs 64 and 16,384); the 9x9 gate at those two rungs is the stand-in, labelled as such. A PASS here says "keeps old kinds", never "F improved".

## Marks self-check (Ben 21:37 rule), one line each
1. **Bars above noise.** Deterministic eval of a fixed net has no run noise, only panel sampling: binomial SE 7 of 200 (p = .5), 8.7 of 300, so 20 of 200 is 2.9 SE and the 17-of-300 maze slack is 2 SE. For sleeps the measured draw SD (distill RESULTS, `sleeps/`, R128 and R16, 3 draws) is 0.6 to 20.1 of 200 on old kinds and 9.6 to 36.2 of 300 on 9x9; margins use max(6, 2 x SE of these draws). The Lead 2 bar of 20 of 200 sits above every R16 cell SD (max 5.3).
2. **"Every seed" reading.** PROVED WRONG needs all 4 cells (blend, Lead 0) or both seeds (Lead 2) to be clearly below; a mixed picture is NOT SHOWN / MIXED. Yes.
3. **Fair comparator.** Blend and Lead 2 are judged against R16 (same information budget, same nets, 3 draws) and against A; R128 is shown, not required, and the reason is written above. Yes, with that disclosed limit.
4. **Row a plain net cannot pass, and not-memorising check.** F_eq >= 40% floor (plain 34% and 33%), F_few floor 8%, Lead 2 plain row (plain sleep64 9x9 of 23 and 14); G_fresh and the fresh panels check the store is not just memorised. No plain net is re-run here (plain numbers are the committed ruler values; labelled).
5. **F_few beside F_eq** as its own required blend row (both seeds). Lead 2 uses the 9x9 gate as a labelled stand-in; Lead 0 makes no gain claim.
6. **Sleep gates** use the mean of 3 sleep draws and margin max(6, 2 x SE). Yes.

## Process
- A crashed job is re-run unchanged and the crash is reported. Nothing is tuned after any score is seen.
- RESULTS reports every mark with counts and labels claims shown / suggested / untested. The Director's blind recount uses `verdicts.json` inputs (`lead0/`, `blend/`, `sleeps/`, `frows/`) and this file only.
- $0, CPU, fp32, dev panels only.
