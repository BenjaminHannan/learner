# A3 teacher delay: corrected stage contract

19 September 2026. Track A only. Design for Ben to hand to Opus; implementation and execution remain unrun.

**Suggested — decision.** Accept both specification objections. Replace `A3-teacher-delay-v1` with **`A3-teacher-delay-v2`**: retain half the historical FLOP budget, restore the historical early phase budgets by rescaling the fractions, and use a learned one-hop/practised-two-hop gate as the primary stage endpoint. Register **48 fresh pairs / 96 jobs**. Stage acceptance can unlock a relation-fix comparison; it does not certify held-out transfer.

**Shown — scope and authority.** This review used source/text reads and Python standard-library calculations on saved JSON. No tests, training, project imports, checkpoint or tensor-dataset loading, GPU, SSH, spending, messaging, or credential inspection occurred. Only this new design file was written. “Shown” means source facts, saved-record counts or arithmetic; “suggested” means decisions/inferences; “untested” means future behavior or execution requirements. This file supersedes [11]'s A3 budget, curriculum, sample size, advancement endpoint and the associated sequencing requirement. It makes a specific stage-endpoint amendment to [08]'s treatment of this A3-timing comparison. Other [08]/[09] contracts, including the separately named A4 comparison and G_cert, remain in force. This is not a launch authorization.

## Q1 — Preserve the early phases without hiding the lost own-fetch training

**VERIFIED — shown.** Across the 40 [plain control run JSONs][runs], the saved `train_report.flop_budget` has minimum `68124072492342.38`, median `68125630225366.484`, and maximum `68139523909151.89`. The v1 budget divided by that median is **0.5001586134**. Keeping its old fractions therefore approximately halves the absolute early phase budgets. The [curriculum implementation][train] uses FLOPs spent **before each update**, not update count.

**VERIFIED — shown, with two qualifications.** For the 80 plain/shared and plain/separate-pool runs, the numbers with logged answer loss above 0.1 at steps 600/900/1200/1500/1850 are **80/30/12/6/5**. However, 30/80 is not a measured probability that the new half-budget control “cannot read”: the threshold is a loss proxy on historical trajectories. Also, the [soft-read registration][softreg] rescales fractions but its literal step-length claim does not follow from a FLOP clock. Gold uses two loops; teacher and own use four for this toy. Multiplying a fraction by the nominal total steps is not an exact phase calculation.

**NOT VERIFIED — untested.** Runtime phase-boundary equality on fresh streams, half-budget success probabilities, and whether the shortened own-fetch tail suffices. Historical step boundaries are approximate logged observations, not exact promises for every new seed.

**DECISION — suggested.** Use half of the *median historical* budget, with exactly doubled historical fractions. This restores the gold and control teacher **absolute FLOP allowances**, and hence approximately their historical update lengths under the unchanged workload. It does **not require the full historical budget**. A literal guarantee of exactly 1,850 and 2,850 updates cannot be made with global FLOP fractions on variable fresh batches; that would require a different clock. The contract below does not claim such a guarantee.

### Revised CONTRACT — untested: budgets and curriculum

> Experiment ID: `A3-teacher-delay-v2`. Reference budget `B_ref = 68125630225366.484` counted model FLOPs. Both arms receive the explicit numeric budget **`B = 34062815112683.242 = B_ref / 2`**. Freeze these numeric literals; do not recompute B from each seed, requested steps, or `budget_for_steps`. This small correction also removes v1's approximate-half convention.
>
> Both arms are fresh plain/shared models: legacy request path, shared key/value pooling, no relation-location wire, pooled selectors, ST, new loss or architectural change. Retain the historical top-1 retrieval, native ASK gate, K=4 evaluation, unordered evidence targets, random teacher-card selection, model configuration, AdamW configuration, learning rate `1e-3`, 100-update warmup and no cooldown. Expected parameter count is **79,748**, with **zero added parameters**. Gold still gives ASK/HALT losses zero weight. Existing evidence supervision is disclosed; no new input privilege is introduced.

| Setting | Control | Delayed teacher |
|---|---:|---:|
| Explicit counted FLOPs B | 34062815112683.242 | 34062815112683.242 |
| Gold ends | **0.2000** | **0.2000** |
| Teacher ends / ramp begins, t | **0.3666** | **0.6000** |
| Ramp width, w | **0.1668** | **0.1668** |
| Ramp ends, t+w | **0.5334** | **0.7668** |
| Maximum own-fetch probability | **0.75** | **0.75** |

> With `f = FLOPs_spent_before_update / B`, use gold for `f < .2`, pure teacher for `.2 <= f < t`, and the existing own mode thereafter, with `p_own = .75 * clip((f-t)/.1668, 0, 1)`. **The only independent arm difference is t**; derive ramp end from `t+w`. No adaptive transition, competence threshold, extra training prefix, or post-budget own-only extension is permitted.

**Shown — phase accounting.** These are nominal intervals; actual batch crossings must be recorded.

| Interval | Control, share of B | Delayed, share of B | Control / delayed, share of B_ref |
|---|---:|---:|---:|
| Gold | .2000 | .2000 | .1000 / .1000 |
| Pure teacher | .1666 | .4000 | .0833 / .2000 |
| Ramp | .1668 | .1668 | .0834 / .0834 |
| At maximum own probability | **.4666** | **.2332** | **.2333 / .1166** |

**Shown.** The teacher window is `0.4000/0.1666 = 2.40096` times the control's. The maximum-own tail receives approximately **1.58937e13 versus 7.94345e12 FLOPs**. “Full-own” here means the schedule has reached **p_own=.75**, with teacher insertions still possible; it never means p_own=1. The historical maximum-own tail was `.7333 B_ref`. Both new arms therefore have substantially less of it, particularly treatment.

**Suggested — approximate update interpretation.** Using the handoff's roughly 1,850 gold updates and 10,400 subsequent updates per `.9 B_ref`, a constant post-gold average-cost approximation gives roughly **960 versus 2,310 pure-teacher updates**, then **2,700 versus 1,350 updates at maximum own probability**, ending near **6,470 total updates**. These are planning illustrations, not requested-step caps or predicted exact boundaries. They preserve the historical approximately 950-update control teacher window much better than v1. Fresh batch costs and boundary rounding determine the actual counts.

> Record the actual update and FLOP boundaries, realized phase totals, ramp-end crossing, and time at p_own=.75. Evaluate the primary stage gate once at budget completion. The estimand is the **net effect of delaying the ramp at this fixed B**, including the cost of reduced own-fetch practice. A positive endpoint result supports this recipe at this budget. A null or negative result does not isolate whether a longer teacher window is useless or its benefit was offset by less own practice. Faster escape alone cannot rescue failed stage acceptance. Do not claim equivalence to a full historical run or extrapolate acceptance to another B.

### Revised CONTRACT — untested: completion and Ben's time/cost rule

> Use the frozen FLOP counter and **tolerance .05**. Training completion requires a FLOP-budget stop **and** `budget_ok=true`; an update/time stop or a saved checkpoint is insufficient. Set an update ceiling of **20,000**, solely as a safety ceiling, and a training cap of **1,200 seconds per job**. Reaching either first is incomplete. Report actual compute and any loop/accounting mismatch. Calibration and all evaluation are additional resource costs.
>
> For all **96 jobs**, use
>
> **`T = s + ceil(96/C) * (B/f_rate + e)`**.
>
> `C` is measured simultaneous job capacity; `f_rate` is a conservative per-job counted-FLOP rate at that load, bounded using the slower arm and all phases. `e` covers each job's calibration, checkpoint I/O, complete six-cell evaluation, READS and integrity work. `s` covers remaining setup, queueing and final reporting/bootstrap overhead. Include any serial evaluation bottleneck in the bound. The nominal per-job training floor is **`B/1200 = 2.838567926e10` counted FLOP/s**; it does not by itself admit a wave. Nominal training alone totals **3.270030251e15 counted FLOPs** across the roster.
>
> Prefer the free RTX 5070 Ti. Target **T <= 1,500 seconds** to leave margin below Ben's **30-minute wall-clock ceiling for the whole comparison**. Do not call each batch of C jobs a separate qualifying comparison. Do not shorten B, drop cells or reduce n to achieve admission.
>
> Apply Ben's stated exception explicitly: if a credible available configuration completing the whole comparison within 30 minutes can be obtained for **$2 or less**, a slower run does not qualify for the cost exception. If meeting the ceiling would cost **over $2**, document the lowest-cost credible qualifying option considered and its complete price basis; the slower free configuration may then use the exception. Register its actual longer T. Count rehearsal, setup, billing increments, fees, retries and discarded work in cost. Any paid route must also fit the approximately **$24.9 remaining** resource ledger; that figure is the supplied balance, not a newly checked account balance. The exception is not permission to exceed the per-job completion cap or to omit evaluation.
>
> Throughput, memory, e, s and prices require a disjoint resource rehearsal/quote under later execution authority. No qualifying time/cost result has been established here. The historical “five jobs in about 39 minutes” is neither a 96-job wave estimate nor a throughput measurement for this revised half-budget recipe. **The design is specified; resource admission is pending.** Full historical B is unnecessary for preserving the early windows; using it to restore a longer own tail would be a separately frozen contrast with a new resource bound, not a repair made after seeing these results.

## Q2 — Accept a plateau-stage improvement without claiming relation transfer

**VERIFIED — shown.** From the saved [pair-suite rows][rows], plain/shared has **29/40 passing c1 AND c2**; individual c1..c6 pass counts are **33, 29, 1, 0, 1, 1**, and G_pair passes are **0/40**. Requiring an improvement in full G_pair before permitting research on its outstanding relation failure creates the sequencing defect Fable identifies. It does not prove that a schedule can never affect transfer indirectly; that stronger claim remains untested.

**VERIFIED — shown, numerical correction.** For the simpler “not stuck” endpoint, assume control success .825, treatment success 1, and independent seed pairs. At n=16, the probability of at least five susceptible controls is **0.133132**, rather than approximately .12. That is also maximum primary-rule power under these assumptions, with no losses. For the c1/c2 learned gate, control success .725 and perfect treatment give only **0.460639** power at n=16. Five gains/zero losses is the smallest passing case, not a requirement that every passing comparison have zero losses.

**NOT VERIFIED — untested.** The new half-budget control pass probability, treatment effect, pairing dependence and total probability of passing all safeguards. Historical rates supply explicit planning scenarios, not measured prospective rates. The learned gate is a stage capability endpoint, not a pure measurement of the subject-selection mechanism.

**DECISION — suggested.** Choose **both learned-gate attainment and logged time to escape, with the learned gate as the sole primary endpoint**. Retain 08's exact paired test and effect floor, applied to this explicitly named stage gate. Use 48 fresh pairs. Relative no-harm checks on held-out performance must not turn back into an absolute requirement to solve held-out transfer before investigating it.

### Revised CONTRACT — untested: roster, primary and power

> Register **n=48 independent seed pairs**, with two jobs per pair using Q1's B and curricula. Pair initialization, training-world stream and training RNG seed; use independent substreams for data generation, evaluation and diagnostics. Freeze the 48 initialization/data/evaluation seed assignments before learning, reject collisions with historical assignments, and publish every intended job. Use fresh seed-specific development panels, shared within each pair and independent across pairs; do not reuse historical evaluation rows or consume certification data. Balance execution order and use one declared hardware/numerics configuration for both arms and the whole comparison. A common seed is a blocking variable, not a promise of bitwise-identical GPU trajectories.
>
> At the budget-complete checkpoint, run native hard top-1 retrieval with ASK and fixed K=4. Define **`L_train = [c1_correct >= 1969 of 2048] AND [c2_correct >= 1969 of 2048]`**, where c1 is one-hop and c2 is practised two-hop. Held-out cells do not enter L_train. No supplied evidence enters this native evaluation.
>
> Let g count control-fail/treatment-pass pairs on L_train, l count control-pass/treatment-fail pairs, and d=g+l. Compute
>
> `p_exact = sum(comb(d,k) for k in range(g,d+1)) / 2**d`, with p=1 when d=0.
>
> The primary passes only if **`p_exact <= .05` and `(g-l)/48 >= .10`**: at least five net gains, plus the exact-test requirement. Report the complete 2x2 table. No sample enlargement, outcome-based replacement, early efficacy stopping, endpoint switching or selective omission is allowed. Invalid/incomplete jobs stay in the roster as failed outcomes; incomplete training or evaluation prevents advancement, rather than manufacturing treatment gains from missing controls.

**Shown — prospective power arithmetic, not a model result.** For iid pairs with gain probability a and loss probability b, I summed the multinomial probabilities over all `(g,l)` satisfying both primary inequalities:

`Power = sum_pass [48!/(g! l! (48-g-l)!)] a^g b^l (1-a-b)^(48-g-l)`.

| Planning scenario | a / b | Primary power at n=48 |
|---|---:|---:|
| L_train .725 → .95, independent arm outcomes within pairs | .26125 / .03625 | **89.16%** |
| Same marginal rates, most discordant feasible pairing | .275 / .050 | **85.69%** |
| L_train .725 → .90, independent arm outcomes | .2475 / .0725 | **63.34%** |
| L_train .725 → .875, independent arm outcomes | .240625 / .090625 | **48.72%** |

**Suggested — interpretation.** Forty-eight pairs are a powered test of a **large, 22.5-point planning improvement**, with limited power for smaller effects. The assumptions are particularly uncertain because this control ends earlier than the historical roster. These percentages cover the primary rule only; safeguards lower total advancement probability. The exact primary test is one-sided size at most .05 under iid pairs and Pr(gain)<=Pr(loss); the observed 10-point floor is not a confidence bound claiming a 10-point population gain. This does not control an entire adaptive sequence of future experiments.

### Revised CONTRACT — untested: safeguards and stage status

> Evaluate **all six G_pair cells** and a **fresh 512-world READS panel per seed**. Keep G_pair's published cutoffs unchanged: c1/c2 `1969/2048`, c3 `1876/2048`, c4/c5/c6 `945/1024`. Every twin pair is one scoring/resampling unit with the existing joint-correct rule, including c6's output-invariance requirement. Legacy selector mode is explicitly `not_applicable`.
>
> Acceptance requires all of the following:
>
> 1. The L_train primary passes and all 96 training/evaluation/integrity records are valid and complete.
> 2. **No increase in fresh c1-stuck count**, using `c1_correct <1536/2048` in both arms, with all 48 pairs retained.
> 3. The paired one-sided 95% lower bound on treatment-minus-control **mean one-hop accuracy and mean READS accuracy is greater than -.02**, as required by 08. For this stage contract, extend the same relative no-harm requirement to each of **c2, c3, c4, c5 and c6**. These use continuous per-seed cell accuracies, not a demand that the cells pass their absolute cutoffs. No additional model evaluations are needed beyond the registered panels.
> 4. **Observed G_pair pass count does not decrease**. Publish its gains and losses; individual losses are not a zero-loss veto. This count check is descriptive, not a claim of a confidence-certified G_pair non-inferiority margin. The per-cell intervals in item 3 supply the additional uncertainty-aware protection when binary G_pair is near zero.
> 5. Source, label-noninterference, episode-isolation, inference-policy, budget and time/cost checks pass. No wire, special role access, selective seed rescue or diagnostic feedback to training is allowed.
>
> For item 3 retain 08's **100,000 paired hierarchical bootstrap resamples**: resample seed pairs, then world units within each drawn pair/cell, using the same sampled units for its two arms; keep both members of an intervention twin together. Weight seeds equally. Use the sorted **5,000th** bootstrap difference as the one-sided lower bound, with independent manifest-derived diagnostic RNG. All required bounds must exceed -.02. These are the inherited approximate intervals, not exact small-sample guarantees; inconclusive does not establish no harm.
>
> Passing these conditions earns **“accepted plateau-stage background: A3-teacher-delay-v2 at B=34062815112683.242”**. It means improved native learned-gate attainment with the declared safeguards; it does not mean every seed escaped, that the plateau's cause is proved, or that held-out relations are solved. A pair of all-zero G_pair rosters does not automatically fail stage acceptance: absence of a positive held-out score is different from a detected relative degradation.
>
> This status **unlocks eligibility for a separately registered relation-fix comparison** on the accepted schedule. That comparison must train both arms afresh on the complete new seed roster, including potential stuck seeds; it cannot fine-tune or select only this stage's successful models. It retains G_pair as its advancement endpoint, the no-increase-in-stuck safeguard and the other 08/09 safeguards. If its background differs from 08's named A4 recipe, give it a new complete contract rather than silently editing A4. The static-token residual remains unbuilt, with 11's asker-contamination prediction intact. Qualification does not itself authorize implementation/training of that module. G_cert and its independent 77-of-80 campaign remain separate and unchanged.
>
> If L_train or any safeguard fails, this recipe is **not stage-accepted**. Secondary escape timing cannot override that result. Report uncertainty and the reduced-own-practice alternative; a negative result is not a general rejection of schedule remedies or of the separately normalized-loss mechanism.

### Revised CONTRACT — untested: secondary escape timing

**Suggested.** Timing is useful evidence but not automatically more powerful: escapes during the shared prefix and joint censoring can leave many pairs uninformative about the delay. It does not replace the declared primary or its power calculation.

> Keep the existing 50-update training-log cadence and passive `gold_recall_at_4` metric. For each complete run, report the first **non-gold** saved log with recall **strictly greater than .3**, its update and cumulative counted FLOPs, and an event/censor flag. Despite its name, this is ungated first-opportunity top-1 gold recall, not K=4 retrieval success; its ceiling is .75 for the equal one-/two-hop mixture. Gold-phase observations involve preloaded cards and do not count as empty-workspace escapes.
>
> For a common-horizon secondary comparison use logs through nominal B: define event time as the first qualifying log's FLOPs minus `.2B`; otherwise right-censor at **`.8B` of post-gold compute**. Ignore any terminal log beyond nominal B for this common-horizon statistic, while retaining it in the raw record. Report paired restricted times, their treatment-minus-control differences, event counts and joint censoring; end-censored runs have not been observed to escape. Also report raw first-crossing update counts and actual run-end censoring for comparison with historical curves. Logs average observations and may straddle a phase boundary, so neither timestamp is an exact onset or a measured escape hazard. No new forward pass or training control is added. There is no secondary pass mark or route around the primary.

## Q3 — Separately normalized first-request CE

**VERIFIED — shown:** the frozen [loss code][model] concatenates missing-evidence CE terms before averaging; with Q questions equally split between one/two hops, top-1 teacher insertions yield `1.5Q` terms, while an all-miss four-loop trajectory yields `4Q`, giving first-request coefficients in the ratio **3/8**. **NOT VERIFIED — untested:** that limiting dilution is typical, that it causes the plateau, or that removing it helps. **DECISION — suggested:** keep teacher delay first; separate normalization is a cleaner follow-up for the *denominator mechanism specifically*, whereas delaying the ramp tests the net value of a longer teacher period. **CONTRACT — untested:** v2 above keeps the original loss in both arms, with its fixed B, 48 pairs, L_train primary, safeguards and timing rule; add no normalization arm now. A possible separate follow-up loss is `L_set = (2/3) mean_q CE_first(q) + (1/3) mean_(q,t>0,missing) CE_later(q,t)`, with an empty later group contributing zero and all other loss weights/BCE unchanged. For this fixed equal-hop toy it matches the original teacher-only weighting and holds the first-group weight fixed as later missing-evidence terms multiply; it adds zero parameters. It keeps the **scheduled** teacher/own mixture unchanged, although altered learned retrieval can change the realized own states. That distinct contrast needs its own frozen registration after the delay result; it is not bundled into this launch package or substituted after a failed primary.

## Opus build list — additive launch package, not work executed here

**Suggested — handoff scope.** Ben can give this contract to Opus sub-agents. Add the following files; the proposed paths were absent when this review was written. If a path has since appeared, coordinate its ownership rather than overwrite it. Reuse existing source through imports/wrappers where parity permits; do not modify it. Completion of this build list means a reviewable adapter, not an admitted learning run.

| File to add | Required responsibility |
|---|---|
| `scripts/premonition_teacher_delay.py` | Plan/manifest and single-job launcher for the two exact v2 schedules. Explicit B, fresh paired seed/data streams, preserved base builder/optimizer, full log retention including FLOPs, phase-boundary accounting, 20,000-update/1,200-second caps and FLOP completion predicate. Capture resolved configuration, initial-state/stream digests and actual source closure. Refuse existing output directories, arbitrary recipe overrides under this experiment ID and auto-launch from planning/reporting. |
| `scripts/premonition_teacher_delay_eval.py` | Fresh seed-specific six-cell and READS panels; wrapper around existing counting/inference semantics with labels removed before inference. Explicit legacy policy record, unchanged-weight/output checks and episode isolation. New manifests/outputs and 09's complete reuse identity; no historical-row relabelling or sealed test access. |
| `scripts/premonition_teacher_delay_report.py` | Full 48-pair roster accounting, L_train/G_pair/stuck tables, exact primary and power sums, all seven continuous safeguards, censor-aware secondary summaries, complete resource formula/ledger and distinct statuses for specified, admitted, complete, stage-accepted and G_pair outcomes. Accept no missing-arm shortcut or endpoint switch. |
| `tests/test_premonition_teacher_delay.py` | Schedule/budget/clock boundaries and launcher accounting; disabled-option/base-path parity, common initialization and data streams, passive-logging parity, no-extra-parameter and completion/failure fixtures. |
| `tests/test_premonition_teacher_delay_eval.py` | Fresh-panel pairing and isolation; c1..c6/READS counts and cutoff boundaries; labels affecting scores only; native ASK/top-1/K=4 behavior; policy and source-key mismatch rejection; no weight/state changes from scoring. |
| `tests/test_premonition_teacher_delay_report.py` | Exact-test enumeration and planning-power fixtures; roster/missing-run handling; paired hierarchical resampling/twin preservation; safeguard boundaries; escape ties/censoring; stage acceptance with both G_pair counts zero; rejection on regression and prevention of a stage-to-certificate relabel. |

**CONTRACT — untested parity requirements for Opus.**

1. **Original computation.** On fixed CPU fixtures with explicit RNG states, compare the new adapter's legacy model against the executed historical source lineage for gold, teacher, ramp and p_own=.75 states. Check state-dict keys/count, logits, score paths, fetch/ASK decisions, loss components, gradients and a short optimizer-update fixture. No extra model operation or diagnostic may perturb RNG or normalization. CPU parity is a code-integrity requirement; GPU bitwise trajectory identity is not presumed.
2. **Correct clock.** On a deterministic sequence of accounted batch costs, compare the historical `.10/.1833/.2667` curriculum at B_ref with v2 control at B_ref/2 through their shared range. Absolute gold/teacher/ramp thresholds must agree, subject only to the same batch crossing. Assert the treatment's sole changed independent field is t, its ramp width remains .1668, and the nominal maximum-own intervals are .4666B/.2332B. Check values below, at and above every boundary. Record actual boundaries on later real runs; do not make nominal-step assertions.
3. **Common prefix and passive telemetry.** Both arms must have equal shared initial tensors and identical generated training batches before training; teacher/gold fixture losses and updates must agree before the control ramp starts. Retaining FLOP fields, boundary metadata and escape summaries must not add forward calls, alter samples, change losses or consume model RNG. Full-run GPU divergence after the common prefix is an outcome, not grounds to drop a seed.
4. **Evaluation integrity and reuse.** Use new development panels, retain original twin counting and isolate every world/episode. Perturb labels without changing inference outputs. Verify parameters and normalization state before/after. Match 09's complete key `(checkpoint_path, checkpoint_sha256, evaluation_manifest_sha256, evaluator_source_hashes, loader_source_hashes, selector_policy, execution_config_sha256)` plus successful completion/integrity; missing/mismatched fields forbid reuse. A4's pooled-selector diagnostics and affine probe are not prerequisites for this unchanged legacy-request experiment.
5. **Statistical/accounting fixtures.** Verify n=48 g=5,l=0 passes the primary and g=4,l=0 fails; losses are included in the exact tail and net gain. Use explicit fixtures where L_train improves, G_pair remains zero, and safeguards pass, and where a stuck-count increase or a -.02 lower-bound boundary blocks acceptance. Missing runs must block acceptance without disappearing from n. Check bootstrap units, event-versus-censor handling, and that no secondary statistic can change the primary decision. Include the stated exact-power values as arithmetic fixtures.
6. **Admission before learning.** Freeze and validate the finished source/configuration manifest, 48 seed pairs, full evaluation workload, concurrency/order and full-wave resource worksheet. Resource rehearsal streams must be disjoint from the learning/evaluation roster. A time/step stop is incomplete even if a checkpoint exists; completion alone is not stage acceptance. No learning starts from an unpriced or unmeasured timing claim. Run these checks/rehearsals only within Ben's later implementation/execution instruction; none were run in this analysis-only turn.

**CONTRACT — protected material.** Do not edit `archive/` or any frozen source/checksum, existing `premonition/` model/loss code, existing scripts/tests, design files 00–11 or other prior design/review files, historical manifests/results, checkpoint bytes, datasets or certification splits. Do not add the residual, early-search loss, frontier target, normalization fix, pooled selectors, wire or ST as part of this work. Future generated manifests/panels/reports/checkpoints belong in newly named output directories, with no overwrite. No GPU/SSH/jobs/spending/messages are authorized by this document; no inspection of `~/.config/vastai/` is part of the work. Preserve concurrent user/agent changes. Only this design file is the current deliverable.

**For Ben.** The corrected experiment gives the model the original amount of early reading and teacher practice, then tests whether extra teacher practice helps more fresh runs learn ordinary one-hop and practised two-hop questions. It uses 48 matched pairs because 16 pairs could easily miss a useful improvement. Passing would let us investigate the separate relation problem without pretending it is already solved. The shorter run leaves less time to practise its own retrieval, so we will report that trade-off, keep the no-harm checks, and establish the complete time and cost before anything runs.

[08]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/08-pairsuite-adjudication.md
[09]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/09-reconciliation.md
[11]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/11-fix-review.md
[runs]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-20260919/control/runs
[rows]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-pairsuite-20260919/rows.jsonl
[train]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/train.py:81
[model]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:596
[softreg]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-softread-20260919/PREREGISTERED.md
