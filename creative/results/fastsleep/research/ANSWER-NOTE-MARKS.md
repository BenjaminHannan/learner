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
