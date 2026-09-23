---
name: cardfold-sleep-result
description: 2026-09-22 CardFold sleep toy registered result — 2 FAIL + 1 VOID; lesson-practice beats raw-log replay 0.94-0.99 vs 0.03-0.09, but 1-11% on longer inputs
metadata:
  type: project
---

CardFold sleep experiment (scripts/fable_cardfold_sleep.py, artifacts/fable-cardfold-sleep-20260922/RESULTS.md), seeds 4101-4103: VOID (base 0.945), FAIL, FAIL — all on or besides M3 (inputs longer than practised: 1-11%). M1/M2/M4 held 3/3: fresh practice from a software-induced lesson puts the rule in the weights (94-99%), raw-log replay at equal compute only memorises (3-9% on new inputs), and without old-skill replay old skills drop to ~0%.

**Why it matters:** supports Ben's "sleep stores lessons, not answers" idea on a toy only; the lesson was found by program search, not the model. Length generalisation is the recurring wall (see [[canonical-operator-roadmap]], [[exp19-replay-result]]).

**How to apply:** never say "sleep works"; next sleep work needs a length-generalisation fix first. Predictions P138-P144 (I wrongly expected no VOID). Related: [[ben-vision-20260921]].
