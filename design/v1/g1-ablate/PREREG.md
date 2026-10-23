# G1 ablation on the creative module (fixes #8 and #9 of the ten-weaknesses audit), pre-registered 2026-10-23, before any run

Creative module only (no D, no bridge, no village data; the village model is a separate thing and is not touched).

## Why
- #9: `v1/g1.py` calls `kf.kfac_stats(..., bs=64)` with `norm=None` (empirical G). The L14 "NK30" recipe it cites uses `protect_g='example'`
  (per-example normalised G). The cited evidence belongs to a different lock.
- #8: v1 never measures what G1 is for. No skills score after W1/W2, no run without G1. C2b's harm gate (`creative/c2_keep.py` `HARM_MAX = 2.0` points) was not ported.

## Flags (all default OFF; v1 is bit-identical without them)
- `G1(norm='none'|'example')`, CLI `v1/run.py --g1-norm` (default `none`).
- `run_creative(retention=fn)`: skills5 + creative dev after W1 and W2 (default None), CLI `v1/run.py --sleep-retention`.
- `v1/run.py --no-g1`: creative sleep with `guard=None`.
No other behaviour changes. In particular the KL weight/rows, diary (first 1,024 rows), energy 0.99, lr 1e-3 nights stay as in v1 (the other three sub-claims of #9 are not tested here).

## Arms (one change at a time, same parent, same seed)
| arm | G1 |
|---|---|
| g1_empirical | v1 as is (`norm=none`) |
| g1_example | `norm=example`, everything else equal |
| g1_off | `guard=None` |

Parent B2_s200 (sha256 94057436...), seed 0 (one seed; see Noise), steps = `run_creative` full sizes (warm-up 2,048 rows, N', search n1=32 n2=480, two nights, lr 1e-3, 32 visits).
Run sequentially on one box.

## Measures (dev only; the sealed test split is never opened)
- Creative DEV greedy first-try (256 questions, `creative_sleep.dev_report`) after W1 and W2.
- Skills harm in points = 100 x (skills5(raw B2) - skills5(checkpoint)), `fastsleep.skills5` (pooled-5 exact, the C2b measure) after W1 and W2.
  Primary reference is the RAW parent (common to all arms, since G1 changes N' too). Also logged: harm vs each arm's own N' (C2b's exact reading).
- All pass marks use W2 (final night). W1 reported.

## Pass marks (fixed now)
1. **g1_example is acceptable** if harm(g1_example) <= harm(g1_empirical) AND |first_try(g1_example) - first_try(g1_empirical)| <= 2 points.
2. **G1 buys retention** only if harm(g1_off) - harm(g1_empirical) >= 2 points.

## Result that proves a fix wrong
- Switching to `example` is wrong (keep `none`, relabel G1 as a variant not NK30) if harm(example) > harm(empirical), or first-try differs by more than 2 points.
- "G1 buys retention" is wrong if harm(off) - harm(empirical) < 2 points: then G1's cost (17-27% of the loss, 41 frozen tensors) is not shown to pay for itself on this measure.
- Passing mark 1 does not mean `example` is better, only not worse; a tie is reported as a tie.

## Noise (disclosed)
One seed, 256 dev questions (one question = 0.39 points) and a skills5 set of a few hundred rows. Differences of ~2 points are within plausible sampling noise;
a "pass" or "fail" is a single-seed reading, labelled suggested, not shown. A positive result should be repeated with seeds 1-2 (extra cost ~ the same per seed).

## Cost cap
$3.00 hard cap for the box (rent.py stage `g1ablate`, wall-clock self-stop). Expected about 2-3 GPU hours incl. ~20 min setup at ~$0.35/h = about $1.

## Not tested here
The 4,096-row diary, KL weighting vs NK30 (sub-claims 2, 3), nights lr (4), re-anchoring each stage, and any village-model effect.
