**Draft — LINK isolation v2 prerequisites and contrasts · 20 September 2026 · Track A only**

Status: audit amendment draft for the new LINK-isolation work, not frozen. Preserve existing staged runs and any frozen isolation files. No training during active Mac waves. The scope is discovering the intermediate person under a supplied two-call decomposition.

**Problem with the existing evidence.** Marg-staged activated the marginal before attribute lookup was competent. It therefore does not test learning LINK against a competent terminal. Record-density and monolithic-loss interference remain separate hypotheses.

**Stage A: establish the prerequisite.** Keep the proposed attribute-only setup: no LINK target, no supporting-line loss, no monolithic questions. Six attribute-answer records per world, 16 worlds/update, three relations, six people. Use the rescaled 79,316-parameter operator. The proposed 3,000-update schedule and curriculum (16 fact rows initially, grow between 750 and 1500, then full stories) may be retained, but freeze all coefficients, RNG states and learning-rate schedule before launch. Seeds 1400, 1401, 1402, with independently named model/data streams.

Only the fixed final stage-A checkpoint can qualify. On a separate, prebuilt full-story validation set, require ≥487/512 attribute answers independently for each relation 8/9/10. Also require ≥487/512 terminal answers given the true endpoint of practised two-hop questions. The latter is an evaluator-only diagnostic, never a training label or input to LINK. Report terminal discriminability: probability of the observed answer under the true person versus wrong present people, stratified by answer-value collisions.

If a seed fails qualification, report “stage A failed; stage-B hypothesis untested for this seed.” Do not run its stage B as a test of a competent frozen terminal, search checkpoints, replace seeds or secretly extend training. An extended stage A is a new registration. Qualification data is development validation; reserve a separate final confirmation set.

**Stage B: shared versus frozen.** For each qualified stage-A checkpoint, restore identical trainable weights, optimizer state and data/RNG state in both arms. Use identical full stories, questions and ordering. Two attribute-only records plus two marginalised two-hop records per visit; no monolithic loss. Coefficients stay 1/3 attribute CE + 1/3 marginal, matching the proposed isolation comparison. Freeze the stage-B schedule and budget at 3,000 updates, warmup 100 to 1e-3, flat through 2,000, decay to 1e-4 at 3,000. No quality-triggered budget changes.

| Arm | LINK probabilities | Terminal probabilities in marginal |
| --- | --- | --- |
| Shared | trainable model | same trainable model, gradients through both calls |
| Frozen | trainable model | separate immutable stage-A copy, no gradients |

The frozen copy must be excluded from the optimizer, remain in eval mode, retain its fingerprint and have no accumulated gradients. Check this at initialization, every checkpoint and final scoring. A detached terminal call on shared weights is not the frozen arm.

A benefit of Frozen supports this entire intervention: stable terminal behavior plus removal of marginal gradients through the terminal. It does not uniquely distinguish the two effects. If needed, register a third diagnostic arm whose terminal probabilities are detached but recomputed from the moving trainable weights; compare it with each primary arm. Do not relabel it as frozen.

**Absent-candidate contrast.** The primary two arms both sum over 16 entity IDs without renormalizing the full-vocabulary LINK softmax. A separate clean mask arm uses the same Frozen setup and sums only over present people, still WITHOUT renormalization. This preserves the loss penalty for wasting LINK probability on absent/non-entity tokens.

The existing `frozen-terminal-6` renormalized arm is a different intervention: conditional normalization removes that penalty. Away from clamps its marginal is invariant to excluded logits, although native decoding still uses full-vocabulary argmax. Do not interpret its result as an isolated absent-person test. If retained, explicitly label it conditional decoding/training research and report unrestricted as well as constrained decoding; constrained decoding supplies an additional type/presence prior and cannot count as the original native pass.

**Measurements and acceptance.** Before any stage-B update and every 100 updates, report LINK full-vocabulary argmax accuracy, entity-only argmax as diagnostic, probability mass on true/wrong-present/absent/non-entity choices, terminal true-person margin, answer-value collision rate, and attribute accuracy by relation. All intermediate labels are evaluator-only.

Freeze six-person and sixteen-person validation probes before training and include their actual semantic signatures in the exclusion union. Six-person probes are the primary fit condition; sixteen-person transfer is reported separately. Final confirmation: ≥487/512 LINK predictions and retained attribute accuracy per relation, plus ≥461/512 complete correct two-call paths and final answers, for every qualified seed. Report the original three-seed denominator and any stage-A failures; a subset of qualified seeds is not “3/3.”

Score TWO inference systems separately for frozen arms:

1. LINK from the trainable model followed by the frozen terminal used in training.
2. Both calls through the trainable model, the intended single-model deployment.

The current isolation diagnostic calls the trainable model twice. That alone cannot establish whether the frozen-terminal system succeeded. A success with two copies uses an additional 79,316 frozen parameters and extra storage; it is an optimization diagnostic, not a parameter-matched architectural win.

**Readings.** Shared fails and Frozen passes: this intervention resolves a failure under the stated prerequisite; further ablation is needed to assign it to terminal drift versus backward interference. Both fail: freezing alone did not suffice; this does not prove intermediate labels are necessary. Marginal likelihood rises without true LINK accuracy: final-answer supervision found an ambiguous or unintended route. A two-copy system succeeds but the single-model deployment fails: distinguish learning LINK from retaining terminal competence.

**Optional cause-separation before stage A.** If attributing the old staged failure matters, independently vary attribute-record count 2 versus 6 and monolithic coefficient 0 versus 1/3, keeping attribute group coefficient 1/3, story schedule, paired data and budget fixed. Do not call the current dense arm a pure record-count intervention: it also changes group coefficients. This optional 2×2 is a new experiment, not a prerequisite to the primary qualified-terminal test.

**Preflight.** Poison intermediate/evidence diagnostic fields and verify identical training losses/gradients. Verify frozen-copy immutability; paired batches and optimizer states; unrestricted LINK argmax; no hidden action supervision; train/probe exclusion; and complete dependency/checkpoint manifests. Reports must say decomposition, token grammar and visible fact parsing remain supplied.

