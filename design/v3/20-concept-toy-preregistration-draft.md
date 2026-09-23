# 20 — Concept toy: staged preregistration draft

Astra · 20 September 2026 · prospective `ct20-v1`, not a frozen registration or a result.

**Decision to make:** does selecting and retaining small learned state functions improve prediction and subsequent learning over ordinary models with the same observations and total compute allowance? First establish that the simulator occupies a useful difficulty range using only a GRU and transformer. A failure at that gate ends this version before the new mechanism is built.

The [simulator/model spec](20-concept-toy-simulator-spec.md) defines the executable contract. The [build plan](20-concept-toy-build-plan.md) assigns three Opus agents and lists confounds. These documents take no credit for lookup results. In particular, fragile transformer initialization and cross-machine seed failures motivate the startup and reporting rules below; they are not evidence for this new method.

## 1. Freeze order and hypotheses

The three stages are calibration → fixed-trace feasibility → final source-and-reuse test. There is one recipe, no accuracy sweep and no automatic difficulty search. The initial baseline-only freeze covers the generator, G/T architecture, initialization, data/compute budgets, pilot rules and all future final-panel recipes. After calibration passes, a second freeze adds implementation hashes/counts for the other models. Their mathematical definitions and pass marks below are already fixed; this is implementation completion, not permission to tune them against the pilot gap.

Hypotheses:

- **H0, calibration:** ordinary small models can learn this world, but do not already reach the prediction floor with 32 transitions.
- **H1, learned-state utility:** P improves fixed-trace sample efficiency over G, T, T-fit, R, Q and P-fixed at equal cumulative compute allowances, on both C and the held-out M family.
- **H2, persistence:** freezing and reusing learned state functions improves task B relative to resetting those functions, and relative to equally retained baseline encoders.
- **H3, restraint:** controls usually select k=0 and suffer no material predictive harm.
- **Architecture question, separate:** does P also beat T-pool? A method result does not require that outcome. No result here establishes that the existing lookup/dispatcher architecture is superior, since none of it is used.

Write and hash Fable's predictions before the first model fit. The section at the end is intentionally empty. Agent code reviews, synthetic interface tests and algebra checks are not experiments; accuracy measurements are, regardless of what they are called.

## 2. Fixed seeds, optimizer and initialization

Use exactly **three training seeds: 20001, 20002, 20003**, for every required world and arm. All seed/world outcomes appear in the main report. No seed replacement, best-of-three, failure-conditioned restart, successful-seed-only mean or hardware substitution is permitted. These three seeds are a small engineering screen, not a well-powered population study.

All arms use AdamW, learning rate 0.001, betas (0.9,0.99), epsilon 1e-8, weight decay 0.0001 on matrix weights only, global gradient norm clip 1.0. First eight optimizer updates linearly warm up from 0.001/8 to 0.001; then the rate stays constant. Optimizers and schedules continue through source-budget rungs. No early stopping, checkpoint choice, dropout, stochastic latent sampling or hyperparameter trials.

Initialization is generated on CPU in float32, using the spec's per-parameter namespaces, and saved before transfer to the registered training device:

- Ordinary Linear matrices: Xavier uniform, gain 1; all biases zero.
- GRU input matrices: Xavier uniform separately for reset, update and new gates. Recurrent matrices: orthogonal separately for each gate, gain 1. In PyTorch gate order r/z/n, set **input-side update-gate bias to +1**, all other input/recurrent biases zero. Do not accidentally set both update biases to +1.
- Transformer pre-LN scales 1, offsets 0. Initialize attention/FF weights as above, then divide attention-output and FF-output matrices by sqrt(2). This is the registered residual scale, not an optional rescaled-init branch. Fixed sinusoidal position encoding uses the usual sin/cos frequencies `10000^(-2*j/24)`; position indices cover all 17 records, including RESET.
- Pool and dense-state functions use the same Linear recipe; their explicit 0.1 initializer and 0.25 residual multipliers are in the model equations, not hidden initialization adjustments.

Freeze the initialization implementation and exact serialized tensors for every seed. Corresponding components across arms and candidate k values have identical starting bytes. Register framework, NumPy, CUDA/driver versions and the parameter-name ordering. Use float32 throughout, disable TF32 and automatic mixed precision, select deterministic kernels and explicit math attention. Unsupported deterministic operations are a preflight failure, not a warning to ignore.

Use one hardware/backend configuration for every arm in a comparison. CPU-generated common initialization reduces one reproducibility ambiguity; it does not promise identical CPU/GPU optimization. A Mac/Linux replica is a new labeled replication with every seed, never a replacement for a failed run.

## 3. Shared fitting loss and compute accounting

All systems receive the spec's same nested discovery stream, including the 3:1 fitting/selection split. There is no cross-world pretraining. B denotes **all observed environment transitions**, not gradient updates, labels or only successful observations.

One source optimizer update samples four fitting episodes with replacement from the current prefix, using the shared minibatch stream. Horizon cycles 1,2,4 by global optimizer update index; within each sampled episode choose endpoint t uniformly from h..8, observe the recorded prefix through t-h, and forecast h actions with blank intermediate observations. Loss is `(prediction - observed_sensor_t)^2 / 0.25` on present endpoints only. A minibatch with no present endpoints has zero prediction loss, consumes its scheduled work and is logged; do not redraw until a useful batch appears. No hidden-state loss, extra coefficient label or oracle action is allowed.

Candidate selection uses one forecast per eligible horizon per selection episode: choose the **last observed endpoint t >= h** for each h in {1,2,4}. If none exists, that horizon/episode contributes no observation. Average within horizon and then over available horizons. If the entire selection set has no labels, select k=0 and log `no_selection_labels`; do not acquire more data. This bounds selection work and avoids consulting missing labels. G/T/T-fit/R/Q/P-fixed evaluate the same selection records for diagnostics but do not select checkpoints.

For each world × seed × arm, allocate **2.0e8 counted floating-point operations per source rung**, cumulative allowances 2e8,4e8,6e8,8e8,1e9 at B=32..512. This is a cap including fitting, selection, registered query inference and state/feature computation, not just optimizer updates. Reserve the known selection cost and the worst-case selected-model query cost before calculating fitting steps; for pool arms reserve k=4 inference. Initial-checkpoint scoring is charged to the first rung; final fitting and state-use diagnostics are charged to the last rung. P and T-pool divide the remaining fitting allowance equally among k=0/1/2/4 candidates; no reallocation from a rejected candidate. Other arms use the entire fitting allowance for their sole model. Charge all four candidates' validation work and only the selected candidate's actual external query prediction; unsuccessful candidates are nevertheless retained in the audit log. Savings from a smaller selected k cannot buy additional fitting after selection. Report those savings and enforce the same 5% actual-use rule; a reservation is not fictitious consumed work.

Before any fitting, the independent auditor produces an operator-level cost table for forward, backward, optimizer, state update, transformer history recomputation, initialization and evaluation at the fixed tensor shapes. Count a multiply and add as two operations; declare costs for non-MAC operators in the manifest. Profiling must include backward/optimizer work rather than assuming every architecture has the same cost per update. A documented FLOP estimate is acceptable if the same convention covers every arm and the report labels it an estimate. It is not an assertion of equal elapsed time or energy.

The step count is the largest integer number of complete updates fitting the remaining allowance. All actual work, including discarded candidates, preprocessing, auxiliary losses and feature caches, appears in the ledger. Freeze rung-specific step counts before accuracy runs; they cannot depend on learning success. Require counted total use within **5% across arms at each rung** and never over the allowance. If complete-update granularity prevents that, the allocation is a preflight failure requiring a revised registration, not padded dummy computation. Report actual estimates, useful updates, examples, storage, wall time and peak memory alongside nominal allowances. A compute-matching failure prevents an advantage claim.

No validation-error-based extra iterations, probe fits, latent searches, alternative inits or unpublished rejected models exist outside this ledger. Engineering timing uses synthetic fixtures with no registered world data or accuracy selection and is charged to the wave's elapsed time. Its resource cost is also reported separately from model discovery cost.

For task B, allocate **1.0e8 counted operations per rung**, cumulative 1e8,2e8,3e8 at 8,16,32 transitions. This includes feature-cache construction, fitting, auxiliary A prediction and inference. Precompute and freeze a step-count table for every possible selected k, for retained and reset arms, before final source fitting; the source winner merely indexes this table. Do not choose a downstream budget from its accuracy. Time the worst-case k branch for wave feasibility. Four fitting episodes are sampled with replacement from the available one/two/four episodes; draw h and t exactly as above, use B labels at every endpoint, and average B loss plus the A term specified below. B labels are never encoder inputs. Use the same AdamW recipe, resetting the optimizer and eight-update warmup at the start of task B only.

For a single unambiguous v1 choice, **include auxiliary A loss with coefficient 1** in both retained and reset pool arms, and in all ordinary retained baseline arms. Use the frozen A decoder and present A endpoints. It has no trainable path in a fully frozen retained encoder, but its forward cost still counts. In reset arms it can teach the newly initialized modules. Do not choose this option after seeing results. All B decoders have identical initialization for corresponding world/seed across arms. Frozen-feature caching is permitted equally wherever mathematically valid; recomputing features for mutable reset modules counts as real downstream cost.

## 4. Metrics, floor and independent units

Every measurement report includes raw noisy-target MSE, raw noise-free-response MSE, and normalized error. The evaluator knows simulator responses; the learner never sees them.

For each outer pool, task and family, set `V = max(variance of noise-free responses in that pool's ordinary and composition query panels, 0.05)`. Use the panels' fixed equal weighting, not each model's predictions. Compute this once for scoring; no model gets V or a family tag. This permits deterministic normalization on controls including N, whose signal variance is zero. Publish V and the analytic sensor floor `0.0009/V`.

Primary excess normalized error is `E = mean((prediction - noise_free_response)^2) / V`. E=0 is exact prediction of the conditional mean. A model “at floor” has E<=0.05: this is a registered tolerance, not an assertion that its noisy-target MSE equals exactly the analytic floor. Selection/training still use observed y and constant 0.25; evaluator-only noise-free responses cannot drive training or candidate gates.

For each world/seed/B, average ordinary and composition E equally. Source data-efficiency score is `A = mean(E_32,E_64,E_128,E_256,E_512)`, an equal average over these five logarithmically spaced budgets. Report every point; the mean cannot conceal final-budget failure. For each world/seed, `D_0.25` is the first registered budget reaching E<=0.25; record >512 or >32 when the threshold is never reached, not an invented numerical crossing.

Reuse score `A_B = mean(E_8,E_16,E_32)` and B crossing budget use fresh B panels and B normalization. Equal family weighting means C and M count equally regardless of their raw variances. O and N are separately reported restraint checks, not ways to inflate the hidden-family score.

For effect intervals, resample worlds within each family and training seeds as crossed blocks, with replacement, **10,000 draws**, keeping each model contrast, every budget and both halves of each pair aligned. Use the frozen statistics RNG. Report two-sided percentile 95% intervals for mean error differences and ratios; protect a ratio denominator by max(error,0.01), consistently in point estimates and resamples. Publish world-level and seed-level tables so three seeds cannot masquerade as hundreds of independent trials. These intervals are descriptive engineering uncertainty under this sample, not a claim of broad population coverage.

Never treat transitions, horizons, both halves of pairs or repeated budgets from one world as independent world samples. The conjunctive pass rule requires every specified contrast; do not choose the weakest baseline after looking at results. There is no additional unregistered significance search.

## 5. Wave 1: baseline-only calibration pilot

Build and run **only the simulator/panels, G, T and shared harness**. Do not implement, fit or tune P, T-pool, T-fit, R, Q, P-fixed or persistence until this gate clears. Static design and independent generator tests are allowed. No M-family learning trace or score may be inspected.

Use all six `train` worlds and all six `validation` worlds, all three seeds, both G/T, all five budgets. Fit each world separately; a train-world checkpoint is never loaded into validation. Train worlds diagnose fit and implementation. **Only the four C and two control validation worlds determine calibration**, under the rules fixed here. This is 72 independent model fits, each with five continuation checkpoints; vectorization may combine computation but never parameters or gradients.

Classify calibration using E and fixed initial-checkpoint E on the same query panels:

1. **Startup/observable competence prerequisite:** each arm must have E_512<=0.10 on at least 5 of its 6 control world×seed cases, and no numerical failures. Failure means `calibration-invalid/startup-or-implementation`, not evidence that hidden concepts are hard. Report which control type failed.
2. **Too easy:** either G or T has median C E_32<=0.05, at least 10/12 C cases with E_32<=0.10, and median C E_512<=0.05. Stop before building the mechanism. There is insufficient low-budget prediction error left for the proposed 20% practical gain.
3. **Learned case:** E_512<=0.50 and at least 25% lower query E than that arm's untrained initial checkpoint on the same world/seed.
4. **Too hard under this budget:** neither arm has at least 9/12 learned C cases. Stop. This is failure of this toy/recipe/budget combination, not proof that hidden-variable learning is impossible.
5. **Advance window:** the prerequisites hold, neither easy nor hard rule triggers, the better arm's median C E_32 is at least 0.15, and at least one arm has median C E_512<=0.50. “Better” means lower median at that budget, not choosing a different arm per case. Advance only if all conditions hold.

All other combinations are `calibration-inconclusive`, and stop v1. In particular, a narrow middle region does not justify adjusting the pass marks. If a toy is too easy, the next candidate change is delayed effects or a second interacting quantity; if too hard, first remove missing observations or noise, without changing the held-out family. The spec lists the knobs. Choose and preregister a new version before another pilot; **no within-v1 retuning or final-family peeking**. A stopped pilot is a useful result and consumes only the first wave.

## 6. Wave 2: feasibility on fixed traces

Only after calibration passes, implement the remaining six source arms and the persistence API. Freeze their source/config hashes, exact parameter counts, compute table and Fable's per-arm predictions before fitting. Use the six validation worlds, all three seeds, all eight source arms, all five budgets. Reuse G/T's wave-1 checkpoints and ledger if byte-identical to this registration; do not retrain until a better run appears. Newly fitted arms number 108 (6 worlds × 3 seeds × 6 arms), each with five rungs. P/T-pool candidate copies are additional fits within their common per-arm allowance, not free jobs.

The gate asks whether the method can learn and whether the reuse test is meaningful, not whether it has already beaten the baselines. Advance to final only when:

- P and T-pool each have at least 9/12 learned C cases by the calibration definition; each training seed supplies at least 2/4 such C cases.
- P and T-pool select k>=1 at B=512 on at least 8/12 C cases, covering every training seed, and k=0 on at least 5/6 control cases each.
- Every arm clears E_512<=0.10 on at least 5/6 control cases, has finite checkpoints and valid compute accounting. An inadequate baseline blocks the comparison; it is not a P victory.
- The freeze and causal-interface audits pass, including empty-state reset, task-B label isolation, rejected-candidate accounting and identical P/T-pool module code.

Do **not** train task B yet. Create and audit the second-task API with synthetic fixtures only. If the gate fails, stop v1 with the full table. No mechanism tuning, extra module sizes, candidate substitutions, module restarts or hidden-family calibration is allowed. Seeing a large P advantage in these already-used validation worlds is development evidence only.

## 7. Wave 3: untouched source and reuse evaluation

After feasibility, freeze all code, parameter counts, cost tables, diagnostic definitions, query recipes and source-and-B evaluation programs. Generate/hash the 24 final worlds and public support/query tensors without giving any final query targets to fitting or selection. The independent evaluator holds hidden responses. The eight M worlds are first encountered here. Run all eight source arms, three seeds and five budgets: **576 source arm fits**, with candidate fitting included inside P/T-pool. Store each B=512 winner before any task-B training.

Then run task B for all eight retained source arms plus **P-reset and T-pool-reset**: 24 worlds × 3 seeds × 10 arms = **720 short B fits**, each with three continuation checkpoints. The retained source encoders are frozen; only B decoder weights train. In reset arms only the reset module functions and new decoder train. Source k and source checkpoint hashes cannot change. P-fixed reuses its fixed four-coordinate functions. All methods receive the same B traces/labels and can retain their complete learned source encoder.

Run both source and B according to the frozen schedule without choosing whether to continue based on final accuracy. Accuracy is released only after the planned final set finishes or the hard deadline ends the wave. Intermediate source scores must not steer B training, difficulty, seeds or stopping. An incomplete wave is not a pass and is not repaired by dropping worlds.

### Required method pass: every condition, not a menu

1. **Integrity and completion:** all required worlds, seeds, arms and rungs complete under the frozen recipe and resource limits; no data/label leak or invalid comparison; all controls satisfy E_512<=0.10 on at least 11/12 cases for O and separately N in every source arm. In addition, each ordinary comparison arm G/T/T-fit/R/Q/P-fixed must escape the registered `never_started` classification in at least 6/8 worlds per hidden family in each seed. This permits learned-and-failed comparisons but blocks a concept-advantage verdict against baselines that mostly never optimized. Missing/NaN runs remain in the report and prevent a pass.
2. **Source prediction:** separately in C and M, mean source A for P is **at least 20% lower than each of G, T, T-fit, R, Q and P-fixed**. For every one of these contrasts, the paired 95% interval for `A_baseline - A_P` has lower bound >0. In each seed, P's family mean A must be lower than each baseline's; no seed can be rescued by averaging the other two.
3. **Absolute competence:** P has E_512<=0.25 in at least **6/8 worlds per hidden family in each seed**. It selects k>=1 in at least 6/8 worlds per hidden family in each seed. Matching simulator dimension is not a success criterion.
4. **Add nothing when appropriate:** P and T-pool each select k=0 at B=512 in at least **22/24 control world×seed cases**, with at least 11/12 separately on O and N, and at least 7/8 control worlds in each seed. Their mean control E_512 is no more than the corresponding zero-pool backbone's E_512 +0.02, separately on O and N. Selection of a nonzero gate on N is a false discovery, even if a module name sounds plausible.
5. **Reuse contribution:** separately in C and M, P's mean B A_B is at least **20% lower than P-reset**, with paired 95% difference interval strictly >0 and a benefit in every seed. P reaches E_16<=0.25 in at least 6/8 worlds per hidden family in every seed. In at least **half of those 24 world×seed cases per hidden family**, P reaches E<=0.25 at least one registered B rung earlier than P-reset. A crossing at 32 versus >32 counts as later only when P actually crossed; no extrapolated crossings.
6. **Reuse against capable alternatives:** separately in C and M, P's mean B A_B is at least **20% lower than each retained G, T, T-fit, R, Q and P-fixed**, with every paired 95% difference interval strictly >0 and a benefit in every seed. Source-plus-B compute and marginal B compute both obey matching rules. This prevents calling a benefit from reset alone a competitive advantage.
7. **Intervention/invariance guards:** at B=512, P's relevant-pair difference MSE divided by V is <=0.10 in each hidden family and each seed, and <=0.02 in controls. On irrelevant pairs, normalized MSE between its two mapped predictions is <=0.02, separately by family and seed, and mean E over the edited branches is no more than the unedited E+0.05. These guards cannot substitute for primary prediction accuracy.
8. **The saved state is actually used:** apply the state perturbation diagnostic below. It must meet its prespecified impairment and control conditions; a nonzero gate with an unused state is not evidence for the proposed mechanism.

These intentionally strict conjunctions may produce an inconclusive result with three seeds. They are engineering advancement marks, not power calculations. Do not enlarge the final panel or add seeds after seeing uncertainty under this registration.

### State-use diagnostic

On the final B=512 source ordinary/composition panels, replay the complete history normally. Immediately before the final query prediction, replace P's selected module-state tensor with that from the next query unit in the same world/panel (cyclic permutation of unit index). Hold public inputs and backbone context fixed. This tests whether the decoder depends on the inferred state at the point of use; it is a diagnostic intervention, not a deployable prediction method. For the paired control diagnostic, replace the first 4*k context coordinates from that same donor unit instead; k<=4, so this fits within context width 24. Run both diagnostics for T-pool too. For G/T/R/Q/T-fit/P-fixed, report the analogous first-16-context-coordinate perturbation where a 24-wide context is present. Do not assert these perturbations have equal information content or equal energy.

P's module permutation must increase mean E by **at least 0.10 absolute and 25% relative**, separately in C and M, in every seed. Use max(unperturbed E,0.01) for the relative denominator. In control cases selecting k=0, it must be an exact no-op up to 1e-6 in predictions. Other context perturbations are reported, not required to hurt less: ordinary features may also be essential. This diagnostic establishes use, not uniqueness or causal identification of the coordinates. It is conducted after prediction checkpoints freeze and cannot select a module.

### Transformer-with-mechanism interpretation

T-pool receives precisely the same selection, candidate budget, functions and persistence treatment. Apply the source/reuse usefulness marks to it as a separately labeled secondary method check; compare its reset arm when evaluating persistence. Do not turn a P failure into the preregistered primary P pass merely because T-pool wins.

An additional **backbone advantage within this toy** requires P to have at least 20% lower source A and reuse A_B than T-pool in both hidden families, paired 95% differences strictly >0, and a benefit in every seed. Even then this is GRU-context-versus-transformer-context evidence, not a result about the old dispatcher.

If P and T-pool perform similarly, the supported result is a method that can help a transformer. Report practical equivalence only if a paired 90% ratio interval lies wholly inside [0.90,1.10], for source and reuse separately in both hidden families. Otherwise report “no established backbone advantage” or “uncertain,” not a statistically demonstrated tie. **A tie, or an unresolved gap, permits no claim that a non-transformer architecture is necessary.**

## 8. Startup lottery, failures and reporting

At initialization and at the fixed B=512 endpoint, score a deterministic fitting audit set: for each fit episode and each h, its last eligible observed endpoint. Use the same initial/final set; do not choose cases by difficulty. Compute the training-label loss reduction and evaluator-only fitting E. Fitting E is diagnostic only and cannot alter optimization.

Classify every world×seed×arm, and separately every P/T-pool candidate:

- **Never started:** final observed fitting loss improved less than 10% relative to initialization **and** final fitting E>=0.80. If the initial loss is <=1e-8, mark `initially_at_floor`, not a startup failure.
- **Started, not yet learned:** it escaped that criterion but did not achieve fitting E<=0.25. This includes the intermediate 10–20% improvement region; do not imply that any small improvement proves learning.
- **Learned and failed to transfer:** fitting E<=0.25 but final source query E>0.50. This is distinct from an optimizer stuck near its start.
- **Learned with intermediate/competent generalization:** fitting E<=0.25 and query E<=0.50; report whether it also reached the required 0.25 mark.
- **Numerical failure:** NaN, Inf, invalid gradient or divergent optimizer; stop that job and report it. **Infrastructure incomplete:** interruption, deadline or missing required output; record separately. Neither disappears from a denominator.

Also publish the full curve; these labels are coarse diagnostics, not alternative success criteria. A numerical failure or uncompleted job blocks the complete pass. Failed startup in a hidden world remains a reported error; no successful-seed subset may support the main claim.

Exact-state resumption is allowed only after infrastructure interruption within the registered wave schedule, using weights, optimizer, RNG, rung/update/data cursor and candidate state. Accuracy-conditioned restarting is prohibited. No extra wave is silently added to finish a three-wave test. If a recipe is revised, keep this version's failures and create a new registration.

## 9. Resource schedule and feasibility boundary

Use the free RTX 5070 Ti if available; run one coordinator and vectorize independent world/seed lanes with **separate parameters, optimizer states, losses and gradients**. Do not average gradients across worlds. On Mac, maximum six simultaneous jobs with OMP/MKL/OpenBLAS/PyTorch intra-op and inter-op thread counts each set to 1. Use one platform per stage's compared set; do not mix Mac and GPU results into paired contrasts. Prefer using the same GPU throughout all three waves.

Each wave has a **1,200-second soft compute stop and a 1,500-second hard wall deadline**, including timing checks, data work, scoring, file writes and shutdown. This stays below 30 minutes. No cloud job or spending is part of this design; the remaining roughly $27 requires Ben's explicit yes before any cloud use.

| Wave | Work | Advance condition |
| --- | --- | --- |
| 1 | Baseline-only pilot: 12 worlds × 3 seeds × 2 arms, five source budgets. | Calibration window and integrity. |
| 2 | Complete remaining source arms on six validation worlds; audit persistence interface with synthetic data. Reuse identical G/T pilot evidence. | Fixed-trace feasibility gate. |
| 3 | 24 untouched worlds × 3 seeds × 8 source arms, then 10 B arms with three B budgets; final guards/diagnostics and report. | All final marks, or report failure/inconclusive/incomplete. |

Before a wave's registered fits, time a bounded synthetic fixture at the actual vectorized shapes, including optimizer/selection/evaluation/I/O paths. Do not use accuracy to choose settings. Reserve 300 seconds for scoring/I/O/shutdown; require projected remaining full-wave work **with a 1.5× timing margin** to fit within 1,200 seconds of total wave elapsed time. If it does not, do not launch an inevitably partial experiment: record `resource-infeasible` and stop this version. Do not shrink world/seed/arm counts after registration. Batching can be engineered without changing mathematical results; changes affecting floating-point reduction/order must be frozen before fitting.

The arithmetic budget is intentionally small, but tiny-model GPU overhead and independent-lane batching may dominate. **No measured three-wave runtime is claimed.** This is a plan that either finishes within three bounded waves or reports why it cannot. A longer experiment, reduced scope or different budget needs a new explicit design; it cannot be presented as completed ct20-v1. Compilation/timing/failed or rejected work appears in elapsed-resource reporting.

## 10. Verdicts and maximum claims

- Calibration at floor: this toy does not justify building a special mechanism yet.
- No baseline learns: fix the task/optimization question before interpreting concept invention.
- C succeeds but M fails: one-family representation learning only; no general concept-creation claim.
- P matches T-fit or R/Q: extra fitting/capacity or ordinary system identification may explain performance.
- P matches P-fixed: no demonstrated benefit from selecting the number of added coordinates.
- Reuse matches P-reset: no demonstrated value in persisting the learned state functions under this test.
- Controls select modules: the selection rule can mistake noise/visible structure for missing state.
- Results vanish after rejected-candidate accounting: no equal-compute advantage.
- P and T-pool tie: a potentially useful general method, not transformer replacement.
- Wide intervals, weak baselines, missing runs or deadline failures: inconclusive/incomplete, never a pass by excluding inconvenient entries.

**Maximum full-pass statement:** “With fixed intervention traces in these continuous and held-out discrete toy worlds, a prespecified method learned, selected and reused small predictive state functions more efficiently than the tested ordinary and fixed-dimension alternatives under matched data and counted-compute budgets, while usually declining extra state in controls.” Add a transformer-method qualification according to T-pool's result. Describe it as a concept new to this learner, operationalized by prediction, intervention sensitivity and reuse.

It would not establish a unique recovery of the simulator's true variables, discovery new to humanity, general original thinking, autonomous scientific experimentation, superiority to all transformers or published discovery systems, cross-world transfer, or an advantage of Premonition's existing operator/dispatcher. Those are future questions.

## Fable's predictions
