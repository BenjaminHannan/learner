# G1 ablation, KL only, no hard mask (pre-registered 2026-10-31, before any run)

Creative module only; village model untouched. Follows `PREREG.md`. Motive: the lighter-lock run (`PREREG-light.md`, 3 seeds) failed. Cutting the KL weight from 30 to 10 changed nothing (W2 first-try 32.8 vs 34.0 empirical, 40.2 off; harm 0.17 vs 0.17 vs 2.83). That suggests (untested) that the first-try cost comes from the hard K-FAC mask (projection plus frozen unprojected tensors), not from the KL term.

## Change (one)
New arm `g1_nomask` = `g1_empirical` with the hard mask removed (`G1(mask=False)`: no K-FAC statistics, no projection, nothing frozen). The KL term stays at weight 30, with 32 rows and the same diary. Default `mask=True`, so v1 stays bit-identical.

## Run
Arms `g1_empirical, g1_nomask, g1_off`; seeds 0, 1, 2; same sizes as PREREG.md. Dev only; the sealed test split is never read. All three arms are rerun on all three seeds so the comparison is paired.

## Pass marks (fixed now; means over seeds 0,1,2; W2 = final night; harm vs the RAW parent, in points)
PASS only if BOTH:
1. mean first_try_w2(g1_nomask) >= mean first_try_w2(g1_empirical) + 2.0 points;
2. mean harm_w2(g1_nomask) <= mean harm_w2(g1_off) - 1.0 point.
Computed by `v1.g1_ablate.verdict_nomask` into `results.json`.

## What proves it wrong
- Fails mark 1: the mask is not what costs first-try. The cost is in the KL term or is shared between the two.
- Fails mark 2: the protection comes from the mask; KL alone forgets almost as much as no lock.
- Fails both: neither half alone gives a middle ground; keep G1 as coded.
A pass is "suggested" at 3 seeds, not shown. If it passes, the next step is a v1 switch behind a flag, not a default change.

## Command
`ARMS=g1_empirical,g1_nomask,g1_off SEEDS=0,1,2 v1/box/g1ablate.sh` (same wrapper as the lighter-lock run).
