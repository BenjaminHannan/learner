# Addendum A19 (6:09 AM ET 10-12): GW-PC, move the flatness from the temperature into the add-on

Written before any GW-PC code runs. Commit time = seal (the shared folder is unreadable tonight).

## Why
- Shown (A17): the T0 parent ignores the view; its start is a do/up habit that a view-blind sampler matches.
- Shown (A18): GW-P8's 8 nights added only +0.40 / +0.58 unlocks; the temperature stayed ~20 the whole run; each night's policy
  step was small (approx KL 0.004-0.010 a night, 3-11% of ratios clipped, nights 1-3 of both seeds).
- Suggested (API judge, Fable 5.1 + Opus 5.5): dividing the word log-probs by T ~20 shrinks every policy step about 20x; the fix is to
  put the T0 policy into the weights, then learn at T = 1.

## The one change (`--start distil`, else exactly GW-P8's command and code)
1. T0 is fitted as before (A13).
2. Distil day (day 50, practice worlds 1,000,000 + seed x 10,000 + 5,000 + i, i < 64; never quiz, sealed or a night's day): the
   parent plays 64 episodes at T0; 4,096 of their views (even subsample) are split 90/10 into train / held-out. Target p = the
   parent's softmax(log-probs / T0) on each view. The add-on alone is trained at T = 1 to minimise KL(p || softmax(log-probs)),
   Adam lr 1e-3, minibatch 256 (chunks of 64), grad-norm clip 0.5, up to 12 passes, stopping early once held-out KL <= 0.05 nats.
3. From then on T = 1 (still learned each night, as in A13), and the run is GW-P8: night-0 quiz, 8 fixed nights of PG on the add-on.

## Marks (both seeds 200 and 201; on the Mac, scored there; paired by map against the Mac's GW-P8 After files)
| Mark | Pass | Proved wrong |
|---|---|---|
| PC-0 setup check (not the idea) | held-out KL after distilling <= 0.10 nats AND night-0 quiz within 3 points of GW-P8's (16.90 / 15.63) | either fails: the run is not a test of the idea; report and fix the setup |
| PC-1 the idea | GW-PC After - GW-P8 After >= +0.5 with interval low > 0, both seeds | < +0.1 on both seeds |
| PC-2 the mechanism | mean approx KL per night (nights 1-8) >= 5x GW-P8's on the same seed | < 2x on both seeds |
Carried, reported with their A15 bars: Q-1 After - Before_T0 >= +1.0; Q-2 >= the stronger PPO at equal moves; Q-3 wood pickaxe
>= 10%; GW4 old skills (routed); GW5 audit (rows of the distil day allowed, kept_by 'distil', day 50).
A near-miss counts as a pass for PC-1 only within 0.05. Two seeds = a screen; a confirm needs 6 paired seeds.

## Outcomes
- PC-1 pass: confirm on 6 seeds, then try the cross-night archive of unlock moves (API judge's second idea).
- PC-1 proved wrong while PC-2 passes: bigger steps alone do not help; the bottleneck is elsewhere (credit or exploration).
- PC-2 proved wrong: the distilled add-on still takes small steps; look at the add-on's capacity (rank 8) before anything else.
