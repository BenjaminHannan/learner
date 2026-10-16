# PREREG (DRAFT, NOT SEALED): GPU-RUN-4, the deferred batched writer and the K/V concat hoist

Status: **draft written 2026-10-16 by the launch-bound solve session.** It is sealed only when Muse or Ben adds a dated "SEALED" line below. No box may be rented on it before then. Amendments follow the house rule: dated, written before the result files they concern are read, and the original text kept.

Code: custom_io at 74d6e92c75 (PC mainline code), run through `launch/prof_launch.py`, which registers `defer`, `kvcat` and `fastteach` into `prof/prof_train.py`. Model: B3G2 3M, caps_b3g2.json, real pool `p10-rung30-s400-a64-L`, real EmbeddingGemma 2, bf16 autocast, seed 400, batch 256.

## Arms (one change per arm, in this order)

| arm | A | B | accum |
|---|---|---|---|
| D4 | baseline | `defer` | 4 |
| K4 | `defer` | `defer,kvcat` | 4 |
| D8 | baseline | `defer` | 8 |
| AA | baseline | baseline | 4 (noise control) |

## Sections per box, in this order

1. `profiler,syncs` for baseline and `defer` (counts, 2 profiled updates each).
2. `abequiv --ab-variants defer,kvcat` (mark 6 bf16 bar, with the rerun noise floor). For `kvcat`, also under `torch.use_deterministic_algorithms(True, warn_only=True)`: baseline vs baseline, then baseline vs `kvcat`.
3. E4 for `defer`: a 300-update loss trace against the baseline, same seed and rows.
4. `abbench`: arms AA, D4, K4, D8; 3 interleaved rounds A,B,A,B,A,B of 10 warm-up + 40 timed updates (chunks of 5).
5. The host monitor (10 s: SM clock, power, temperature, throttle reasons, CPU steal, trainer-core MHz) runs throughout.

## Marks (fixed now)

1. **Win.** A speed arm counts only if, on the warm stretch, every one of its 3 normal-speed rounds has B < A, median B ≤ 0.95 × median A, peak allocated ≤ 10 GB, and mark 2 holds.
2. **Same maths.**
   - `defer`: bf16 bar (relative loss difference ≤ 1e-4, gradient cosine ≥ 0.9999, beside the rerun floor) AND E4 (mean |Δloss| over updates 101–300 ≤ 0.02, the two means within 0.01). It is labelled **numerics-changing** whatever the result.
   - `kvcat`: in deterministic mode, bitwise equal (loss, all gradients, 3 updates) if baseline vs baseline is bitwise; otherwise arm-vs-baseline ≤ baseline-vs-baseline on every statistic. Failing that it falls to the bf16 bar and is relabelled near.
3. **Normal speed (Amendment 5 of PREREG-b3g2-speed-ab, extended).** A round is read only if all of these hold:
   - its A median is ≤ 1.10 × the fastest A round of the same box over all arms;
   - no host-monitor sample in the round shows a throttle reason other than idle;
   - CPU steal is < 2%;
   - the A chunk spread (largest / smallest chunk) is ≤ 1.05.

   An arm with fewer than 3 normal rounds is "regime-confounded" and is repeated, never read.
4. **Identical work.** Each A and B round logs Σ rounds per update. Any mismatch voids the round.
5. **Noise.** AA must show |median B / median A − 1| < 1%. Otherwise nothing on that box counts.
6. **Replication.** D4 must meet mark 1 on two boxes on different hosts, reported separately and never pooled.
7. **Mechanism (deterministic counts, from section 1).** For `defer`:
   - stream syncs per update ≤ 300 (baseline ≈ 1,305);
   - DtoH per update ≤ 150 (≈ 745);
   - kernels per update ≤ 0.65 × the baseline's.

   A D4 speed result whose counts miss these is reported as an artifact, not a win.

## Predictions (each with what proves it wrong)

- P1: D4 ≥ 1.25× on each box. Proved wrong if < 1.10× while mark 7 holds; **that result also kills the launch/sync-bound account** (solve report §7).
- P2: D8 gain ≥ D4 gain. Proved wrong if D8 < D4.
- P3: K4 between 1.00× and 1.10×. Proved wrong outside that band.
- P4: on the PC (separate session, same marks), D4's gain is smaller than on the 4090. Proved wrong if it is larger.
- P5: `defer`'s peak allocated is ≤ baseline + 0.5 GB.
- P6: the baseline's unprofiled kernel time (CUDA events around the update) is ≤ 1.6 s/update. Proved wrong if it is ≥ 2.0 s; that also kills the framing.

## Money

The box refuses to start without the offer's hourly price, and refuses MAXH × price above $1.50 (box 1: MAXH 3 h; box 2 runs abbench D4 + AA only, MAXH 1.5 h). Expected total ≈ $1.8 at about $0.43–0.46/h. Every dollar figure is wall time × the billed rate. The week's spend is read from SPEND.md before renting, against the $50 Vast cap.

## Rules carried over

- No ratio from a slow regime is quoted anywhere.
- The historical 2.24 s/update is quoted beside the in-box A, never instead of it.
- A numerics-changing arm is used only in runs started at update 0 with it, under a new run name, with `--speed-arms` in the resume config hash.
