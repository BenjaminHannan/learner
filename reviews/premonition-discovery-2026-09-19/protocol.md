# Executable experiment specification

19 September 2026. **Proposed, not executed.** Implementing or running this protocol is outside this research session. The main recommendation is D0–D2, a frozen-checkpoint diagnostic. T is a conditional writer/training study; C is a later transfer/continued-learning direction. Do not silently combine their results.

## D0. Development feasibility, before confirmation exists

Use a new harness and output directory, importing the archived source through the existing hash-checked bootstrap. Load all five baseline and five relation-shortcut 12k checkpoints only in the future experiment. Verify each checkpoint hash against its run JSON and record the actual imported modules. No checkpoint access was performed for this review.

On 32 **development-only** worlds:

1. Establish no-op parity with `own_fixed(..., loops=4)`, including actual output tokens, ASK decisions, fetched indices and decoder memory. Preserve the bypass decoder, top-1 choice, fetched-card exclusion and NULL. HALT is ignored, as in the historical primary policy. Four loops allow at most three fetches.
2. Validate visible field extraction for every real card: subject at line offset 1, relation at 2, object at 3. Reject malformed lines; never interpret fillers as facts. Extract the question subject from its visible layout. These are disclosed parsing hints, not simulator evidence labels.
3. Check that changing `answer`, `gold_lines`, intervention labels or pair IDs cannot change a prediction. The evaluator owns these labels in a separate object. Check that the Q and QD first requests are bit-identical.
4. Check a two-edge fixture with different endpoint values, wrong source, NULL, and a non-link first card. This validates semantics, not model quality. Measure memory and time for one checkpoint and extrapolate the full schedule.
5. Record first-link selection and correct-first-link rates under Q, separately for each seed. Do not select checkpoints based on them. These 32 development worlds estimate feasibility only; adequate opportunity for the scientific decision is defined on the entire frozen panel below.

No parameter updates or fitted probes. One implementation repair is permitted on these development worlds. After parity and label-separation checks, freeze source hashes, generator, seeds, conditions and analysis. A second implementation failure ends this version of the experiment.

## D1. Frozen causal comparison

**Question:** given the same first retrieved card, does using its visible destination as the next source fix answers that the latent workspace gets wrong?

Use all five shortcut seeds 0–4 as the prespecified main panel, including stuck seeds. Run the same interventions on all five long baseline seeds as a separately reported comparison. These are five existing training replications per recipe, not ten independent runs of one architecture. Their historical validation performance influenced this proposal; new worlds cannot make the training seeds an untouched reliability sample.

### Interventions

All conditions build the same field view and carry the same ordinary model state. Only the stated eligibility mask changes. Do not modify scores of surviving cards, temperature, age bias, ASK decisions, number of loops, decoder, or weights.

| Code | Exact operation |
|---|---|
| U | Native `fixed_K4` retrieval. |
| Q | At the first request only, permit real fact cards whose parsed subject equals the question subject; preserve NULL. Subsequent requests are native. |
| D | Only on questions containing a visible LINK operator, if the first actually fetched card is a link with a valid entity object, constrain the **second request only** to that object as subject. Otherwise do nothing. Never replace a wrong first card or consult gold. This task-type restriction uses question tokens, not a simulator hop label. |
| QD | Q at request one, followed by D at request two. |
| QW | Q, then the same second-source gate using a different in-world entity instead of the selected destination. Choose it by a fixed hash of the neutral world index, excluding the destination; do not use answers. |
| N | Execute all instrumentation but apply an all-eligible extra mask. Must match U exactly. |

If the first selection is NULL, a filler, an attribute card, or no card because ASK is off, D is inactive and that example remains in the denominator. A wrong link carries its wrong object. Preserve eligibility of NULL when no real card matches. Record both attempted and effective interventions, and all predictions.

**Primary contrast: QD − Q.** The first card is identical by construction. QW tests whether an arbitrary restrictive mask creates the same benefit. U vs Q measures an upstream address problem; U vs D estimates the intervention's ordinary, ungated usefulness. These are secondary contrasts and cannot replace the primary one after results arrive.

This intervention tests whether explicit *input-derived source restriction* can improve use of the chosen intermediate. It cannot distinguish a deficient writer key from deficient query geometry at that boundary, prove that information was absent, or establish that a newly trained model learns faster. Do not describe it as such.

### Data and task family

**Primary cell:** 512 fresh, independent worlds, each with six people, three attributes, 16 uniformly assigned attribute values, shuffled ENT0–15 assignments and fact order, the current 128-token gap, and one two-hop query using the held-out relation. Create a second version changing the queried person's friend to another valid person with a **different target value**, while keeping unrelated facts fixed. Score whether **both answers are correct**. There are 512 independent world-pair clusters and 1,024 predictions per checkpoint/condition.

Generate pairs by a recorded rejection sampler; record rejection counts and recheck the endpoint-value distribution. Do not let pair IDs, edit type, gold evidence or target-derived flags enter inputs. This is a fresh diagnostic from the same family, not a new reasoning domain.

**Secondary family:** 128 independent paired worlds per cell, varying one burden at a time:

- N=12 rather than 6 people, at two hops: more competing subjects within the 16-ID capacity.
- Three rather than two fact lookups, N=6: more binding uses. Use a no-repeat path, so fetched-card exclusion cannot make the task impossible. Four loops still permit three fetches. This is untrained depth for these checkpoints.
- Gap=512 rather than 128, with the same two-hop facts: reader-state leakage/delay.
- One-hop changed-attribute pairs, N=6: the handoff intervention should be inactive.

For depth three, construct question `ENT LINK LINK REL`; keep final relation positions consistent with the shortcut's disclosed parse. The diagnostic intervenes only at the first handoff, so it does not claim to implement a general multistep executor. Report the actual number of handoffs and eligible first-link selections.

On every generated example run a deterministic tuple interpreter. It must achieve **100%**, or the dataset is invalid. Also report question-blind/modal-value, relation-only, and direct-question-subject answer strategies. Their measured ceilings, especially on changed-link pairs, must sit below the proposed success threshold. An exact interpreter solves this templated task; success does not demonstrate discovering an unknown reasoning algorithm.

Freeze generator and analysis source digests before producing confirmation seeds. The future harness should generate and seal a seed manifest; seeds must not be chosen for favorable model behavior. Record the manifest hash before loading models. Check exact-world and exact-input overlap against all locally saved train/validation/test fingerprints. The old 4,000-batch training digest covers only part of the long stream: reconstruct the model-free world fingerprints for the full consumed prefix (12,251 batches plus any separately consumed calibration batches, as determined from the trainer), or explicitly report incomplete overlap coverage and do not claim zero overlap. No replay or counterfactual training may introduce held-out multihop relation questions.

### Primary outcome and thresholds

Let `B_s(X)` be the fraction of primary pairs for which both answers are correct for seed s under condition X. Define

`Delta = mean_s [B_s(QD) - B_s(Q)]`, over the five shortcut seeds, with equal seed weights.

Advance the **local handoff-use hypothesis**, not an efficiency or novelty claim, only when all hold:

1. **Primary effect:** Delta ≥ **0.15**, and its one-sided 99% paired world-cluster lower bound exceeds **0.05**, conditional on this fixed panel of models.
2. At least **two of five** seeds improve by ≥0.15, and no seed loses more than 0.03. Requiring four positive gains would be inappropriate when several comparator seeds may already be near ceiling.
3. QD achieves pair accuracy ≥**0.80 in at least four of five** seeds. This is more demanding than obtaining a lucky correct answer to one member of a pair.
4. The QW wrong-destination control scores at least **0.15 below QD on average**. N equals U on every prediction and trace. One-hop QD−Q is exactly zero by construction; one-hop Q−U must not lose more than 0.03 per seed.
5. Fresh confirmation passes, with adequate handoff opportunity as defined below. Store isolation is adjudicated separately; it is required for a store-only architectural claim, not for the narrower score-mask causal finding.

The 15-point effect is a minimum useful diagnostic improvement, not an estimated effect or a power calculation. It prevents promoting a mechanism based on a handful of corrected cases amid very large training-seed variation. The 80% and four-of-five requirements demand broadly usable behavior; they are not a bound on rare failures.

Use the same sampled world clusters across conditions and seeds, with 10,000 bootstrap resamples. Resample worlds, retaining paired versions and the full vector of seed outcomes. Report every seed separately, the mean and range. A separate bootstrap over training seeds may be descriptive, but five exposed seeds cannot support precise population reliability claims. Never treat 5×1,024 answers as independent training replications.

**Opportunity audit, without changing denominators:** for each seed report (a) how often Q selects the correct first link, (b) subsequent error rates, (c) the fraction of Q-incorrect pairs for which every currently wrong member is D-eligible, and (d) the fraction for which those wrong members also have the correct first link. Express (c) and (d) as fractions of **all** primary pairs. Quantity (c) bounds the possible positive pair-accuracy gain from this intervention; (d) bounds the available correct-bridge rescue opportunity. The evaluator can use gold evidence for this audit, never inference. For a negative result to reject the correct-bridge handoff account, require mean (d) ≥0.15 and (d) ≥0.15 in at least two seeds. Otherwise report low available opportunity, while still reporting the unconditional effect. Apply this audit to D1 and confirmation; do not infer adequate coverage from 32 development worlds or from any-link counts alone.

**No useful handoff effect:** with adequate coverage, Delta <0.05 and the conditional one-sided 99% upper bound <0.10. Reject this intervention at this boundary. Values between the rejection and advancement rules are inconclusive; do not pick another metric. Technical failures are invalid runs, not scores of zero; preserve them and their costs. Low-performing valid checkpoints stay in all summaries.

### Factual-store and causal checks

For a real input intervention, replace the first link's destination and verify the correct changed answer, using the whole generated pair. Change a tempting unrelated link as a negative input control; the correct answer must remain unchanged. These corroborate the mask intervention, which creates states the original model was not trained to encounter.

Wiping only `CardStore.valid` is insufficient. In a full erasure condition, clear cards, tuple/index views, raw diary access, cached reader states, contextual question states computed from the diary, bound slots, fetched/pre-Think rows, `_reading`, copied handles, provenance and any derived-result cache. Rebuild a question-only state. Preserve only question-visible names and nonfactual spelling machinery. Do not rebuild cards from retained `batch.tokens` or permit a raw-field helper to reread the diary.

On fresh random facts, factual answer accuracy after this wipe must be ≤**11.25%** (1/16 + five percentage points), and the one-sided world-cluster upper bound must be ≤0.15. This is a bounded accessible-fact check, not proof of universal deletion or weight unlearning. If the model has an unknown answer class, report it separately; do not demand an untrained output token.

Restoring only the designated store into a fresh question state must recover at least **90% of unwiped accuracy**. Otherwise the claimed store-only architecture depends materially on another factual channel, or the reconstruction is defective. That blocks architectural promotion even if the narrower score-mask result is informative.

### Exact-code control, without a training campaign

For each selected entity, compare direct ID matching with normalized tied matching using the **same** input entity and relation eligibility. On distinct one-hot or orthonormal codes they must agree. Count ties and precision issues; do not turn an avoidable numerical defect into an architectural victory.

Synthetic soft distributions p, with contamination fractions {0, .1, .25, .4} spread over {1, 3, 7, 15} other entities, can compare p with `EᵀEp`. This diagnoses a potential soft interface only. The existing hard-card model does not naturally transport this p, so these results cannot explain its failure without an independently observed matching internal state. Do not fit a decoder and call its distribution the model's actual transport mechanism.

## D2. Fresh confirmation and decisions

Before D1 is scored, seal a second independent set of 512 primary world pairs and freeze its analysis. Use it only if D1 meets the advancement rule. Run Q, QD, QW and N/U parity on all five shortcut seeds; require the **same** effect, quality and non-regression thresholds. Failure to replicate retracts the promotion; it does not authorize tuning against this set.

If an independent evaluator cannot hold seeds, document that limitation and use a timestamped/hash-recorded manifest. Data called “test” in old milestone-3 reports have already influenced decisions and cannot be reused as confirmation.

| Result | Interpretation and next action |
|---|---|
| D1+D2 pass, controls support handoff | A fixed identity interface is a useful local intervention. Use the simplest equivalent known method. A new training comparison is still needed for learnability/efficiency claims. |
| Efficacy but QW/no-op/input edits contradict the mechanism | Reject the causal explanation. Audit masking, metadata, stochasticity and answer path. |
| Local efficacy confirmed, but full erasure/restoration fails | Preserve the local causal finding. Reject the store-isolation claim and fix the factual interface before architectural promotion. |
| Q helps; QD adds little | Writer/query alignment is the actionable target. Run the bounded T study, if separately undertaken. |
| No efficacy with valid implementation/coverage | Reject this implementation's useful effect here. Keep alternative tasks and architecture families open. |
| Parity/label-separation/opportunity fails, or budget exhausted | Invalid or inconclusive for the affected claim. One development repair maximum; confirmation stays untouched. |

## Resources for the recommended diagnostic

No new trainable parameters; all parameters frozen. The existing models contain **79,748 / 80,293 parameters by static calculation**. Verify actual loaded totals before executing. Record checkpoint bytes separately from parameter bytes and per-world stores. At fp32 the shortcut's weights alone are 321,172 bytes; optimizer state, Python/runtime overhead and activations are additional. The ordinary key/value payload is 48 fp32 values = 192 bytes per card before metadata. Three int64 tuple fields add 24 bytes per card; a hard handle requires one integer. These are payload calculations, not peak-memory measurements.

The proposed primary/secondary comparisons and confirmation run on the laptop CPU. Measure peak RSS and per-question latency, including store construction, field extraction, masking and decode. Report amortization over 1/10/100 questions only if actually measured. Do not infer inference time from training throughput.

| Complete diagnostic envelope | Hard planning allowance |
|---|---:|
| Development, parity, fixture checks and timing calibration | 10 CPU minutes |
| Main panel, primary and secondary cells, first-result analysis | 35 CPU minutes |
| Wipe, restoration and causal checks | 10 CPU minutes |
| Fresh confirmation if triggered | 20 CPU minutes |
| Failed loads, one bounded development repair, I/O reserve | 15 CPU minutes |
| **Total, including failed attempts** | **90 CPU minutes; zero GPU time; $0 cloud** |

These are caps, not measured forecasts. Calibrate before the full panel. If it cannot fit, reduce secondary cells before freezing; never drop required seeds, primary controls or confirmation to declare success. Failed calibration ends the proposed envelope rather than silently expanding it.

## T. Conditional established repair study

Only if the upstream explanation remains the useful lead, the clean training follow-up is a **2×2** comparison, all on the long relation-shortcut baseline: shared versus separate key pooling; original early gold phase versus early retrieval supervision. This distinguishes separating representations from changing their learning schedule, and allows the combination to matter.

Use `scripts/premonition_key_pool.py` unchanged unless a genuine implementation defect is established. For the early-retrieval factor, add a first-request loss on **one-hop questions only** during the initial gold phase: create an empty episode, use the existing gold card as the retrieval target, and apply the existing ASK BCE + marginal set loss with weight 0.5. Do not use the already-preloaded episode, whose missing-evidence target is empty. Do not supervise held-out compositions or turn unordered two-hop evidence into an ordered program.

All four arms compute/log the same auxiliary diagnostic; only its gradient weight changes. They receive the same examples, field hints, existing answer/evidence labels and RNG stream. Count the extra forward/backward work and repeated presentations. Use the original baseline's calibrated schedule and stopping reference for every arm, rather than each arm's separate FLOP fit; report actual updates and auxiliary FLOPs. This is initially an equal-example causal comparison, **not** an equal-compute efficiency result.

Five fresh matched seeds **100–104** per cell; all 20 runs reported. Keep the long recipe's requested 12k horizon and phase fractions .10/.1833/.2667. Match shared tensors explicitly and use a separate RNG for added scorer construction. Development uses seeds 200–201 only, at most four 20-minute trials total, with common choices across arms; no tuning on 100–104. Freeze the resulting configuration before any main run.

Primary metric: mean held-out two-hop **both-correct pair accuracy** on the D-style fresh world pairs, using native `fixed_K4`. Primary contrast: separate minus shared pooling **within the original curriculum**, fixed before scoring. Advancement: ≥0.15 mean improvement; at least two seed improvements ≥0.15; no seed regression >0.03; ≥0.80 pair accuracy and ≥0.90 practiced/one-hop accuracy together in four of five runs. The early-objective main effect and interaction are secondary explanations, not replacement primary outcomes. Repeat the fixed pass criteria on separately frozen fresh confirmation worlds without retraining.

Record every failed run; do not restart poor-learning runs. Permit at most one technical rerun per arm, same seed/data, with cause and both costs retained. A user-facing “usable model cost” includes all main seeds and development; do not report just the successful checkpoint's runtime. This study cannot establish a rare-failure rate: even 5/5 successes leaves a one-sided 95% failure-probability upper bound about 45%; approximately 59 independent successes with no failures would be needed to put that bound below 5%. Such a reliability campaign is not included or recommended yet.

**Whole T envelope:** 20 main runs × ≤60 minutes, ≤80 minutes development, ≤20 minutes calibration, ≤120 minutes evaluation/confirmation, ≤240 minutes technical-failure reserve; round upward to a **30 GPU-hour maximum**, plus ≤2 CPU hours of preprocessing/analysis. Use the owned GPU serially for interpretable timing. This is an upper bound, not a runtime prediction. Saved 38–39 minute per-process runs were concurrent and do not establish isolated throughput. If calibration predicts >60 minutes per main run, stop and revise before freezing. Zero cloud spend planned. No current funds are assumed available.

## C. Second-stage transfer and continued learning

Do this only after the diagnostic and ordinary repairs establish a usable factual interface. The scientific question then changes: can a shared controller acquire a **data-dependent procedure** more easily, beyond the template's supplied relation sequence?

Use executable symbol records on a linked list: `next(node,node)` and explicit `marked(node,true/false)`. Learn “walk until the first marked node,” returning unknown on missing evidence and a distinct cycle/limit outcome when appropriate. Use a vocabulary and layout different from the village; train lengths 2–4, test 5–8, with reordered records and fresh ID assignments. A mere village renaming would not be this transfer test. Do not conditionally sample only easy graphs; freeze marks, length and cycle frequencies. An exact interpreter is the ceiling.

Use **one shared Think controller with an NPI-style call/argument interface in every arm**, with the same factual executor, learned parser inputs and primitives. The three arms below vary learning policy only; they do not compare controller architectures or claim superiority to NPI. A static predicted relation list is only a diagnostic because it lacks adaptive termination. For this feasible first acquisition study, give identical simulator execution traces to all arms, count every labeled step, and disclose the richer supervision. No large model supplies programs; answer-only program learning is a separate harder question.

For a minimal A→B test, A teaches lookup, equality, two-hop paths and a simple conditional; B teaches the new iterative procedure. Compare (i) frozen old procedures with restricted old call scopes, (ii) the same total parameter/storage budget with shared fine-tuning and **25% fresh simulator replay**, and (iii) an explicitly counted joint A+B reference. All use five matched seeds, the same B examples, total example presentations and maximum execution steps. The replay baseline receives fresh A examples within that total; count simulator calls and give the frozen arm an equal opportunity to use those A presentations for any allowed new parameters. Report explicit task-ID dispatch and learned dispatch separately; router/retrieval failures count as forgetting.

Prespecify B quality ≥90%, A loss ≤2 percentage points, and ≥2× fewer B examples to the target than the matched replay baseline as the **acquisition** bet. If only retention improves, report preservation rather than faster learning. Freeze a separate audit set never used by any sleep/rollback acceptance rule. A new base-relation-token condition and a new-fact-only condition distinguish schema learning from procedural learning; fact updates use no gradient steps. Report all later practice, so “told once” never hides replay or self-generated examples.

Reserve at most **24 additional GPU hours** for this later 3×5 comparison: 15 main runs × ≤1 hour, four development trials × ≤20 minutes, ≤20 minutes calibration, ≤2 hours evaluation/confirmation, and ≤4 hours technical-failure reserve, rounded upward. Add ≤2 CPU hours for preprocessing/analysis. That is a separate, conditional planning envelope, not a promise the new task fits. No tenfold efficiency or general continual-learning claim follows from D or T. The complete staged maximum is therefore **54 owned-GPU hours + 5.5 CPU hours**, with **$0 cloud** planned, if every stage is pursued; the recommended next action is only the 90-minute CPU diagnostic.
