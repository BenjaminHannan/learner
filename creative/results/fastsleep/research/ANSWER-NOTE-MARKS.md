# Can the answer note come back without harm? Marks (written 9:42 AM ET 10-07, before any run of this setting; commit 3d4c03912)

Ben asked (9:34 AM ET 10-07) for more research into fast sleep. The coordinator's default included one question: whether the answer note
can come back without the harm it caused on s205.

## What changes
- **Arm M2** = C2b's arm M (memory + 512 old notes, answer note off) with the answer note switched back on behind an **agreement gate**.
  - The answer note may fire on a question only if at least one step note fired on that same question in the same pass. Its own
    calibrated gate must also clear, as before.
  - Code: `m_knn(..., ans=2)`.
- **Why:** on s205 the step notes never fired on chain-5 skills rows, while the answer note fired on 13.9% of them. Every skills harm
  came from answer-note firings on questions the step notes did not recognise.
- **Nothing else changes:** c 50, theta 0.9, cal 0.99, old 512, k 16 and tau 0.05 all stay. There is no tuning. This is one run per parent.

## Parents
All eight kept parents: s100, s101 and s200-s205. Each uses its own W records.

## Measures
1. **DEV gain** (tuning split, reported): greedy first try on W, M2 minus N and M minus N, pooled over the 6 confirm parents.
2. **Fresh harm:**
   - Slice: `data_big/dev/frame.jsonl`, all 6,800 rows across 34 families. This split has never been scored by any fast-sleep run.
     Earlier runs read only `dev/in_dist`.
   - Harm = N's exact minus M2's exact, in points, on the whole slice and on its chain-5 rows (1,000) separately.
   - M (answer note off) is scored on the same slice and reported beside it.

## Marks
- **Harm pass:** M2 harm <= 2.0 points on every parent, on the whole frame slice AND on its chain-5 rows.
- **Worth bringing back:** M2's pooled DEV gain is at least M's pooled DEV gain + 1.0 point.
- **Adopt M2** (recommend it to the roadmap in place of M) only if both pass. Otherwise the answer note stays off.
- **Proved wrong:** M2 chain-5 harm > 2 on any parent. The agreement gate then does not stop the harm.

No re-runs and no other slices. A failing parent is reported as it is.

## Result (10:15 AM ET 10-07): harm PASS, gain mark missed by 0.02 points, so the answer note stays off

| Parent | M DEV gain | M2 DEV gain | M2 minus M | Frame harm M / M2 | Frame chain-5 harm M / M2 |
|---|---|---|---|---|---|
| s100 | 33.98 | 34.38 | +0.39 | -0.26 / -0.26 | 0.00 / 0.00 |
| s101 | 28.12 | 28.52 | +0.39 | -0.35 / -0.35 | 0.00 / 0.00 |
| s200 | 31.25 | 32.03 | +0.78 | -0.28 / -0.29 | 0.00 / 0.00 |
| s201 | 37.50 | 37.50 | 0.00 | -0.21 / -0.22 | 0.00 / 0.00 |
| s202 | 16.41 | 21.48 | +5.08 | -0.22 / -0.22 | 0.00 / 0.00 |
| s203 | 28.91 | 28.91 | 0.00 | -0.15 / -0.13 | 0.00 / 0.00 |
| s204 | 40.62 | 40.62 | 0.00 | -0.19 / -0.21 | 0.00 / 0.00 |
| s205 | 32.03 | 32.03 | 0.00 | -0.41 / -0.41 | 0.00 / 0.00 |

- **Harm pass: PASS.** M2's harm is at most 2 points on all eight parents, on the whole frame slice and on its chain-5 rows. Every harm value is 0 or slightly negative, including s205, the parent the answer note hurt in the confirm.
- **Worth bringing back: FAIL, narrowly.** Pooled over the 6 confirm parents, M2 is 32.10 against M's 31.12, a gain of +0.98. The mark needed +1.0. Over all 8 parents it is +0.83. Most of the gain is one parent, s202 (+5.1). Four parents show no change.
- **Proved wrong: no.** The agreement gate did stop the harm.
- **Decision by the marks:** do not adopt M2. C2b's arm M keeps the answer note off.
