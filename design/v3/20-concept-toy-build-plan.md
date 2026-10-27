# 20 — Concept toy: three-agent build plan and independent audit

Astra · 20 September 2026 · design handoff, not an implementation or experiment report.

**Fable should build the baseline calibration first, using three independent Opus roles. The new state mechanism waits until that pilot passes.** The work is a separate `concept-toy20` track, not an extension or renaming of the existing lookup, replay or inhibition experiments.

Authoritative contracts: [simulator/model spec](20-concept-toy-simulator-spec.md) and [staged preregistration](20-concept-toy-preregistration-draft.md). Resolve contradictions before the affected freeze; do not let separate agents silently pick different conventions. Astra has created only these three `design/v3/20-concept-toy-*.md` files. No code, old design, checkpoint or registration was edited, and no model was run.

## 1. Three Opus assignments

### Agent 1 — Simulator and panels

**Owns:** simulator, deterministic generators, public tensor serialization, whole-world splits, source/B support and query recipes, truth-side evaluator records. Does not implement a learner or tune world difficulty.

First deliver the v1 C/O/N simulator, anonymous public interface, nested 32..512 support sets and calibration panels. Implement M's equations behind the evaluator boundary and verify algebraic identities, but do not publish mode-family example traces, calibration scores or learning curves. No final-world generation is needed for the pilot.

Suggested implementation units, all in a fresh `concept-toy20` namespace, without modifying prior experiment entry points:

- `world`: immutable world record; eight-transition episodes; C/M/O/N update laws; float64 simulator arithmetic, cast public records to little-endian float32 at serialization.
- `streams`: SHA-256-to-PCG64 seed derivation, independent properties/actions/masks/noise, canonical world/episode hashes and collision audit.
- `traces`: support prefixes with 3:1 fitting/selection partition; QUERY-before-OBSERVED tokenization; reserved four-verb composition; fixed action scheduler.
- `panels`: ordinary, composition, relevant-pair and nuisance/renaming-pair recipes; source and B versions; deterministic normalization metadata.
- `public_loader`: only public tensors and observed fitting targets; no private world object or evaluator imports inside model datasets.

World metadata is canonical JSON with sorted keys, compact separators, finite Python float64 values serialized using the frozen Python version's round-trip representation, and no timestamps. Record a full SHA-256 and a second hash with action permutation removed. Public tensor hashes cover dtype, shape and raw contiguous little-endian bytes. Use the frozen files as cross-device data, not regeneration on each device.

**Public batch contract:** reset/property tensor, action tokens, masked observed A targets, fitting/selection episode roles, detector query IDs, and padding mask. Source query batches carry only prefix observations, future actions and queries. B fitting batches additionally carry B training labels in a target-only field. Public files contain no hidden state, coefficient, family, simulator seed, final query response or normalization constant. The coordinator can know world IDs for bookkeeping; those IDs never become network inputs.

**Private evaluator contract:** truth responses, noise, family, world identity, paired edit mappings and panel identity; joined to predictions by opaque record ID only after fitting/checkpoint selection. All scoring must be possible without granting the trainer an in-process simulator object.

**Required tests:** exact pulse/contact/invert algebra; simultaneous contact update; directional XOR; no hidden storage in O/N; reset scope; malformed action rejection; missing value really zero; target not present in QUERY; episode/outer-world disjointness; unchanged r under nuisance edits; specified nonzero intervention differences in C/M; zero differences in O/N; action-pattern exclusion; budget counts including validation; task-B labels absent from encoder inputs. These are meaningful semantic tests, not tests that merely copy implementation lines.

**Handoff:** generated calibration files/hashes, schema, complete generator config, collision report, and a readable small synthetic interface fixture. Fixtures can verify format but must not expose final worlds or a mode-family accuracy example. No plots of learner performance produced by this agent.

### Agent 2 — Models, training and persistence

**Owns:** model code, optimizer, common objective/forecast API, batched independent-world fitting, checkpoints and compute hooks. Does not own final labels, pass/fail scoring or generator difficulty.

Phase A implements **only G and T** and the shared loss/initialization/runner. Verify causality, reset behavior, actual parameter counts, shape/gradient validity, per-lane independence and exact-state resumption on synthetic data. The baseline calibration must finish before constructing the pool or other new model arms. Model size estimates in the spec are contract checks, not permission to change hidden widths to chase accuracy.

After the calibration gate, implement P, T-pool, T-fit, R, Q and P-fixed from the registered equations. P/T-pool must use one shared pool implementation, selector and persistence class; the backbone is the only switch. Candidate k copies start identically on shared coordinates but have independent gradients/optimizers. All four candidates receive their predetermined shares even if selection repeatedly rejects them. No candidate may inherit a trained model, get an extra fit, or gain access to a discarded candidate's predictions.

For transformer training, prefix attention includes only preceding RESET/QUERY/OBSERVED records. The current target OBSERVED record must be outside the computation graph producing its QUERY prediction. A useful leak test changes future observed values and asserts the earlier forecast is unchanged. Multi-step rollout must substitute blank observations rather than teacher-forcing intermediate sensor values.

Implement the callable state API in the spec, then the new B decoder and reset ablations. Freeze the entire retained encoder, pool and A decoder. Assert via parameter hashes that B fitting changes only permitted parameters. The auxiliary A head uses its own `(last_action.source, NONE)` detector query, **not** the B pair query. B pair IDs are provided only as public query inputs, and B labels never enter the state updater. At k=0, retained/reset P predictions must agree under identical decoder initialization and optimization; the ablation cannot introduce unrelated RNG differences.

For vectorization, keep parameters, Adam moments, gradients and random choices separate for each world/seed/candidate. Shared batching is an execution optimization only. Verify one vectorized lane against the same unbatched synthetic run to tolerance 1e-6 on CPU; disclose any GPU tolerance before registered training. Never average a minibatch across world-specific parameter sets. No hidden meta-training may occur through shared optimizer tensors or normalization statistics.

**Handoff:** source/config hashes, actual trainable/stored parameter counts, initialization tensor hashes, per-rung deterministic step counts, common loss implementation, model/persistence API, resumable checkpoint schema, full work events and dry-run timing. No self-awarded pass verdict and no requests to retune based on final scores.

### Agent 3 — Independent auditor and scorekeeper

**Owns:** independent generator checks, data-boundary/leakage review, accounting table, frozen gate calculator, private final scoring, failure report. Must not co-author model modifications or repair failures until the version's verdict is preserved. Findings go to Fable with concrete reproduction steps; the relevant author fixes code before a freeze or versions the experiment after it.

Independently derive key analytic examples rather than importing the simulator's answer routine as the test oracle. Check C conservation for contact only; M truth tables; O/N state absence; B difference responses; reserved composition grammar; masks independent of targets; hidden responses inaccessible to trainers. Validate numeric conventions and hashes before any performance run.

Verify the operation-cost ledger includes all four candidate fits, all rejected states, fitting/selection/query forwards, backward/optimizer, initialization and initial-checkpoint scoring, final fitting diagnostics, source perturbation diagnostics, transformer history recomputation and task-B feature caches. Charge source discovery in full to both retained and reset arms when comparing total acquisition cost; do not amortize it away because the source checkpoint was physically shared. Record actual shared execution savings separately. Data generation is common infrastructure and is reported in wall time; model-specific computation is in each arm's discovery ledger.

Recompute the parameter counts from instantiated models without training. Check effective capacity as well as stored counts: zero-masked decoder columns are not active parameters, four candidate copies are real search/storage overhead, and a transformer's retained public history is real memory. The 5% rule applies to counted total computation, not nominal updates. Flag a comparison if a baseline's cost budget buys fewer updates because of an implementation bug or unnecessary asymmetric work.

Write a pure gate calculator against a result-table schema **before results exist**. Test the calculator on hand-constructed boundary cases: exactly 20% improvement; interval touching zero; 21 versus 22 control selections; 5 versus 6 worlds; failed seed; missing arm; C pass/M fail; P/T-pool tie; >32 crossing; zero denominators; infrastructure timeout. A paired interval must resample the same worlds/seeds for both arms.

After all final fitting and checkpoint selection are sealed, score once and release the complete tables. Every seed and candidate startup status is included. A missing result is a visible missing cell, never a dropped row. The auditor reports the gate result even when it contradicts Fable's or Astra's prediction.

**Handoff:** signed/hash-frozen audit checklist, explicit unresolved findings, cost table, gate-calculator source, final world/seed tables, uncertainty tables and a one-paragraph verdict separating capability, method and architecture claims.

## 2. Integration sequence for Fable

1. Create a new isolated implementation/output namespace. Preserve existing design/experiments and sealed lookup tests. Avoid bare “20” output paths because an unrelated inhibition draft already uses that number. Do not import old operator checkpoints or historical final panels.
2. Give Agents 1–3 the same two contracts. Agents 1 and 2 can build simulator/baselines in parallel; Agent 3 reviews independently. Mathematical ambiguity is resolved in a new additive ruling before the affected freeze, with any changed hypothesis clearly versioned.
3. Freeze baseline code/config/data/costs, write predictions, and run the bounded timing fixture. Execute wave 1 only if the projected complete wave fits. Publish its calibration verdict and every seed before building new models.
4. If the gate passes, Agent 2 builds the registered pool/comparison models; Agent 1 prepares validation files and B API fixtures; Agent 3 audits the implementation/costs. Freeze them, then execute wave 2. No B accuracy training and no M accuracy inspection at this point.
5. If feasibility passes, lock all recipes and final evaluators. Agent 1 creates final public supports and private targets, Agent 2 runs the predetermined final source+B jobs, Agent 3 scores after checkpoints are sealed. Fable enforces the 1,200/1,500-second wave limits; it is acceptable to report resource-infeasible rather than start a run known not to fit.
6. Publish a complete report regardless of outcome: pilot decision, feasibility decision, per-seed startup classifications, per-family source/B curves, zero-gate rates, paired guards, P-versus-T-pool interpretation, complete candidate costs, parameter/history storage and elapsed time. Add all failures to the report before proposing another version.

No cloud spending is authorized by this plan. No extra run is justified simply because one seed looks unlucky. An implementation bug found after fitting requires the failed version to remain visible and an explicit revised freeze; it cannot be hidden as a clean repeat.

## 3. Reviewable launch and output artifacts

Before each applicable wave, require:

- One manifest with version, authors, source/config hashes, world/panel hashes, RNG mapping, device/software/thread settings, architecture/counts, optimizer/init, and resolved per-rung step counts.
- Predictions recorded before first fitting; an empty predictions section is not a completed freeze.
- Separate public-support and private-evaluator file lists, with explicit read boundaries.
- A 1.5× timing projection including candidate selection, query panels, diagnostic forwards and writes; a hard-deadline handler tested on a fixture.
- A complete schedule of required world×seed×arm cells, with status transitions `pending/running/complete/numerical_failure/infrastructure_incomplete`. No silent deletion.

Per checkpoint, write world/seed/arm/rung, data-prefix hash, model/init/checkpoint hashes, candidate k and selection losses/costs, actual trainable parameters, persistent bytes, working/history bytes, updates/examples/observed targets, counted forward/backward/optimizer/evaluation work, wall time and failure status. Record candidate acceptance/rejection even at intermediate rungs.

Per score, write raw noisy MSE, raw noise-free MSE, V, E by panel/horizon, source A or reuse A_B, threshold crossing, control gate decision and startup label. Pair tables retain both predictions and their difference. The verdict script reads this complete schema; it does not infer success from a plotted mean.

## 4. Ways this could fool us

| Failure mode | Why it would mislead | Registered defense / remaining limit |
| --- | --- | --- |
| A GRU already remembers one scalar cheaply | A complicated mechanism solves a problem ordinary memory already solved. | Baseline-only 32..512 pilot; stop at floor. G/T retain full history and online fitting. |
| An unfairly weak transformer | Bad init, missing history or too little adaptation manufactures a win. | Explicit residual init, same data/storage/fitting, T-fit and T-pool; observable control prerequisite. A single tiny transformer is still not all transformers. |
| Charge-specific hand tuning | Object-wise scalar slots are almost the answer for C. | M uses discrete directed/XOR dynamics and is withheld from tuning; no hidden labels. The hypothesis class and object slots remain human supplied. |
| New name for ordinary system identification | “Concept” language makes an established representation-learning method sound unprecedented. | R and Q controls; scope the result to this specified method, not novelty over published work. |
| Giving only P a lasting memory | Reuse merely reflects unequal storage rights. | Every baseline saves its complete encoder and public-history access. All episode states reset. |
| Persisting yesterday's value | Copying q or a hidden buffer can mimic a reusable concept. | Persist functions/weights; fresh episodes/objects; assert empty local state before B. |
| Calling any nonzero slot a discovery | Noise fitting or a dead feature looks like concept invention. | Observable/noise controls, conservative selection, held-out predictions, state-use diagnostic and reuse. |
| Selecting by the final answer | Discovery validation or final query labels leak into adaptation. | Separate support/selection/query boundaries and independent scorer; no checkpoint search. |
| Target in the current input | Sensor value in a causal decoder token makes prediction trivial. | QUERY precedes OBSERVED; change-future-label invariance test. |
| Teacher-forced future sensors | Four-step success is really four one-step predictions with hidden answers supplied. | Blank OBSERVED records during every forecast, for all models. |
| Action/metadata shortcuts | Verb arity, dose, IDs or record order reveal answers. | Arity/dose are intentionally public hints shared by all; names/family/seeds are forbidden inputs; random verb mapping and object IDs, unseen compositions and changed nuisances. Do not claim a fully unstructured discovery setting. |
| Sensor noise used as a difficulty knob | Irreducible error creates a fake “hard” task. | Separate raw noisy error and noise-free evaluator error; deterministic hidden dynamics; never tune using hidden labels. |
| Convenient control pooling | Easy noise-only cases hide failures on observable controls. | Separate O/N counts and error marks as well as combined gate count. |
| Rejected candidates are free | Four chances to train are compared with one baseline's compute. | Complete candidate ledger; shared per-arm cap; no extra successful-seed/candidate runs. |
| Candidate selection actually chooses a lucky backbone | Independent k copies introduce search over training outcomes. | Same shared-component starting bytes and fixed minibatch stream; all search cost charged; P-fixed and T-pool. Residual selection benefit may still include regularization/optimization, not uniquely new semantics. |
| More capacity explains the result | An extra hidden vector, not selected reusable functions, earns the gain. | T-fit, matched-size R/Q and P-fixed; report actual effective parameter/storage differences. |
| Reuse wins only against a deliberately crippled reset | Frozen methods get source training while the comparison gets nothing. | Ordinary baselines also retain everything; reset removes only proposed functions, retains context, and can relearn with equal B compute and A observations. No claim rests on reset alone. |
| A trivial second task | The B head is almost a linear remix of the source response. | This is openly a first representation-reuse test, not discovery of a second mechanism. Require competitive low-data benefit; later tasks must be harder. |
| Good prediction means true-variable recovery | Equivalent or entangled coordinates can predict without matching q or m. | No coordinate-correlation pass mark; claim useful state, not unique causal identification. |
| Ablation damage is overstated | Almost any feature permutation harms a small model. | Report ordinary-context perturbations; use state-use diagnostic as necessary evidence, never sufficient proof. |
| Seed lottery or machine swap | Success-only results disguise unreliable startup. | Three fixed seeds, common CPU init bytes, full failure table, one backend, explicit never-started versus learned-failed labels. |
| Correlated samples inflate certainty | Thousands of transitions are treated as independent discoveries. | Worlds and seeds are resampling blocks; paired units and repeated budgets stay together. Three seeds still limit certainty. |
| Batched training shares gradients across worlds | Hidden meta-training makes final adaptation look cheap. | Independent parameter/optimizer lanes; compare batched/unbatched fixtures and inspect normalization state. |
| Timing assumptions erase required comparisons | A too-large matrix finishes only favored arms before deadline. | Full-wave projection with margin before launch, fixed complete schedule, incomplete means no pass. Runtime is unmeasured in this design. |
| Final M results guide repairs | The nominally held-out family becomes another development family. | One final release; changes need a new held-out family/version. Never reuse it as “untouched.” |
| P ties T-pool but gets an architecture headline | A general learning method is sold as transformer replacement. | Separate practical-equivalence/uncertainty rule; no backbone claim without its own stronger contrast. Existing Premonition architecture is untested here. |

## 5. Design boundary

The first possible success is modest but useful: a small learner inferred predictive state functions from observations, usually declined unnecessary state, and saved functions that reduced learning cost on a second readout task, including in a discrete family excluded from development. The simulator designer already knows the laws. Active experiment choice, cross-world library reuse, unknown scientific discoveries and open-ended original thinking remain outside this experiment.
