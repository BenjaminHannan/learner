---
name: astra-audit-18
description: 2026-09-20 Astra audit 18 rulings — baseline failure inconclusive (init mismatch), v2 drafts for factorial/link-isolation/baseline/confirmation panels+operator swap, wording rules
metadata:
  type: project
---

Astra's audit `design/v3/18-audit-before-fable-continues.md` (2026-09-20) plus four v2 drafts in `design/v3/18-*-draft.md`. Rulings I am following:
- Baseline at chance ≠ win for decomposition: no execution bug found, but its Linear init (std 0.02) is ~4× smaller than the operator's rescaled init; token accuracy hid a lookup failure. Build baseline v2 = init × hint 2×2; require ordinary lookup to succeed before arguing about composition.
- Start-up factorial v1 (already running when the audit arrived) is development evidence only: "D" is NOT historical e0, "start" rule is weak, size sweep unpaired. v2 per draft.
- marg-staged = failed preparation stage, not a test of LINK learning. Link-isolation v1 withdrawn before any run; v2 needs a stage-A qualification gate (≥487/512 per relation), seeds 1400–1402, no renormalised 6-person arm, score both inference systems.
- Reused ten cells / 25 cells are development panels. Fresh confirmation panels are mandatory before any generalisation, baseline-superiority or end-to-end claim.
- End-to-end gap: swap grow-blind operators into frozen v3 dispatchers (pairing seed i↔i, mark 58/64), additive scorer must recompute stale operator diagnostics.
- Wording: do NOT say "label-free operator" — grow-blind removes the supporting-line loss and label-informed line selection but still trains gold intermediate people. 48/48 would only give a ~94% one-sided lower bound.

**Why:** Astra is design owner ([[gpu-budget-cap]]); Ben relays audits. **How to apply:** build to Astra's drafts via Opus agents, keep v1 artifacts, state claims with these scopes. See [[canonical-operator-roadmap]].
