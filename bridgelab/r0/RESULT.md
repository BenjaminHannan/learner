# R0 result: is v1's bridge a fixed bias?

Subsets (same questions in every condition): DEV = 400 random visits of the 5,000 (train shards 380-399), n = 3,399 questions; validation = 150 of 1,000 visits, n = 1,307.
Data regenerated with the v1 generator (seed 0); name detector fitted on 40 train shards, not 380 (deviation, see PREREG). Sanity: real = 81.3% dev / 45.3% val vs REPORT-V1 82.0 / 46.1 on the full sets; off = 22.5 / 20.3 vs 23.6 / 20.1. Wall time: ~20 min scoring (+9 min data generation). Binomial s.e. about 0.7 pt dev.

| Condition | DEV acc | VAL acc | cos(ctx_c, alt) | cos(out, real out) | |out| (real 80.7) |
|---|---|---|---|---|---|
| 1 real | 81.29 | 45.29 | 1 | 1 | 80.7 |
| 2 off (zero vector) | 22.51 | 20.28 | - | - | 0 |
| 3 ctx_c x0.5 | 81.29 | 45.29 | 1 | 1 (max abs diff 4e-6) | 80.7 |
| 3 ctx_c x2 | 81.29 | 45.29 | 1 | 1 (bit-identical) | 80.7 |
| 3 output x0.5 | 55.60 | 35.20 | - | 1 | 40.4 |
| 3 output x1.5 | 78.99 | 41.16 | - | 1 | 121 |
| 4a creative dev-256 mean (W2, fresh) | 54.60 | 32.90 | 0.611 | 0.995 | 41.0 |
| 4b creative warm-256 mean | 53.84 | 33.13 | 0.587 | 0.995 | 39.8 |
| 4c single prompt, draw 0 / 1 / 2 | 46.40 / 48.63 / 49.99 | 30.83 / 31.91 / 31.75 | 0.51 / 0.52 / 0.56 | 0.992-0.996 | 34-38 |
| 4d Gaussian, same RMS, seed 0 / 1 / 2 | 21.33 / 21.21 / 25.51 | 18.82 / 19.66 / 20.73 | about 0 | -0.63 / -0.77 / 0.97 | 2-8 |
| 5 frozen constant b = p_cd(unit(ctx_c)) | 81.29 | 45.29 | - | bit-identical vector; identical answer tensors on the first dev batch | 80.7 |

## Labels

* SHOWN: at evaluation the bridge is a single fixed vector. Condition 5 is bit-identical to 1 (vector equal, accuracy equal, answers equal on a batch). ctx_c x2 gives a bit-identical vector; x0.5 differs by 4e-6 (float rounding) and scores identically, so unit() removes scale.
* SHOWN: removing the vector costs about 59 points on dev (81.3 to 22.5) and 25 on validation. D depends on having this vector.
* SHOWN: D is very sensitive to the exact vector. Every plausible creative summary (4a-4c) moves dev accuracy by 27 to 35 points (outside the pre-registered 1-point band), validation by 12 to 14. By the pre-registered rule, "pure bias, insensitive to content" is NOT supported. Random Gaussian summaries are no better than off.
* SHOWN: scaling the projected output alone also moves accuracy (x0.5: 55.6, x1.5: 79.0), and the alternative-summary outputs have the same direction as the real one (cos 0.99+) but only about half the norm (34-41 vs 81). Their accuracy (46-55) is about that of the real vector at x0.5 (55.6).
* SUGGESTED: so most of the loss in 4a-4c is probably magnitude/offset, not "different information": a fresh mean of W2's registers, fed through unit() and p_cd, lands in the right direction but not at the right point. The saved ctx_c (cos 0.5-0.6 to fresh means) is a specific, slowly-averaged point (EMA over training batches of all stages) that P_cd and D co-adapted to. That fits "a learned constant whose value must be exactly right", and ctx_c is the carrier of that constant; it is not evidence that ctx_c carries question-relevant or even task-relevant information.
* UNTESTED: whether rescaling the 4a-4c outputs to the real norm (or adding the real vector's mean component) restores accuracy; whether any direction of ctx_c beyond the bias matters; a trained-from-scratch constant b of the same size (does D reach 81% with a learned free vector?); whether D can use the vector after retraining against a different summary.
* By construction (not a result): no condition here can show per-question use of the creative side, since the vector is identical for every question.

Plain summary for Ben: the "bridge" at test time is one fixed list of 128 numbers added to D's scratch rows, the same for every question. Taking it away drops D from 81% to 22%, so D needs it. But swapping in similar-looking numbers made fresh from the creative model does not work either (about 50%). So it behaves like a tuned dial setting that D got used to, not like a message from the creative model. One cheap follow-up (untested) is to rescale the swapped-in vectors to the right size.

Files: bridgelab/r0/r0.py (run: `python -m bridgelab.r0.r0 --root ROOT --dev-visits 400 --val-visits 150 --single-draws 3 --gauss-seeds 3`), gen_data.py (data regeneration), results.json.
