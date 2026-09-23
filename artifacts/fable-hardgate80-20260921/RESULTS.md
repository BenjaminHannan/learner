# Experiment 80 — results: noise-mismatch stress of the live sleep recipe

One change vs exp 46 (live recipe: robust loss eps=0.10 + harden-before-gate,
imported read-only): the TRUE number of wrong teacher answers in 20 episodes
sweeps 0, 2, 4, 6, 8, 10, 20 with epsilon fixed at 0.10. Seeds 4101–4103,
3 words each: 21 rows/seed, 63 total. Every installed word: audit 0/60
disagreements and fresh accuracy 1.00.

## Installs per seed (installs /3 words; wrong installs in brackets)

| wrong /20 | 4101 | 4102 | 4103 | pooled /9 |
|---|---|---|---|---|
| 0 | 3 (0) | 3 (0) | 3 (0) | 9 (0) |
| 2 | 3 (0) | 3 (0) | 3 (0) | 9 (0) |
| 4 | 3 (0) | 3 (0) | 3 (0) | 9 (0) |
| 6 | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| 8 | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| 10 | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| 20 | 0 (0) | 0 (0) | 0 (0) | 0 (0) |

Wrong installs over all 63 rows: 0.

## Marks

- J1 replicate (0/2/4: 9/9 each, 0 wrong): PASS. Overlapping seeds 4102/4103
  match exp 46 on all 24 shared rows for installed/fresh-accuracy/audit/
  routed-chain/chosen-updates (cv_table differs in 7/24 cells, see deviations).
- J2 measure (6/8/10, no gate): 0/9 installs at each level, 0 wrong installs,
  on every seed (0/3 each). The gate refuses; it never installs wrong.
- J3 nonsense (20/20): 0/9 installs, 0 wrong installs: PASS (safety holds).
- J4 breakpoint: none up to 10/20 — no wrong install occurred at any level.
- J5 time: 276 s wall for the 3-seed wave (rows 200.7 s + base 58.3 s),
  Mac CPU, one process at a time: PASS (< 30 min).

Predictions: P80.1 TRUE, P80.2 FALSE (predicted >= 7/9 installs at 6 wrong;
got 0/9 — the gate refused everything; the 0-wrong-installs half held),
P80.3 TRUE, P80.4 TRUE, P80.5 TRUE. Brier: 0.0625, 0.36, 0.16, 0.09, 0.01.

## What it means

A human teacher who slips occasionally (up to ~1 lesson in 5 wrong) can
still teach a new word from 20 examples. When ~1 lesson in 3 is wrong, sleep
learns nothing instead of learning something wrong — refusal, not error.

## What it does not mean

The cliff sits between 4 and 6 wrong of 20 (5/20 was not tested, so the edge
is located only to +-1 lesson); 20/20 is still the only nonsense tested;
toy village, no language — nothing here says how this scales to real words.

## Deviations

1. Brief's "15/15" is exp 46's 5-seed batch size; this wave runs 3 seeds, so
   PASSMARKS.md sealed J1 as 9/9 per level (pooled 27/27) before the run.
2. Mode tag "hard80-wrong{W}" (vs 46's "hard-wrong{W}") feeds the
   fold-shuffle and batch-sample RNG, so cv_table differs from exp 46 in 7 of
   24 overlapping cells; episodes, gate, and all install decisions identical.
3. No re-runs; no other changes.

## Reproduce

W=worktree root; A=$W/artifacts/fable-hardgate80-20260921; cd $W/scripts;
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; for s in 4101 4102 4103; do uv
run --offline --no-project --python 3.12 --with torch --with numpy python -B
fable_hardgate80_noise.py --seed $s --out $A/runs; done (sequential, ~5 min).

Questions for Ben: none.
