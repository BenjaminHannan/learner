# Pass marks: deep experts (each expert has 4 or 8 hidden layers) in the sparse-MoE loop

Sealed 2026-09-29 11:18 UTC (from `date -u`), before any source practice, maze score or GPU run of these configs. Nothing here changes after a score is seen; a later change needs an ADDENDUM committed before the next score. Ben asked for this on 2026-09-29 (11:13 UTC relay, "experts with 4 and 8 hidden layers each, on the many-layer reasoner"). It runs beside the sealed test (`artifacts/claude-moe-deep-20260929/`), which is not edited.

## Question and arms
Does making each routed expert a deeper MLP, at the same stored and active size, raise the practised few-example score over the main entry?
- **MX** = L8-E64 (8 layers per round, 64 experts, top 8 + 1 shared, every expert one hidden layer of 64). Its numbers come from the sealed phase 1 dev ladders (`artifacts/claude-moe-deep-20260929/eq-runs/L8-E64-pre-s{0,1}/adapt.json`), read, never rerun here.
- **X4** = L8-E64-X4: same, every expert 4 hidden layers of width 49 (residual inside the expert). 19.28M stored (0.988 of MX), 4.61M active (0.982 of MX) (`artifacts/claude-moe-deepx-20260929/selftest2.json`).
- **X8** = L8-E64-X8: 8 hidden layers of width 41. 19.55M stored (1.002 of MX), 4.62M active (0.983 of MX).
Each arm: qualified source practice, then the ruler's dev ladder (practised start, 9x9, 8 rungs k = 1 ... 16,384), seeds 0 and 1, run through the sealed driver (`scripts/claude_moe_deepx_run.py` wraps it, adds only the two configs). `F_eq` and `F_few` are the ruler's: mean of 100 x (9x9 learned-stop right of 300) over all eight rungs, and over k = 1, 4, 16, 64.
This is a **dev** comparison (report only, like the sealed scaling rows). No holdout is scored. A holdout for an arm needs its own sealed marks, and is asked for only after a HELPS here.

## Validity, before any maze rung (same as the sealed test)
- **V1**: source guard at least 190 of 200 on 4-digit sums and on 5x5 grids, source lr 1e-3, one retry at 5e-4 (source only). If both fail in a seed: that arm-seed is **DID NOT TRAIN** and gets no maze ladder.
- **V2**: every 2-D weight matrix gets a nonzero gradient (the harness check). Expert liveness is reported, not gated.

## The words (dev 9x9)
Per arm A in {X4, X8} and seed s: gap(A, s) = F_eq(A, s) - F_eq(MX, s).
- **HELPS**: gap >= +8.0 in every seed (8.0 = 2 x 3.96, the all-starts F_eq SD, `artifacts/claude-dir-lr-20260928/NOISE.md`; the house "helps" bar).
- **HURTS**: gap <= -8.0 in every seed.
- **PROVED WRONG** (for "deeper experts help"): gap <= 0 in every seed (no gain over one-layer experts in any seed).
- **NOT SHOWN**: anything else. **DID NOT TRAIN** as above. With one seed run, every word carries "(one seed: suggested)".
Each gap is also printed in SD units (gap / 3.96).
Depth inside the expert: X8 - X4 per seed is reported with the same HELPS / HURTS / NOT SEPARABLE words at 8.0.

## Required rows (words fixed now; they do not change the verdict)
- **F_few (k = 1 to 64), dev**: few-gap = F_few(A, s) - F_few(MX, s); HELPS if every seed >= +10.5, HURTS if every seed <= -10.5, else NOT SEPARABLE (10.5 = 2 x 5.23, all-starts F_few SD).
- **Plain row**: recorded practised plain net (holdout F_eq 33.79 / 33.58) and the sealed plain-big dev row if it exists, beside A. A HELPS on F_eq with A not above plain-big is called suspect (memorising), listed as such.
- **Per-rung table**: x of 300 at every rung, learned stop and fixed-16 read, cap hits. **Stop failure** = learned right more than 6 of 300 below the fixed read at a rung; listed per arm-seed.
- **Routing health**: dead experts, busiest/mean load, load entropy per stage (`routes.json`).
- **Size**: stored and active weights next to MX.

## Marks self-check (Ben 21:37 UTC 09-28)
1. Bars above noise: 8.0 = 2 x SD 3.96 (NOISE.md, all-starts F_eq, dev); F_few 10.5 = 2 x 5.23.
2. "Every seed" reading: HELPS / HURTS need every seed; PROVED WRONG only if every seed is at or below MX; else NOT SHOWN.
3. Comparator: MX from the sealed run, same seeds and ruler; also compared to plain-big and the recorded loop rows in the report.
4. Plain-net row: plain-big / recorded plain listed; a same-size plain net cannot pass a maze row it never practised.
5. F_few is its own required row beside F_eq.
6. Sleep: no sleep claim is made from this test (it does not run sleep gates).
Caveat, not a mark: MX ran on whichever machine the sealed run used (a vast RTX 5080 or BensPC), these arms run on BensPC or vast; strict fp32 is set by the driver in every case; a machine difference is small next to the 3.96 SD but is untested here.
