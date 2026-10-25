# G1 ablation, lighter lock (pre-registered 2026-10-25, before any run)

Creative module only; village model untouched. Follows `PREREG.md`. Motive (seeds 0,1 of that run): removing the lock gave about +5 points W2 creative dev first-try (39.1% vs 34.2%) but cost about 1.75 more skills5 harm points (2.5 vs 0.75). Question: does a weaker lock keep most of the gain and most of the protection?

## Change (one)
New arm `g1_light` = `g1_empirical` with KL weight 10 instead of 30 (`G1(kl_weight=10.0)`; default stays 30, v1 bit-identical). Everything else equal: norm none, 32 KL rows, energy 0.99, diary, lr, nights, parent B2_s200.

## Run
Arms `g1_empirical, g1_light, g1_off`; seeds 0, 1, 2; same sizes as PREREG.md. Dev only; the sealed test split is never read. Seeds 0 and 1 of `g1_empirical`/`g1_off` already exist but all three arms are rerun on all three seeds so the comparison is paired and uniform.

## Pass marks (fixed now; means over seeds 0,1,2; W2 = final night; harm vs the RAW parent, in points)
PASS only if BOTH:
1. mean first_try_w2(g1_light) >= mean first_try_w2(g1_empirical) + 2.0 points;
2. mean harm_w2(g1_light) <= mean harm_w2(g1_off) - 1.0 point.
Computed by `v1.g1_ablate.verdict_light` into `results.json`.

## What proves it wrong
- Fails mark 1: a lighter lock does not recover the creative gain; the gain needs no lock at all (or is noise).
- Fails mark 2: the lighter lock gives up the protection (harm within 1 point of no lock), so 10 is no better than off.
- Fails both: no middle ground at this one setting; this is not evidence about other weights.
A pass is "suggested" at 3 seeds, not shown; no further weights are tried from this result alone.

## Command
`ARMS=g1_empirical,g1_light,g1_off SEEDS=0,1,2 v1/box/g1ablate.sh` (wrapper supplies ROOT J PY DPH). Defaults without env vars: arms g1_empirical g1_example g1_off, seed 1.
