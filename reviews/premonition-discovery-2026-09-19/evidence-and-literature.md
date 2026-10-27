# Evidence and literature notes

19 September 2026. Companion to [brief.md](brief.md) and [protocol.md](protocol.md). File identities and UTC modification times are in [source-audit.json](source-audit.json). The audit used only filesystem reads, JSON parsing, source hashing and small standard-library calculations. No torch import, checkpoint loading, model execution, dataset generation, fitting, training, tests, GPU or outside-model contact occurred.

## A. Raw-result reconciliation

Source roots:

- `artifacts/claude-long-20260919/runs/long-s{0..4}-12000.json`
- `artifacts/claude-relcut-long-20260919/runs/relcutlong-s{0..4}-12000.json`

| Arm; seeds 0–4 | Own one-hop /512 | Own practiced /341 | Own held-out /171 | Oracle-card practiced /341 |
|---|---|---|---|---|
| Baseline | 115, 512, 512, 512, 489 | 84, 341, 341, 340, 341 | 6, 13, 88, 18, 12 | 341, 341, 337, 341, 332 |
| Relation shortcut | 506, 99, 92, 512, 473 | 339, 69, 75, 338, 257 | 171, 32, 35, 170, 132 | 341, 341, 341, 323, 306 |

All own scores above use `validation.fixed_K4`; all oracle scores use `validation.gold_read_K2_no_fetch`. The separate `learned_halting` scores must not substitute for either. Gold-card reading selects at most two correct cards and performs no further fetches; it does not certify general composition. In this task only the attribute card contains a value answer.

The shortcut passed oracle ≥307/341, practiced ≥171/341 and held-out ≥86/171 jointly in seeds 0 and 3 only. Seed 4 misses oracle reading by one answer. Its high held-out score still belongs in the report, but does not change the predeclared conjunction.

Both recipes use fp32 on an RTX 5070 Ti, tiny width 32/key width 16, `bypass-k1`, no teacher distractors, four loops, and long phase fractions .10/.1833/.2667. Actual stops are 12,250–12,251 steps. Static parameter breakdown: embedding 2,176; reader 31,936; writer 1,665; Think 30,480; heads 595; decoder 12,896; total 79,748. Shortcut adds `32*16 + 32 + 1 = 545`. Separate scorer adds 33.

**Shown by source:** the relation path is initially zero because its projection is zero. Its sigmoid gate initially equals 0.5, so describing the gate itself as initially closed would be wrong. A bias added identically to every token's softmax-pooling logit cancels; the extra scorer's counted bias parameter does not independently alter pool weights. Count all parameters anyway.

### Runtime and memory

| Quantity from saved JSONs | Baseline, five runs | Shortcut, five runs |
|---|---:|---:|
| Sum of `seconds_train` | 11,385.75 s = 3.16 process-hours | 11,665.18 s = 3.24 process-hours |
| Sum of `seconds_total` | 11,437.01 s | 11,712.16 s |
| Training duration per process | 2,256.96–2,313.05 s | 2,300.31–2,362.43 s |
| Reported FLOPs per run | approximately 6.81e13 | approximately 6.81e13 |
| Peak allocated CUDA memory per process | 170.42–170.65 MiB | 170.65–170.73 MiB |
| Peak reserved CUDA memory per process | 192–194 MiB | 192–194 MiB |

The baseline report says five concurrent runs took about 39 elapsed minutes. Summed process time is **not** exclusive GPU time. These data do not measure isolated throughput, GPU utilization, driver/context memory or inference latency. The proposed envelopes use conservative per-run caps and require local calibration, not a claimed speedup extrapolated from concurrency.

The local rental ledger, modified 19 September 00:20 UTC, says $30 remained under a handoff-specific accounting convention excluding older spend. It is not a current billing reconciliation. No available balance was assumed; every proposed stage uses the owned hardware and plans zero cloud charges.

### Probe scope

`person_probe.json` is supported by a script fitting 16-way linear readouts on even validation visits and evaluating on odd visits, with a second score restricting choices to people in that world. It used 400 optimizer steps for each readout, with model weights fingerprinted as unchanged. Thus “read-only model probe” does not mean the probe itself was unfitted. Those fits are historical; none was repeated here.

For baseline stuck seed 0, person-token decoding is .997, key decoding .174 in-world; first-request one-hop person hit is .168. Shortcut stuck seeds 1 and 2 show the same broad discrepancy. This suggests an address representation/use problem but leaves nonlinear information and causal relevance unresolved.

The temperature probe rescored saved representations with kappa 3/10/30/100, with and without age biases. It tests frozen ranking/loss behavior, not training trajectories. The report's claims of no hidden partial solution or of an identified temperature *cause* exceed what those probes establish.

### Additional local history

`artifacts/opus-m03-20260919-071009/eval/retrieval-{original,mean,two}-s0.json` supplies the older 1,517-step comparison:

| Writer | One-hop /512 | Practiced /341 | Held-out /171 | All practiced gold cards fetched /341 |
|---|---:|---:|---:|---:|
| Original | 32 | 24 | 7 | 173 |
| Mean | 37 | 18 | 11 | 177 |
| Two pools | 37 | 18 | 11 | 120 |

This used an earlier curriculum and one seed; answers were card-blind according to the associated saved intervention reports. Its source (`premonition/card_pools.py`) splits off the **value** scorer; the newer wrapper splits off the **key** scorer. At equal cloned initialization they express the same two-pool computation, although implementation identities and recipes differ. Source docstrings saying the older variant was “not yet trained” are stale.

The address-selection confirmation JSON reports seed-0/1 choosing 500/466 versus pooled 147/164, with changed-fact both-correct 238/218 versus 1/1 of 256. It also reports no meaningful two-hop advantage. This confirms the brief's distinction between choosing and chaining; it is not an extra retrieval-ladder replication.

The local two-lookup design already proposes a soft read of the first selected object's embedding as input to a second request, and an unchained comparison. This review does not claim to have invented that proposal. Its distinctive contribution is the stronger tied/orthogonal comparator, explicit upstream-vs-handoff intervention, and stricter replication and erasure protocol.

No completed 12k `key_pool=true` report was found in local Claude run JSONs. Baseline seed 5–14 log files are zero bytes, with no corresponding completed run JSONs. No remote status was checked. Checkpoint SHA fields were copied from reports rather than independently verified. The fixed base source is verified by its manifest, but current non-archived wrappers may postdate the runs; preserve this provenance limitation.

## B. Mechanism and prior-art audit

Methods were opened for the close matches below. Publication years were taken from papers rather than search-engine “published/crawled” age labels, which sometimes mislabeled old PDFs.

| Work | Methods inspected; assessment |
|---|---|
| [TensorLog (2016), §3](https://arxiv.org/html/1605.06523) | Logical variables/literals become factor-graph components and differentiable message passing. Supports the equivalence between relational execution and numeric operations; no claim that the proposed tuple constraint system is new. |
| [Neural LP (2017), §§3.2–3.3](https://arxiv.org/html/1702.08367) | One-hot entities, relation matrices, learned attention over operators and previous states. The entity-transport idea survives only as an application/optimization bet, not a novel algorithm. |
| [End-to-End Memory Networks (2015), §2.2](https://arxiv.org/html/1503.08895v5) | Adjacent output/input embedding tying is explicit. “Preserve the space across hops” alone is already established. The exact-hard-code argument in the brief is our elementary derivation, not a result claimed by this paper. |
| [Key-Value Memory Networks (2016), §§3–4](https://aclanthology.org/D16-1147.pdf) | Separate key and value encodings and iterative reads; structured address/content representations. Close ordinary baseline for pooling and field separation. |
| [Neural Symbolic Machines (2017), §2.2](https://aclanthology.org/P17-1003.pdf) | Continuous keys refer to symbolic variable values stored by an interpreter. Same central separation of learned references and exact symbolic contents; weak-supervision training does not establish that Premonition's curriculum will work. |
| [MAC (2018), §2.2](https://arxiv.org/html/1803.03067) | Separates control and recurrent memory; learned read/write units. Shared ingredient, not exact identity preservation. The Stanford PDF fetch failed, but arXiv methods were available. |
| [NPI (2015), §§3, 4.3](https://arxiv.org/html/1511.06279v3) | Recurrent controller with a program library and environment operations; fixed-core addition of new programs. Old-call protection is already discussed. Its supervised traces are richer than unordered evidence. |
| [Neural Production Systems (2021), architecture section](https://arxiv.org/html/2103.01937) | Selects rules and bound entities to update object states. Shared modular-rule ingredient; not evidence for exact binding, deletion or retention in this project. |
| [Local Module Composition (2021), §3](https://arxiv.org/html/2111.07736) | Local relevance/structural scores select modules; expansion learns new modules. Router selection is a real part of retention, not a problem solved by merely freezing module weights. |
| [Compositional Attention (2022), §3 and appendix B](https://arxiv.org/html/2110.09419) | Separates search choices from value-retrieval choices. Related dependency removal; differs from transporting an entity coordinate. It also identifies optimization difficulties in learning the selection mechanism. |
| [RAG (2020), §2](https://arxiv.org/html/2005.11401v4) | Marginalizes document-conditioned predictions. Close computational precedent for interpreting before aggregation; its pretrained components cannot be imported as uncounted expertise. |
| [How Do Transformers Learn Variable Binding in Symbolic Programs? (2025), §2](https://arxiv.org/html/2505.20896v1) | From-scratch transformer experiments on variable dereferencing and causal analysis are counterevidence to an impossibility claim. Their task/scale do not establish efficiency of Premonition or this proposal. |

### Current-work search and verification limits

Searched through the task's actual date, **19 September 2026**, including queries combining variable binding, exact pointers, compositional reasoning, relational joins, query/key optimization, skill induction and continual module composition with 2025/2026. Search is not exhaustive and cannot certify absence of prior art. Only primary sources inform the comparisons; review/blog snippets were discovery aids.

- [Lifting Traces to Logic (May 2026)](https://arxiv.org/html/2605.01293) describes programmatic skill induction for foundation-model agents. Its use of modular control and dynamic bindings reinforces the crowded prior art; its setting does not provide an allowed ready-made teacher or result for this model.
- [How to Build Marcus's Algebraic Mind (May 2026)](https://arxiv.org/html/2605.21379) proposes XOR/shift binding. Do not use its exactness assertions as validation here. In its displayed additive bundle, swapping two fillers leaves `R1 XOR shift(F1) XOR R2 XOR shift(F2)` unchanged by XOR commutativity, contrary to the adjacent claimed role-swap distinction. This is a check of the displayed formula, not an audit of every implementation or companion paper. It supplies no basis to prefer that substrate.
- [GuardNet / Learning to Reason over Neighborhoods, ICLR-2026 submission PDF](https://openreview.net/pdf/86ad106c52504ec719e56aa7c348f54d9802a920.pdf) was surfaced as a recent differentiable-logic neighbor. The initial indexed PDF opened, but focused follow-up retrieval hit a verification page. Its close computational identity and empirical claims were **not fully verified**; it is not used to settle novelty or predict a gain. Submission status is not treated as acceptance.

No VQ/codebook growth, latent-prediction objective, adaptive halting, fast-weight update, sleep/replay/merging scheme or verifiable-reward algorithm emerged as necessary to the selected computation. They could change capacity, search or optimization, but presently add moving parts without separating the observed address explanations. This is a relevance decision, not a novelty finding or a judgment that those methods cannot work. In particular, fast factual weights or caches would enter the erasure audit; transactional rollback needs an independent audit set; existing paired objectives and ordered-evidence supervision are already project ideas.

## C. Constructive revisions and limits

### Compact records for alternatives not selected

**Tuple constraints.** State is one candidate tuple table per query clause, with shared variable identifiers. Update a table by removing rows lacking a compatible row in a neighboring table on **all** shared variables; for an acyclic query, complete the join/projection after reduction. A learned reader predicts clauses/roles from answer/evidence training; supplied query structure would be a separately disclosed hint. Inference operates on predicted clauses, never gold witnesses. Example: `give(Ada,Ben,seed)`, `give(Cara,Dax,bell)`, `owns(Ben,boat)` does not imply anyone gave a bell to a boat owner. Tuple compatibility rejects the spurious Cara/Ben combination. Unlike independent entity marginals, it predicts gains on same-witness conjunctions, with little benefit on functional chains. Local consistency can miss impossible cycles, and exact joins may require large intermediate tables. This is established constraint/database computation.

**Interpret before combining.** State is a distribution over typed outcomes. Update `P(z)=sum_i alpha_i R(z | question, card_i)` instead of reading a pooled card vector. Train the local reader and address scores from the same answer/evidence labels; inference applies the reader to actual candidates before marginalizing. Example: two cards with attribute pairs `(1,1),(-1,-1)` and two with `(1,-1),(-1,1)` have the same uniform mean `(0,0)`, but within-card products have opposite signs. Computing the product before averaging preserves the distinction. This predicts a difference under diffuse reads and nonlinear card interpretation, not under sharp reads or affine interpretation. An ordinary writer could learn that product itself, so this is no general expressiveness theorem. Candidate-wise compute and lost cross-card correlations are the main costs. [Relation Networks, architecture](https://arxiv.org/html/1706.01427v1) provide another primary precedent for learned processing before aggregation; only this ordering is used in the comparison.

**Separate pools / early objective.** State remains the current card store and workspace. Compute `key=Wk pool_k(line)` and `value=Wv pool_v(line)` instead of projecting one pool twice; alternatively keep the shared pool and train the first request before answer-only saturation. Ordinary inference stays unchanged. Example: for `Ada color blue`, a value scorer can emphasize blue while a key scorer can preserve Ada/color. Supervision is the existing answer and evidence loss, with the auxiliary one-hop target specified in T. A longer answer-only phase should hurt a genuinely conflicting shared pool more; an early-objective rescue with no architectural benefit favors the optimization explanation. Both can fail if the reader itself omits identity or the relation controller is wrong. No novelty: local code already implements the architectural option.

The initial strongest candidate was direct identity transport. Literature and the critic exposed two reductions: it is relational execution under another name, and a competent hard tied lookup can be the same computation. The revision is therefore **a narrower causal diagnostic**, not an attempt to rename the idea into novelty.

The remaining potentially consequential question is whether removing repeated identity reconstruction makes procedure acquisition easier when the next operation depends on retrieved contents. That requires a new conditional-control task, an exact-executor baseline, matched supervision, and explicit A→B measurement. Static chains and correct extraction from two supplied cards cannot answer it.

For the second strong candidate, frozen callable procedures, the same audit found NPI already contains the retention mechanism and the new-key interference issue. The revision focuses on acquisition efficiency and usable dispatch, rather than reporting unchanged old weights as evidence of continual learning. Either candidate may prove useful without being novel; neither has demonstrated benefit in this session.
