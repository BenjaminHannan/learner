<!--
PROVENANCE NOTE (Fable, 20 September 2026). Two separate Astra chats each wrote
design/v3/20-concept-toy-rulings-2.md. The first version (11,678 bytes, written 18:15 EDT, on-disk
sha256 8a62ef050e2120209761e858109aa9195b87c88790fb7827dd5b547a56defc8d as hashed by Fable at the time)
was overwritten at 18:17 EDT by the second chat's version (8,687 bytes, sha256
1245e46f567dd1a265d6b05d8482f0267052c735159b8d05864dd6b861a110f2), which is what is on disk now.
The text below is the first version as Ben relayed it in chat. It is NOT byte-identical to the
overwritten file (link markup was lost in relay), so its own hash differs from 8a62ef05….
Fable read both and found no conflict: same E definition, median, precedence, gap rule, tie rule,
advance window, isolation rule, padding, step totals and authorization. This version is more explicit on
(i) the three cost constants, (ii) per-rung query scoring, (iii) the per-rung step table, (iv) the launch
preflight, (v) the secret-salt recommendation. The on-disk version is more explicit on the
complete-wave (train + validation) integrity requirement. The freeze binds both; where one is silent the
other governs. Neither was edited by Fable.
-->

# 20 — Concept toy: Astra rulings 2

Astra · 20 September 2026 · prospective addendum to `ct20-v1.1`; no calibration accuracy results considered.

**R1–R5 below resolve the outstanding freeze decisions.** This addendum takes precedence on these points over the preregistration (20-concept-toy-preregistration-draft.md), simulator/model spec (20-concept-toy-simulator-spec.md), build plan (20-concept-toy-build-plan.md), and rulings 1 (20-concept-toy-rulings-1.md), whose SHA-256 remains `40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de`. Keep experiment version `ct20-v1.1` and bind this additional document's hash in the freeze manifest; these prospective decisions do not redraw data, initialization or RNG streams. Preserve Fable's already-hashed predictions (`420f9363…`, as supplied).

I read the pilot audit (../../artifacts/fable-concept-toy20-20260920/audit/PILOT-AUDIT.md), including its appended re-check, and the relevant schema/calculator. The latest audit verdict is **freeze-ready conditional on these rulings**; its earlier missing-preflight finding has been superseded. Test counts and timing below are auditor/builder evidence, not checks I reran. I ran no experiments, fits or tests and changed only this new document.

**R1 — Gate E: panels 1 and 2 only, equally weighted.**

For every world × seed × arm × checkpoint, use `E = E_primary = (E_panel1_ordinary + E_panel2_composition)/2`. Preserve the spec's within-panel weights: panel 1 is the equal average of its three horizon-specific means (h=1,2,4), and panel 2 averages its 16 units equally. Do not replace panel 1 with a flat mean of its 6/5/5 targets. Divide squared noise-free-response errors by the fixed evaluator-only V from ruling B6: panels 1/2, equal panel weighting, population variance and floor 0.05.

This definition covers every query-E threshold in prereg §5, including controls and `E_initial`, and the primary source/reuse metrics in later waves, using each task's own panels and V. Panels 3 and 4 remain separately scored guards; **no panel-4 branch enters primary E**, even when its recipe is ordinary or composition. All 96 targets are still predicted, scored and charged. This matches the spec's explicit separation of primary error and pair guards.

**R2 — Median: mean of the two central order statistics.**

Sort the 12 finite C world×seed values separately for each arm and budget; with one-based order statistics, `median = (x_(6) + x_(7))/2`. Do not average within worlds or seeds first, pool arms, or drop missing/failed cases. Use binary64 arithmetic on unrounded evaluator values and the exact registered inequalities, with no tolerance or `isclose`. Ruling C9's `1e-12` tolerance remains confined to its startup loss-improvement predicate.

**R3 — Control prerequisite first; only an eligible too-easy verdict stops.**

The order is **integrity/completeness → control competence → too easy → too hard → advance window → inconclusive**. Numerical failure, missing required results, invalid accounting or failed integrity stops without H. Otherwise, a complete finite tier-L run that fails control competence triggers the single complete H tier, **even if the raw C numbers also satisfy the too-easy predicate**. Until controls pass, those numbers do not constitute a too-easy verdict: the calibration prerequisite has failed.

When controls pass, too easy stops without escalation; advance adopts that tier; too hard or inconclusive at L triggers H once. Apply the same precedence at H: a control failure remains `calibration-invalid/startup-or-implementation`, even alongside low C errors, and never buys another tier. H remains a fresh complete trajectory from the same initialization bytes under ruling A3. This qualifies A3's phrase “a too-easy result stops” and ratifies the calculator's prerequisite-first implementation.

**R4 — Ratify option (a), with branch-level isolation enforced by the harness.**

Ratify SCHEMA.md §4.0 (../../artifacts/fable-concept-toy20-20260920/SCHEMA.md): panel-3 pair membership is recoverable from identical 24-float property blocks, and panel-4 membership from multisets of channels 0–1. Remove “pending Astra ratification” when incorporating this ruling. Keep the existing panel recipes and bytes.

**No prediction may depend on any other query sequence, including the other branch of its own pair.** A pair is one statistical unit, but its two branches are two isolated inference sequences. Given the frozen fitted checkpoint, each prediction may use only that sequence's permitted prefix, actions, properties and detector query. Reset all episode-local hidden state, pool coordinates and history for each sequence; no query-driven parameter updates, cross-query attention/statistics, pair matching, output copying or shared mutable query cache. Pooling across objects or coordinates *within* an episode remains permitted by the registered model equations.

This applies to every arm, candidate and source/task-B evaluation in all waves. Vectorized batching is allowed only with isolated lanes. The harness must enforce the boundary; the auditor must verify on fixtures that changing companions, ordering or batch partition leaves a fixed query's prediction unchanged under the frozen numerical convention. Only the evaluator joins the branches after predictions are sealed. Thus the pair guard can test invariance without granting pair-detection access.

**R5 — Ratify all three ledger choices and the reconciled step tables.**

Accept `OPS_INIT_PER_PARAMETER=2`, `OPS_LOSS_PER_TARGET=4`, and `OPS_LOSS_PER_BATCH=2` as additional fixed engineering-estimate constants under A1. Query-panel scoring passes execute and are charged at **every** rung; among post-fit rungs, only B=32 and B=512 feed the wave-1 accuracy predicates, alongside the initial checkpoint. Intermediate results remain required for the full curves and integrity checks.

Register the cross-arm gap as `(max(actual_counted_ops) − min(actual_counted_ops))/max(actual_counted_ops) <= 0.05`, inclusive and without tolerance. Apply it at each rung within the same world, seed and tier across compared arms, not only to pooled totals. Require valid positive costs and no arm over its allowance. This normalization is the declared convention; dividing by max gives a smaller gap than dividing by min or mean, so it must not be described as the more conservative denominator.

Freeze these **additional updates per rung**, not cumulative counts:

| Tier / arm | B=32 | 64 | 128 | 256 | 512 | Total per fit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| L / G | 62 | 81 | 81 | 80 | 66 | 370 |
| L / T | 39 | 58 | 57 | 57 | 43 | 254 |
| H / G | 421 | 440 | 439 | 438 | 425 | 2,163 |
| H / T | 306 | 325 | 324 | 323 | 310 | 1,588 |

Retire the provisional 378/262 totals. Keep A1's distinction between reservations and actual execution: charge real shapes, report unused reservations, and never spend savings on extra fitting or dummy work. The audited worst planned gap, 1.41%, passes; executed ledgers must still pass. Describe comparisons as **“equal counted operations under the registered estimate”**, with the permitted 5% spread disclosed, never “equal compute.” The G/T update ratio's 1.25–1.46 sensitivity to alternative conventions prevents a hardware-compute interpretation.

The reported worst-case complete L+H projection (217 s raw, 326 s with the 1.5× margin, within 900 s usable) satisfies the freeze preflight; the auditor independently reproduced a passing projection. Repeat the bounded synthetic preflight immediately before fitting on the actual machine state, charge its elapsed time, retain the 300 s reserve and 1,200/1,500 s limits, and stop `resource-infeasible` if the remaining complete schedule no longer fits.

**Register-only decisions (audit §7 labels; A4 is resolved by R5).**

- **A5:** An exact G/T median tie names G as “better” for deterministic reporting; the common median determines the predicate.
- **A6:** Yes, arm identity may differ across budgets: require `min(median_G32, median_T32) >= 0.15` and `min(median_G512, median_T512) <= 0.50`, after earlier rules; the first condition necessarily puts both arms at or above 0.15.
- **A7:** “No numerical failures” covers every arm, family, seed, checkpoint and required measurement anywhere in the validation gate split; additionally A3's full-schedule integrity requirement means a numerical failure in a required train-world fit also stops without H, although train accuracy never enters the calibration statistics.
- **A8:** The 25% query-improvement test applies to learned C cases in waves 1/2, not O/N competence; controls retain their absolute E and restraint requirements, while §8/C9 startup diagnostics remain unchanged for all families, including the separate `L_initial <= 1e-8` exception (no invented query-E epsilon or floor waiver).
- **A9:** “25% lower” means `E_512 <= 0.75 * E_initial`, alongside `E_512 <= 0.50`; `E_initial` is the single untrained pre-rung-1 checkpoint's R1 query E for that arm/world/seed, with fixed panels/V, never a rung-specific restart or fitting loss.

**Freeze closure and claim limits.**

Ratify SCHEMA §2.3.1's all-zero serialized padding; an internal alternative is permitted only at row indices `>= n_records`, excluded from prediction, with cross-producer real-row equality checked separately. The stale audit-key mismatch prose identified by the audit's re-check R1.4 remains a non-blocking documentation correction. Incorporate this addendum and resolved disclosure into the manifest, freeze schema/adapter hashes together, and have Agent 3 record that the final bytes and gate wiring implement these decisions. Hash any documentation corrections too. Existing fixture evidence may be cited where bytes and behavior are unchanged. These are concrete freeze conditions, not a request for another Astra approval.

Record explicitly that public/private separation is procedural, not cryptographic; the public design can regenerate private quantities, including final worlds. An evaluator-held secret salt, committed before final generation and kept from builders, is recommended as a separately versioned final-split amendment before wave 3, not a silent seed change here. Disclose any actual final-data exposure; already inspected worlds cannot subsequently be called untouched.

Tier-L failure alone does not establish difficulty. Even a complete, valid H too-hard verdict supports only **“not learned by these baselines under either registered budget”**; unresolved control failure remains calibration-invalid. No convergence or intrinsic-hardness claim follows.

**Fable may freeze and run baseline-only wave 1 once these decisions are incorporated, Agent 3 closes the conditional freeze verdict, and the immediate launch preflight passes.** Prior authorization includes exactly the conditional H tier; no further Astra confirmation is needed. This document launches no run and grants no early pool-model, task-B or M-family learning work.

**Five lines for Ben**

The gate uses only the ordinary and composition panels, with exact thresholds and the usual middle-two median.
A complete, finite small-tier run with failed controls gets the one larger-budget check, even when its hidden-world scores look easy.
Every query branch stays isolated so a model cannot pass the pair guard by copying its partner.
The full cost ledger and both step tables are accepted as a declared operation-count estimate.
Fable may run wave 1 after the rulings are incorporated, the auditor closes the freeze, and the launch timing check passes.
