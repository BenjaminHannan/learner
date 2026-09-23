# Experiment 20 draft: recent-activity inhibition during intact rehearsal

Astra · 2026-09-20 · Track A only.

**DRAFT — no experiment authorized or run by this document.** This session creates a research note and this draft only. Fable can later implement it with Opus sub-agents. Implementation, predictions and a resolved launch manifest must be frozen before registered execution. Do not modify any hash-frozen experiment-18/19 scripts, checkpoints or panels.

**Question in plain words:** When practice becomes repetitive, does briefly quieting the channels used most recently preserve other skills better than ordinary inhibition?

This is a retention experiment inspired by BARR sleep events. It tests neither original thought nor a cure for the three-call STOP bug. The AI proposal predates us; see the [research note](20-undercovered-brain-mechanisms.md), [Karaba et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC11428313/), and [Rudroff et al.](https://doi.org/10.3390/brainsci14111111). Activity-dependent inhibition already has task-learning precedents, especially [Selfless Sequential Learning](https://arxiv.org/abs/1806.05421) and [SCoMMER](https://arxiv.org/abs/2301.05058). Our cumulative control is a controlled analogue, not a reproduction of either full system.

## 0. Order and scope

Finish experiment 19 under its current registration. Investigate the stopping failure in its own one-change experiment before making this a priority. This draft still specifies the **original frozen v4 reg+ctx** as its common base and measures only one-to-three-call behavior. It does not silently incorporate a future STOP repair. If the base changes, create and hash a revised preregistration before any 20 training.

One intervention: **which existing hidden channels receive temporary attenuation during alternate offline updates**. Every arm receives the same intact rehearsal records in the same order. No generated questions, long practice, macro-actions, new reward, memory-index module, unit reset, auxiliary critic, question-length hint or forced action.

## 1. Definitions and registered hypothesis

Use **c = total primitive lookup calls, including the final attribute lookup**. Existing scripts call this `hops`; LINK traversals are c−1. Worlds use 16 possible entity IDs, attribute relations 8/9/10 and LINK=11. `ANSWER=5` is the question delimiter; the transformer emits `END=68`.

**Hypothesis:** following one ordinary rehearsal update, attenuating the quarter of readout channels most active in that update will preserve short held-out compositional behavior during biased rehearsal better than equal-update rehearsal and equally costly untargeted, long-history-targeted or uniform attenuation.

The primary question types are c=2/3 ending in relation 10. They are never trained, but must already be solved before offline practice for D's outcome to be called retention. A treatment that merely adds randomness or shrinkage must lose its special-mechanism claim if the corresponding controls match it.

These are **engineering pass marks**, not a registered population-level significance test. Three seeds are a screen, not a reliability certificate.

## 2. Fixed learners and six fresh awake runs

### Dispatcher D

V4 reg+ctx, width 32, **24,035 trained parameters**, with both learned replacements active. No supplied recency flag, relative offsets, remaining-length counter or gold STOP. Keep the raw-question/self-generated-transcript interface; the controller does not read story rows directly. Preserve invalid-action semantics and full-vocabulary operator argmax.

Use one common frozen canonical operator:

`/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_seed-1/final.pt`

Reported SHA-256: `e7e5b6f3a6bfecf3890538bd0a14af7f5189b1565329e5cf411b52dd4d4dfbec`. Verify actual bytes in the implementation freeze; a mismatch blocks launch. Do not choose among operators using any experiment-20 scores. Its historical training used gold intermediate people.

### Plain transformer T

Corrected baseline-v2 **I1-H1**: width 48, three layers, four heads, feedforward width 208, 69-token vocabulary, tied embeddings, steps output, supporting-line loss 0.5, line positions, learned position tables and original target-loss mask. Operator-style Linear rescaling is 1/sqrt(3×fan-in). Freeze exact instantiated parameter count and initialization code. Check maximum input/output positions against every registered grammar before any training; no clipping/clamping.

T is a plain end-to-end transformer baseline; the proposed gain hook adds no trainable parameters to either architecture.

### Seeds, data, schedules

Use paired fresh seeds **2000, 2001, 2002** for each architecture: six awake runs. Initialize once per architecture/seed; all later arms clone its final checkpoint. No historical checkpoint as the causal control.

Awake practice: **6,000 updates**, 16 six-person worlds × four questions/update. Generate the same raw world/question stream for D and T for each seed. Sample c uniformly from 1..3; use r8/9 uniformly at c≥2 and r8/9/10 uniformly at c=1. Preserve the existing fact/filler grammar. Ban every composite r10 question from every training/label channel. Primitive r10 facts and c1 queries remain allowed.

D: RLOO K=16 episodes/question; scalar reward = final-answer correctness −0.01×executed calls. AdamW lr 0.003, betas (0.9,0.99), epsilon 1e-8, weight decay 0.01, warmup 100 updates, clip norm 1.0; entropy coefficient linearly 0.2→0.02 over the block.

T: AdamW lr 0.001, same betas/epsilon, weight decay 0.1, warmup 100, final-third decay to 0.0001, clip norm 1.0. Preserve baseline step and supporting-line targets and loss normalization. Freeze exact schedule endpoint conventions in source/config before launch; no mutable defaults.

All D training has cap **8** from update one, with the same eight-step masked allocated unroll. A cap hit is a failure, never a STOP target or input. Native D evaluation cap is 16. T has output capacity 12. The common training cap differs from historical v4; fit must be established afresh.

No inhibition during awake practice. All arms have the same instrumentation path with unity gain during that phase.

**Fairness boundary:** raw data are matched across D/T, but their supervision and historical training are not. D uses scalar RLOO rewards and a pretrained operator; T uses intermediate and line labels. Within-architecture arm contrasts isolate the intervention. Do not call D/T total compute, supervision, or prior knowledge equal.

## 3. Intact memory and a fixed biased rehearsal stream

Save the first **1,024 semantically distinct awake worlds** in encounter order and the four actual questions presented with each: 4,096 intact world/question records. World identity ignores row order and filler. Skip duplicate-world admission using only the signature, never performance, and retain original bytes/provenance. Memory must be full by update 6,000; otherwise report a prerequisite failure.

Partition those actual records into the seven practiced type buckets:

`(1,8), (1,9), (1,10), (2,8), (2,9), (3,8), (3,9)`.

An empty bucket is a prerequisite failure; do not manufacture a replacement record.

Each offline minibatch has **64 intact records**, sampled with replacement:

- 58 records from bucket (1,9);
- one record from each of the other six buckets;
- shuffle all 64 with a fixed independently named RNG.

Thus 58/64 of rehearsal targets one simple type. This exact bias is an experimental stressor supplied by us, **not a claim about natural sleep**. It must not be strengthened or changed after observing forgetting. Unlike awake grouping, the offline batch consists of 64 independently sampled stored records; it may contain up to 64 different worlds. Use the same padded shape in every arm.

The full 2,000-update offline index stream is generated and hashed before any offline run. D/T and all corresponding arms receive identical original story/question bytes and order. No new question, relabeling, recombination, success filtering, uncertain-item mining or curriculum. The existing interpreter supplies D rewards and T labels from those stored facts; it never supplies runtime actions or modifies operator outputs.

## 4. Five arms and exactly one gain intervention

Clone each qualifying final awake checkpoint into five arms:

| Arm | Even offline update gain | Purpose |
| --- | --- | --- |
| **B: recent** | 0.5 on the top quarter by activity from the preceding odd update; 1 elsewhere | Proposed recent targeting |
| U: unity | 1 everywhere | Matched-update intact rehearsal |
| S: shuffled | Randomly permute B-style channel ranks, then apply 0.5 to one quarter | Same sparsity/gain histogram, unrelated target channels |
| C: cumulative | 0.5 on top quarter by cumulative activity from all preceding odd updates | Controls long-history activity targeting |
| A: uniform | 0.875 on every channel | Same mean gain as quarter-at-0.5 suppression |

**Odd updates always have gain 1 in every arm.** Offline updates are numbered 1..2,000; the first suppressed update is 2. The gain is constant across a whole optimizer update, every sampled trajectory, decision and target position. It cannot vary with a call's ordinal position, relation or outcome.

All arms compute recent and cumulative statistics, stable rankings, random permutations and all candidate gain vectors, using the same shapes. The arm flag selects only the multiplier used in the forward path. Randomness uses a dedicated mask RNG in every arm, including U/C/A, so instrumentation does not advance policy/data RNGs differently. Ranks are determined within each run from that run's own activations.

### Exact D hook

The existing dispatcher uses a pointer query `q = state + register` before lookup, and raw updated `state` for STOP after the native call.

- Pass `g*q` to both subject and operation pointer heads.
- Leave candidate keys and the selected subject key supplied to the operation head unchanged.
- Pass `g*state_after_call` to the STOP head.
- Do not overwrite stored state/register with gated values. Keep GRU transitions, transcript embeddings, question encoder, register writes, operator inputs/outputs and all other equations unchanged.

For each **odd** update, collect one raw q vector and one raw post-call STOP-state vector per live executed decision across the K=16 rollouts. Let e[j] be their combined elementwise mean absolute value. Include only decisions actually executed while live; exclude padded dead steps. Detach before aggregation/ranking. If there are no live vectors, set e=0 and flag the anomaly; do not invent activity from the gold path.

The top 8 of 32 e entries define recent targeting for the next even update. Maintain an equal-update cumulative mean of odd-update e vectors for C, initialized to zero at the offline boundary. Ties use ascending channel index after descending activity. C's first pulse can equal B's; later pulses test the time horizon.

Collecting q and STOP inputs is an explicit modeling choice, not a claim that those are hippocampal cells. Do not add separate masks per head or layer.

### Exact T hook

Collect raw final decoder hidden vectors **after the existing final normalization, if present, immediately before tied vocabulary projection**, restricted to nonpadding supervised output-token positions under the baseline loss mask. Aggregate mean absolute activity across those vectors on odd updates only. Do not include question/story tokens merely because their hidden states exist.

Use the same ranking rule with **12 of 48** channels. Multiply by g before vocabulary logits on even updates. Supporting-line attention/loss is unchanged. No per-layer gate, new normalization, inverted-dropout rescaling or additional penalty.

### State and evaluation

Added trainable parameters: **zero**. Recent activity requires width floats; cumulative sums/counts and mask bookkeeping are common instrumentation, not extra learned capacity. Save them in resumable checkpoints. Clear them at the awake/offline boundary.

All evaluations use g=1, no trace update, native greedy action/decoding and no test-time adaptation. Evaluation must not alter subsequent training RNG or optimizer state. Record both masks used during training and the unity setting at score time.

## 5. Offline optimization and resource matching

Each arm receives **2,000 optimizer updates**, batch 64 intact records, final-update checkpoint only. Reset optimizer state at the offline boundary in **every** arm. Repeat the same optimizer settings with schedules defined over 2,000 updates; D retains K=16 and entropy 0.2→0.02. Total per solver is 8,000 updates.

This is at most **six awake runs plus 30 offline continuations** across two architectures and three seeds. Do not launch all at once.

All D arms allocate the same eight-step padded unroll, question/story widths and K. Compute the frozen operator's complete permissible lookup table per stored world with identical batching/caching rules in all arms, or use identical dense operator evaluation work; choose and freeze the single common implementation before launch. Do not use sparse inference only in a winning arm. Report cache construction and all operator work.

All T arms allocate identical sequence lengths, padding, output capacity and losses. Useful active calls can change when policies change, even with equal allocation. Report trained parameters, stored bytes, updates, examples, supervised tokens, allocated and useful FLOPs, active calls, wall time and preprocessing separately. Do not “match compute” by giving a fast control more optimizer updates.

## 6. Development panels and awake gates

New development panels contain **64 independent units per cell**. A pair is one unit. Primary chains have distinct visited people; retain the existing filler/distractor grammar. Balance answers as evenly as the actual value vocabulary permits through a fixed interpreter-only generation rule. No model-confidence filtering.

| Family | Cells | Awake requirement | Offline requirement for B |
| --- | --- | --- | --- |
| F: ordinary fit | c1 × r8/9/10; c2/3 × r8/9, six-person worlds: **7 cells** | D and T: ≥61/64 answers and strict traces in each cell/seed | ≥61/64 answers and strict traces |
| H: short held-out endings | c2/3, r10 × people 6/16: **4 cells** | D: ≥61/64 answers and strict traces in each cell/seed; T: measured without a qualification gate | ≥58/64 answers and strict traces; strict paired-gain gates below |
| E: edit guards | c3, r10, 16 people: changed LINK, changed terminal value, irrelevant-fact edit: **3 pair cells** | No fit selection using these cells | ≥58/64 strict pair successes |

Total: **14 cells**. Score all arms at the registered endpoints. Before offline training, score F and H only at the final awake checkpoint. Do not use intermediate checkpoint scores for selection.

For D, failure of F or H in **any registered seed/cell** means the retention prerequisite failed. Do not replace the seed or continue with only successful seeds and call it the registered result. Report the failed prerequisite. T requires F across all seeds; if that fails, report incomplete baseline comparison. A qualifying architecture may finish its own block, but the cross-architecture comparison is incomplete until both qualify under a frozen design.

T's H scores may start low, as historically observed. Its final B-control contrasts are still worth reporting, but an increase from a low starting score is acquisition/transfer, not preservation. No D claim requires the transformer to fail.

### Strict trace definitions

D: correct subject, semantic operation and returned token for every native lookup, in the requested order, then STOP immediately after the terminal attribute lookup. Duplicate question-position pointers with identical semantic operation are not errors by themselves. Wrong paths with a lucky final answer fail strict scoring. A cap hit always fails.

T: exact emitted intermediate-person sequence, terminal answer and END, no extras. This observable sequence is not identical internal evidence to D's operation log; label that difference.

For edit pairs, both sides must satisfy strict scoring. Relevant LINK/value edits must really change the interpreter's answer. Irrelevant edits must preserve it. Generate edits with fixed interpreter-only rules, never by choosing a pair the model happens to fail. The checker is an evaluator only.

## 7. Exact primary decision

D-B passes development only if **every condition holds in every cell and every seed**:

1. Integrity checks and all D awake F/H prerequisites pass.
2. In each of the four H cells, B has ≥58/64 correct final answers and ≥58/64 strict successes.
3. In each H cell, strict successes(B) − strict successes(U) **≥13**.
4. In each H cell, strict successes(B) − strict successes(control) **≥7 separately for S, C and A**.
5. Every F cell retains ≥61/64 answers and strict traces; every E cell has ≥58/64 strict pair successes.

All arms use the same cell instances. Report paired discordances: B-only successes, control-only successes, ties; the registered gain is wins minus losses. Answer-only gains are secondary.

Apply the same final H/E/F marks and paired-gain rules to T as an independently reported transformer intervention test, conditional on its F prerequisite. Label H outcomes according to their measured starting competence. T neither rescues nor invalidates D's within-architecture pass.

Report native per-seed, per-cell integer counts for all arms, with per-cell Wilson intervals and paired discordance counts. Include premature STOP, late STOP, cap hits, invalid calls, operator errors and answer-with-wrong-path cases. Do not pool seeds or average cells to claim success.

## 8. Untouched confirmation and leakage exclusions

Freeze these namespaces and the exact hash-to-seed implementation in the launch manifest:

```text
astra-inhibition20-awake-v1:<seed>:<update>:<world-slot>
astra-inhibition20-memory-v1:<seed>
astra-inhibition20-offline-order-v1:<seed>:<update>
astra-inhibition20-mask-v1:<seed>:<update>
astra-inhibition20-policy-v1:<seed>:<stage>:<update>
astra-inhibition20-dev-v1:<cell>:<unit>:<attempt>
astra-inhibition20-confirm-v1:<cell>:<unit>:<attempt>
```

Separate model, data, policy, mask and evaluation RNGs. Use identical base policy random streams across arms, acknowledging that changed probabilities yield changed trajectories. Freeze integer widths and library versions.

Before training, hash dev bytes, labels and all available legacy exclusion signatures. Exclude historical evaluation/confirmation worlds from new training and memory. Record raw-tensor hashes, canonical fact-set-plus-question signatures and world-only signatures; canonicalization ignores row order and filler. Apply exclusions to every side of every edit pair and across dev/confirmation. Training collisions abort as integrity failures rather than silently altering the registered stream.

Reconstruct operator-training world signatures from provenance/generator seeds **without model forwards** if possible. If unavailable, mark operator-training disjointness unverified; do not declare complete isolation. Do not open or score sealed `test.pt` files to obtain exclusions. Use permitted metadata/signatures only; do not read labels from existing confirmation panels.

If a registered architecture passes development without recipe changes, lock **all five final checkpoint hashes for all three seeds**. Then generate a fresh confirmation copy of the same 14-cell grammar, **512 independent units/cell**, without predictions. The generator recipe is already frozen; hash its bytes, labels, sources and rejection log before scoring. Exclude all training, memory, dev and legacy-panel worlds. Interpreter-only duplicate/validity rejection has maximum 10,000 attempts per unit; exhaustion aborts.

Confirmation marks are exactly scaled:

- 58/64 → **464/512** absolute primary/edit successes;
- 61/64 → **488/512** ordinary retention;
- 13/64 → **104/512** paired gain over U;
- 7/64 → **56/512** paired gain over each S/C/A.

Evaluate all five arms, all three seeds, once. No training, checkpoint selection, mark changes or replacement panels after confirmation. Any failed required cell rejects the registered pass. A revised idea gets a new version and a newly isolated confirmation set.

## 9. Bounded waves, startup failures and reproducibility

No throughput measurement has been run for this draft. Before registered model training, Fable may do a disposable synthetic-fixture timing/shape check after source and predictions are frozen. It must not use registered panels or select settings by accuracy.

A wave uses **at most six one-thread Mac jobs or one consumer GPU**, never both. Set a 1,200-second soft compute limit and a **1,500-second hard wall deadline for the entire wave**, including scoring and checkpoint I/O. Reserve shutdown time. Start with chunks no larger than 750 awake updates or 500 offline updates; a frozen timing result may choose smaller chunks. Score panels in bounded chunks too.

Resume exactly: weights, optimizer, gradient scaler if used, RNG states, update number, schedule, data cursor, recent/cumulative activity statistics and mask RNG. Chunk boundaries cannot reset the odd/even schedule or create extra ordinary updates. No outcome-dependent budget extension.

Keep hardware/backend/thread settings fixed within a registered seed's complete contrast. Log all startup failures; do not rerun until a lucky initialization succeeds. Infrastructure interruptions may resume the exact state and must be disclosed. Numerical divergence is a reported run failure. A hardware-specific replica requires a separately labeled registered replication, not substitution.

An incomplete wave/run is **incomplete**, not evidence for or against the mechanism. If the fixed compute protocol is infeasible, report that outcome and revise before a new experiment; do not call unmeasured timing “under 30 minutes.”

## 10. Negative outcomes and allowed conclusions

- U never forgets enough to permit the registered gain: **no demonstrated benefit under this stressor**. The experiment may have a ceiling; do not change the bias retrospectively.
- B beats U but ties S: ordinary stochastic inhibition explains the gain.
- B ties C: no evidence that the short recent-activity horizon matters.
- B ties A: global shrinkage explains the gain.
- B meets H marks but damages F/E: fails the registered usefulness claim.
- Effects exist only with inference gates enabled: not this training hypothesis.
- A dev pass fails confirmation, or only selected seeds pass: report the failure.
- A T benefit would show that this rule can help a plain transformer too; it is not a threat to the hypothesis.
- No B benefit does not refute rodent BARR physiology; the translation is deliberately simple.

Maximum positive claim: **under a fixed biased intact-rehearsal schedule, recent-activity-targeted readout attenuation preserved the registered toy behavior better than the specified equal-update controls, across these three seeds and an untouched confirmation panel**. This is not evidence of original thought, new primitives, biological equivalence, superior general intelligence, or a first-ever AI mechanism.

## 11. Implementation handoff and freeze checklist

Fable may divide later work among Opus sub-agents: isolated data/panel generation and exclusions; a common D/T gain hook with the five arms; and an independent scoring/resource audit. Integration should produce new experiment-20 code/config paths without editing frozen prior experiments. No sub-agent should launch registered runs before the single shared freeze manifest.

The reviewable handoff must contain:

- resolved source paths and hashes; exact canonical operator hash; parameter counts and no-hint interface audit;
- serialized data/optimizer/schedule/seed settings; precomputed intact-memory and offline-index provenance; all bucket counts;
- train/eval gate definitions with unity-eval checks, detached traces, live-position masking, stable tie rules and identical dummy work;
- dev-panel and exclusion hashes, frozen confirmation recipe, all marks and the all-seed decision logic;
- per-wave deadline/resumption settings and explicit resource reporting;
- written per-arm, per-seed predictions, including the possibility of no forgetting or no gain, hashed before any run.

Static/interface checks and a future disposable-fixture smoke check should establish hook placement and deterministic resumption. Do not load registered confirmation labels or run a miniature accuracy sweep as “testing.” New evidence that changes the recipe requires a new version before execution.

## Fable's predictions
