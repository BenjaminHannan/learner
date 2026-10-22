# Positive controls for the restart gate (trace A): what a broken restore looks like next to healthy nondeterminism

Branch claude/restart-gate-solve, CPU only, nothing outside this folder touched, nothing committed. Labels: **[shown]** = measured here and in the tables below; **[suggested]** = the numbers point that way but the evidence is thin or indirect; **[untested]** = not tried.

## Setup (what was actually run)

- Tree: `git archive 74d6e92c75 custom_io` + the pack overlay `train.py` + `tests/test_ckpt.py` + `tests/test_ckpt_b3g2.py`. torch 2.14.1+cpu, numpy 2.5.3, Python 3.13.16, `OMP_NUM_THREADS=1`.
- Step 1: `python3 -m custom_io.tests.test_ckpt_b3g2` printed `ALL OK` (log: `step1_test_ckpt_b3g2.log`; 5 checks, all bit for bit; "machine noise: none").
- Driver `posctrl.py` runs `custom_io.train.main` in-process with monkeypatches. Tiny b3g2 CFG of the pack test, 48-row test data set, batch 8, lr 3e-3, warmup 5, seed 1, `--log-every 1`, `--ckpt-every 30`, `--steps 60`, accum 4 and 8. C = one uninterrupted run; the step-30 checkpoint + sidecar is copied aside; every resume (healthy R1..R4 and one per fault) is a fresh process with `--resume` on a copy of that folder, redoing updates 31..60.
- NOISE_EPS: after every micro-batch backward, `param.grad += eps * rms(param.grad) * N(0,1)` for every parameter, normals from a numpy Generator seeded from `os.urandom` (no global RNG touched). Because it is added after the backward, the loss of the first redone update (31) is a pure forward pass on the restored state and is exact for any eps; noise first shows at update 32.
- Faults are applied in the one place where train.py has just loaded model + optimizer (`restore_model_streams` is called right after `model.load_state_dict`, `opt.load_state_dict`, `restore_global_streams`): `opt_reset` (`opt.state = defaultdict(dict)`), `opt_moments_zero` (step kept, exp_avg and exp_avg_sq zeroed), `data_shift` (`batches_from(skip+1)`), `rng_noreset` (neither the global python/numpy/torch streams nor the model's own random.Random streams are restored: left as seeded/built), `lr_step_off` (`lr_at(step+1)` for the whole resumed process), `weights_eps` (every weight times `1 + 1e-3 N(0,1)`, fixed seed). Two extra splits of rng_noreset: `rng_global_noreset`, `rng_model_noreset`. All 6 asked-for faults could be placed faithfully.
- Logged losses are rounded to 5 decimals by train.py, so 1e-5 is the resolution of every number below. "Loss level" = mean of C's loss over updates 31..60.
- Statistics per resume vs C over the 30 redone updates: first_diff (update 31), early_max (max over updates 31..33), mean_abs, max_abs, signed mean (R - C). D/N = mean over R1..R4 of mean_abs(Ri,C) / mean over the 6 pairs of mean_abs(Ri,Rj). Bug-to-noise ratio = fault mean_abs / mean over R1..R4 of mean_abs(Ri,C). ">10x at update" = first redone update where the fault's |dL| > 10 * max(largest healthy |dL| at that update over all 4 R-C and 6 R-R comparisons, 1e-5).

## Which eps (and why) -- the 0.1% / 1% targets are only partly reachable

Calibration sweep (`calibration_sweep.txt`, a healthy C + 2 resumes per eps, accum 4 and 8): with this noise form the tiny CPU model is far less chaotic than the GPU run. Mean |dL| of R vs C stays near 1e-5 .. 5e-4 (0.000 .. 0.006% of the loss) for eps up to 0.03, and reaches roughly 0.1% only around eps 0.3 .. 1. At eps >= 0.3 the noise itself damages training: the loss level over updates 31..60 is 7.94 (accum 4) / 7.64 (accum 8) without noise, 13.7 / 13.9 at eps 0.3, 19.2 / 22.4 at eps 1, 61 / 57 at eps 8 (no learning at all, initial loss is 49). So:
- **eps = 1 ("e1")**: healthy mean|dL| / level = 0.037% (accum 4) and 0.170% (accum 8) in the main cell; three further healthy replicates (`raw/rep_*`) give R-C mean_abs 0.0131/0.00925/0.01123 (accum 4, level ~19) and 0.0136/0.0339/0.0237 (accum 8, level ~22), i.e. about 0.05% .. 0.15%. This is the nearest to the 0.1% target that does not collapse training (but the loss level is already 2.4x - 2.9x the noise-free one). In absolute terms it is of the same size as the GPU gate (mean |dL| 0.0167 at accum 4, 0.0282 at accum 8): here 0.0072 (accum 4) and 0.0381 (accum 8). [shown]
- **eps = 8 ("e2")**: 0.38% (accum 4) / 0.45% (accum 8) of a loss level of ~60. 1% was not reachable at any eps without a fully collapsed run; e2 is therefore a **stress case** (noise-dominated, nothing is learned), not a healthy-like regime. [shown]
- Extras run in the same protocol: eps 0.01 (bf16-rounding scale: mean|dL| 4e-4 = 0.005% of the loss, early divergence of the same size as the GPU gate's "<= 2e-4 over the first 7 updates") and eps 0.3. All five noise levels 0, 0.01, 0.3, 1, 8 x accum 4, 8 = 10 cells, each with 4 healthy and 8 faulty resumes.
- Total wall time about 55 min on 4 cores (calibration sweeps included).

## Plain summary (10 lines)

1. With NOISE_EPS = 0 the restore is bit-exact: all 4 healthy resumes equal C at all 30 redone updates in both accums. [shown]
2. With noise, the first redone update (31) is exact in every healthy resume at every eps (u31 diff 0.00000 in all 10 cells x 4 resumes), because it is a pure forward pass; healthy divergence starts at update 32 and grows over the window (pooled mean |dL| in updates 48-60 is 1.8x .. 7.8x that in 31-37). [shown, same qualitative shape as the GPU gate]
3. Faults that change weights, data or RNG are visible at update 31 as a non-zero loss difference: data_shift (u31 diff 2.4 .. 25), rng_noreset and rng_global_noreset (0.88 .. 45), rng_model_noreset (0.0015 .. 0.064; also `plan_rows/plan_gapped/drill_share` differ) and weights_eps at 1e-3 (7.3e-4 .. 0.0145). An exact-match test on update 31 therefore catches all of them even when the healthy noise is huge. [shown]
4. opt_reset and opt_moments_zero are INVISIBLE at update 31 (loss diff exactly 0, no other logged field differs) and show first at update 32 (opt_reset 0.014 .. 0.98, opt_moments_zero 0.11 .. 1.01 at u32). lr_step_off is invisible in the loss at u31 but shows in the logged `lr` field at u31 (an exact field) and in the loss from u32 (0.027 .. 0.077). A gate that only looks at update 31 loss would miss these three; a gate that compares updates 32-33 does not. [shown]
5. Bug-to-noise ratios (fault mean_abs / healthy mean_abs R-C, eps 0.01 / 0.3 / 1): opt_reset 367 / 23 / 12 (accum 4), 778 / 16 / 1.4 (accum 8); opt_moments_zero 421 / 226 / 128 and 231 / 95 / 23; lr_step_off 230 / 49 / 36 and 280 / 33 / 5.8; data_shift 3654 / 631 / 666 and 3907 / 456 / 138; rng_noreset 1655 / 585 / 689 and 1452 / 433 / 156; rng_model_noreset 181 / 33 / 37 and 236 / 29 / 10; weights_eps(1e-3) 9.8 / 0.9 / 1.0 and 4.2 / 1.6 / 1.2. [shown]
6. weights_eps at 1e-3 is NOT separable from healthy noise by mean_abs once the noise is >= ~0.1% of the loss (ratio ~1 at eps 0.3 and 1, 0.5 at eps 8); it is separable only through the exact u31 check (its u31 diff scales linearly with the perturbation: 3.4e-3 at 1e-3, 3.3e-4 at 1e-4, 3.0e-5 at 1e-5, 0 at 1e-6 at the 1e-5 print resolution). [shown]
7. First update where a fault exceeds 10x the healthy max at that update: 31 for data/rng/weights faults, 32 for opt_reset, opt_moments_zero and lr_step_off at eps 0.01 and 0.3 (accum 4 eps 1 lr_step_off: 36; accum 8 eps 1 lr_step_off: never). At eps 8 (collapsed training) opt_reset, opt_moments_zero and lr_step_off are never above 10x (ratios 0.2 .. 4.6). [shown]
8. Healthy D/N (accum 4; eps 0.01, 0.3, 1, 8): 1.19, 0.74, 0.66, 0.68; (accum 8): 0.70, 0.77, 3.13, 0.60. Six healthy replicates at eps 1 (fresh C and R1..R4): 0.67, 0.60, 0.82 (accum 4) and 0.97, 1.24, 0.85 (accum 8), so the 3.13 (C was the most distant of the five runs) is a one-off draw. C is exchangeable with the R's to within the sampling noise at accum 8; at accum 4, 6 of 7 cells with noise are below 1 (median 0.68) while the same estimator applied to R-only subsets (`dn_control.txt`) gives 1.01 .. 1.97: C looks slightly more central than an R, R-R about 30% larger than R-C. Small, unexplained, not a restore bug (eps 0 is bit-exact). [suggested]
9. Absolute scale: at eps 1 the healthy mean |dL| (0.0072 accum 4, 0.0381 accum 8) is of the same size as the GPU gate's (0.0167, 0.0282), but the model had to be pushed into a noise-damaged regime (loss level 19 - 22 vs 7.9) to get there; at bf16-like eps 0.01 the healthy divergence (4e-4, 3e-4) is 40x - 90x smaller than the GPU one. So how much the GPU gate's mean|dL| can be trusted as "noise only" (not as a smaller bug on top of noise) is NOT settled by this emulation. [shown for the numbers, untested for the GPU]
10. Not tested: partial/graded versions of the optimizer faults (e.g. moments off by 1%), faults combined with each other, bf16 kernels, a longer window than 30 updates, other models than b3g2, other data than the 48-row toy set (batch order wraps every 6 updates there, which may make data_shift look larger than on a real corpus).

## Tables

### Table A: healthy redo (4 resumes R1..R4, each a fresh process with its own noise) over updates 31..60

| accum | NOISE_EPS | loss level (mean C, 31..60) | first_diff (u31) mean R-C | early_max (u31..33) mean | mean_abs R-C | mean_abs/level | max_abs R-C (max of 4) | signed mean R-C | mean_abs R-R pairs | mean_abs R-C (each of R1..R4) | D/N | C rank of 5 (1 = most central) | healthy exact-field mismatch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 0 | 7.9394 | 0.00000 | 0.00000 | 0.00000 | 0.0000% | 0.00000 | 0.00000 | 0.00000 | 0.00000, 0.00000, 0.00000, 0.00000 | n/a | 1 | {None} |
| 4 | 0.01 | 7.9428 | 0.00000 | 5.33e-04 | 4.06e-04 | 0.0051% | 0.00112 | -3.77e-04 | 3.41e-04 | 2.70e-04, 4.60e-04, 2.18e-04, 6.77e-04 | 1.190 | 4 | {None} |
| 4 | 0.3 | 13.7311 | 0.00000 | 0.00285 | 0.00509 | 0.0371% | 0.01726 | 0.00222 | 0.00684 | 0.00506, 0.00408, 0.00694, 0.00428 | 0.744 | 1 | {None} |
| 4 | 1 | 19.2167 | 0.00000 | 0.00575 | 0.00715 | 0.0372% | 0.02808 | 0.00214 | 0.01082 | 0.00669, 0.00665, 0.00936, 0.00590 | 0.661 | 1 | {None} |
| 4 | 8 | 61.1044 | 0.00000 | 0.06207 | 0.23492 | 0.3845% | 1.85528 | 0.22685 | 0.34387 | 0.05889, 0.66779, 0.04507, 0.16794 | 0.683 | 4 | {None} |
| 8 | 0 | 7.6402 | 0.00000 | 0.00000 | 0.00000 | 0.0000% | 0.00000 | 0.00000 | 0.00000 | 0.00000, 0.00000, 0.00000, 0.00000 | n/a | 1 | {None} |
| 8 | 0.01 | 7.6882 | 0.00000 | 7.25e-05 | 3.28e-04 | 0.0043% | 0.00247 | 9.72e-05 | 4.66e-04 | 4.39e-04, 2.19e-04, 4.09e-04, 2.45e-04 | 0.704 | 1 | {None} |
| 8 | 0.3 | 13.9286 | 0.00000 | 0.00178 | 0.00614 | 0.0441% | 0.02214 | -0.00392 | 0.00798 | 0.00906, 0.00753, 0.00347, 0.00452 | 0.770 | 1 | {None} |
| 8 | 1 | 22.4107 | 0.00000 | 0.00608 | 0.03814 | 0.1702% | 0.11291 | -0.03812 | 0.01217 | 0.03018, 0.03983, 0.04274, 0.03980 | 3.134 | 5 | {None} |
| 8 | 8 | 57.4285 | 0.00000 | 0.11023 | 0.25914 | 0.4512% | 1.46097 | -0.14217 | 0.43310 | 0.16486, 0.15702, 0.62651, 0.08818 | 0.598 | 1 | {None} |

### Table B: faulty resumes (same NOISE_EPS as the healthy ones, one fresh process each) vs C over updates 31..60

"u31 diff" = |loss(R) - loss(C)| at the first redone update (0 = exact match of the logged 5-decimal loss). "first nonzero" = first redone update at which the loss differs at all. "exact-field mismatch" = first update at which a field that must be exactly equal in a healthy redo (lr, rounds, plan_*, drill_share, copy_share, stop_w, cap_hits) differs. "x healthy" = mean_abs / healthy mean_abs(R,C). ">10x" = first redone update where |dL| > 10 * max(healthy max at that update over all R-C and R-R comparisons, 1e-5).

| accum | NOISE_EPS | fault | u31 diff | first nonzero | exact-field mismatch (update: fields) | early_max | mean_abs | max_abs | signed mean | x healthy (mean_abs) | >10x at update |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 0 | opt_reset | 0.00000 | 32 | none | 0.97789 | 0.21500 | 0.97789 | -0.10739 | n/a (healthy=0) | 32 |
| 4 | 0 | opt_moments_zero | 0.00000 | 32 | none | 0.66056 | 0.13604 | 0.66056 | 0.06720 | n/a (healthy=0) | 32 |
| 4 | 0 | data_shift | 2.76655 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 3.64401 | 1.47579 | 3.64401 | -0.10005 | n/a (healthy=0) | 31 |
| 4 | 0 | rng_noreset | 0.88193 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 5.52833 | 0.65598 | 5.52833 | -0.39452 | n/a (healthy=0) | 31 |
| 4 | 0 | rng_global_noreset | 0.88001 | 31 | 31: rounds,stop_w | 5.60610 | 0.66942 | 5.60610 | -0.39818 | n/a (healthy=0) | 31 |
| 4 | 0 | rng_model_noreset | 0.00145 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.07348 | 0.05650 | 0.22843 | 0.00799 | n/a (healthy=0) | 31 |
| 4 | 0 | lr_step_off | 0.00000 | 32 | 31: lr | 0.04542 | 0.06680 | 0.13767 | 0.06680 | n/a (healthy=0) | 32 |
| 4 | 0 | weights_eps | 0.00338 | 31 | none | 0.01104 | 0.00213 | 0.01104 | -0.00213 | n/a (healthy=0) | 31 |
| 4 | 0.01 | opt_reset | 0.00000 | 32 | none | 0.62595 | 0.14892 | 0.89954 | 0.07137 | 366.7 | 32 |
| 4 | 0.01 | opt_moments_zero | 0.00000 | 32 | none | 0.28951 | 0.17111 | 0.67551 | 0.15181 | 421.3 | 32 |
| 4 | 0.01 | data_shift | 2.81398 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 3.65008 | 1.48421 | 3.65008 | -0.05343 | 3654.2 | 31 |
| 4 | 0.01 | rng_noreset | 0.91389 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 5.76129 | 0.67228 | 5.76129 | -0.39685 | 1655.2 | 31 |
| 4 | 0.01 | rng_global_noreset | 0.91697 | 31 | 31: rounds,stop_w | 5.84832 | 0.68510 | 5.84832 | -0.39390 | 1686.7 | 31 |
| 4 | 0.01 | rng_model_noreset | 0.00340 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.08239 | 0.07360 | 0.23180 | 0.03834 | 181.2 | 31 |
| 4 | 0.01 | lr_step_off | 0.00000 | 32 | 31: lr | 0.04208 | 0.09350 | 0.19410 | 0.09350 | 230.2 | 32 |
| 4 | 0.01 | weights_eps | 0.00370 | 31 | none | 0.01259 | 0.00399 | 0.01259 | -0.00399 | 9.8 | 31 |
| 4 | 0.3 | opt_reset | 0.00000 | 32 | none | 0.42168 | 0.11568 | 0.42168 | 0.11568 | 22.7 | 32 |
| 4 | 0.3 | opt_moments_zero | 0.00000 | 32 | none | 0.99022 | 1.15092 | 8.04398 | 1.15092 | 226.0 | 32 |
| 4 | 0.3 | data_shift | 6.56460 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 9.36654 | 3.21236 | 9.36654 | -0.15067 | 630.8 | 31 |
| 4 | 0.3 | rng_noreset | 3.08238 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 20.86909 | 2.97960 | 20.86909 | -1.38020 | 585.1 | 31 |
| 4 | 0.3 | rng_global_noreset | 3.14678 | 31 | 31: rounds,stop_w | 21.05845 | 3.04352 | 21.05845 | -1.36847 | 597.6 | 31 |
| 4 | 0.3 | rng_model_noreset | 0.06441 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.41516 | 0.16673 | 0.44951 | 8.55e-04 | 32.7 | 31 |
| 4 | 0.3 | lr_step_off | 0.00000 | 32 | 31: lr | 0.07864 | 0.25091 | 0.57702 | 0.25091 | 49.3 | 32 |
| 4 | 0.3 | weights_eps | 0.00821 | 31 | none | 0.02284 | 0.00468 | 0.02284 | -0.00298 | 0.9 | 31 |
| 4 | 1 | opt_reset | 0.00000 | 32 | none | 0.32300 | 0.08720 | 0.32300 | 0.06450 | 12.2 | 32 |
| 4 | 1 | opt_moments_zero | 0.00000 | 32 | none | 1.01478 | 0.91337 | 2.35660 | 0.91337 | 127.7 | 32 |
| 4 | 1 | data_shift | 8.76487 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 12.73379 | 4.76408 | 14.51805 | -0.25868 | 666.3 | 31 |
| 4 | 1 | rng_noreset | 4.32958 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 29.45236 | 4.92933 | 29.45236 | -2.04493 | 689.4 | 31 |
| 4 | 1 | rng_global_noreset | 4.38440 | 31 | 31: rounds,stop_w | 29.75596 | 5.01175 | 29.75596 | -2.01886 | 700.9 | 31 |
| 4 | 1 | rng_model_noreset | 0.05478 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.60117 | 0.26096 | 0.72902 | 0.00285 | 36.5 | 31 |
| 4 | 1 | lr_step_off | 0.00000 | 32 | 31: lr | 0.08439 | 0.25932 | 0.64786 | 0.25932 | 36.3 | 36 |
| 4 | 1 | weights_eps | 0.00878 | 31 | none | 0.02190 | 0.00685 | 0.02190 | -9.20e-04 | 1.0 | 31 |
| 4 | 8 | opt_reset | 0.00000 | 32 | none | 0.62193 | 0.68094 | 1.55375 | -0.68094 | 2.9 | None |
| 4 | 8 | opt_moments_zero | 0.00000 | 32 | none | 0.37842 | 1.07186 | 2.66565 | 1.07186 | 4.6 | None |
| 4 | 8 | data_shift | 24.88439 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 38.52763 | 19.01694 | 62.89604 | -1.19855 | 81.0 | 31 |
| 4 | 8 | rng_noreset | 14.26030 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 101.12409 | 26.07672 | 101.12409 | -8.90011 | 111.0 | 31 |
| 4 | 8 | rng_global_noreset | 14.23069 | 31 | 31: rounds,stop_w | 101.79994 | 26.49807 | 101.79994 | -8.54948 | 112.8 | 31 |
| 4 | 8 | rng_model_noreset | 0.02593 | 31 | 31: plan_rows,plan_gapped,drill_share | 2.07986 | 1.37153 | 4.23372 | -0.27422 | 5.8 | 31 |
| 4 | 8 | lr_step_off | 0.00000 | 32 | 31: lr | 0.06697 | 0.04111 | 0.13079 | 0.00648 | 0.2 | None |
| 4 | 8 | weights_eps | 7.30e-04 | 31 | none | 0.02413 | 0.11898 | 0.28732 | 0.11893 | 0.5 | 31 |
| 8 | 0 | opt_reset | 0.00000 | 32 | none | 0.53462 | 0.25250 | 0.80267 | -0.25250 | n/a (healthy=0) | 32 |
| 8 | 0 | opt_moments_zero | 0.00000 | 32 | none | 0.18380 | 0.09813 | 0.24124 | 0.05721 | n/a (healthy=0) | 32 |
| 8 | 0 | data_shift | 2.40016 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 2.70139 | 1.28300 | 2.72576 | -0.11804 | n/a (healthy=0) | 31 |
| 8 | 0 | rng_noreset | 1.64494 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 1.64494 | 0.44977 | 1.64494 | 0.01191 | n/a (healthy=0) | 31 |
| 8 | 0 | rng_global_noreset | 1.67948 | 31 | 31: rounds,stop_w | 1.67948 | 0.42873 | 1.67948 | 0.00342 | n/a (healthy=0) | 31 |
| 8 | 0 | rng_model_noreset | 0.03460 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.22191 | 0.06145 | 0.22191 | 0.01345 | n/a (healthy=0) | 31 |
| 8 | 0 | lr_step_off | 0.00000 | 32 | 31: lr | 0.06965 | 0.06222 | 0.13339 | 0.05005 | n/a (healthy=0) | 32 |
| 8 | 0 | weights_eps | 0.00212 | 31 | none | 0.00249 | 9.10e-04 | 0.00249 | -7.68e-04 | n/a (healthy=0) | 31 |
| 8 | 0.01 | opt_reset | 0.00000 | 32 | none | 0.36689 | 0.25515 | 0.60195 | -0.25515 | 777.5 | 32 |
| 8 | 0.01 | opt_moments_zero | 0.00000 | 32 | none | 0.25901 | 0.07576 | 0.25901 | 0.06149 | 230.9 | 32 |
| 8 | 0.01 | data_shift | 2.50121 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 2.81121 | 1.28201 | 2.81121 | -0.09310 | 3906.6 | 31 |
| 8 | 0.01 | rng_noreset | 1.85971 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 1.85971 | 0.47638 | 1.85971 | -0.01628 | 1451.6 | 31 |
| 8 | 0.01 | rng_global_noreset | 1.89737 | 31 | 31: rounds,stop_w | 1.89737 | 0.45349 | 1.89737 | -0.02726 | 1381.9 | 31 |
| 8 | 0.01 | rng_model_noreset | 0.03771 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.21651 | 0.07740 | 0.21682 | 0.02783 | 235.8 | 31 |
| 8 | 0.01 | lr_step_off | 0.00000 | 32 | 31: lr | 0.02757 | 0.09181 | 0.21551 | 0.09181 | 279.8 | 32 |
| 8 | 0.01 | weights_eps | 0.00264 | 31 | none | 0.00281 | 0.00138 | 0.00435 | -0.00138 | 4.2 | 31 |
| 8 | 0.3 | opt_reset | 0.00000 | 32 | none | 0.13649 | 0.09628 | 0.21921 | -0.07193 | 15.7 | 32 |
| 8 | 0.3 | opt_moments_zero | 0.00000 | 32 | none | 0.97648 | 0.58326 | 1.55396 | 0.58090 | 94.9 | 32 |
| 8 | 0.3 | data_shift | 6.56417 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 6.56417 | 2.80157 | 8.63351 | -0.35492 | 456.0 | 31 |
| 8 | 0.3 | rng_noreset | 9.90659 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 9.90659 | 2.66199 | 9.90659 | -0.51851 | 433.3 | 31 |
| 8 | 0.3 | rng_global_noreset | 9.95246 | 31 | 31: rounds,stop_w | 9.95246 | 2.60854 | 9.95246 | -0.49083 | 424.6 | 31 |
| 8 | 0.3 | rng_model_noreset | 0.04587 | 31 | 31: plan_rows,plan_gapped,drill_share | 0.72486 | 0.17689 | 0.72486 | -0.07020 | 28.8 | 31 |
| 8 | 0.3 | lr_step_off | 0.00000 | 32 | 31: lr | 0.08112 | 0.20037 | 0.48312 | 0.20037 | 32.6 | 32 |
| 8 | 0.3 | weights_eps | 0.01298 | 31 | none | 0.01627 | 0.01013 | 0.02087 | -0.00966 | 1.6 | 31 |
| 8 | 1 | opt_reset | 0.00000 | 32 | none | 0.12259 | 0.05399 | 0.14431 | -0.03200 | 1.4 | 32 |
| 8 | 1 | opt_moments_zero | 0.00000 | 32 | none | 0.86203 | 0.89155 | 1.86729 | 0.89155 | 23.4 | 32 |
| 8 | 1 | data_shift | 10.25053 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 10.25053 | 5.26922 | 17.23757 | -0.76266 | 138.2 | 31 |
| 8 | 1 | rng_noreset | 16.85285 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 16.85285 | 5.95475 | 16.85285 | -0.43719 | 156.1 | 31 |
| 8 | 1 | rng_global_noreset | 16.89387 | 31 | 31: rounds,stop_w | 16.89387 | 5.84580 | 16.89387 | -0.39188 | 153.3 | 31 |
| 8 | 1 | rng_model_noreset | 0.04101 | 31 | 31: plan_rows,plan_gapped,drill_share | 1.30134 | 0.39440 | 1.30134 | -0.17992 | 10.3 | 31 |
| 8 | 1 | lr_step_off | 0.00000 | 32 | 31: lr | 0.06520 | 0.21961 | 0.59760 | 0.21961 | 5.8 | None |
| 8 | 1 | weights_eps | 0.01451 | 31 | none | 0.02406 | 0.04438 | 0.09840 | -0.04438 | 1.2 | 31 |
| 8 | 8 | opt_reset | 0.00000 | 32 | none | 0.49792 | 0.84854 | 1.86162 | -0.84854 | 3.3 | None |
| 8 | 8 | opt_moments_zero | 0.00000 | 32 | none | 0.15990 | 0.13506 | 0.45967 | 0.09831 | 0.5 | None |
| 8 | 8 | data_shift | 24.45042 | 31 | 31: rounds,plan_rows,plan_gapped,drill_share | 24.45042 | 17.64762 | 55.82071 | -3.30793 | 68.1 | 31 |
| 8 | 8 | rng_noreset | 45.02859 | 31 | 31: rounds,stop_w,plan_rows,plan_gapped,drill_share | 45.36164 | 21.38322 | 48.69631 | -0.27878 | 82.5 | 31 |
| 8 | 8 | rng_global_noreset | 45.00413 | 31 | 31: rounds,stop_w | 45.00413 | 21.19520 | 47.49887 | 0.08515 | 81.8 | 31 |
| 8 | 8 | rng_model_noreset | 0.01814 | 31 | 31: plan_rows,plan_gapped,drill_share | 3.72302 | 1.36529 | 4.56682 | -0.59783 | 5.3 | 31 |
| 8 | 8 | lr_step_off | 0.00000 | 32 | 31: lr | 0.12487 | 0.11835 | 0.32369 | -0.11589 | 0.5 | None |
| 8 | 8 | weights_eps | 0.00429 | 31 | none | 0.15221 | 0.22356 | 0.54722 | -0.22356 | 0.9 | 31 |

### Table C: early separation. |loss(R)-loss(C)| at update 32 (the first update where an optimizer-state or lr fault can show) vs the largest healthy |dL| at update 32 (over the 4 R-C and 6 R-R comparisons)

| accum | NOISE_EPS | healthy max u32 | opt_reset | opt_moments_zero | data_shift | rng_noreset | rng_global_noreset | rng_model_noreset | lr_step_off | weights_eps |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 0 | 0.00000 | 0.97789 | 0.66056 | 3.64401 | 5.52833 | 5.60610 | 0.07348 | 0.03211 | 0.01104 |
| 4 | 0.01 | 0.00115 | 0.62595 | 0.28951 | 3.65008 | 5.76129 | 5.84832 | 0.08239 | 0.03147 | 0.01259 |
| 4 | 0.3 | 0.00260 | 0.42168 | 0.99022 | 9.36654 | 20.86909 | 21.05845 | 0.18751 | 0.07486 | 0.02284 |
| 4 | 1 | 0.00900 | 0.32300 | 1.01478 | 12.73379 | 29.45236 | 29.75596 | 0.30938 | 0.07708 | 0.02190 |
| 4 | 8 | 0.13843 | 0.62193 | 0.32266 | 38.52763 | 101.12409 | 101.79994 | 0.66081 | 0.06697 | 0.01764 |
| 8 | 0 | 0.00000 | 0.01450 | 0.18380 | 2.70139 | 0.96324 | 1.02081 | 0.08337 | 0.03036 | 0.00249 |
| 8 | 0.01 | 7.00e-05 | 0.36689 | 0.15809 | 2.81121 | 1.10404 | 1.16031 | 0.08361 | 0.02757 | 0.00275 |
| 8 | 0.3 | 0.00248 | 0.13649 | 0.55509 | 6.54743 | 6.12669 | 6.19522 | 0.21831 | 0.03898 | 0.01519 |
| 8 | 1 | 0.00619 | 0.12168 | 0.45781 | 10.20857 | 10.76607 | 10.82680 | 0.32606 | 0.03157 | 0.01947 |
| 8 | 8 | 0.08867 | 0.28129 | 0.10619 | 24.18581 | 29.84588 | 29.81874 | 0.69530 | 0.05301 | 0.06936 |

### Table D: weights_eps sensitivity (relative perturbation of every weight, resume from the same step-30 checkpoint, vs C)

| accum | NOISE_EPS | weights_eps | u31 diff | early_max (u31..33) | mean_abs | max_abs |
|---|---|---|---|---|---|---|
| 4 | 0 | 0.001 | 3.38e-03 | 1.10e-02 | 2.13e-03 | 1.10e-02 |
| 4 | 0 | 0.0001 | 3.30e-04 | 1.10e-03 | 2.11e-04 | 1.10e-03 |
| 4 | 0 | 1e-05 | 3.00e-05 | 1.10e-04 | 1.97e-05 | 1.10e-04 |
| 4 | 0 | 1e-06 | 0.00e+00 | 1.00e-05 | 1.00e-06 | 1.00e-05 |
| 4 | 0 | 1e-07 | 0.00e+00 | 0.00e+00 | 0.00e+00 | 0.00e+00 |
| 4 | 0.01 | 0.001 | 3.70e-03 | 1.22e-02 | 3.87e-03 | 1.22e-02 |
| 4 | 0.01 | 0.0001 | 3.70e-04 | 1.23e-03 | 6.65e-04 | 1.23e-03 |
| 4 | 0.01 | 1e-05 | 3.00e-05 | 1.40e-04 | 4.64e-04 | 7.80e-04 |
| 4 | 0.01 | 1e-06 | 0.00e+00 | 5.40e-04 | 6.97e-04 | 1.20e-03 |
| 4 | 0.01 | 1e-07 | 0.00e+00 | 1.90e-04 | 2.70e-04 | 5.40e-04 |
| 8 | 0 | 0.001 | 2.12e-03 | 2.49e-03 | 9.10e-04 | 2.49e-03 |
| 8 | 0 | 0.0001 | 2.10e-04 | 2.50e-04 | 8.83e-05 | 2.50e-04 |
| 8 | 0 | 1e-05 | 2.00e-05 | 3.00e-05 | 9.67e-06 | 3.00e-05 |
| 8 | 0 | 1e-06 | 0.00e+00 | 0.00e+00 | 3.33e-07 | 1.00e-05 |
| 8 | 0 | 1e-07 | 1.00e-05 | 1.00e-05 | 3.33e-07 | 1.00e-05 |

### Table E: does the healthy divergence grow over the window?

| accum | NOISE_EPS | 31-37 | 38-47 | 48-60 | ratio (48-60)/(31-37) |
|---|---|---|---|---|---|
| 4 | 0.01 | 2.65e-04 | 3.06e-04 | 4.69e-04 | 1.8 |
| 4 | 0.3 | 2.08e-03 | 5.93e-03 | 8.49e-03 | 4.1 |
| 4 | 1 | 5.03e-03 | 6.89e-03 | 1.36e-02 | 2.7 |
| 4 | 8 | 7.47e-02 | 2.18e-01 | 4.85e-01 | 6.5 |
| 8 | 0.01 | 9.77e-05 | 1.78e-04 | 7.59e-04 | 7.8 |
| 8 | 0.3 | 2.36e-03 | 6.90e-03 | 1.01e-02 | 4.3 |
| 8 | 1 | 7.23e-03 | 1.96e-02 | 3.31e-02 | 4.6 |
| 8 | 8 | 1.19e-01 | 3.58e-01 | 4.99e-01 | 4.2 |

### Table F: exchangeability control for D/N

```
D/N with C as reference (4 R-C distances / 6 R-R) vs the same estimator with each R as the reference (3 R-R distances to it / 3 R-R among the other three), averaged over the 4 choices. Exchangeable runs -> both near 1.
a4_e0.01.json          accum 4 eps 0.01  D/N(C ref) 1.190   R-only D/N 1.063
a4_e0.3.json           accum 4 eps 0.3   D/N(C ref) 0.744   R-only D/N 1.014
a4_e1.json             accum 4 eps 1     D/N(C ref) 0.661   R-only D/N 1.057
a4_e8.json             accum 4 eps 8     D/N(C ref) 0.683   R-only D/N 1.967
a8_e0.01.json          accum 8 eps 0.01  D/N(C ref) 0.704   R-only D/N 1.062
a8_e0.3.json           accum 8 eps 0.3   D/N(C ref) 0.770   R-only D/N 1.055
a8_e1.json             accum 8 eps 1     D/N(C ref) 3.134   R-only D/N 1.053
a8_e8.json             accum 8 eps 8     D/N(C ref) 0.598   R-only D/N 1.276
rep_a4_e1_1.json       accum 4 eps 1     D/N(C ref) 0.670   R-only D/N 1.233
rep_a4_e1_2.json       accum 4 eps 1     D/N(C ref) 0.604   R-only D/N 1.288
rep_a4_e1_3.json       accum 4 eps 1     D/N(C ref) 0.816   R-only D/N 1.205
rep_a8_e1_1.json       accum 8 eps 1     D/N(C ref) 0.972   R-only D/N 1.083
rep_a8_e1_2.json       accum 8 eps 1     D/N(C ref) 1.240   R-only D/N 1.137
rep_a8_e1_3.json       accum 8 eps 1     D/N(C ref) 0.854   R-only D/N 1.143
accum 4: n=7 cells; mean D/N(C ref) 0.767 median 0.683; mean R-only 1.261 median 1.205
accum 8: n=7 cells; mean D/N(C ref) 1.182 median 0.854; mean R-only 1.116 median 1.083
```

### Calibration sweep (healthy only, C + 2 resumes per eps; mean |dL| of R vs C)

```
accum 4 eps 0.0001: loss level 7.9382  mean|dL| R1-C 0.00001 (0.000%)  R2-C 0.00000 (0.000%)  R1-R2 0.00001  first 0.0e+00 early_max 1.0e-05
accum 4 eps 0.001: loss level 7.9462  mean|dL| R1-C 0.00001 (0.000%)  R2-C 0.00002 (0.000%)  R1-R2 0.00001  first 0.0e+00 early_max 2.0e-05
accum 4 eps 0.01: loss level 7.9559  mean|dL| R1-C 0.00027 (0.003%)  R2-C 0.00050 (0.006%)  R1-R2 0.00028  first 0.0e+00 early_max 3.6e-04
accum 4 eps 0.03: loss level 8.3165  mean|dL| R1-C 0.00057 (0.007%)  R2-C 0.00077 (0.009%)  R1-R2 0.00050  first 0.0e+00 early_max 3.1e-04
accum 4 eps 0.1: loss level 10.2066  mean|dL| R1-C 0.00309 (0.030%)  R2-C 0.00411 (0.040%)  R1-R2 0.00195  first 0.0e+00 early_max 2.1e-03
accum 4 eps 0.3: loss level 13.7477  mean|dL| R1-C 0.01083 (0.079%)  R2-C 0.01534 (0.112%)  R1-R2 0.00475  first 0.0e+00 early_max 2.2e-03
accum 8 eps 0.0001: loss level 7.6397  mean|dL| R1-C 0.00001 (0.000%)  R2-C 0.00001 (0.000%)  R1-R2 0.00001  first 0.0e+00 early_max 0.0e+00
accum 8 eps 0.001: loss level 7.6384  mean|dL| R1-C 0.00005 (0.001%)  R2-C 0.00004 (0.001%)  R1-R2 0.00001  first 0.0e+00 early_max 2.0e-05
accum 8 eps 0.01: loss level 7.7084  mean|dL| R1-C 0.00302 (0.039%)  R2-C 0.00319 (0.041%)  R1-R2 0.00037  first 0.0e+00 early_max 1.3e-04
accum 8 eps 0.03: loss level 8.2877  mean|dL| R1-C 0.00067 (0.008%)  R2-C 0.00063 (0.008%)  R1-R2 0.00088  first 0.0e+00 early_max 1.8e-04
accum 8 eps 0.1: loss level 10.7154  mean|dL| R1-C 0.00509 (0.047%)  R2-C 0.00435 (0.041%)  R1-R2 0.00905  first 0.0e+00 early_max 1.9e-03
accum 8 eps 0.3: loss level 14.0176  mean|dL| R1-C 0.01103 (0.079%)  R2-C 0.01792 (0.128%)  R1-R2 0.00921  first 0.0e+00 early_max 1.7e-03
accum 4 eps 0.6: loss level 16.1936  mean|dL| R1-C 0.00267 (0.017%)  R2-C 0.00309 (0.019%)  R1-R2 0.00284  first 0.0e+00 early_max 1.1e-03
accum 4 eps 1: loss level 19.0088  mean|dL| R1-C 0.04381 (0.230%)  R2-C 0.01609 (0.085%)  R1-R2 0.02827  first 0.0e+00 early_max 4.1e-03
accum 4 eps 2: loss level 26.5312  mean|dL| R1-C 0.05208 (0.196%)  R2-C 0.02747 (0.104%)  R1-R2 0.07627  first 0.0e+00 early_max 7.1e-03
accum 4 eps 4: loss level 46.1151  mean|dL| R1-C 0.26389 (0.572%)  R2-C 0.20331 (0.441%)  R1-R2 0.09076  first 0.0e+00 early_max 2.0e-02
accum 4 eps 8: loss level 58.8666  mean|dL| R1-C 0.33627 (0.571%)  R2-C 0.57145 (0.971%)  R1-R2 0.90772  first 0.0e+00 early_max 1.1e-01
accum 8 eps 0.6: loss level 17.2107  mean|dL| R1-C 0.01285 (0.075%)  R2-C 0.00638 (0.037%)  R1-R2 0.01477  first 0.0e+00 early_max 2.7e-04
accum 8 eps 1: loss level 22.7569  mean|dL| R1-C 0.05958 (0.262%)  R2-C 0.05218 (0.229%)  R1-R2 0.00840  first 0.0e+00 early_max 2.5e-03
accum 8 eps 2: loss level 46.1181  mean|dL| R1-C 0.05536 (0.120%)  R2-C 0.09659 (0.209%)  R1-R2 0.04584  first 0.0e+00 early_max 4.8e-02
accum 8 eps 4: loss level 54.9842  mean|dL| R1-C 0.37740 (0.686%)  R2-C 0.12729 (0.232%)  R1-R2 0.26124  first 0.0e+00 early_max 5.4e-03
accum 8 eps 8: loss level 55.2770  mean|dL| R1-C 0.16423 (0.297%)  R2-C 0.26108 (0.472%)  R1-R2 0.11802  first 0.0e+00 early_max 7.4e-02
```
