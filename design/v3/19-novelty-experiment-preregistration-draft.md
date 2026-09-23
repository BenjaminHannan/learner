# 19 — Compositional replay: experiment preregistration draft

**Draft · Astra · 20 September 2026 · Track A only**

Status: prospective design, not frozen and not launch authorization. No experiments have been run under this draft. Preserve all existing sources, registrations, hashes, checkpoints and panels. Implement later through new entry points and output directories. Do not access the prohibited sealed `test.pt`. The village track is outside scope.

**Question.** Does generating unasked compositions of familiar operations improve the learned controller’s performance on a question family excluded from both ordinary practice and replay, compared with the same number of updates on intact rehearsal? Does the same intervention help the corrected plain transformer?

**One intervention.** Change the source of offline practice questions. Hold the solver architecture, operator, loss, update budget and input interface fixed within each architecture. Do not add a new STOP mechanism, recency flag, relative offset, macro library, exploration bonus or learned critic. Research rationale and limitations: [companion note](19-novelty-mechanism-research.md).

## 1. Definitions and hypothesis

Use **`c` = total primitive lookup calls**, including the last attribute lookup. In existing scripts this is called `hops`. The number of LINK traversals is `c−1`. Thus:

```text
c=1: [QUESTION, person,                         r, ANSWER]
c=3: [QUESTION, person, LINK, LINK,             r, ANSWER]
c=5: [QUESTION, person, LINK, LINK, LINK, LINK, r, ANSWER]
```

This resolves the possible off-by-one ambiguity in “k hops, then read a relation.” `ANSWER=5` here is the question boundary token, not the baseline’s emitted `END=68`.

The world remains visible fact rows, 16 possible entity IDs, attribute relations 8/9/10 and LINK=11. Attribute values are terminal values; do not silently reinterpret them as people or add new edge types. Questions remain a unary chain, so this experiment cannot demonstrate invention of a new primitive or branching plan.

**Registered hypothesis.** A replay generator that reuses learned operation transitions can produce previously unasked four/five-call question structures. Training on these with endings 8/9 can improve transfer to four/five-call questions ending in 10, even though *all composite relation-10 questions are absent from every training channel*.

Distinguish the following claims throughout reporting:

| Label | Exact meaning |
| --- | --- |
| New instance | A new story/question pair, possibly with a familiar operation string. Insufficient for the main novelty claim. |
| Generated type | An operation string absent from ordinary practice but produced by the replay mechanism, e.g. `LINK LINK LINK 8`. Once trained on, it is not held out. |
| Useful generation | Generated questions cause a prespecified gain over equal-update rehearsal on disjoint evaluation data. Unusual strings alone do not qualify. |
| Never-trained type | A composite relation-10 string absent from awake practice, proposal learning, accepted replay, solver updates and supervised targets. The primary cells use `c=4/5`. |
| Length extrapolation | Successful execution at `c=6..8`, beyond both awake (`≤3`) and replay (`≤5`) practice. A separate, secondary claim. |

The fixed sampler’s inductive bias and interpreter are supplied by us. The model does not discover the grammar, its desire to practise, or the meaning of the verifier. “Useful autonomous recombination within a supplied language” is the maximum novelty claim from the primary experiment.

## 2. Frozen architecture and starting procedure

**Dispatcher D.** V4 `reg+ctx`, width 32, 24,035 parameters. Both learned replacements stay active; both hand-supplied v3 hints stay absent. Preserve the raw-question and self-generated-transcript interface. Preserve the learned STOP decision, full-vocabulary operator argmax, invalid-action semantics and lack of a story input to the controller.

Use the **same frozen canonical operator in every D arm and seed**: the operator named in the current reg+ctx seed-0 training manifest, `/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_seed-1/final.pt`. The manifest lists SHA-256 `e7e5b6f3a6bfecf3890538bd0a14af7f5189b1565329e5cf411b52dd4d4dfbec`; Fable must verify actual checkpoint bytes before freezing. No operator selection, swap or adaptation in this experiment. This is historically a hinted operator. Grow-blind replacement, although of interest, would be another intervention.

**Transformer T.** Corrected baseline v2, primary I1-H1: operator-style Linear initialization rescale, supporting-line loss 0.5, steps output, line positions, width 48, three layers, four heads, hidden width 208, 69-token vocabulary, tied embeddings and original loss masking. Preserve its learned position tables. A position redesign is not part of this experiment. Record exact parameter count from the implementation before freezing.

**Fresh paired runs.** Use seeds **1900, 1901, 1902** for each architecture. Generate one common awake data stream per seed, shared byte-for-byte across D and T. Ordinary training is 6,000 updates, each with 16 six-person worlds × four questions, uniform `c=1..3`, terminal relations 8/9 at `c≥2`, and all three relations at `c=1`. Use existing world/filler grammar; include full visible stories. Do not compare newly trained replay arms against historical checkpoints as the causal controls.

All D training, including awake practice and every control, uses a **common cap of eight primitive calls**, starting from update one. This gives enough room for replay questions and avoids increasing a cap only for the treatment. The cap is a failure limit, never a target, input feature or STOP signal. Native evaluation uses the existing cap 16. A cap hit is failure even if the last token happens to equal the answer. T uses common output capacity 12, sufficient for the registered questions and END. Assert no position-table clipping or clamping in any panel.

The common cap differs from historical v4’s training cap of four. It is a declared common harness setting, not evidence that historical results have already reproduced under this recipe. Awake fit is therefore a prerequisite. No inference-only forced actions or oracle paths may help clear it.

**Awake optimizers.** D: existing RLOO, 16 sampled episodes/question; final-answer correctness minus `0.01 × executed calls`; AdamW lr 0.003, betas (0.9,0.99), epsilon 1e-8, weight decay 0.01, 100-update warmup, clip 1.0; entropy coefficient linear 0.2→0.02 over 6,000 updates. T: baseline-v2 AdamW lr 0.001, same betas/epsilon, weight decay 0.1, warmup 100, final-third decay to 0.0001, clip 1.0; preserve its step and supporting-line targets. Freeze resolved settings, not merely references to mutable defaults.

D receives a scalar outcome reward plus the existing call cost; T receives intermediate step targets and line targets. This is **matched stories/questions, not equal supervision or equal total compute**. Within-architecture replay contrasts support causal statements. A D-versus-T gap alone does not isolate architecture, replay, prior operator training or credit assignment.

## 3. Replay memory and the only new learned state

Save the **first 1,024 distinct awake training worlds** in encounter order and the four actual awake questions presented with each. World identity ignores row order and filler. If a duplicate world appears, retain the first and continue to the next awake world; log it. Memory selection cannot depend on correctness, reward, confidence, path length success or any evaluation outcome. Store provenance: seed, update, world slot, original visible rows and questions.

Build empirical transition counts from these 4,096 question operation strings, with BOS/EOS added and entity names removed. Alphabet is `{BOS, LINK, 8, 9, 10, EOS}`; counts form a 6×6 table. Normalize each nonempty row to probabilities. **No smoothing, pseudocounts, temperature tuning, length bonus or hand-entered transitions.** Empty rows terminate proposal generation as invalid. Each learned edge must be traceable to an awake question.

This is a tiny learned generative model: zero new gradient-trained parameters, at most 36 counts. `LINK→LINK` can be sampled more often in a generated string than in any complete training question. No routine for `c=4` or `c=5` is hard-coded into the proposal probabilities. The fixed assumption is that local transitions can compose.

The transition table is frozen for the entire offline block. Do not update it from generated questions: that would introduce a self-amplifying curriculum. There is no learned question ranking, utility predictor or novelty reward in this first test.

## 4. Arms and fixed offline block

After the final awake checkpoint, clone its weights into all three arms of its architecture. This is **six shared awake training runs** followed by **18 offline continuations**, across the three seeds. Do not run all jobs together.

| Arm | Offline question source | Purpose |
| --- | --- | --- |
| D-R / T-R | The four original awake questions for each remembered world, intact. | Equal-update, no-recombination control. |
| **D-G / T-G** | Operation strings sampled from empirical transition counts, bound to remembered worlds and people; correctness checked by the same interpreter. | Primary compositional-replay treatment. |
| D-U / T-U | Generic fixed random curriculum: sample `c` uniformly from 1..5; choose r uniformly from 8/9/10 at `c=1`, otherwise from 8/9. | Tests whether any advantage needs learned proposal statistics, or ordinary synthetic practice suffices. |

**Prepare each G buffer before any offline solver updates.** For every remembered world, generate exactly 64 independent candidate operation strings, in fixed RNG order, starting at BOS. Sample until EOS, rejecting any string with more than five calls, missing an attribute terminus, or any invalid transition. Never truncate a long proposal into a valid question or append a convenient terminal. A maximum of seven draws after BOS suffices to detect a valid ≤5-call string plus EOS or an overrun; exceeding it is rejection. For each syntactically valid string, choose the start person uniformly from that world with a separately named RNG stream.

Accept the first four distinct question signatures per world. Duplicates consume a candidate attempt. Reject every `c≥2, r=10` candidate before label generation, even if a bug or future input corpus would otherwise allow it. Record proposed and rejected type histograms; no information about rejected held-out types reaches a learner. If fewer than four valid distinct questions survive, fill missing slots with that world’s original awake questions in source order, recording each fallback. Do not increase the 64-attempt budget. Process U with the same attempt, duplicate and fallback rules. Do not choose candidates based on an operator or controller’s correctness.

All buffers therefore contain 1,024 worlds × four questions. World bytes and their coverage are identical across R/G/U; the question source is the intervention. D and T receive exactly the same corresponding buffers for a seed. U has a different length distribution from G by design; record it. G-versus-U evaluates the practical proposal recipe at equal update budget, not a purified neural mechanism at identical length histograms.

**Training labels/rewards.** The fixed fact interpreter reads only the visible stored story and generated question. It computes the final answer for D’s reward service, and the existing step/line labels for T. It does not call a pretrained language model, load evaluation answers or correct the learned operator’s native outputs. Filler rows remain in the operator/transformer input. A malformed fact table is an integrity failure, not an invitation to drop a difficult world. This is simulator-generated supervision, not label-free learning.

**Offline budgets.** Every arm receives exactly **2,000 solver optimizer updates**, 16 memory worlds × four questions each, sampling world indices with replacement from a fixed shared stream. Corresponding arms share world-index order; corresponding D/T runs share raw data order. Reset optimizers at this boundary in every arm and state that choice in the manifest. Use the awake optimizer settings again, with schedules parameterized by 2,000 rather than 6,000 updates. D still uses K=16, call cost 0.01 and entropy 0.2→0.02. Final-update checkpoint only. No outcome-dependent extensions, best checkpoint, replacement seed or selective restarts.

Total per solver: **8,000 updates**, of which 2,000 are offline. There are no generator optimizer updates. Buffer preparation is common, logged preprocessing, even when an arm only consumes R. Operator inference/caching, label generation, proposal attempts, padding, active decisions, target-token counts and wall time are separately reported. Use common padded maximum widths and an eight-step masked rollout for all D arms so termination does not silently change the allocated training unroll. Active actions and useful supervision still differ; do not call useful FLOPs or label counts exactly matched. Normalize T losses in the same way across its arms.

## 5. Novelty audit and fit gates

**Generation gate, each seed.** G must produce and accept at least **16 distinct questions in at least 16 distinct worlds for each of the four structures** `(c=4,r=8)`, `(4,9)`, `(5,8)`, `(5,9)`. Count only sampled questions, excluding fallbacks and duplicates. These structures must have zero awake instances. This is a prespecified measurement, never an acceptance quota used to steer generation. Missing a structure fails the generation gate; do not fill it by hand.

Check before scoring that composite r=10 has zero exposure in ordinary questions, proposal-count training, accepted buffers, solver labels and any teacher-forced diagnostics used for training. Primitive `(person,10)` facts and one-call questions remain allowed. A type exclusion is global across entity names and worlds, not an exact-hash exclusion.

**Ordinary-fit gate.** At the final awake checkpoint, score seven fresh six-person development cells: `c=1` separately for r=8/9/10, and `c=2/3` separately for r=8/9. Each has 64 units. Require **≥61/64 final answers and ≥61/64 strict sequences in every cell, in every seed**, separately for D and T. A failing architecture has not met the prerequisite under this recipe. Report all failures and stop its registered offline claim; never omit its failed seeds. The other architecture may continue, but there can be no completed cross-architecture comparison until both qualify under one frozen design.

The unmodified final awake checkpoint is also a descriptive before-replay anchor. Its scores are not an equal-update control. Historical v4 and baseline-v2 results are context only.

## 6. Development panels and exact primary decision

Create new development panels, independent of all training/replay worlds. Every cell contains **64 independently drawn units**. A pair is one unit, not two independent examples. Stratify final answers as evenly as the existing value vocabulary permits, with the outcome-independent generation rule recorded. For c≤5, choose chains with distinct visited people in both six- and sixteen-person worlds to reduce accidental success by cycling. Retain the existing distribution of distractor/filler rows; no confidence-based screening.

| Family | Cells | Role and marks |
| --- | --- | --- |
| **N: never-trained question types** | r=10 × c=4/5 × people=6/16: **4 cells** | **Primary**. D-G must reach ≥58/64 answers and ≥58/64 strict sequences in every cell. In each cell and each seed it must exceed D-R strict successes by **≥13/64**. |
| E: sensitivity/invariance | c=5, r=10, 16 people; changed LINK, changed endpoint value, irrelevant fact edit: **3 pair cells** | Required anti-shortcut guard: D-G ≥58/64 strict pair units in each. No separate gain threshold. Both sides must be correct; irrelevant edits must preserve the answer. |
| F: retention | The **7 ordinary-fit cells** above | Required: D-G ≥61/64 answers and strict sequences per cell after offline practice. |
| P: practiced-length transfer | r=8/9 × c=4/5 × people=6/16: **8 cells** | Descriptive explanation of learning from generated practice. Mark 58/64, but not a substitute for N. |
| H: short held-out endings | r=10 × c=2/3 × people=6/16: **4 cells** | Descriptive check of transfer already seen in historical reg+ctx. Ceiling effects are expected and cannot establish novelty. |
| L: beyond all training lengths | c=6/7/8 × ending group {8/9 balanced, 10} × 16 people: **6 cells** | Secondary length-extrapolation screen; mark 58/64 answers and strict sequences. Failure does not become success because N passed. |

There are **32 distinct development cells**. Awake fit uses only F; do not use N/E/P/H/L outcomes for checkpoint or recipe selection. At the offline endpoint score all arms on all cells, including R and U. T gets the identical marks for a separately reported T-G versus T-R replay result. No averaging across people counts, lengths, endings or seeds is allowed to rescue a cell.

**Primary development pass** means: valid integrity audits, generation gate, all D awake-fit gates, all N absolute and paired-gain marks, and all E/F guard marks, **for all three registered seeds**. Predeclare this intersection; do not select successful cells. Treat it as an engineering screen, not a universal population-reliability guarantee or an automatically significant causal effect at any chosen alpha.

**Strict scoring.** D must choose the correct subject, operation and result at each native call in order and STOP immediately after the requested terminal lookup. Duplicate question-position pointers with the same operation do not constitute a wrong semantic call by themselves; evaluate the emitted call sequence, not a privileged pointer path. T must greedily emit the exact intermediate-person sequence, final value and END, with no extras. T’s outputs do not expose operation pointers; record that its strict sequence is an observable trace metric, not identical internal evidence to D’s call log. Answer-only correctness, call count and stop status are always separate columns.

For pair cells require both strict successes. Changed LINK and endpoint edits must actually change the oracle answer; choose edits using fixed interpreter-only rules. Irrelevant edits preserve it. Keep pair membership in all reporting and uncertainty calculations.

Report per-cell native counts, paired G/R gains and losses, G/U differences, invalid actions, operator errors, premature STOP, late STOP, cap hits and answer-with-wrong-path cases. Include per-seed Wilson intervals for single-cell success and paired discordance counts; never pool seeds into one headline average. All diagnostics are evaluation-only and may not select training records.

## 7. Untouched confirmation and data governance

The previously scored 25-cell development panels and baseline fit confirmation panel are historical evidence. Existing fresh panels at `W/artifacts/fable-confirmation-panels-20260920/` remain unscored by this proposal. Their metadata/signature exclusions may be used for isolation, but they are not a substitute for the new novelty confirmation suite.

Freeze namespaces now:

```text
astra-novelty19-awake-v1:<seed>:<update>:<world-slot>
astra-novelty19-propose-v1:<seed>:<world-index>:<candidate>
astra-novelty19-bind-v1:<seed>:<world-index>:<candidate>
astra-novelty19-uniform-v1:<seed>:<world-index>:<candidate>
astra-novelty19-offline-order-v1:<seed>:<update>
astra-novelty19-dev-v1:<cell>:<unit>:<attempt>
astra-novelty19-confirm-v1:<cell>:<unit>:<attempt>
```

Use independent model, world, proposal, subject-binding, policy-sampling and evaluation RNGs. Specify the exact hash-to-seed function, integer width and library versions in the launch manifest. Generate dev panels and the relevant legacy exclusion union before training. If a training item collides, abort that run as an integrity failure; do not silently skip it and alter the registered stream.

After final checkpoint hashes are locked, and only if development passes without recipe changes, generate **512 units per cell** for a fresh confirmation copy of the 32-cell specification. Generate it without reading any model predictions. Exclude all training, candidate-generation and replay worlds, not merely accepted training questions. A fixed interpreter-only rejection sequence with at most 10,000 attempts/unit may resolve duplicates or invalid pair constructions; exhaustion aborts. Hash panel bytes, labels, sources and rejection log before scoring. No training or selection follows confirmation.

Confirmation marks scale exactly: **464/512** for 58/64 marks, **488/512** for 61/64 marks, and primary strict G−R gain **≥104/512** per N cell per seed. Repeat generation/integrity audit evidence; generation itself is not rerun or improved for confirmation. A dev success without untouched confirmation is reported as development success only. If outcomes motivate a changed recipe, these panels become development and a separately registered namespace is required.

Use the prior 18-* semantic-audit principles: hash sorted eligible visible fact tuples plus full raw question, ignoring row order and filler; also record raw tensor hashes and world-only fact-set hashes. Include both pair sides, reduced/full presentations if any, and the primitive-question exclusion expansion over all 16 entities × four operations. No reduced-story training is planned here. Exact named-token identity is not universal alpha-equivalence; additionally audit type exclusion after stripping entity names. Because this design creates fresh data streams, retain every training/replay signature and the complete generator state instead of relying on an unverified reconstruction later.

The frozen operator also has a training history. Include its historical training signatures in panel exclusions, reconstructed from the exact archived generator, source hashes, initial RNG and training schedule without model forwards. If that provenance cannot be recovered, disclose that historical disjointness is unverified and do not certify the full untouched-confirmation claim. Distinct namespace strings alone do not prove disjointness. Perform this audit in a bounded idle wave; no such reconstruction was run to write this draft.

No panel example, answer, trace, attention target, confidence, gain score or desired length is available to proposal learning. The maximum proposal length is a declared experimental limit, not learned evidence. A safety validator may see type exclusions; it may not return a replacement held-out question or informative training feedback.

## 8. Failure interpretations and artifact controls

| Risk or result | Required interpretation/control |
| --- | --- |
| Held-out r=10 compositions accidentally generated or supervised | Global structure-level quarantine and logged zero-exposure audit. Any learner exposure invalidates the never-trained-type claim. |
| New questions are only renamed copies | Strip entity names and compare operation strings against the entire awake corpus. Require the four generation-gate structures and disjoint evaluation worlds. |
| Improvement is merely more updates | D-G and D-R have identical 8,000-update totals, phase schedules, batch counts and initial weights; compare final endpoints. Do not use the 6,000-update anchor as the control. |
| Improvement is generic synthetic augmentation | Compare G with U and give the same G/R/U data to T. If U matches G, learned proposal statistics have no demonstrated benefit; do not attribute the result uniquely to a brain-inspired mechanism. |
| More effective computation or teacher labels explain architecture gap | Log actual operator pretraining, calls, FLOPs, valid targets and attention supervision. Make the primary claim within D and separately within T. There is no pure architecture-superiority claim here. |
| Bookkeeping hints return through the implementation | Assert controller inputs contain only raw question and its own transcript; no remaining-length scalar, gold subject, next-pointer mask, recency flag, relative pointer offsets, forced CONTINUE or gold STOP. Fixed shape padding and caps must not become input features. |
| Interpreter performs the reasoning for the learner | It supplies reward/targets only on training data and oracle diagnostics only after native evaluation. Never pass interpreter states to D or substitute oracle calls for the learned operator. Disclose that question validity and reward depend on a supplied simulator. |
| Selecting easy worlds hides operator failures | Accept by syntax, signatures and task semantics only. No filtering by learned operator correctness. Report native scores on all units and an oracle-operator diagnostic separately. |
| A cap change alone repairs stopping | Common cap eight in all D training from initialization; both replay and rehearsal controls use it. Native STOP remains learned. |
| Baseline has unseen output positions | T-G/T-U train positions used by c=4/5 on matched practice. Primary N uses those lengths. T-R’s lack of long practice is the intended intervention contrast. c=6..8 remains position-confounded and must be labeled. |
| G generates enough novel types but N gain is <13/64, or absolute/guard marks fail | The registered mechanism did **not help enough under this recipe**. Report partial gains without declaring a pass. |
| G cannot generate the four types in its fixed budget | Proposal mechanism failed this screen. Do not call this a test of all possible neural replay mechanisms or fill in missing types manually. |
| G learns c=4/5 but stops at exactly five on c≥6 | The ceiling moved with practice; unrestricted continuation is unestablished. |
| T-G improves as much as D-G | Replay can help the transformer too; no special exclusivity to our architecture. This is a useful result. |
| All three seeds do not pass | No registered replicated pass. Report every seed, including failures and incomplete runs; no mean rescues it. |

Sparse final-answer reward may fail to teach longer action chains even with correct proposed questions. Diagnose that possibility from training logs and native/oracle evaluation, then register a separate credit-assignment change if warranted. Do not add path supervision to D mid-run.

## 9. Timing, freeze and implementation handoff

Each wave must be **under 30 minutes** on the Mac with **at most six one-thread jobs**, or on one consumer GPU. Respect existing training jobs and the resource guard. Set OMP/MKL/BLAS and framework intra/inter-op threads to one on the Mac; count all workers, including validators and proposal generation. Do not run a hidden second pool. Mac and GPU are separate reported execution profiles; do not silently move unsuccessful seeds between them.

No runtime guarantee is established by this document. The historical seed-0 v4 manifest reports 6,000 updates in about 928 seconds with cap four; our cap eight, matching and concurrent jobs can change that substantially. Later preflight may use a disposable non-panel fixture for timing only. It must not be used to tune pass marks, sample lengths or learning parameters.

Schedule awake work in resumable chunks of at most **750 updates**, offline work in chunks of at most **500**, with a **1,200-second compute budget and 1,500-second wave deadline**, leaving room for serialization. If the timing preflight shows a chunk cannot fit, split it further before launch without changing total updates. Save optimizer state, all RNGs, scheduler position, current batch location and sampler/buffer identity at chunk boundaries. If an unexpected deadline is reached, resume the exact next update in a later wave; timeout is incomplete, not a final trained model or scientific failure. Never evaluate an intermediate chunk as the final endpoint.

Keep proposal generation, signature audits and panel scoring in their own bounded waves if necessary. A buffer contains only 1,024 worlds and 4,096 questions, with 65,536 attempted proposals/seed/recipe; this is a design size, not a measured memory/time result. Split scoring by frozen cell/unit ranges, with all expected ranges required for completeness. Maximum six parallel jobs is a ceiling, not a target.

Before any registered training or scoring, Fable must make the design concrete and freeze:

1. The complete registration, **Astra and Fable predictions**, arm identities, seeds, marks and outcome rules; Fable’s final section below is deliberately empty for independent predictions.
2. New source files and resolved dependency hashes, fixed operator bytes, architecture counts, actual command arguments, software/hardware profile and RNG specification. Confirm imported base-checkout modules cannot drift unnoticed.
3. The new development panels and legacy exclusion union; exact interpreter and pair-edit rules; buffer builder and candidate-attempt schedule.
4. A manifest of SHA-256 hashes covering the above. Predictions and marks must be hashed **before any experimental run**, including the fresh awake training. Later confirmation bytes and endpoint checkpoint hashes receive an additional immutable manifest before confirmation scoring.

This research draft itself is not a frozen preregistration: hashes of implementation and final independent predictions do not yet exist. Any preflight change that affects semantics, labels, treatment or decision criteria requires an additive amendment **before** experimental outcomes are read. Never edit the old 18-* registrations or frozen v4/baseline sources.

Suggested implementation ownership for Fable’s later Opus sub-agents: one builds the additive buffer/generator and data pairing; one builds additive training/resume adapters; one independently audits leakage, native scoring and report completeness. Give them separate new-file scopes. Fable integrates and freezes their work before launch. This document does not dispatch agents or authorize experiments now.

Required preflight checks, to be implemented later on disposable fixtures: empirical counts match only awake strings; length cap rejects rather than repairs; zero composite-r10 exposure; all arms have identical world bytes and update/order budgets; swapped r=8/9 labels do not change exclusion logic; candidate failures/fallbacks are reproducible; no gold features in controller inputs; cap-hit is failure; sequence/END scoring and pair rules; frozen operator/cache SHA identity; checkpoint/resume equals uninterrupted continuation for the same short fixture; confirmation exclusion and completeness. These are implementation-integrity checks, not extra outcome searches.

## 10. Reporting and next decision

Write an additive report with one row per **arm × seed × cell**, counts and denominators, paired gains/losses, every failed gate, and all incomplete jobs. Include proposal type histograms before filtering, accepted counts, rejection/fallback counts, primitive coverage, parameter counts, historical operator supervision and complete compute accounting. Keep development and confirmation tables visibly separate. Print a plain-language conclusion before technical tables.

If G passes N/E/F and fresh confirmation, the supported statement is: **under this registered recipe, generated compositional practice improved transfer to excluded question types beyond equal-update intact rehearsal.** The comparison with U decides whether the learned transition sampler deserves credit beyond generic augmentation. The comparison with T shows whether this training intervention is useful across both architectures. Neither establishes general intelligence or new primitive invention.

Do not wait indefinitely for a separate STOP fix before testing this treatment: producing longer questions does not depend on the failing STOP head. First establish ordinary fit and proposal integrity, then test replay. If N fails, retain the failure and address stopping or credit assignment separately. If only L fails, retain the bounded novelty result and separately investigate continuation beyond all practice. Library induction remains a later, separate experiment.

## Astra's predictions

These are prospective judgments, not findings. I expect the empirical transition sampler to produce all four new structures without hand-filled quotas. I expect G and U to improve practiced four/five-call execution more than intact rehearsal, but I am uncertain that final-answer-only RLOO will cross the primary all-seed marks in 2,000 offline updates. I expect U to be competitive with G in this very small grammar. I expect six-to-eight-call performance to remain the hardest part, with a material risk that the stopping ceiling merely moves to five. I do not predict an exclusive advantage unavailable to T. The pass marks above remain fixed even if these expectations are wrong.

## Fable's predictions
