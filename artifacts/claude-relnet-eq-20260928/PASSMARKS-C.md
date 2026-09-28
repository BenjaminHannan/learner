# Test C on the equal-practice ruler: the relation net as the loop

Written 2026-09-28 18:51 UTC (`date -u`), before any practice run of this test and before any maze dev or holdout score of the
relation net. No mark changes after this file is committed. The marks are RACE-PASSMARKS.md Test C
(artifacts/claude-fewex-20260927/RACE-PASSMARKS.md, line 11) with RACE-ADDENDUM-1.md's substitution, and the common
gates (line 5) read exactly as the sparse test read them in artifacts/claude-sparse-20260928/ADDENDUM-D1.md.
Thresholds are unchanged. Each seed is judged alone; seeds are never pooled.

## The design (fixed now)
The race's loop, replaced by the relation net of scripts/claude_relnet_net.py, unchanged: 1,644,198 weights (the
loop has 1,645,726: -0.09%), a GRU state for every pair of cells carried across rounds, a mean message, a GRU cell
update and an MLP, the loop's stop head, 48-round cap. No kind label, no maze rule. The one change from the
baseline loop is this net; nothing else moves. It is wrapped for the harness by scripts/claude_relnet_eq_plugin.py
(the plug-in contract of PROTOCOL.md; the baseline Learner and sleep are inherited, only the four-update maze step
is rewritten for the (h, r) state). scripts/claude_fewex_eq_bench.py is not edited.

Last night's GPU practice (artifacts/claude-relnet-20260927/) used a different recipe (6,000 batches, xfer-1
batches, a GPU). Those nets are **not** used. This test trains its own nets with the ruler's recipe.

## Practice (ADDENDUM-3's qualified recipe, as the sparse test ran it)
scripts/claude_relnet_eq_practice.py (a copy of claude_sparse_practice.py with this plug-in): 12,000 batches of 64
source puzzles from the ruler's generator, source RNG 7000000+seed, model seed = seed, AdamW 1e-3 (weight decay
0.1, betas 0.9/0.95), 200-step warm-up then cosine, clip 1.0, fixed depth chosen on source dev SOURCE_SEED+100,
V1 judged on the untouched guard SOURCE_SEED+300, the harness's one-step gradient check. Seeds 0 and 1. fp32 on CPU.
No maze is generated or scored in practice.

## Source guard (before any maze run)
Each seed's practised relation net gets at least 190 of 200 on the guard's 4-digit sums and at least 190 of 200
on its 5x5 grids, and every 2-D weight matrix gets a nonzero fp32 gradient on a sums or a grids batch (the
harness's gradient_check). If either fails in either seed: report it and stop. No maze run.

## How the race runs (no harness edit, mirroring the sparse test)
`python -B scripts/claude_fewex_eq_bench.py adapt --plugin claude_relnet_eq_plugin --arm loop --seed {0,1} --init {pre,fresh}
--source artifacts/claude-relnet-eq-20260928/runs/relnet-s{seed} --out artifacts/claude-relnet-eq-20260928/eq-runs/relnet-{pre,fresh}-s{seed}`,
fp32 on CPU. `--out` and `--source` always point into this folder. Order: all four dev runs first, and no change of
any kind after a dev score is seen; then the holdout once per run with the harness's `holdout` command (which
refuses unless the baseline's EQ-DEV-GATE.json says PASS; it did, artifacts/claude-fewex-20260927/RESULTS-EQ.md).
"The loop" and "the practised plain net" are the baseline's `eq-runs/loop-s{seed}-pre` and
`eq-runs/plain-s{seed}-pre` (adapt.json, holdout.json), not retrained. "The relation net's own fresh copy" is this
plug-in with `--init fresh` (the harness's seed 900000+seed).

## Pass, in both seeds
1. `F_eq` at least **10 points above the loop**.
2. `F_eq` at least 5 points above the practised plain net, and at least 5 above the relation net's own fresh copy.
3. Old kinds before maze adaptation (`old.before`: 200 sums4, 200 grids5): at least 190 of 200 each, and not more
   than 6 of 200 below the loop's `old.before` on each kind.
4. After the k=64 sleep and after the k=16,384 sleep (`sleep.64.old`, `sleep.16384.old`), each old kind not more
   than 6 of 200 below the loop's same record. Being above the loop always passes.
5. Stored weights within 2% of the loop (1,644,198 vs 1,645,726).
Learned stopping keeps the 48-round cap and the source-selected fixed-depth check; raw example memory and rounds are
disclosed.

## Proved wrong (REJECTED)
- `F_eq` no higher than the loop in both seeds (a tie counts as no higher); or
- a maze gain made only by breaking an old-kind gate: in any seed where the relation net's `F_eq` is above the loop's,
  at least one of marks 3-4 fails. (Mazes are compared through `F_eq` only, as the sparse test read it.)

## Verdict words
PASS if marks 1-5 hold in both seeds. REJECTED if a proved-wrong condition holds. Otherwise NOT PROMOTED, with the
failing marks named per seed.

## How the numbers are read (fixed now)
- `F_eq`: the mean over the eight positive rungs k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384 of 100 x right / 300 on
  the 9x9 holdout, learned stop (ADDENDUM-4, RACE-ADDENDUM-1). Differences are in percentage points.
- Fixed-depth check: a learned-stop score more than 2 points below the source-selected fixed depth is a stop
  failure; it is reported for every rung.
- The report script is scripts/claude_relnet_eq_race.py (a copy of the sparse race script with this design's names).
  If the baseline is INCONCLUSIVE the holdout stays sealed; it is PASS, so this does not arise.

## Report only (no mark)
E50 (the smallest rung with at least 150 of 300 on 9x9), the 7x7 and 11x11 panels, mean rounds and cap hits, the
fixed-depth check, training and adaptation time, stored weights, raw example memory (the harness's replay only).
Also: whether last night's decay at a forced 48 rounds on sums shows up. It is read from the untouched guard
(SOURCE_SEED+300, 200 sums4) as the count right at fixed depths 8, 16, 32 and 48
(`guard_fixed_right_by_depth` in source.json), and per rung from the 9x9 fixed-depth scores.

## Compute (disclosed before any run)
CPU only, at most 3 cores across all my jobs, $0. No GPU and no rental. The relation net costs about 4-6 times the
loop per step at 7x7-11x11 (artifacts/claude-relnet-20260927/REVIEW.md, shown), so the ladders are expected to be
much slower than the sparse test's; if a measured estimate says a dev ladder cannot finish, I report it and do not
change the recipe.
