**Draft — startup factorial v2 · 20 September 2026 · Track A validation only**

Status: proposed replacement registration. Preserve the frozen v1 exactly. Create new source, tests, manifest and output directory; do not amend v1 hashes. No training while current waves are active.

**Question and scope.** At fixed questions and supervision, does adding eight fact rows, adding filler-only/gap rows, or their interaction change learning within 2,500 updates? This does not by itself establish the microscopic gradient mechanism.

Keep the v1 shared-plan construction: select 16 random visible fact rows, build answerable questions and gold canonical LINK/terminal records from that subset, then materialize:

| Arm | Fact rows | Filler-only/gap rows |
| --- | ---: | --- |
| A | 16 | none |
| B | 16 | all |
| C | 24 | none |
| D | 24 | all |

Question tokens, answers, record weights, support facts, model initialization, world draws and optimizer schedule must be identical within each seed across arms. Retain inline filler tokens within fact rows in every arm. D is “full context with subset-selected questions,” not e0. Historical e0/grow-blind runs are context, not matched controls.

Use seeds 1300, 1301, 1302 with fresh model/data streams; use one world and one subset/question stream per seed shared across all arms. Register namespaces `astra-startup-factorial-v2-world:seed` and `astra-startup-factorial-v2-plan:seed`. Same 79,316-parameter rescaled operator, 16 worlds/update, canonical/monolithic loss 0.75/0.25, AdamW and clipping as v1. Warm up to 1e-3 over 100 updates, then hold 1e-3 for all 2,500 updates. No context growth. Report updates, FLOPs and wall time separately.

**Onset definition.** Build a fixed 512-question attribute-only validation probe from a separate namespace, with matched questions/worlds across arms. Exclude its actual visible signatures from training. At updates 0, 50, …, 2500, compute accuracy. “First qualified onset” is the earliest t≥200 for which all five scheduled probes t−200, t−150, t−100, t−50 and t are present and each reaches at least 461/512. Missing probes do not qualify. Record first onset, subsequent regressions and final-window status separately.

At final update, also evaluate a second untouched 512-question probe; require ≥461/512 to call onset independently confirmed in that condition. Report ordinary attribute questions, endpoint-derived terminal questions and LINK questions separately in training diagnostics. This is an operational threshold, not literal first learning or a reliability certificate.

**Routing diagnostics.** Retain the small, fixed v1-style probe for affordable gradients every 50 updates. Its question plan is shared across arms and separately excluded from training. At initialization and each probe time:

1. Record raw correct-line mass and mass divided by the uniform-over-eligible-token baseline, separately by each of three reads and four heads, and by question-token position where feasible.
2. Report raw double-precision reductions of gradient inner products, norms and cosines, without rounding to eight decimal places. Differentiate attribute, LINK and monolithic loss components separately, then their registered weighted sum.
3. Measure the analytic derivative for plain SGD. Validate it by central finite differences on disposable parameter copies at eta=1e-3, 1e-4 and 1e-5. Report disagreement/cancellation rather than forcing a sign verdict.
4. Separately measure attention change from one hypothetical AdamW update on a disposable copy of the model AND optimizer state using an independent training-distribution probe batch. The live training state must remain byte-identical. Report this as optimizer-specific, not the same statistic as the SGD derivative.
5. Report prediction distributions separately for attribute and LINK outputs, plus per-relation answer accuracy.

A positive derivative in all arms does not refute dilution: scale and variability still matter. Failure of average final-token attention to rise does not prove that no head or other token position learned retrieval. Temporal association is diagnostic evidence, not a causal proof.

**Primary comparisons.** At the fixed budget report all per-seed trajectories and paired filler effects B−A and D−C, fact effects C−A and D−B, and their interaction. Binary start outcomes are secondary to the full trajectories. Keep statements conditional on the tested sizes and budget. Do not infer “only time matters” from one D success or “impossible barrier” from an 18k failure.

**Freeze-before-growth evaluation.** Evaluate the final A checkpoint without updates. For each validation world select questions supported by a common 16-fact core, then add nested facts and nested filler rows while keeping each question and answer fixed. Six-person cells: 16/24 facts × filler fractions 0/0.5/1. Sixteen-person cells: 16/24/64 facts × the same filler fractions; include the genuine full 64-fact world. Use 512 paired units per cell, frozen before training and excluded by actual presented-input signatures. Verify checkpoint fingerprints before/after. Success ≥461/512 per cell describes transfer over these sizes, not arbitrary size independence.

**Long-run question, separate from the factorial.** For D, preregister an 18,000-update trajectory from initialization: warmup 100, flat to 16,000, decay to 1e-4 at 18,000. Save complete model, optimizer, all RNGs, configuration and source hashes. Compare its own frozen 6,000-update checkpoint with its 18,000 checkpoint. Call this an extension under a declared schedule, not a continuation of historical e0. Do not select seeds based on old validation success or alter the schedule after seeing the trace.

**Overlap and launch preflight.** Use the validation protocol in [the companion draft](/Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/18-validation-and-operator-swap-v2-preregistration-draft.md). For each training record audit the actual reduced visible memory and the full-source memory; do not assume one hash covers the other. Freeze all new probes/exclusions before training.

Implement a machine-wide capacity guard and queue, with at most three audit-experiment workers and at most six total registered training workers; no new audit-experiment training while Fable's current waves are active. The default command must not spawn all 12 jobs. Count worker processes rather than shell wrappers. Each resumable chunk ≤1,200 seconds; a capacity refusal is a scheduling result, not a model failure. Test the launch plan without starting workers.

