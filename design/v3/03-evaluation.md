# Evaluation, privileges, budgets and reliability

**Untested — specification.** This is the preregistration contract for future authorized work. It does not retroactively change historical gates. [The final resolution](07-final-resolution.md) incorporates completed probes and the pooled-first decision.

## Historical results and their limits

**Shown:** original gates are one-hop not stuck ≥384/512; READS ≥307/341 on `gold_read_K2_no_fetch.two_hop_trained_rel`; practised ≥171/341 and held-out ≥86/171 on `fixed_K4`. `all_three` is READS ∧ practised ∧ held-out, **not** a conjunction including one-hop. Record both all-three and all-four when needed, with distinct names.

**Shown:** [toy-results](../../reviews/astra-design-2026-09-19/toy-results.md) regenerates the original 30 rows. [arrivals-results](../../reviews/astra-design-2026-09-19/arrivals-results.md) adds the 160 key-pooling runs and probes without altering the old populations. New key-pooling all-three counts 17/40 and 33/40 are screening outcomes on a shared stream, not certification. Neither result has the causal pair suite below. Do not infer that an unevaluated checkpoint passed or failed a missing causal criterion.

## Track A: controlled twins

**Untested — specification.** Derive independent train/dev/test streams from a versioned seed manifest; never use Python's process-dependent hash. Each training seed pairs two recipe arms on exactly the same batches, world values, layout draws and evaluation panels; different seed pairs have independent streams. Assign initialization, data, evaluation, perturbation and sampling RNG substreams separately. Common-random-number comparisons reduce nuisance variation; they do not justify treating multiple questions from one world as independent training trials.

Freeze these paired-world families, each with 256 independent world pairs, balanced over entities/relations/values and with guaranteed different target answers when a relevant edit requires it:

| Intervention | Exactly changed | Required behavior |
|---|---|---|
| Direct value | Asked owner's requested value token | New value; first address unchanged |
| First-hop link | Asker's LINK object, with destination values made different | Follow new person and return that person's requested value |
| Second-hop value | Resolved person's requested attribute | New answer, same relevant path identities |
| Owner decoy | An irrelevant owner's value, even if it equals the answer | Answer and intended address unchanged |
| Relation decoy | Same owner's unasked relation | Answer unchanged |
| Reverse LINK | Add or replace an irrelevant reverse edge at equal length | Do not reverse subject/object |
| Evidence missing | Remove the needed assertion and replace by equal-length irrelevant text | NOT_TOLD; do not fabricate or copy a distractor |
| Restore / sham | Undo each edit; separately edit nonfactual filler | Restore exact deterministic outputs; sham preserves answer |

Correct twin answer labels from the generator's visible semantics. Source data must retain original and edited token digests and a diff certificate; a probe with stale labels cannot score answer correctness. Equal-length substitutions avoid truncation/position confounds. When removal changes length, compare with an equal-length irrelevant replacement and publish a separate raw-deletion result. Measure both-twins-correct, expected answer change, same-answer consistency, address identity, and causal-path accuracy. A model that always changes its answer fails joint correctness; one that always abstains fails answerable cells.

Keep original-layout and new-layout suites separate. Hold out complete grammatical arrangements. Do not conflate adding relations, inverse forms, distractors or a new tokenizer with a mechanism change. Same training/evaluation generator in both arms of each comparison. Preserve all easier tests when adding difficulty. Single-card multi-token generation and two-card composition get different cells; a copy-only head must not be admitted to the latter without an explicitly new composition mechanism.

At every loop log requested person and relation separately, chosen card/NULL/no-ASK, evidence coverage, head entropy, first/second fetch accuracy, answer-card selection, source/abstention and hard/soft disagreement. Token-pick accuracy is N/A for pooled selectors. Linear readout fits use a disjoint diagnostic calibration set and cannot influence model parameters, selection gates or test head assignment.

## Same-model factual-path interventions

Saved probe C already supplies a useful toy diagnostic. For future variants repeat normal, cards unavailable, question-only reader state, both, sham and exact restoration. Reset slots, decoder memory, recurrent state and caches; mask or hold constant score/margin/occupancy features and the cast-validity mask in the **full isolation** condition. Count each residual observable channel. Clear actual payload access, not merely the visible card list. Hash parameters and normalization statistics before/after evaluation.

A low ablated score establishes dependence under the intervention; it does not prove the removed component uniquely stores all facts. An off-distribution intervention can damage the use of surviving information. Report this alongside ordinary matched-training no-store controls when available, never in their place. No-store retraining is not one of the already completed probes.

Report measured best constant answer, empirical frequency sampling baseline `sum_v p(v)^2`, uniform baseline where applicable, and question-only learned control trained without story facts. For randomized twin pairs, report the appropriate joint chance under the actual without-replacement sampling rule. A best constant answer is an achievable reference, not an accuracy floor; a model can score below it. Estimate uncertainty by resampling world clusters within a seed and independent seed pairs across recipes. Never pool thousands of questions into a false training-reliability interval.

## Strict seed-level gate for a future Track A certificate

The candidate uses hard card retrieval and its declared deployed selector policy, fixed K=4/top-1 unless a different budget was registered **before** recipe selection. On a fresh seed-specific evaluation stream:

- One-hop, practised two-hop and held-out-relation two-hop: each ≥487/512 exact answers (≥95%). Gold-given READS is also ≥487/512 on its own fresh panel, a diagnostic ceiling rather than autonomous evidence.
- Relevant direct/link/second-hop pairs: each ≥244/256 both-twins-correct (≥95%). All are answered autonomously.
- Owner/relation/reverse-edge/filler controls: each ≥251/256 expected invariance (≥98%) **and** ≥244/256 both correct; invariance alone is insufficient.
- Never-told pairs: ≥244/256 correct abstention; answerable counterparts ≥244/256 correct non-abstaining answers.
- Original and held-out layout panels independently meet the answer/pair criteria if structural generalisation is in the certificate's claim. A fixed-layout certificate may omit the layout extension only if its title and claim explicitly say fixed layout.
- Zero invalid output/source-policy events, nonfinite failures or incomplete evaluation cells; exact restoration of every deterministic output. Gold-field noninterference, source manifest and budget checks pass.

This defines a considerably stronger target than 86/171. It is untested; no current arm has been shown to pass. A model can pass with disclosed evidence-supervised **training**; inference may not receive parsed relation positions, gold cards or hidden roles for a “learned lookup” certificate. Supplied-location arms get a separately titled privileged certificate.

## Track B: leak-controlled persistence and attribution

World cohorts have independent names, namespaces, values and action schedules. Use two replicas of each world differing in exactly one relevant fact while preserving introductions and observations elsewhere. Split exposure assignment by world/relation. Use the current/historical-belief/historical-truth/corrected/never-told/wrong-owner/contradicted/outdated/evicted cells in 02. Report before correction, immediately after observation without training, after repair, after eviction, and after unrelated learning.

Cards-only, weights-only and hybrid conditions are separate. Weights-only uses fresh question context, no store/index/resolver/guard features, frozen model state and no test-time updates; see the exact contract in 02. Authority override counts as card assistance. An abstention caused by a guard is not evidence of corrected weights. Randomized supplemental exposure, matched replay, delayed retention and twin values establish whether any weight gain is attributable to the practiced fact.

For each seed use 256 independent test worlds per active query family; resample whole worlds for uncertainty. The initial symbolic contract gate is zero wrong authority/version/identity outputs, zero stale releases and correct explicit unknown outcomes on every enumerated fixture plus a frozen 1,000-world generated panel. This is functional conformance, not a neural reliability certificate. The first learning pass mark is the registered paired improvement in 04, not a claim that the village milestone is finished. A future village certificate must separately freeze numerical thresholds for hybrid accuracy, closed-book accuracy, retention delay, correction failure rate and unknown-history behavior after these assays exist; do not import Track A's 77/80 result into it.

Truncation is a failing input-contract check if it removes requisite evidence. Record each arm's visible fact IDs after tokenization/windowing, not merely token count or matching question IDs. Fix wording for the next milestone; name substitution, wording structure, question type, answer type and prior exposure are independent columns. Do not reuse the legacy “fresh names” slice as a clean names test.

## Required privilege ledger

Use one row per training/evaluation mode; booleans alone are insufficient when a privilege is conditional.

| Arm/mode | Identity pointerization | Architecture/output masks | Parsed fields/locations | Gold-card/role targets | Gold teacher insertion | Gold-based weighting | Gold loop/schedule/competence inputs | Answer labels | Full-store soft access | Exact temporal resolver |
|---|---|---|---|---|---|---|---|---|---|---|
| Legacy toy train | Synthetic ENT IDs | Eligibility/copy vocabulary contract | Fixed grammar, no supplied relation head | ASK targets | Curriculum-dependent | Early answer | Teacher count | Yes | No | No |
| Relation shortcut | Same | Same | Supplied question relation location | As recipe | As recipe | As recipe | As recipe | Yes | As recipe | No |
| Pooled selector | Same | No role masks | No input role labels | Explicitly name chosen recipe | Explicit | Explicit | Explicit | Yes | Only if surrogate | No |
| Fully label-free retrieval | Same | Padding/causal eligibility only | None | None | None | None | None | Yes | Disclose companion | No |
| Parser-assisted village | Visible introductions/aliases | Address/version eligibility | Yes, grammar and timestamps | Parser-derived practice targets | N/A | None hidden | No hidden simulator truth | Yes | Explicit | Yes |
| Village weights-only eval | Visible question identities only | No store features | Question wording contract | None | None | None | None | Scoring only | No | Disabled |

“No evidence labels” requires the model/training decisions to be unchanged when gold-card fields and counts are replaced while ordinary answer labels stay fixed. This is a future implementation noninterference check. Evaluation may inspect gold fields for scoring only. Disclose gold-based development recipe selection even when it is absent from training inputs.

## Budget and reporting contract

Emit one JSON per intended seed/arm including failed/missing status; then generate one table from that manifest. Fields include source/model/tokenizer/generator hashes, seed substreams, hardware/numerics, active/allocated parameters, FLOPs by component, updates, real/padded/target tokens, soft candidate accesses, distinct facts, persistent/temporary/optimizer bytes, checkpoint/eval time, concurrency and end-to-end wall time. Budget includes all restarts and discarded pilot work. Record curves at common FLOP budgets, not just identically named step counts. Report failures in denominators and diagnose them separately.

For matched comparisons, hold model initial shared weights, data, supervision, optimizer and evaluator fixed. Both arms pay for shared scaffolding. If a change increases rows, decoding passes or access to all cards, report that and match total FLOPs; an equal-parameter contrast alone is inadequate. Report equal-exposure views secondarily when equal FLOPs changes exposures. Primary questions/metrics and directional/magnitude thresholds are fixed before looking at results.

## Certification and power

**Shown — exact binomial arithmetic:** 36/40 has a one-sided 95% lower confidence limit 0.78560. At 77/80 it is 0.90593. Passing 77/80 supports a >90% probability of passing the **specified per-seed gate**, under the fixed independent-seed population. It does not establish 95% reliability or universal reasoning.

At true seed-pass probability 0.95, the probability of achieving ≥77/80 is 0.42845; at 0.97, 0.78067; at 0.98, 0.92315. Thus the threshold is deliberately difficult for a merely 95%-reliable recipe. Freeze the recipe, generator, gate, budget, hardware/numerics and seed derivation, then run 80 **new** initialization/data/evaluation seeds. No development reuse, checkpoint choice on test results, dropped failures or reseeding. Stop as soon as the fourth failure makes success impossible; report a failed truncated attempt, not an ordinary 80-run confidence interval. A later revised recipe requires a new named attempt and entirely fresh seeds; publish every attempt. A positive certificate requires completion under its registered rules.

**Untested — comparison screens:** use 16 independent paired streams per learning contrast. A meaningful win is the prespecified ≥3 percentage-point primary improvement unless a row in 04 sets a larger margin. Require ≥12 wins/16, count ties/failures as nonwins, plus the stated no-harm gates. Under the null win probability ≤0.5, the exact one-sided size is 0.03841. Power is 0.79825 if the true meaningful-win probability is 0.8, and 0.92095 at 0.85; it is only 0.4499 at 0.7. These are assumptions about seedwise effects, not promises of power for an arbitrary mean effect. Six adaptive screens do not produce a familywise 95% causal claim; report each as screening and use fresh certification for the selected recipe. A null screen at this budget is not equivalence or impossibility.
