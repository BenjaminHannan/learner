# Roadmap 7d screens: creative-only sleep (loop 1), CPU, DEV only

Spec: creative roadmap sec. 7d, rulings b69b136446, 71050e463c, 13f4b987eb. Code: `creative/sleep7d.py`, `creative/knew.py`. Parents: N' rebuilt on CPU from B2_s100 / B2_s101 (`build_nprime.py`, `s1/s10x/nprime-build.json`). Run: `chain2.sh`. No sealed file, C2 labelled set, research-loop holdout or K_new test was opened. No K_new set was written or sealed.

## S1 (finished 03:56 UTC 10-08 = 11:56 PM ET 10-07)

Day: the worker (adapter off) tries each of 1,024 C2 pool questions greedily, and it fails almost all of them (passes 0.1% and 0.6%). On the stuck questions, the adapter-on search makes 32 tries, then 480 more where none of the 32 fit. Loop 1 (REINFORCE on the adapter only, KL 0.1 to the pre-night adapter) trains on up to 8 fitting and 8 failing tries per question: 550 and 565 questions kept. S is the placebo: the same updates with shuffled rewards. U is the untrained adapter. The setting is picked on fit@32 over the C2 DEV questions the worker fails (255 / 254 of 256). Both parents picked lr 1e-3 with 1 pass. Higher lr or more passes collapsed (KL 30-66, fit@32 down to 0-19%).

Measures: 512 tries per question at T=3 in creative mode, one sampling seed for every arm. The intervals are paired 95% bootstraps per question.

| | s100 | s101 |
|---|---|---|
| C2 DEV reach@32: U / S / C | 24.2 / 25.0 / 42.2 | 27.3 / 25.0 / 43.4 |
| **C - U** (mark >= +5) | **+18.0** [13.3, 22.7] | **+16.0** [11.3, 21.1] |
| **C - S** (mark >= +3) | **+17.2** [12.1, 21.9] | **+18.4** [13.7, 23.4] |
| distinct fitting programs / question within 32: C vs U (mark C >= 0.8 x U) | 0.79 vs 0.33 | 0.52 vs 0.36 |
| worker untouched (adapter off == N', before and after training) | pass | pass |
| reach@512: C - U | -0.8 [-5.1, 3.5] | -0.8 [-3.9, 2.3] |
| tries to first fit (questions with a fit): U / C | 90 / 31 | 79 / 34 |
| near-copy kinds (102 q), C - U | +40.2 [30.4, 50.0] | +35.3 [26.5, 45.1] |
| multi-step kinds (154 q), C - U | +3.2 [-0.6, 7.1] | +3.2 [-0.6, 7.8] |
| transfer, K_new DEV reach@512 (192 q, report only), C - U | -2.1 [-4.2, -0.5] | -2.6 [-4.7, -0.5] |

Verdict (`s1/s1-report.json`): **PASS on both parents.** Multi-step C - U pooled over both parents is +3.2 [0.6, 6.2]. That lower end is above 0, so the label is **"beyond near-copy"**, though only narrowly. Not proved wrong: the upper end of C - S is far above +1.

How to read it:
- *Shown:* within 32 tries, the trained creative part finds a fitting answer about 3 times sooner on the kinds the worker was stuck on. Shuffled rewards do nothing.
- *Shown:* it does not reach more questions at 512 tries (C - U is about -1 at reach@512). It finds the same answers faster; it does not find new ones. This is the usual pattern when reinforcement learning sharpens a sampler.
- *Shown:* most of the gain is on the near-copy kinds. The multi-step gain is small (+3).
- *Shown, small:* on the transfer kinds it loses the few rows the untrained search reached (reach@512 2-3% falls to 0).
- *Caveat:* the setting was picked on the same C2 DEV questions it is measured on, with different samples. The pick beat 5 other settings by a wide margin on s100, but tied with lr 1e-3 / 2 passes on s101. The pick can inflate C a little, and S (trained at the same setting) does not cancel that inflation.
- Wording, per the ruling: "finds answers faster on the kinds it was stuck on", never "more creative in general".

## S3

Pending (`s3/`).
