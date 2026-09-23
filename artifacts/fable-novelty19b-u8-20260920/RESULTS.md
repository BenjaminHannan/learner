# Experiment 19b (D only, U5 vs U8) — results

Fable (coordinator) · 20 September 2026 · development panels only (38 cells × 64 units), seeds
1900/1901/1902, 2,000 offline updates from experiment 19's D awake checkpoints. Run once under
FREEZE-MANIFEST.md (sha aa07e1d2…). Source tables: `logs/report.txt`, `logs/gates.txt`, `scores/*.json`.

## Registered verdict: FAIL in all three seeds

No seed met the five conditions. `DEV-PASSED.json` was not written; confirmation panels stay locked.
Provenance gates passed (9/9 endpoints, 38/38 cells, one trainer version, no conflicts).

Promised hand cross-check (manifest disclosure 3): per-unit flags summed against cell totals for answers and
strict, all 9 score files — 684 checks, 0 mismatches.

## Every seed (answers/strict out of 64; "calls" = mean operator calls)

| Seed | U5 (practice 1–5 calls) | U8 (practice 1–8 calls) | U8 retention |
|---|---|---|---|
| 1900 | N-c4 42/41, 49/48; c5 0 strict | collapsed: exactly 2.0 calls, 0 strict on every cell c≥4 | pass |
| 1901 | N-c4 62/62, 60/60; N-c5 52/52, 49/49 | collapsed: exactly 3.0 calls, 0 strict on every cell c≥4 | FAIL: H-c3-p16 64→53/52, H-c3-p6 64→57, F-c3-r9 58/57 |
| 1902 | N-c4 26/25, 31/29; N-c5 34, 38/37; lost H-c3 (64→25/21, 28/25) | improved: N-c4 61/61, 58/58; N-c5 53/53; P-c4 60–62; L-c6 strict 31/36/39; L-c7, L-c8 0 | pass |

Summed strict over the four c=4/5 N cells, U5 → U8: 89 → 0, 223 → 0, 125 → 225.
Mean calls on L-c8-r10-p16, U5 → U8: 3.98 → 2.00, 5.19 → 3.00, 6.02 → 4.25 (U8 lower in every seed).
Treatment mark (U8−U5 ≥ 13 strict on all three c=6/7/8 r10 cells): not met anywhere; seed 1902 met it on
L-c6-r10 only (39 vs 5). Edit-pair guard E at c=8: 0 strict everywhere (c=5 E cells, best per arm: U5 57/46/40 in s1901, U8 48/38/48
in s1902, 0 in both collapsed U8 seeds — none at the 58 mark). No cell at c=7 or c=8 above 1 strict.

## What it means

- Widening practice from 5 to 8 calls, with everything else the same, did not produce dependable long chains.
  In two of three seeds it made the controller stop *earlier* than before (2 or 3 calls), wiping out the
  4–5-call skill U5 gives. In one seed it helped: 4–5 calls became near-reliable and 6 calls about half right.
- U5 reproduced experiment 19's U arm on fresh panels (c4 N strict within ±12 on all six cells), including
  seed 1902's loss of the short held-out skill. The 19 result was not a fluke of its panels.
- The outcome is strongly seed-dependent, and nothing ever reaches 7–8 calls.

## What it does not mean

- Not evidence that long chains are unlearnable, or that more time or a new mechanism is necessary (claim
  limit in the manifest): one mixture, 2,000 updates, one world family, three conditional seeds.
- Not a causal finding about *why* two seeds collapsed. A reading consistent with the data — most long
  practice rollouts fail under a final-answer-only reward, so the per-call cost makes "stop early" the
  locally best policy — is a hypothesis only; 19b has no arm that isolates it.
- Seed 1902's gain is descriptive; it is not a pass and not seed generalisation.
- The three seeds are continuations of experiment 19's checkpoints, not three fresh replications.

## Fable predictions (hashed before the build, sha 2298881d…)

| # | p | Outcome | Brier |
|---|---|---|---|
| P83 full pass | 0.03 | FALSE | 0.0009 |
| P84 bounded competence ≥1 seed | 0.07 | FALSE | 0.0049 |
| P85 ≥58 strict on a c=6 cell | 0.30 | FALSE (max 39) | 0.0900 |
| P86 ≥58 strict on a c=7/8 cell | 0.10 | FALSE (max 0 in U8) | 0.0100 |
| P87 U8 calls > U5 on c8/r10, 3/3 | 0.80 | FALSE — U8 *lower* in 3/3 | 0.6400 |
| P88 treatment mark ≥1 seed | 0.15 | FALSE | 0.0225 |
| P89 dilution at c4/5 in ≥2/3 | 0.60 | TRUE (89→0, 223→0) | 0.1600 |
| P90 U8 loses ≥7 on an H cell | 0.45 | TRUE (s1901 −7, −11/−12) | 0.3025 |
| P91 U5 reproduces exp-19 U | 0.60 | TRUE (41/48, 62/60, 25/29) | 0.1600 |
| P92 c=8 E cell ≥58 | 0.04 | FALSE (max 0 at c=8) | 0.0016 |
| P93 all F cells ≥61 in U8, 3/3 | 0.55 | FALSE (s1901 F-c3-r9 58/57) | 0.3025 |

Mean Brier 0.154. The big miss is P87: I expected wider practice to at least lengthen execution; it shortened it.

## Next

No confirmation read. The design of the next control experiment goes to a Fable reviewer (and the outside
GPT-6 Pro answer, if it arrives); candidates it must weigh include a no-call-cost arm and a staged (5→6→7→8)
curriculum, one change at a time.
