# Reusable computation and compositional reasoning — final sweep

2026-09-19. Research only; no experiments, implementation changes, agents, remote-machine access or spending. Two proposals, one conditionally recommended. Runtime is unknown until measured; this report grants no experiment budget.

**Recommendation, tightened after critique:** demonstrate binding in decoder-visible values, then test the simpler shared repeated reader/query construction. Keep the bounded join as a conditional challenger on one fixed-order task, with no rule bank or program search. Neither supersedes Opus’s pooling controls. Worldwide novelty is unproved.

## Reconciled evidence and dependencies

Both attachments, the specified design/research documents, overnight evidence, source and saved results were read. Old council assignments supply no independent findings; later spec sections govern. Attachments document past work, not renewed authorization.

Milestone-2 supplied-card repair reaches **1024/1024 on both seeds**. Exp-1 final-only Think chooses **181/512** and combines practiced pairs **92/323**; all-loop results are **182/512**, **96/323**. The nearly closed gates make this weak evidence about effective recurrence. Trained no-Think copies perfectly but chooses **166/512**. Gold-only two-hop success can copy the sole attribute; it is not composition evidence.

Exp-2’s longer checkpoint, with four loops and top-1 retrieval, answers **356/512** one-hop, **154/323** practiced two-hop and **14/189** held-out questions; both cards arrive for **1/189**. Earlier validation gives **139/171** first-hop and **0/171** second-hop successes. Correct-relation second fetches increase from zero to nine in the later checkpoint. These are distinct evaluations. Second-seed supplied-card reading fails: **27/512**.

Probes support learned loss of accessible information, not a theorem that one vector cannot represent a fact. Answer-only cards expose values (**2048/2048**) but poorly expose person identity (**116/2048**); retrieval-dominated cards show the opposite pattern. Linear-probe failure does not establish information absence. Initialization exposes both. Thus “single summaries can hold only one idea” overstates the evidence. `card_pools.py` contains prepared, explicitly untrained alternatives. Crucially, the decoder receives **values, not keys**. Decoder key exposure is already proposed in the overnight research note (around line 201), though absent from the prepared implementation; it is not novel here.

**Minimum controls, separated by objective.** For answer-only choosing with supplied cards, compare original versus uniform-mean pooling first. Separate key/value pools introduce no new answer pathway while keys remain unused; that arm cannot isolate dual-channel benefits. For retrieval, compare original/mean/separate pools under the **same evidence-supervised objective**, labeling that supervision as privileged diagnostic information. Mean pooling averages the **same contextual reader states over the same line bounds**, retaining their history; it is neither raw-token averaging nor D-local. No baseline is credited as new research.

The separate Core track records **677/3782**, **632/3782**, **881/3763** held-out-visible hits for old-window 4M/28M and aligned 4M. The last aggregate combines validation/test; final train-heldin is **475/991**. Context, exposure and scored populations differ; capacity is not ruled out. Earlier-label inputs and failed leak gates also preclude primary claims. Its **7,289 / 2460b1347b04…** tokenizer differs from primary **7,068 / 2c9d06aed330…**. Sparse wording plausibly contributes, without isolating the cause.

Two-pool encoding, factorized pointer/relation queries, read-only facts with register-only updates, D-soft, C*, and the hint ladder are already proposed. The mechanisms below must beat those simpler alternatives. Also, `Deriv.steps` sums premise proof sizes in `join()`; it is not sequential dependency depth.

## Literature: six methods examined closely

The search covered recurrence, relational reasoning, interpreters, binding and neural computers. Six methods are evaluated here; published success is not projected onto this model.

1. **Recurrent-depth composition, updated August 2026.** Kohli et al. reuse transformer layers over synthetic graph queries, training on final answers without per-example oracle loop counts. Systematic generalization appears after prolonged optimization; some comparisons match effective depth/FLOPs. This is contrary evidence to “shared recurrence cannot compose.” But inputs use dedicated entity/relation tokens and facts reside in weights. Overthinking, initialization sensitivity, curriculum-dependent depth coverage, and shortcut-driven apparent deep reasoning restrict transfer. D already shares a store and Think weights, so the missing ingredient need not be more sharing. [Paper, §§4–6 and appendices A/F/K](https://arxiv.org/html/2604.07822v2).

2. **Neural Logic Machines.** Relations occupy tensors indexed by objects. Expansion introduces variables, permutation exposes argument orders, min/max reduction implements quantification, and shared small networks combine predicates. This makes variable identity an explicit axis instead of a feature the controller must repeatedly reconstruct. Input predicates are structured; text-to-predicate learning remains ours to solve. Published cost is O(n^B D C²), with maximum arity B; depth limits deductions. Object-count generalization is not evidence for unlimited reasoning depth. [Paper, §§2–3](https://arxiv.org/html/1904.11694).

3. **Neural Production Systems.** A learned rule and its operands are selected separately; the selected rule’s MLP updates a chosen entity slot. Straight-through Gumbel selection enables sparse, reusable interactions. Its experiments concern visual dynamics, not language deduction. Sequential versus parallel application has domain-dependent advantages, and object extraction is a separate dependency. [Paper, §3 and appendix E.3](https://arxiv.org/html/2103.01937).

4. **Neural Harvard Computer.** Coupled data/control memories and shared hard addresses separate algorithm control from payload manipulation; temporal and ancestry links support traversal. Strong reported algorithm transfer depends on learned-beforehand or hand-designed data modules and fitness rewarding correct per-step data and operations. “No memory-access labels” therefore does not mean answer-only supervision. Evolution uses population evaluations, making update counts misleading as compute measures. This is evidence for interface separation, not a cheap end-to-end language recipe. [Paper, architecture and training methods](https://arxiv.org/html/2105.07957).

5. **Neural Execution Engines.** Conditional masks hold algorithm state, a pointer chooses the next region, and binary representations support numeric subroutines. Composed pretrained subroutines execute graph algorithms, but the decomposition is supplied rather than discovered from arbitrary prose. Intriguingly, additional attention-mask supervision hurts extrapolation in an ablation: more privileged targets need not help. Error-free subroutines in controlled numeric domains do not settle noisy binding here. [Paper, §§3–5 and A.2.1](https://arxiv.org/html/2006.08084).

6. **Neural Data Router.** Shared layers combine input-dependent copying with geometric attention favoring the nearest suitable operand. The contribution is adaptive data routing, not simply a stabilizing residual gate. It succeeds on formal compositional sequences; its encoder-only setup leaves variable-length generation open, and baseline hyperparameters required substantial tuning. My inference: proximity is useful in an expression, but can select the wrong fact in arbitrarily ordered cards. Importing its gate alone would repeat an existing project idea. [Paper, §§2–3, conclusion and appendix E](https://arxiv.org/html/2110.07732).

## Proposal 1: bounded relational join — conditional challenger

**Plain explanation.** Make two small tables: who is whose friend, and each person’s attributes. To answer “Mira’s friend’s colour,” match the friend’s name across the tables. The matching operation stays identical when colour becomes shoe size.

**Exact mechanism.** Learned heads produce soft subject, relation and object assignments from the **same decoder-visible values** supplied to competitors. Keys remain retrieval-only. First require successful choosing; identity surviving solely in keys is insufficient. For the ladder, construct F[a,b] for links and A[r,b,v] for attributes. The bounded operation is

`J[r,a,v] = sum_b F[a,b] * A[r,b,v]`.

Compute only the question-selected subject/relation slice, rather than materializing every J entry. Use normalized functional distributions and an explicit unknown channel. One-hop answers read A; two-hop answers use this same readout after the join. Relation recognition comes from visible text, not metadata. Scratch is discarded; cards remain unchanged. No closure engine, module bank, temporal reasoning or plans enter this demonstration.

**Difference and prior art.** This explicitly joins through an intermediate entity instead of learning the next search decision. Its scratch has relational axes, beyond register-only Think. Closest prior art is NLM and relational algebra. The built-in join is an **inductive-bias test**, not learned discovery of reasoning. Give the repeated-reader control the identical learned grounding interface, not merely the same raw text. Worldwide novelty is unproved.

**Bottleneck and strongest objection.** It directly targets the wrong-relation second fetch. But the model must first learn accurate table entries from text. Weak supervision may produce arbitrary latent tables that solve familiar cases without truthful bindings; two learned probabilities can compound errors. A handwritten oracle parser would conceal precisely this failure. The current card bottleneck is therefore a prerequisite, not something joins magically repair.

**Costs and supervision.** F/A storage is n²+RnV scalars. With soft question selectors, aggregate A over relations, compute the intermediate entity distribution, then contract with A: O(RnV+n²+nV), with O(n+V) transient vectors. At n=16, R=3, V=16, F/A alone occupy **2,048 bf16 bytes**, excluding encoding, gradients, cards and optimizer state. Answer loss supplies training; triples, bridge labels and supplied evidence remain privileged diagnostics. Runtime is unknown.

**Explicit algorithm-template split.** Let F be the familiar friend link and A0/A1/A2 familiar attributes. Train on `A0(x), A1(x), A2(x), A0(F(x)), A1(F(x))`. Development validation uses fresh worlds with only these templates. Freeze choices before testing `A2(F(x))`, alongside fresh matched instances of trained templates. A2 must be mastered standalone. Hold surface wording, cardinality and distractor shape fixed; randomly rebind entities and fact values per world. Existing relation-2 evaluations are historical evidence, not untouched tests; a future comparison needs a separately frozen split identity.

This tests **fixed-order composition-role transfer**: a familiar attribute lookup moves to the second position. It does not test reversed operation order, unseen graph topology, longer chains or a new primitive. `F(A2(x))` is generally ill-typed because attributes return values, not people.

**Decisive comparison and explanations excluded.** Compare the single join with the already-proposed factorized query builder, trained no-Think, and repaired final-only Think, all receiving identical decoder-visible values. Fix four/six candidate lines for one/two-hop and prohibit extra retrieval in this privileged diagnostic. Equal inputs exclude improved access, extra facts or reads as explanations; held-out templates exclude memorizing A2 in the second position. Mirror decoys, balanced values and paired question-subject/link-destination changes test against copying any attribute or ignoring the bridge. Irrelevant changes must preserve answers. Final-only remains a necessary comparator: its earlier nearly closed gate did not meaningfully test recurrent computation. This diagnostic does not establish autonomous next-query retrieval; that requires a later common-selector, equal-read comparison.

**Failure criteria.** Do not promote shallow failure or oracle-dependent gains. Use the project's predeclared practical margins for the applicable claim with adequate paired visit-clustered uncertainty; there is no standalone three-point equivalence rule or new five-point screen. A cheaper model is preferable only when the accepted accuracy tradeoff is established. Wide intervals are inconclusive. Preserve one-hop accuracy and causal invariance across precommitted seeds.

**Attribution and reserve.** Give the simpler repeated reader the same learned relation/operand interface and supervision; otherwise a win may be input formatting alone. No gold parser or added traces in the join arm. Typed-program search remains reserve after these controls: spurious programs, combinatorial search cost, and mixtures succeeding while the selected program fails require separate evaluation. No search is part of this recommendation.

## Proposal 2: sparse reusable rule modules over bound operands — defer

**Plain explanation.** Reuse a little instruction on two named boxes, updating only the destination. This alternative is evaluated for completeness, not recommended for the next demonstration.

**Mechanism.** Four scratch slots and four learned two-input MLPs; select `(rule, destination, source)` and update only the destination. Modules share across positions and steps. Slots read immutable cards, use randomized entity bindings, and receive no oracle rule-ID or operand targets. Fix application count independently of proof labels.

**Prior art and bottleneck.** An NPS transfer, with Harvard-style control/data separation: new here, not worldwide novel. Reusing operators across bindings targets positional habits, but modules can specialize to positions or collapse onto one frequently used module.

**Costs.** Routing scores roughly RS+S² pairs; each selected MLP costs O(d²). Four `2d→d→d` MLPs contain roughly 12d² weights, excluding routing. Scratch needs Sd scalars plus card-read state. Serial dispatch may erase savings. Final-answer training only; traces require a privileged diagnostic.

**Comparison and failure.** Use the same fixed-order template split above against one shared MLP conditioned on an operation embedding, with identical slots, reads and final-only supervision. Include trained no-Think. Defer if the shared operator matches at lower measured cost, success requires traces, or results hinge on one seed. Module-use diversity alone establishes nothing; require correct answers and selective operand sensitivity.

## Common decision discipline

No run is authorized. Preserve label-free preprocessing and recorded v2/checkpoint identities, immutable evaluation, frozen source/data, and three precommitted finalist seeds. Use validation for selection; never rebrand previously examined test items as untouched. Cluster paired uncertainty by visit, with the existing coverage floors and primary decision margins; the narrower proposal screen above is not a replacement verdict. Separate primitive novelty, wording, binding, proof size, evidence count and actual dependency depth. Fix evidence availability and read count independently of loops. Account for decoder passes, preparation, failed trials, scratch bytes and episode encoding; amortize only over valid repeated queries. Runtime and any efficiency claim await measurement.

**Local evidence locations:** `artifacts/opus-ovn-20260918-235851/SUMMARY.txt`; its `exp1/tests/`, `exp2/tests/bypass-k1-s0-4000-longread.json`, `exp2/hop2_miss.json`, and saved probes; `artifacts/benspc/{20260919T090156Z-ddb74eb1,20260919T091253Z-7e81df09,20260919T092801Z-1330ff6a}/artifacts/`; `premonition/identity.py:35`; `learnlab/village/oracle.py:110`. These were read locally; no reported test or training run was rerun.

## Focused cross-critique of 03-learning.md

Read the revised [learning report](/Users/ben-hannan/Desktop/projects/beautiful-model/design/research/final-sweep-2026-09-19/03-learning.md). **H1 is a plausible binding objective after representation repair**, not a demonstrated retrieval remedy. Verified value swaps with identical word inventories force identity-sensitive answers; invariance alone permits constant predictions. Its identical-example, grouped-cross-entropy control appropriately separates added data/grouping from the objective. Require both answers correct on changed pairs and correct invariant pairs.

**Oracle boundary:** simulator outputs may supply offline training answers; label-free inputs do not mean unsupervised learning. Pair roles, evidence IDs, bridge entities and change flags must not become model inputs, inference rewards or test-driven selection signals. Construct pair relations from training answers where possible; disclose any additional oracle structural selection. Verify complete worlds, not presumed irrelevance from missing evidence tags. Pair siblings remain in one visit cluster. A benefit from labels/grouping alone is not an objective benefit. Detached hard ASK still prevents H1's answer loss from directly training next-query scores.

**H2** explicitly uses privileged bridge pairing and correctness-based eligibility. That honesty is essential; report the eligible denominator and all-case retrieval, not only successful first-hop subsets. Consistency alone can copy teacher mistakes.

**Replay:** revised 03 no longer proposes rule-boundary replay; retention is postponed. Keep it there: no stable retained procedure or measured forgetting exists yet. Later compare equal-budget uniform replay before rule-conditioned replay, whose oracle boundaries are extra structural information. No experiment is authorized.
