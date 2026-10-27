# Persistent learning system: research review

Research date: 2026-09-17. Design discussion only; no model execution, training, installation, or architecture commitment was performed in this research turn.

## Scope and provenance

Five agents were dispatched using exactly `chatgpt-web/high`, with high reasoning effort. Their remits were persistent weight memory; reasoning and stopping; English-to-memory representations; autonomous practice; and experimental design. Each received the same project constraints and a distinct research question. Each completed an initial review and one refinement; all are now closed.

The agent sessions lacked live source inspection. Initial reports included incorrect paper identifiers/titles, resource estimates, and several confounded experimental suggestions. The coordinating agent inspected primary sources with browsing, supplied corrections, and performed this synthesis. This is a curated design review, not five independently verified literature surveys or experimental replications. Raw reports are not reproduced as authoritative findings.

The user has paused implementation. All recommendations below are proposals for discussion.

## Assessment

The project has relevant precedents. The unresolved hypothesis is whether a trained writer can turn checked experiences into persistent weight changes that improve both factual retention and transfer of methods, while limiting damage to earlier learning. No inspected paper establishes that full combination for this proposed architecture or resource budget.

Three distinctions must survive every comparison:

- Retaining information within a sequence differs from preserving it across attempts and restart.
- Conditioning a pretrained model to execute a known procedure differs from learning a new procedure from experience.
- Improving a whole system does not identify which component caused the improvement.

The chosen network family remains open. Recurrence, attention, memory updates, replay, and language decoding are compatible design dimensions rather than mutually exclusive labels.

## Evidence map

| Question | Relevant verified source | Supported conclusion and limit |
|---|---|---|
| Can a learned network generate fast weight writes? | [Linear Transformers Are Secretly Fast Weight Programmers](https://arxiv.org/abs/2102.11174) | Connects linear attention to fast-weight programming and studies corrective updates. This is not proof of lifelong factual learning. |
| Is the matrix delta update a useful baseline? | [Parallelizing Linear Transformers with the Delta Rule over Sequence Length](https://arxiv.org/html/2406.06484) | Gives the regression/SGD interpretation and demonstrates sequence-modeling and retrieval benefits. Memory retention across a lifelong stream remains a different evaluation. |
| Could memory be a nonlinear network? | [Learning to (Learn at Test Time)](https://arxiv.org/abs/2407.04620), [Titans](https://arxiv.org/abs/2501.00663) | Demonstrate trainable adaptive memory/state mechanisms. Their evidence does not establish our feedback-gated permanent writes from reasoning traces. |
| Can edits be separated from base weights? | [GRACE](https://arxiv.org/abs/2211.11031), [SERAC](https://arxiv.org/abs/2206.06520) | Discrete codebook or explicit-memory editing can reduce collateral damage in the studied tasks. These are comparators, not substitutes for the requested dense weight-learning test. |
| Can latent vectors influence reusable behavior? | [Function Vectors in Large Language Models](https://arxiv.org/abs/2310.15213v2), [In-Context Learning Creates Task Vectors](https://arxiv.org/abs/2310.15916) | Support task information encoded in activations of trained models. They do not establish autonomous, persistent acquisition of arbitrary methods. |
| Can recurrent depth help? | [Universal Transformers](https://arxiv.org/abs/1807.03819), [Recurrent Depth Approach](https://arxiv.org/abs/2502.05171) | Reusing a computation block can improve performance in trained settings. Benefits depend on training and task; recurrence is not inherently human-like. |
| Is there a small recursive-model precedent? | [Less is More: Recursive Reasoning with Tiny Networks](https://arxiv.org/abs/2510.04871) | Reports a small recursive model on specialized puzzle benchmarks. It does not demonstrate English communication or lifelong memory. Parameter count is not a training-cost comparison. |
| Can stopping be learned? | [Adaptive Computation Time](https://arxiv.org/abs/1603.08983), [PonderNet](https://arxiv.org/abs/2107.05407) | Establish adaptive-computation mechanisms. Their training objectives cannot be imported without reconciling our initial absence of a compute-cost penalty. |
| Does replay help without learner task labels? | [Experience Replay for Continual Learning](https://arxiv.org/abs/1811.11682) | Demonstrates retention benefits in sequential reinforcement-learning settings without explicit task boundaries. Broad method transfer remains unproven. |
| Is uncertainty sufficient for curiosity? | [Large-Scale Study of Curiosity-Driven Learning](https://arxiv.org/abs/1808.04355) | Shows successes and stochastic-environment failure modes for prediction-error rewards. Unpredictability is not necessarily learnability. |
| Can generated practice improve a model? | [STaR](https://arxiv.org/abs/2203.14465), [Absolute Zero](https://arxiv.org/html/2505.03335v1) | Support checked self-training/self-play in particular settings. These use established base capabilities and grounded correctness signals, not learning everything from an untrained network. |

Weight-space task arithmetic is a different mechanism from activation task vectors: [Editing Models with Task Arithmetic](https://arxiv.org/abs/2212.04089) combines fine-tuning parameter displacements. It should not be cited as though those displacements were the same objects as retrieved latent contents.

## Additional close precedents found during synthesis

**MemGen is a close conceptual neighbor.** Its trigger decides when to invoke memory; a separately trained LoRA-based weaver generates latent tokens for a frozen reasoner. The weaver is trained on experiences using supervised or reinforcement-learning objectives. This overlaps with selective, experience-trained latent memory influencing reasoning. It does not demonstrate our specific single-event delta-bank writes, full-trace writer, or restart/one-shot-retention protocol. Its interpretation of memory categories as human-like should remain an interpretation. [MemGen, Sections 4.2–4.3](https://arxiv.org/html/2509.24704v2)

**Nested Learning/HOPE makes update timescales a relevant design dimension.** The paper studies nested optimization and multiple memory update frequencies, including continual-learning experiments. Those experiments include adapting pretrained billion-parameter models with substantial further training. The authors explicitly state that catastrophic forgetting is not solved in general. It is a reason to investigate staged consolidation later, not to expand the first prototype into an unmeasured multi-level architecture. [Nested Learning, Sections 9–10](https://abehrouz.github.io/files/NL.pdf)

**Memory-R1 is relevant to the writer's decisions but uses different storage.** It learns operations on external memory. It supports considering learned skip/update policies, while its results cannot count as evidence of persistent weight learning. [Memory-R1](https://arxiv.org/abs/2508.19828)

The novelty claim should therefore be narrow and provisional: feedback-controlled persistent writes from recorded internal experiences, evaluated jointly for factual acquisition, correction, method transfer, and retention under the project's constraints. A literature search cannot establish priority or prove that no exact precedent exists.

## Mathematical conclusions

For fixed k and v, the proposed delta update is one SGD step on:

    L(W) = 1/2 ||Wk - v||²
    W' = W + eta (v - Wk) kᵀ

For another cue k', its immediate effect is:

    (W' - W) k' = eta (v - Wk) (kᵀk')

Thus immediate interference and later repair by replay can both be true. For a fixed, full-column-rank key matrix K and target matrix V, a consistent solution is W = V K†. Appropriately configured repeated updates can approach a consistent solution; that claim does not extend automatically to conflicting targets, deficient rank, ill-conditioned keys, limited replay, or encoder drift. The analytic solution is a diagnostic control with privileged information, not an online learner baseline.

With eta=1 and a unit nonzero key, a single update gives W'k=v. That proves a local association property; it does not prove useful encoding, paraphrase matching, transfer, or retention after other writes. Zero/near-zero keys need explicit handling.

Frozen theta protects its parameter values. Bad memory reads can still impair the combined system. A memory bypass or rollback can restore the base path, subject to any other changed components.

## Candidate training contract: teach, write, clear, query

This is a concrete candidate for discussion, not a settled architecture.

1. Generate a fictional world with randomized facts and transformations. Expose teaching sentences or demonstrations, never evaluator family labels.
2. Encode accepted teaching, or a checked attempt plus its bounded workspace trace.
3. Writer parameters phi produce cue k, content v, write/skip, bank choice, and strength. Reader/router parameters rho construct compatible query cues. Main parameters theta interpret retrieved content and produce answers.
4. Apply a functional update to episode memory W. Clear the teaching prompt and attempt workspace before answering disjoint training queries.
5. During initial episodic training, jointly learn theta, rho, and the relevant writer representations through those query losses. W is updated within episodes rather than serving as a static global answer table. Reset worlds between independent training episodes; retain W across attempts within continual-learning evaluation episodes.
6. Use sampled writer actions and a documented advantage estimator for the RL part; differentiable cue/content paths can learn through the functional write. Bound unrolls and state where gradients stop.
7. Once initial capabilities are trained, freeze theta and rho for controlled writer training. Each paired write/no-write audit freezes every non-memory parameter and differs only in W. Final evaluation also freezes trained writer parameters; only permitted feedback-driven memory writes occur during its teaching/practice phase. Scored queries allow no writes.

Example factual sequence: teach “Nera was born in Lume”; clear context; ask a paraphrase; perform unrelated writes; correct the birthplace; save/restart; query again. Randomize identifiers and values so a pretrained or jointly trained model cannot pass solely from existing associations. Byte/character encoding or controlled subwords can separate addressing failures from unknown-token failures. Negation and corrections need explicit semantics.

Example method sequence: demonstrate enough input/output pairs to distinguish a transformation, then test new operands and compositions. Observing 2→4 alone cannot identify doubling versus adding two. A direct English statement such as “double the input” supplies more information than that ambiguous example. A universal statement is not semantically ambiguous merely because the model might misunderstand it.

Separate exact arbitrary-content recall, procedure selection, composition, and acquisition of novel procedures. Gains on one category do not establish the others.

## Proposed comparisons and protections against misleading results

The four core conditions remain no persistent writes, fixed-rule writes, learned writes at equal memory capacity, and ordinary weight updates with replay. Give meaningful tuning opportunities to every condition. Match initial capabilities and feedback opportunities, then report compute/sample/storage frontiers; all costs cannot generally be equal at once.

Useful targeted additions:

- **Fixed vs learned writer × replay off vs on:** a clean 2×2 comparison when replay invokes the same allowed update mechanism. “No writes plus replay” does not improve a fully frozen system and should not be labeled a comparable learning condition.
- **Full trace vs final-state vs successful-output-only writer inputs:** all still write to weights. Output-only does not mean handing an external answer store to inference.
- **Memory zeroing and between-world swaps:** test whether predictions depend causally on W. Matrix memories do not have independent entries that can casually be shuffled like a database; any scrambling intervention must be defined in terms of banks, cue basis, or contents and checked for confounds.
- **Known-good keys:** diagnostic algebra tests only. The learned condition must construct its own cues without supplied skill IDs.
- **Paired continuation:** answer at saved state, then at several extra depths, with immutable memory and matched randomness. Compare train-range and longer depths. Include restart/sampling alternatives only with deployment-available selection; oracle best-of-N is an upper diagnostic.

Extra iterations can help without convergence, and can harm despite apparently stable norms. Initial stopping reward contains no compute penalty; finite runtime/horizon limits are separate engineering constraints. Ties provide no preference, but expected deterioration can justify stopping. Preserve exploratory longer continuations.

For writer rewards report B and D separately as well as R=B-lambda D. If before/after differences contain zero-mean noise epsilon, E[max(0,epsilon)] is generally positive. Paired seeds, repeated evaluations and an uncertainty estimate help identify this measurement effect. Do not silently redefine away actual item-level forgetting; distinguish noise from heterogeneous real damage. Superseded facts should be scored against corrected truth, not rewarded for retaining known errors.

Use disjoint training/reward, development-audit, and final-test pools. Freeze primary endpoints and useful effect thresholds before confirmation; pilots estimate variance and training adequacy. A ten-minute null result may be inconclusive. An always-write policy can be optimal in a trivial environment; action diversity alone is not a success criterion.

## Autonomous practice

Begin conceptually with a bounded external synthetic generator, a task-selection rule, and a checked replay buffer. Compare random selection, uncertainty selection, and estimated learning progress with exploration while holding the learner and writer fixed. Include unlearnable/noisy candidates, delayed gains and old-skill tests. Count selection, generation, checker and audit costs separately from the stopping reward.

A learned generator is a later distinct question. Absolute Zero demonstrates grounded task proposal/solution training with a code executor and pretrained models; “zero data” does not mean zero pretraining. Reusing its idea does not establish feasibility of its full training setup on this GPU. Replay must keep correction provenance and must not become hidden test-time transcript retrieval.

Accepted teaching/checker feedback can gate individual writes; occasional randomized audits can assess longer-term effects. Requiring a large held-out suite for every write would defeat the stated resource design.

Preserving an unfinished workspace and periodically restoring it can implement input-free activity. With identical full state and inputs, pauses need not change the logical computation, but asynchronous arrivals, deadlines, nondeterministic kernels and stale assumptions can matter. A seed alone is not an exact continuation checkpoint: versions, W, model, optimizer, RNG states, workspace, caches and stream position can all be required. Bounded recorded traces remain part of the planned research.

## Resource arithmetic, not feasibility claims

For fully trainable FP32 parameters with FP32 gradients and two FP32 Adam moments, persistent training tensors total 16P bytes before activations and implementation temporaries. Moments alone total 8P. This is an illustrative setup, not a claim about a future chosen precision/optimizer.

| Parameters | Weights | Gradients | Two moments | Sum |
|---|---:|---:|---:|---:|
| 1M | 4 MB | 4 MB | 8 MB | 16 MB |
| 124M | 496 MB | 496 MB | 992 MB | 1.984 GB |
| 700M | 2.8 GB | 2.8 GB | 5.6 GB | 11.2 GB |

Add writer, router, memory, connecting projections and output heads unless already included in P. Eight 512×512 FP32 banks occupy 8,388,608 bytes. Frozen W does not need Adam state; differentiating through writes still retains intermediate state/activations. Long unrolls, caches, optimizer temporaries and concurrent branches can change peaks substantially. Disk checkpoints omit transient gradients in typical implementations, so disk size is not 16P by default; old+new staging and optimizer states still count.

All prototype runs remain unrun. Do not infer fit from these weights alone or introduce a resident large teacher. Preserve the global 100,000,000,000-byte peak limit, 80GB steady target, actual free-space checks and at-most-ten-minute initial experiment bounds. No reproduction of the cited large runs is proposed.

## Next design decision

Specify the teaching-to-query training contract first: what feedback reaches the writer, what information k and v must preserve, which query loss trains their shared representation, and what gets cleared before answering. Keep the storage interface replaceable. The most informative initial milestone would be a trained tiny system that learns randomized English-expressed facts through W, survives interference/correction/restart, and shows separately measured transfer on a simple transformation family. That would establish a useful mechanism, not broad English reasoning or lifelong learning.
