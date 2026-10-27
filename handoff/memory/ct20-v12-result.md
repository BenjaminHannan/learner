---
name: ct20-v12-result
description: "2026-09-21 concept toy ct20-v1.2 pilot: valid run, registered verdict too-hard — plain baselines learn controls at 5x budget but only 2–3/12 concept cases"
metadata:
  type: project
---

Concept-toy wave-1 calibration pilot (ct20-v1.2, the accounting-fixed rerun Ben said "go" to) ran once on 2026-09-21 UTC: accounting valid both tiers, 72+72 fits fresh. Tier L: controls fail (G 0/6, T 3/6) → tier H required. Tier H: controls pass (5/6, 6/6) but concept cases learned G 2/12, T 3/12 (need 9), median E_512 0.70/0.59 (need ≤0.50) → final verdict **too-hard**, binding. Write-up: artifacts/fable-concept-toy20-20260920/RESULTS-v1.2.md; outputs sealed in wave1/VERDICT-SEAL-v1.2.sha256.txt.

**Why:** the pilot only calibrates baselines G/T as yardsticks; "too-hard" = these baselines at these budgets, not the toy being intrinsically too hard and nothing about System S.
**How to apply:** pre-commitment says no v1.3 from us — any change of budget/baseline/difficulty goes to Astra ([[outside-review-option]], [[handoff-copy-box-format]]). Never pool or report v1.1 numbers. Concept toy is off the teachable-assistant demo path ([[teachable-roadmap-fable-review]]).
