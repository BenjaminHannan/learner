# State lab: pass marks (fixed before any run, 2026-10-23)

Question: can the village model D make better use of its looped think state (76 rows x 128, Think block looped <= 8 times,
register 0 drives ASK and HALT)? FULL v1 uses 2.27 loops of 8 on dev, 2.08 on validation; first-ASK gold recall@4 is 76% dev
vs 60% validation (design/v1/results2/full/final_dev.json).

All arms: D ALONE (no creative model, no bridge), FULL recipe (Muon + S2), same data build as v1, same seed 0, 6,000 steps
(half of v1's 12,000; the curriculum is share-based so phases scale). Village model only; the creative module is not tested here.
The sealed `test` split is never built or read.

| arm | one change |
|---|---|
| base | none (FULL recipe, D alone) |
| base-s1 | seed 1 (noise estimate) |
| inject | each loop re-adds a zero-initialised projection of the rows as first written (input injection) |
| reg16 | 16 registers instead of 4 |
| mq4 | registers 0-3 each send an ASK query; card scores = max over the 4 |
| lastloss | in the "own" phase the answer loss is taken at the final loop only (no per-loop deep supervision), so nothing rewards answering by loop 2; judged at min_loops=8 as well as with HALT (added 19:40 UTC, before any run) |

lastloss additionally: HELPS only if its better of (HALT, min_loops=8) validation clears the HELPS bar; and accuracy at 8 loops
must exceed accuracy at 2 loops (max_loops=2) by >= 5 points on validation, else the loops still are not doing useful work.

Primary metric: `validation` accuracy (held-out names/templates/styles/rules), all 1,000 visits.
Noise band N = |base - base-s1| on validation (floor 1.5 points).

- An arm HELPS if validation >= max(base, base-s1) + max(3 points, N), and dev is no more than 2 points below base.
- An arm is NEUTRAL if validation is within N of mean(base, base-s1).
- WRONG (the idea does not help here) if validation is not above max(base, base-s1).
- mq4 additionally: validation first-ASK gold recall@4 must rise >= 5 points over base, else the mechanism did not work
  even if accuracy moved.

Inference-only checks on base (diag): forcing more loops (min_loops 3/5/8) HELPS if validation +3 points at any one
setting chosen on dev first; per-loop state change and register lesions are descriptive (no mark).

Spend cap: $3 per box, $10 total for this lab (Vast).

## Addendum 1 (21:22 UTC, after base / reg16 / mq4 finished, before base-s1 and before any wave-2 run)
Seen so far (validation): base 42.5, reg16 48.7, mq4 50.0. Wave 2 replicates the two apparent winners and tries them together:
`reg16-s1`, `mq4-s1`, `reg16mq4` (16 registers, registers 0-3 query). Marks:
- reg16 / mq4 REPLICATE if the seed-1 run also clears max(base, base-s1) + max(3, N) on validation.
- reg16mq4 HELPS BEYOND if validation >= max(reg16 runs, mq4 runs) + max(3, N); else the two are not additive.

## Addendum 2 (21:41 UTC, after base-s1 and lastloss finished, before wave 3)
Seen: base-s1 validation 42.4 (N = 0.15, so the 1.5 floor and the 3-point bar apply: bar = 45.5). lastloss validation 45.0 with
HALT, 51.4 at min_loops=8. Wave 3: `lastloss-s1` (replicate) and `all3` = reg16 + mq4 + lastloss together.
- lastloss REPLICATES if seed 1 also clears 45.5 on validation at min_loops=8.
- all3 HELPS BEYOND if validation (better of HALT / min_loops=8) >= best single arm + 3.

## Addendum 3 (22:05 UTC): the noise is bigger than base vs base-s1 showed
A duplicate of lastloss seed 0 on another box (GPU nondeterminism only) scored 46.0 at min_loops=8 vs 51.4: a 5.4-point
spread from the same seed. inject scored 42.2 (neutral). The base pair (42.5 / 42.4) therefore under-states the noise.
From here the judgement uses ALL runs of an arm: an arm HELPS only if its mean over runs clears the mean of all base runs by
>= 3 points AND its worst run beats the best base run. Wave 4 adds base-s2, base-s3, lastloss-s2, mq4-s2 to get >= 3 runs each.
The original per-run marks above are still reported as written.

## Addendum 4 (00:25 UTC 2026-10-24): the steadier test
Bring base, reg16, mq4, lastloss, all3 to 4 runs each (seeds 0-3; wave 5 = base-s3, mq4-s3, reg16-s1/s2/s3, all3-s1/s2/s3).
Metric: validation at 8 loops. An arm HELPS if its mean beats base's mean by >= 2 points AND a two-sample Welch t-test on the
per-run numbers gives p < 0.05 (one-sided). Otherwise NOT SHOWN. Report every run's number with the means.
