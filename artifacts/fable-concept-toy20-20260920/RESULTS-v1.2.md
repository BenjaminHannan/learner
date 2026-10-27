# Concept toy ct20-v1.2 — wave-1 calibration pilot result

Fable (coordinator) · 21 September 2026 UTC · one registered launch under FREEZE-MANIFEST-v1.2.md (sha bc48f066…).
Outputs: `wave1/registered-v1.2/` (sealed: `wave1/VERDICT-SEAL-v1.2.sha256.txt`, 885 files hashed).

## Registered verdict: **too-hard** (two-tier status complete; binding)

"Not learned by these baselines under EITHER registered budget. This is not proof that the toy is intrinsically
too hard and not a convergence certificate; falling loss alone supplies none." (driver's registered wording)

| | Tier L (2e8 ops/rung) | Tier H (1e9 ops/rung) |
|---|---|---|
| Fits | 72 run now, 0 reused, all ok | 72 run now, 0 reused, all ok |
| Accounting | valid; worst cross-arm gap 0.014096; 360 ledger rows, 0 over allowance, 0 negative reservations | valid; worst gap 0.000557; 360 rows clean |
| Control competence (E_512 ≤ 0.10 on ≥ 5/6) | G 0/6, T 3/6 → fails | G 5/6, T 6/6 → passes |
| Concept (C) cases learned (need ≥ 9/12 in one arm) | — | G 2/12, T 3/12 |
| Median C E_32 / E_512 | G 3.15 / 0.82 · T 3.76 / 0.96 | G 2.72 / 0.70 · T 2.60 / 0.59 (advance needs ≤ 0.50) |
| Startup labels, C fits (24 per arm) | all 48 "started, not yet learned" | G: 5 learned+generalised, 7 learned-but-failed-to-transfer, 12 not yet learned · T: 6 / 2 / 16 |
| Gate verdict | calibration-invalid/startup-or-implementation → tier H required | too-hard |

Isolation check: PASS. Wall clock 62.3 s (preflight 16.7 s). Disclosure: one macOS system process
(fileproviderd) held ≈ 1 core during the run; no other Python job ran; the preflight passed before each tier.
v1.1 (permanently invalid, accounting) elapsed resources, as owed: 17.9 s wall, 8.4 s preflight.

## What it means
- The accounting fix worked: the run is valid, so this is the pilot's real answer.
- With the small budget neither baseline even learns the easy control worlds. With 5× the budget both learn the
  controls well, but only 2–3 of 12 concept cases; the typical concept fit is still not trained to low error.
- So wave 1 does not advance: as registered, these two baselines at these two budgets cannot serve as the
  yardstick for the concept toy.

## What it does not mean
- Not evidence the toy is intrinsically too hard, and not evidence about System S or any concept-learning idea —
  no such model was run. It is a statement about two plain baselines under two fixed operation budgets.
- G-vs-T differences here (T slightly better at tier H) are descriptive; the pilot is not a comparison test.
- "Equal counted operations under the registered estimate" is not equal hardware work, time or energy.

## Predictions (sha 420f9363…, written before any fit)
P76 FALSE (.07) · P77 TRUE (.75) · P78 TRUE (.88)† · P79 FALSE (.22)† · P80 FALSE (.03) · P81 FALSE (.65; T beat G)
· P82 TRUE (.70; my reading of the labels). Mean Brier 0.092. † scored on v1.2 only, per ruling 3.

## Reproducibility check (ruling 3 §2.2), done after the verdict was sealed
All 72 tier-L fits are bit-identical between the quarantined v1.1 run and the registered v1.2 run: model
parameters and both optimizer moments at all five rungs (8,640 exact tensor comparisons),
`query_predictions_by_rung`, and both audit prediction sets. No difference of any size. The removed final
query-panel pass was redundant in both versions (final predictions = rung-512 predictions, 72/72). A negative
control confirmed the comparator can see differences. Details: `wave1/V11-V12-COMPARISON.md` (sha 86f045af…).
v1.1's numbers remain unreportable; this line is the only use made of them.

## Next
Per the pre-commitment, no v1.3 from us: any change of budget, baseline or toy difficulty is a question for Astra.
