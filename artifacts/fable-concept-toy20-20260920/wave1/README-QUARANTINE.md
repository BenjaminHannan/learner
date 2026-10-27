# QUARANTINE — do not open `v1.1-INVALID-accounting-QUARANTINED/`

Fable (coordinator) · 20 September 2026 · required by rulings 3 (condition 2).

`v1.1-INVALID-accounting-QUARANTINED/` holds the complete output of the single ct20-v1.1 execution of
wave 1. That run ended `calibration-invalid/accounting`; tier H was never run; the verdict is permanent.
(The ruling suggested the name `registered-v1.1-INVALID-accounting`; the directory was renamed to the
present, stronger marker before the ruling arrived. The driver's refusal test keys on this name.)

Rules (they bind the coordinator, builders, auditors, reviewers and Ben):

1. **Preserve; never delete, edit or re-score.** All 444 files are read-only. Their sha256 list is
   `v1.1-quarantine-sha256.txt` (sha256 of the list: 1ab9656d9ccc27e2769e4854466621abd5a1f2d36b34c1a922e08247f87af9ec).
2. **Until the ct20-v1.2 two-tier final verdict is written and hashed, nobody opens any file in it** —
   `verdict.json`, `report.txt`, `state.json`, gate tables, evaluator outputs, predictions, checkpoints,
   ledgers. `verdict.json` and `report.txt` carry the full scientific result even though accounting was
   invalid, so "read only the accounting fields" is NOT allowed. Listing names and hashing bytes is allowed.
3. **After the v1.2 verdict is sealed** it may be opened for exactly one purpose: the reproducibility
   comparison against v1.2's tier L (tensor equality of parameters and optimizer moments at all five rungs;
   equality of `query_predictions_by_rung` and both audit prediction sets; all 72 fits), reported as one line.
4. **Ever after:** v1.1's numbers are never reported as results, never pooled with v1.2, never used to fill a
   v1.2 cell, never preferred over v1.2. Wording: "wave 1 was executed twice; the first execution was invalid
   for accounting and is reported as such" — never "resumed" or "re-scored".

Diagnosis: `ACCOUNTING-DIAGNOSIS.md`. Ruling: `design/v3/20-concept-toy-rulings-3-fable-review.md`.
