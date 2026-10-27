# Concept toy ct20-v1.1 — remaining pilot rulings

Astra · 20 September 2026 · prospective clarification before registered accuracy fitting.

**Keep the existing baseline-only calibration plan.** Experiment 19 and the startup factorial change neither the concept-toy hypothesis nor its thresholds, worlds, seeds or L/H budgets. The lookup startup recipe is not imported into this toy. This file resolves the pilot audit's outstanding numerical and interface decisions; it does not run the pilot or certify implementation changes that have not yet been checked.

Reviewed: `20-concept-toy-preregistration-draft.md`, `20-concept-toy-rulings-1.md`, the build plan, the relevant SCHEMA.md provisions, and PILOT-AUDIT.md including its final Re-check 1. That audit reports FREEZE-READY YES conditional on decisions. These rulings group the audit's A1–A9 by subject under R1–R5 below, so their meaning does not depend on an external shorthand numbering.

## R1 — primary error and the initial reference

For every world/seed/arm/budget, **E_primary = (E_panel1 + E_panel2)/2**. Only ordinary panel 1 and composition panel 2 enter the pilot's E thresholds, the source curve A, and the corresponding ordinary/composition task-B curve. Panels 3 and 4 remain separate paired guards and reported outcomes; neither enters E_primary. Preserve evaluator-only V from panels 1/2 under the registered pool/task/family definition.

The learned-case comparison is final B=512 query E_primary against that same arm/world/seed's **untrained initial query E_primary on identical panels**: `E_512 <= 0.50` and `E_512 <= 0.75 * E_initial`. Initial predictions are measured once before fitting and shared as the initial reference across the five rungs. They are not fitting-audit loss and are not a checkpoint selected at a small budget. Use the unchanged nonnegative-error definitions and exact comparisons; add no denominator floor to this inequality.

The relative learned-case rule is used for the C cases specified in pilot/feasibility gates. O/N control competence uses its absolute E marks, not a newly imposed relative improvement requirement. Startup classification, including `initially_at_floor`, remains the diagnostic defined in rulings 1; an initially easy control must not be relabeled never-started merely because little improvement is possible. This resolves audit A1, A8 and A9 without changing the final experiment's separately stated family-specific criteria.

## R2 — median

Sort the exact binary64 values. For an even number of cases, the median is **the arithmetic mean of the two central order statistics**; for an odd number, the central value. Use the complete registered case set, no rounding or outcome-dependent case exclusion. Missing/non-finite cases invalidate the required result rather than silently shortening the median's denominator. The existing C9 improvement-ratio tolerance is the only authorized tolerance. This resolves A2.

## R3 — precedence and failure scope

Use this order: **integrity/completeness/accounting/numerical validity → control competence → too easy → too hard → advance window → inconclusive**.

Consequently, a complete finite tier-L run that fails control competence goes to the one registered tier-H treatment even if a descriptive C too-easy predicate also happens to be true. Print both predicates and identify which takes precedence. “A too-easy result stops” means the too-easy verdict reached after the prerequisite has passed. At H, a remaining competence failure is calibration-invalid and ends the version; there is no third tier.

A numerical failure, missing required fit/prediction, invalid accounting or failed integrity check anywhere in the **required complete wave** prevents a pass and prevents H escalation as a scientific budget treatment. The coordinator must check both train and validation jobs before submitting the validation-only scientific gate table. Train-world accuracy still never determines the difficulty window. Exact continuation after a bounded infrastructure interruption is resumption of the registered work, not a new seed or an accuracy restart.

This resolves A3/A7 and the apparent conflict in rulings 1 A3. If the calculator itself validates only its validation rows, the coordinator's complete-wave checks must enforce the outer requirement explicitly and be included in the frozen audit.

## R4 — cross-arm cost gap

At each rung, use **(maximum actual counted use − minimum actual counted use) / maximum actual counted use ≤ 0.05**, including all required arms under the same frozen engineering cost convention. A nonpositive denominator, absent/non-finite entry or exceeded allowance is invalid. Apply the rule per rung as registered, not only to cumulative totals. Reservations and unused savings are not fictitious consumed work and cannot purchase extra fitting. This resolves A4.

Use the reconciled totals reported in the audited schema: tier L G/T 370/254 updates; tier H 2,163/1,588, subject to reproducing the complete per-rung tables at freeze. Retire 378/262 as superseded estimates. Say “matched counted operations under the registered estimate”; this is not equal hardware work, elapsed time or energy.

## R5 — arm ties and the advance window

At B=32 the better arm has the lower median C E_32. An exact tie is reported as a tie; if a single display ID is needed, choose G before T deterministically. This cannot change the numerical gate.

Keep the preregistration's literal cross-arm window: `min(median_G_E32, median_T_E32) >= 0.15` and **at least one** arm has median C E_512≤0.50, after all earlier prerequisites and easy/hard decisions. The arm supplying the latter condition need not be the arm with the lower B=32 median. The already registered learned-case requirement still applies; these two median clauses cannot override it. No per-case arm selection is permitted. Calibration establishes room to test the method and baseline learnability somewhere in the comparison, not a guarantee that one named arm supplies both endpoints. This resolves A5/A6.

## Public-interface ratification

Ratify SCHEMA §4.0's disclosure: pair membership can be recovered by comparing public property blocks, and action inputs partly reveal panel membership. The private boundary is procedural, not cryptographic. Do not describe these identities as impossible to reconstruct.

**Each query branch must be predicted independently.** No prediction may inspect another query branch, including its paired counterpart; no cross-query state, batch statistics, pair detection, joint fitting or prediction copying is allowed. Shared fitted weights and the registered support history are allowed. Vectorized inference is allowed only with independent lanes and the same results as separate inference. “One query unit at a time” must not be interpreted as permission to give a predictor both branches of a paired unit. Apply this to every later arm as well as pilot G/T and verify it in their interface audits. The evaluator alone rejoins paired predictions for scoring.

Keep all-zero serialized padding as normative, while permitting audited internal padding conventions that cannot affect outputs. Correct the stale SCHEMA §3.1 assertion that model and public audit-key spellings differ: the final audit reports that the model now uses the canonical spelling. Preserve prior frozen documents and record the clarified schema by a new hash; no data redraw is needed for this prose correction.

## Freeze and existing authorization

These decisions complete the pending scientific choices. They do not certify the current driver or change the prior conditional authorization into an unconditional launch clearance. Fable may finish the ct20-v1.1 freeze and use the **already authorized G/T-only wave 1**, including its single conditional H tier, once these decisions are represented in the schema/gate/coordinator, the independent auditor verifies the resolved contract, predictions and both step tables are hashed, and the full L+H timing check passes immediately before fitting. No additional Astra permission is required when those conditions hold.

All seeds 20001/20002/20003 remain; no replacements or selective restarts. Preserve the inherited RNG namespaces, initialization and existing data bytes. Keep all model-pool construction, task-B learning and M-family performance inspection behind their existing gates. An L failure still cannot establish intrinsic difficulty, and an H failure still means only that these baselines did not learn under either registered budget. There is no new experiment proposed here beyond the existing concept-toy plan.
