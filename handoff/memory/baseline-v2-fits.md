---
name: baseline-v2-fits
description: 2026-09-20 — plain transformer baseline DOES learn 1–3 hop lookup once init is rescaled + attention hint (I1-H1 3/3 seeds 512/512, sealed confirm too); v1 "baseline can't learn" was an init artifact
metadata:
  type: project
---

Baseline v2 arm I1-H1 (operator-style init rescale 1/sqrt(3·fan_in) + evidence hint 0.5): 3/3 seeds 512/512 on all four fit cells, and 512/512 on the sealed 4-cell confirmation panel (read once, 2026-09-20). P26 hit.

**Why it matters:** the earlier "plain transformer stuck at chance" (v1, A-ev) was NOT evidence that decomposition is needed for lookup. The only open comparison is LENGTH generalisation (4–8 hops, 25-cell suite), predictions P47–P50 in `W/artifacts/fable-baseline-length-eval-20260920/PREDICTIONS.md` (sha cefbac00…).

**How to apply:** never claim "a standard transformer can't learn this toy". Other three arms (I0-H1, I1-H0, I0-H0) ran on rental box 51781306 to separate init vs hint. See [[astra-audit-18]].
