# Experiment 42 — automatic sleep (raw replay only; no lesson, no rule search). 2026-09-21
Marks and script hashed before any run (PASSMARKS.md, SEAL.sha256.txt). 35 runs, one CPU thread each. Wall-clock ≈ 50 min (over the 30-min rule: six parallel jobs slowed each other ~1.6×).
Seed validity (base old skills ≥ 0.95): 4102, 4103, 4104 VALID; 4101 (0.945) and 4105 (0.870) INVALID — shown, no claim.

New-input accuracy after sleep (trained lengths 4–8), every seed:
| sleep recipe | 4101* | 4102 | 4103 | 4104 | 4105* |
|---|---|---|---|---|---|
| R20 (20 raw episodes) | 0.050 | 0.100 | 0.070 | 0.010 | 0.230 |
| R100 | 0.435 | 0.760 | 0.735 | 0.420 | 0.690 |
| R400 | 0.990 | 1.000 | 0.995 | 0.995 | 1.000 |
| R100 + squeeze (wd 0.10) | 0.410 | 0.730 | 0.690 | 0.685 | 0.645 |
| R100 + surprise-ranked replay | 0.385 | 0.645 | 0.610 | 0.415 | 0.765 |
| R100 + squeeze + 4× longer sleep | 0.475 | 0.710 | 0.775 | 0.735 | 0.730 |
| R20 + squeeze + 4× longer sleep | 0.065 | 0.250 | 0.215 | 0.125 | 0.360 |
(* invalid seed)
Longer inputs (lengths 9–10): every recipe ≤ 0.06 on valid seeds. Old skills: R20/R100/R400/surprise ≥ 0.993 on valid seeds; squeeze arms lost up to 0.07 (4103: 0.909).

Marks: A1 reproduction PASS · A2 enough experience works PASS (R400 ≥ 0.995, old skills kept, 3/3 valid) · A3 squeeze helps FAIL (Δ −0.03, −0.045, +0.265) · A4 surprise replay helps FAIL (Δ −0.115, −0.125, −0.005) · A5 longer sleep helps FAIL · A6 tiny-log grokking FAIL (0.25, 0.215, 0.125) · A7 length FAIL.
Predictions: P145 TRUE, P146 TRUE, P147 TRUE (2 of 3 valid seeds ≥ 0.50), P148 FALSE, P149 FALSE, P150 FALSE, P151 FALSE.

Means: on this toy, a fixed automatic procedure (replay raw experiences mixed with old-skill practice) puts a new skill into the bare weights with no lesson and no rule written by anyone — if there are enough experiences: ~7% from 20, 42–76% from 100, ≥ 99.5% from 400, old skills intact. The software "lesson" in CardFold did one job only: manufacturing 400 examples out of 20.
Doesn't mean: nothing here makes sleep need fewer experiences (squeeze, surprise ranking and 4× longer sleep all failed their marks; surprise ranking was slightly worse), and nothing generalises to longer inputs. Toy only; no claim about language or the village task. Squeeze arms cost old skills.

# Experiment 42b — sleep may only make a small change (marks in PASSMARKS-42b.md, hashed first)
New-input accuracy, valid seeds 4102 / 4103 / 4104 (invalid 4101, 4105 in runs42b/):
| recipe | numbers allowed to change | 4102 | 4103 | 4104 |
|---|---|---|---|---|
| R20 (all 1.24M) | 1,240,000 | 0.100 | 0.070 | 0.010 |
| R20-embed | 160 | 0.000 | 0.005 | 0.000 |
| R20-norms | 3,040 | 0.145 | 0.080 | 0.240 |
| R100 (all) | 1,240,000 | 0.760 | 0.735 | 0.420 |
| R100-embed | 160 | 0.000 | 0.010 | 0.000 |
| R100-norms | 3,040 | 0.750 | 0.690 | 0.770 |
Marks: B1 FAIL, B2 FAIL (Δ +0.045, +0.01, +0.23), B3 FAIL. P152 FALSE, P153 FALSE, P154 TRUE (embed-only could not even fit its own 20 episodes: 0.00 seen).
Means: a new skill is NOT just "a new name for what the model already does" — 160 numbers cannot hold it. But 3,040 numbers (0.25% of the model) hold it about as well as changing everything (0.69–0.77 vs 0.42–0.76 from 100 episodes). Doesn't mean: that a small allowed change makes sleep need fewer experiences — it did not (marks failed), and it did nothing for longer inputs.
