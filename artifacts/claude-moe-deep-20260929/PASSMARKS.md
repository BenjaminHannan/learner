# Pass marks: deep sparse-MoE loop on the fair few-example ruler

Sealed 2026-09-29 01:06 UTC (date -u), before any source practice, any maze score and any GPU run. Nothing here changes after a score is seen. A later change needs an ADDENDUM committed before the next score, and it never re-reads scores already seen. Design: `DESIGN.md`. Scoring: `scripts/claude_moe_deep_report.py` (applies these marks from raw JSON). Driver: `scripts/claude_moe_deep_run.py`.

## Question and arms

Question: does the deep sparse-MoE loop (**MX = config L8-E64**: 8 distinct layers per round, 64 experts per layer, top 8 routed + 1 shared) beat the practised loop by at least +10 F_eq **in every seed**? Second question: how does its score change as depth and expert count grow?

- **MX practised**, seeds 0 and 1: qualified source practice, then the ruler's dev ladder, then the one-time holdout.
- **Loop comparator (recorded)**: practised loop holdout F_eq **51.00** (seed 0) and **51.29** (seed 1); F_few 13.83 and 16.17 (`artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre/holdout.json`, recomputed by the report script).
- **Same-GPU loop control** ("loopctl"): the same qualified loop sources (sha256 in `artifacts/claude-distill-20260928/checkpoints-sha256.txt`), re-run through the same driver on the same GPU, dev ladder and holdout.
- **Plain row (recorded)**: practised plain holdout F_eq 33.79 and 33.58, F_few 3.33 and 1.00.
- Report-only rows (dev only, no holdout): the scaling configs, the dense controls, the same-size plain net and MX's fresh copy (below).

Definitions (the ruler's, unchanged): `F_eq` = mean over the eight rungs k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384 of 100 x (9x9 learned-stop right of 300). `F_few` = the same mean over k = 1, 4, 16, 64. Every rung count is reported as x of 300.

## Comparator, fixed now

`L*` = the higher of the two recorded practised loops' holdout F_eq = **51.29**, raised to the higher same-GPU loop control's holdout F_eq if either is higher. `C_few` = the same rule for F_few (recorded higher = **16.17**). If the loop control cannot run (sources not reachable), `L*` = 51.29 and the report says the same-machine check is untested.

## Validity, before any maze rung

- **V1 (source guard)**: MX practised source scores at least 190 of 200 on 4-digit sums **and** at least 190 of 200 on 5x5 grids, on the untouched guard seed (SOURCE_SEED + 300), in each seed. Source lr 1e-3. **If V1 or V2 fails at 1e-3, one retry at 5e-4 is allowed, source only (no maze is generated before it).** If both fail in a seed, that seed gets no maze ladder and the test's word is **DID NOT TRAIN** (hard to train; nothing about mazes is claimed).
- **V2 (gradient)**: the harness's gradient check (every 2-D weight matrix gets a nonzero gradient on one sums batch and one grids batch). Expert liveness (3-D expert tensors) is reported, not gated.
- **V3 (ruler)**: already PASS (`artifacts/claude-fewex-20260927/EQ-DEV-GATE.json`); unchanged.
- **Machine**: the CPU-vs-GPU smoke marks in `SMOKE_MARKS` (driver): max logit difference at most 1e-3, stop-probability difference at most 1e-3, routing agreement at least 0.99 in every layer, whole-model update difference at most 0.05 after 3 practice steps and 8 maze updates, and at most 0.08 after 3 sleep steps, with strict fp32 flags. **If the smoke fails**, the runs still use the GPU (a CPU run takes about 17 h practice + 26 h per ladder per thread: measured 20.7 s per maze batch here). The comparator is then the same-GPU loop control **only**, and every result is labelled "GPU, not CPU-equivalent".

## The verdict (holdout, 9x9)

Per seed s in {0, 1}: **G1**: F_eq(MX, s) >= L* + **10.0**.

- **PASS**: G1 holds in **every** seed (both).
- **PROVED WRONG**: F_eq(MX, s) <= L* in **every** seed (no gain over the best practised loop in any seed). Sub-word **HURTS** when every seed is at or below L* - 8.0.
- **NOT SHOWN**: anything else (for example one seed passes, or both land between L* and L* + 10). A non-win is never called a loss unless both seeds are at or below L*.
- **DID NOT TRAIN**: V1 fails at both source learning rates in a seed.
- The holdout is scored **once**, only after the phase-1 dev records (MX and loop control, both seeds) are committed to main, with no recipe or model selection. A blind recount from raw JSON and these marks follows.

**Reading against noise (fixed now).** Run-to-run noise of F_eq: SD 3.33 (practised-loop dev curves, H12) to 3.96 (all four starts, dev; 4.03 on holdout), `artifacts/claude-dir-lr-20260928/NOISE.md`. The house "helps" bar is 8.0 (2 x 3.96). The +10 bar is 2.5 x 3.96 = 10 points, so one seed clearing it by luck is about 1 in 170 and both about 1 in 30,000 (one-sided normal approximation, z = 2.53; suggested). Each seed's gap is also printed in SD units (gap / 3.96).

## Required rows (words fixed now; they do not change the verdict)

- **R1 F_few (k = 1 to 64), holdout.** Few-gap = F_few(MX, s) - C_few. **HELPS** if every seed's few-gap >= +10.5; **HURTS** if every seed's <= -10.5; else NOT SEPARABLE (10.5 = 2 x 5.23, the all-starts F_few SD, NOISE.md).
- **R2 plain rows.** Recorded practised plain (holdout F_eq 33.79 / 33.58, F_few 3.33 / 1.00) beside MX. The same-size plain net (plain-big, 19.5M, dev) is in the attribution rows.
- **R3 per-rung table**: x of 300 at every rung, 9x9 (7x7 of 48 and 11x11 of 300 secondary), learned stop and fixed-16 read, mean rounds, cap hits, E50. **Stop failure** (the ruler's rule): learned right more than 6 of 300 below the fixed read at a rung; listed per seed.
- **R4 old kinds and sleep**: sums and grids of 200 before, after k = 64 and 16,384, and after each sleep branch. Report only, one sleep draw. **No sleep claim is made from this test.**
- **R5 routing health** per stage (`routes.json`, 32 dev 9x9 mazes, 48 rounds): dead experts, busiest/mean load, load entropy, how often a cell's top expert changes between rounds.
- **R6 size and compute**: stored and active weights next to the loop; GPU minutes per source and ladder.

## Scaling (report only, dev 9x9, phase 2)

Each point has its own source practice (same recipe, same V1/V2 rule) and a practised dev ladder. Depth curve at 64 experts: L = 2, 4, 8, 16 layers. Expert curve at 8 layers: E = 16, 32, 64, 128 (all top 8 + 1 shared). MX's own dev ladder is the L8-E64 point.
- Per seed and curve: Delta = F_eq(largest config) - F_eq(smallest); slope = least-squares slope of F_eq on log2(stored weights), in points per doubling.
- Words per curve: **SCALES UP** if Delta >= +8.0 and slope > 0 in every seed that ran; **SCALES DOWN** if Delta <= -8.0 in every seed; **FLAT** if |Delta| < 8.0 in every seed; else MIXED. With one seed the word is labelled "suggested". A missing smallest or largest point means NOT RUN.
- **Use gain** (does it keep improving with more examples?), per config: F at k = 16,384 minus F at k = 64, in points. Report only, no word.
- What would prove "bigger helps here" wrong: SCALES DOWN or FLAT on both curves in both seeds.

## Attribution (report only, dev 9x9, phase 3)

Words: HELPS if the difference >= +8.0 in every seed, HURTS if <= -8.0 in every seed, else NOT SEPARABLE.
- **A1 experts at equal active weights**: MX - L8-dense-act (8 dense layers, 576-wide FFN).
- **A2 experts at equal total weights**: MX - L8-dense-tot (8 dense layers, 4,224-wide FFN, 19.5M).
- **A3 loop at equal total weights**: L8-dense-tot - plain-big (the same 8 dense layers run once, no loop, the harness's plain arm with its source-only lr sweep).
- **A4 dense depth vs the loop**: L8-dense-act - recorded loop (dev). Confounded by 2.76x weights; said so in the report.
- **A5 practice**: MX practised - MX fresh (the ruler's fresh copy).

## Order and compute (Ben's machines only)

1. This file, DESIGN.md, the three scripts and `selftest.json` are committed to main before any run.
2. GPU smoke and timing on BensPC. Then phase 1: MX sources (seeds 0, 1), MX practised dev ladders (stage checkpoints kept), same-GPU loop control dev ladders.
3. Phase-1 dev records committed to main. Then the one-time holdout (MX practised and loop control, both seeds). Blind recount.
4. Phase 2 (scaling), then phase 3 (attribution), dev only, in the listed order (seed 0 of every config before seed 1). Whatever has not run when Ben stops them is reported NOT RUN. Nothing is chosen by its result.
BensPC RTX 5070 Ti through the Mac queue, $0. No vast rental without Ben's yes.

## Marks self-check (house rule, 21:37 UTC 09-28)

1. Bars above noise: +10.0 F_eq vs SD 3.33 to 3.96 (NOISE.md; house bar 8.0); F_few 10.5 = 2 x 5.23; scaling and attribution 8.0 = 2 x 3.96. Yes.
2. Every-seed reading: PASS and PROVED WRONG both need every seed; anything else is NOT SHOWN. Yes.
3. Fair comparator: the higher of the two practised loops (51.29), raised by the same-machine loop control if higher. Yes.
4. A row a plain same-size net cannot pass: G1's bar (at least 61.29) is 27.5 points above the recorded plain (33.79). The same-size plain net (plain-big) is a named row (A3). Memorising check: the ruler's holdout mazes are layout-disjoint from all 16,384 support mazes, so memorising the support scores nothing. Yes.
5. F_few beside F_eq as its own required row (R1). Yes.
6. Sleep: this test has no sleep gate. Sleep is report-only with one draw, and no sleep claim is made. Not applicable.

## Predictions (guesses, not results)

- P-MXD.1: DID NOT TRAIN in a seed, 10%.
- P-MXD.2: verdict PASS, 15%; NOT SHOWN, 50%; PROVED WRONG, 35%. Reasons: the same-size sparse loop swung +3.88 / -6.25; TRM says MoE and depth overfit small puzzle sets; lf-8 says distinct layers helped at 3.9x weights.
- P-MXD.3: the depth curve is FLAT or MIXED (60%) rather than SCALES UP (25%) or DOWN (15%).
- P-MXD.4: at least one layer has more than 25% dead experts at k = 16,384 (40%).
