# Under-covered brain mechanisms: evidence, prior work, and tests

Research date: 2026-09-20. Astra. Track A only. **Research and design; no experiments run.** “Under-covered” refers to a specified computation, not to a brain-region name. The independent shortlist was settled before consulting Fable's reports.

## Short answer

Most of the obvious ideas have already been tried in AI. Three narrower questions remain worth considering: briefly quieting the circuits most active during replay, alternating between possible futures, and giving similar memories different internal “barcodes.” None is a discovered recipe for original thought.

I would first test temporary inhibition after replay. It is cheap, fits our current model, and could help preserve older skills during repetitive practice. But AI researchers already proposed the idea, and ordinary dropout may work just as well. The experiment must compare them.

The other two need bigger toys: choices between routes, and recall of earlier stories. Finish experiment 19, investigate the stopping bug separately, then run this small retention test. A positive result would establish a useful training rule on this toy—not creativity.

## Survivor table and ranking

| Rank / mechanism | Class of the narrow mechanism | Confidence it is under-covered | Biological evidence | Current-toy fit, 1–5 | Build cost |
| --- | --- | --- | --- | --- | --- |
| 1. BARR-inspired, recent-activity suppression after rehearsal | **UNTESTED**, bounded implementation search; previously proposed for AI | Low–moderate; activity-dependent inhibition itself is TESTED | Moderate: recording plus causal manipulation in one rodent study; independent replication not found | **4**, for retention; 1 for original ideas | Small: training hook, zero new trained weights |
| 2. Adaptation-driven alternating theta sweeps | **BIOLOGY-MODEL ONLY**, for the specific alternation mechanism | Low–moderate; theta learning and diverse search are TESTED | Moderate for alternating sweeps; causal necessity for alternative search unestablished | **2**; needs competing paths | Medium: branch task and equal-budget search |
| 3. Content and event barcodes in the same recurrent population | **LIGHTLY TESTED** | Moderate for limited coverage, low for any claim of novelty | Moderate: chickadee recordings; causal index function and broad replication unestablished | **2**; needs episodic recall | Medium–large: memory task, retrieval controls |

An UNTESTED label is **not** “nobody has thought of this,” nor a claim that the mechanism's broad algorithmic family is new. BARR retains that label only for the short-lived, recent-activity-targeted intervention after replay. If that distinction is too narrow for a novelty claim, classify the proposed engineering method as an activity-dependent regularizer and keep the experiment; do not manufacture a discovery.

## What was searched, and what the labels mean

I searched all 20 starting topics (treating reuniens and claustrum separately), plus BARR and non-Hebbian path-vector memory. The exact query ledger below records 130 queries, including at least four mechanism/learning searches per topic, extra survivor searches, and venue searches. Search results were followed to primary papers, author copies, arXiv, and conference proceedings. Fable's files were consulted only afterward.

I also queried the public OpenAlex citation graph for the key papers. “Screened” below means title, date, venue and DOI metadata screening, followed by reading relevant candidates; it does **not** mean reading every citing paper in full. Older, highly cited papers were bounded to the first 200 citing records ordered by citation count. New papers often had fewer records, all screened. Preprints and journal versions were deduplicated conceptually when counting implementations. Index omissions, imperfect metadata and blocked full texts remain real limitations.

- **UNTESTED:** no implementation of the specified mechanism improving an ML learner was located in this bounded search. A proposal can exist.
- **BIOLOGY-MODEL ONLY:** a mechanism has been simulated to explain neural phenomena, without an identified demonstration that it improves task learning. A paper appearing at NeurIPS is not automatically a learning improvement.
- **LIGHTLY TESTED:** one or two small direct/closely related task demonstrations, with no matched-compute comparison established by this review. Missing controls are qualified if the full methods were inaccessible.
- **TESTED:** sufficient task-learning precedents to reject “missing from AI.” This does not establish that every implementation works.

A neural simulation that demonstrates improved memory binding on a task counts as a task demonstration even if published in a neuroscience journal. This is why barcode memory is not labeled biology-only.

## 1. Temporary suppression after replay: the top pick

### Biology and evidence

After learning, some hippocampal cells replay recent experience during sleep. Karaba and colleagues identified BARR events associated with inhibition of recently recruited CA1 ensembles through a CA2-related inhibitory circuit. Disrupting the process affected memory in their rodent experiments. This is **moderate causal evidence for memory regulation in the tested preparation**, not evidence that inhibition creates new ideas. I found no independent replication establishing the same BARR circuit mechanism. [Karaba et al., Science, 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11428313/)

The possible relevance to new ideas is indirect: prevent a recently dominant representation from crowding out other useful representations. The counterargument is strong: reducing activity may merely impair learning, or duplicate ordinary regularization. Biology may need this circuit to control recurrent excitation, a problem our small networks do not share. The under-explored part is the recent temporal targeting, not “brains inhibit neurons.”

### Kill search and nearest prior work

Nine exact queries are recorded under **BARR** below: four initial queries, four additional inhibition/dropout queries, and a venue query. The Science paper's citation trail yielded 37 indexed citing records, all screened.

The AI idea is already explicit in **Rudroff, Rainio and Klén's 2024 perspective**, which proposes hippocampus-inspired selective inhibition for the stability/plasticity problem. It provides a proposal, not a benchmarked implementation. This is prior conceptual credit, not biological evidence. [Perspective and full text](https://doi.org/10.3390/brainsci14111111)

Two much closer practical precedents than generic dropout must shape the experiment:

- **Selfless Sequential Learning**, ICLR 2019, uses neural inhibition to encourage reusable, less interfering representations. [Aljundi et al.](https://arxiv.org/abs/1806.05421)
- **SCoMMER**, AAAI 2023, uses sparse coding and activity-dependent heterogeneous/semantic dropout in a dual-memory continual learner. It already tests allocation and interference control on learning tasks. [Sarfraz et al.](https://ojs.aaai.org/index.php/AAAI/article/view/26161)

A further 2026 neural simulation studies anti-Hebbian plasticity stabilizing replay dynamics; it is relevant but does not benchmark the BARR translation proposed here. [Baron, Diba and Amarasingham](https://doi.org/10.1002/hipo.70089)

**Verdict:** no task-learning implementation of this specific recent-pulse protocol found; low–moderate confidence, not priority. A win over no inhibition alone would be insufficient. Our cumulative-activity control is inspired by the nearest prior, **not a claimed reproduction of SCoMMER's full method**.

### Concrete translation

Use the existing v4 reg+ctx dispatcher D, width 32, 24,035 trained parameters, and the frozen canonical lookup operator. The controller still sees its question and own transcript, not the story. During a separate offline block, alternate an ordinary rehearsal update with an update in which the readout channels most active in the previous ordinary update have gain 0.5. Select exactly 8 of 32 channels, using a detached batch mean of absolute head-input activity. All other gains are 1. No extra loss, labels, generated question types, trainable gates or extra optimization steps.

Apply the gain to the existing pointer-head query and STOP-head input; preserve raw state, register updates, candidate keys, and operator. The code has different pointer and STOP inputs, so collect both explicitly as specified in the companion draft. The trace is 32 floats, plus common control statistics. Zero new trainable parameters. All inhibition is off during evaluation.

**Transformer version:** apply the same training-only rule to the last decoder hidden vector before vocabulary logits: 12 of its 48 channels. A larger transformer could use the same channel-level readout hook during continual training. Neither scale nor benefit is established.

### Falsifiable test

After fresh normal training on one-to-three-call questions, clone the final checkpoint into five equal-update arms. Rehearse **only intact previously seen questions**, with a fixed bias toward one easy question type. Compare recent targeted suppression against no suppression, randomly targeted suppression, cumulative-activity suppression, and uniform gain reduction. This changes inhibition alone; it is not experiment 19's question generator.

Primary measurement: retention of previously successful two/three-call questions ending in relation 10, in 6- and 16-person worlds. Composite relation-10 questions remain absent from all training. Three seeds, **2000–2002**, all reported. D must first pass both ordinary fit and those short held-out cells at ≥61/64 per cell/seed; otherwise retention cannot be claimed.

After rehearsal, require ≥58/64 strict successes in every primary cell, a ≥13/64 paired advantage over no suppression, and ≥7/64 over **each** of the other three controls; ordinary retention ≥61/64 and edit-pair guards ≥58/64. Fresh confirmation uses 512 units/cell with proportional marks. Apply the same final comparisons to the plain transformer on identical raw data, but call its result retention only in cells it already solved before rehearsal. Full gates, budget and exclusions are in the [preregistration draft](20-top-mechanism-preregistration-draft.md).

**Nulls count:** controls matching the intervention, a baseline that never forgets, damaged ordinary skills, or failure on fresh confirmation means no demonstrated value under this protocol. Do not increase the rehearsal bias after seeing a ceiling. The main artefact is regularization or extra work masquerading as a special memory mechanism; equal masks, controls, schedules, and fixed unrolls address it. No gate may read chain length, correctness, relation identity, remaining steps or gold STOP.

## 2. Alternating theta sweeps: test alternatives in a branching toy

### Biology, promise and objection

Vollan and colleagues recorded left/right alternating sweeps in entorhinal–hippocampal spatial representations. Ji and colleagues reproduced alternation with firing-rate adaptation in a systems model. These establish a phenomenon and a plausible generator, not that alternation is required for creative planning. [Vollan et al., Nature, 2025](https://www.nature.com/articles/s41586-024-08527-1); [Ji et al., Current Biology, 2025](https://discovery.ucl.ac.uk/id/eprint/10206261/)

A 2026 navigation study links theta sweeps to goal direction and correct choices, with a continuous-attractor model. It strengthens the planning interpretation but does not causally establish the advantage of left/right alternation. [Yu et al., Nature Neuroscience, 2026](https://www.nature.com/articles/s41593-026-02365-2)

The potential benefit is preventing repeated consideration of nearly identical options. The obvious objection is that standard diverse search already does that, often with better bookkeeping. The exact neuronal alternation has limited cross-study support; related theta phenomena are not replications of its proposed computational function. It may be under-explored because it is recent, spatially specific, and serial work is awkward on GPUs.

### Kill search

The ledger records nine queries for this topic. I screened all 56 indexed citations of the main neuroscience paper and 22 of Ji's model, plus venue searches.

**General theta-based learning is already tested:** George and colleagues use STDP and theta phase precession to learn predictive maps. [eLife, 2023](https://elifesciences.org/articles/80663) **Diversity-based candidate generation is already tested:** Diverse Beam Search evaluates it on sequence-generation tasks. [Vijayakumar et al., 2016](https://arxiv.org/abs/1610.02424)

The citation/venue trail reached **NeurIPS 2025 path-integration RNNs** and **NeurIPS 2024 Lie-group motion planning**. Neither inspected method establishes task-learning gains from adaptation-driven alternating sweeps. The latter uses shifted sensory representations to implement operator search; that is a closer precedent than “no planning models.” [Path integration](https://papers.nips.cc/paper_files/paper/2025/file/938fc9c39a6fc95ccf9dedb773363b52-Paper-Conference.pdf); [Motion planning](https://papers.nips.cc/paper_files/paper/2024/hash/c7201deff8d507a8fe2e86d34094e154-Abstract-Conference.html)

One search-indexed OpenReview PDF citing the theta paper remained unidentified behind access controls; see the limitations ledger. It lowers confidence. **BIOLOGY-MODEL ONLY is provisional for the precise alternation, not a claim that theta or neural planning lacks AI implementations.**

### Module and necessary task change

Our current question names one deterministic chain. There are no alternative correct plans to imagine. Do not claim that adding two trials diagnoses the three-call STOP bug.

Use a later toy with **four candidate start people** and a visible target value. Exactly one candidate's two/three-call chain ends at that target. Train with four candidates; test both four and eight, with familiar and new arrangements of distractor branches. All facts remain ordinary LINK/attribute rows; no new primitive is introduced.

For D, use a shared 32→1 linear candidate scorer on contextual candidate embeddings: **33 additional trainable parameters**. It proposes two full native rollouts. A fixed, within-question adaptation rule subtracts cosine similarity to the first selected candidate's representation from second-proposal logits, coefficient 1. Its state is one detached 32-vector; reset at the start/end of each question. This is an engineering abstraction of fatigue, not a biophysical theta model. Train the scorer and controller with final task reward; freeze the operator. A common selector can compare each actually returned value with the **visible goal**; it cannot inspect unexecuted paths or oracle answers. If neither succeeds, use a fixed first-proposal fallback and count the resulting error.

A standard transformer gets the same candidate lists, target and raw stories, two complete decoding attempts and the same visible-goal check. At larger scale the translation is a diversity penalty between successive plan representations.

### Test and controls

Use seeds **2100–2102**, six fresh awake runs across D/T, then equal-update continuations with two rollouts per question in every arm. Controls: independent proposals, sampling without replacement, conventional token/action-diverse beam-2, and an equally sized adaptation trace shuffled across questions. All arms calculate the same scorer and similarity matrices; inactive effects are discarded. Fix 6,000 training updates and batches of 64 questions before implementation. Preserve the ordinary one-to-three-call fit guard; never train composite r=10.

Dev: 64 units in each of four cells, candidates 4/8 × calls 2/3, balanced r8/9; add a goal-changing relevant edit and an irrelevant-edit pair cell for each configuration. Require ≥58/64 correct choice **and strict executed solution** in every cell; ≥13/64 over independent search and ≥7/64 over every stronger control, every seed. Ordinary lookup retention ≥61/64. Confirmation: 512 fresh units/cell, marks 464/512, 104/512 and 56/512; retention 488/512.

Freeze source, data grammar, predictions, candidate-scoring interface, seeds and marks before any run; apply the shared execution rules below. If without-replacement or diverse beam search ties, the specific mechanism adds no demonstrated value. If the two-rollout budget alone helps, report search-budget value only. Main risks are the supplied goal checker, extra calls, a candidate-position hint and learned scorer capacity: give all arms the identical checker, capacity, random candidate ordering, update counts and allocated compute. This is a later **branch-selection experiment**, not an original-thought benchmark.

## 3. Hippocampal barcodes: separate similar episodes

### Biology and existing task models

Chettih and colleagues observed sparse event-specific hippocampal activity during seed caching in chickadees, intermingled with place coding and reinstated at retrieval. This is compelling recording evidence, but the “index” interpretation is not a causal demonstration. Independent cross-species replication of this exact barcode phenomenon was not established by this review. [Cell, 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11015962/)

**A task model already exists.** Fang and colleagues' recurrent network generates barcode-like activity and tests memory binding and retrieval. It includes content-only/barcode ablations and a feedforward construction; those are not new controls invented here. It is one project with a 2024 preprint and subsequent eLife versions, including the January 2026 version—not several independent replications. [Fang et al., eLife](https://elifesciences.org/articles/103512)

Zeng, Recalde, Wiskott and Cheng's 2025 preprint learns flexible storage/retrieval tasks with spatial and episodic representations. Its abstract was checked; full methods were not accessible, so exact controls remain unverified. [Primary preprint](https://doi.org/10.1101/2025.09.21.677534)

### Kill search and verdict

Nine queries are logged; 75 indexed citing records of Chettih were screened. The nearest exact implementation is Fang, not generic attention. Sparse distributed memory and random-key associative memories further kill any broad “random handles are missing from AI” claim. Pang and Recanatesi's non-Hebbian path memory is another task-learning precedent, though not the same barcode construction.

**LIGHTLY TESTED** is the conservative classification: one direct task-model project and one closely related preprint, no matched-compute modern learner comparison established here. The open question is whether recurrently generated, mixed content/index codes outperform cheap independent random keys at the same memory and work budgets.

Barcodes could preserve the distinct experiences from which useful comparisons are later made. Conversely, they may deliberately separate things we want to combine. Biology's shared-cell constraint may offer no engineering advantage over separate key/value arrays. The work is recent, niche, and already has an obvious conventional substitute.

### Module and bigger toy

Do not append a random ID to a visible fact row and call the result episodic memory. Today's solver has the whole story in front of it and no previous-episode memory requirement.

A later task presents 8 or 16 separate six-person stories, each with an observable 32-bit context cue. Reuse the same entity vocabulary across episodes with different facts, then hide the earlier stories. A query supplies a partial context cue and an ordinary one-to-three-call question about one stored episode. Generate cues so the visible partial cue uniquely specifies an episode; impose the same constraint for every arm, independently of model success.

A minimal translation uses a fixed 32→64 cue projection and fixed 64×64 recurrent matrix, four recurrent iterations, and eight active barcode channels. Mix the resulting code with the projected content cue **in the same 64-vector**. Fixed numerical choices, normalization and RNG must be frozen in a later implementation preregistration. A 64×32 fast association matrix binds the visible cue to that mixed vector through a fixed Hebbian outer-product rule. At query time its output scores the stored mixed vectors; retrieve one raw story for the unchanged frozen operator and D. The controller never receives a gold episode number or the stored barcode as a supplied answer.

Budget: **zero additional SGD-trained weights**, 6,144 fixed matrix entries, 2,048 fast plastic values, 64 values per episode, and a bounded raw-story store. This is a small engineering translation, not a replication of Fang's larger network. Memory capacity and bytes are part of the resource budget even when they are not trained parameters.

A large-transformer version would use the mixed event code to address an episodic cache. The plain-transformer control here must receive the same observed history and partial cue, with enough context for every episode and position capacity fixed before training; silently truncating its history would invalidate the comparison.

### Test and controls

Seeds **2200–2202**; fixed 6,000 common solver-training updates, batch 64, no composite r10 exposure. All memory mechanisms run on exactly the same episode bundles. Compare recurrent mixed codes, independent random sparse keys, feedforward sparse expansion, and content-only dense keys. Equalize stored bytes, retrieval operations, projection sizes and the four-iteration allocated budget with discarded computations where necessary. Report useful FLOPs too; padding cannot make resource differences disappear.

Dev cells: episodes 8/16 × calls 1/3 × cue visibility 16/24 of 32 bits: eight cells, balanced r8/9. Primary success requires both correct episode retrieval and strict answer ≥58/64 in every cell, ≥13/64 over content-only keys and ≥7/64 over **both** random-key and feedforward controls, every seed. Two further pair cells at 16 episodes, c3, 16 visible bits change either the queried endpoint or an unrelated stored story: ≥58/64 strict pair successes. A full-story visible guard requires ≥61/64 to establish that retrieval, rather than lookup failure, is being tested. Confirmation has 512 units/cell and proportionally scaled marks. Report plain T separately on the same answer/trace marks; it has no exposed retrieval index.

A random-key tie rejects the claimed need for recurrent barcodes. A benefit only with extra storage, supplied episode IDs, easier cues, or a truncated transformer context is an invalid comparison. Use the shared freezing and wave rules below. This is an interference/recall task, not evidence of recombination or idea generation.

## Shared execution discipline for all survivor designs

These are requirements for later implementation, not experiments performed in this session.

1. One mechanism per experiment; include a zero-effect control through the same hooks. Freeze operator, architecture, optimizer, data and resource budgets, exact marks, all seeds and written predictions, then SHA-256 them **before any run**. Development outcomes cannot choose checkpoints, change parameters or replace seeds.
2. Use new development panels and independently generated untouched confirmation panels. Freeze the confirmation generation recipe before training; generate its bytes after final checkpoint hashes, without predictions, and hash before scoring. Do not score existing sealed confirmation files. Deduplicate semantic fact sets and questions, not just token bytes; exclude all sides of edit pairs and all historical panel/training signatures available. If historical operator-training overlap cannot be reconstructed, disclose the limitation.
3. Each cell is reported per seed, with native success counts, strict traces, paired gain/loss counts and failure modes. Never average away a failing seed or cell. The all-seed gate is an engineering requirement, not a population reliability estimate.
4. Each wave: ≤6 one-thread Mac jobs **or** one consumer GPU. Soft stop at 1,200 seconds, hard deadline at 1,500 seconds, including scoring/checkpointing; chunks/resumption must preserve optimizer, RNG, schedule and data state. Timing feasibility is unmeasured. A future disposable-fixture timing check may set a smaller chunk size **before registered runs**, never change total updates. An incomplete wave is incomplete, not a failed hypothesis.
5. Match updates, raw examples, labels available within each architecture, candidate budgets and allocated tensor work. Report memory, active calls, useful FLOPs and wall time separately. D's pretrained operator and scalar-reward training differ from T's intermediate/line supervision; matched raw data does not mean equal prior training or equal total compute.

## Eliminated or parked candidates

Broad mechanisms marked TESTED are excluded from the shortlist. Narrow remnants are not automatically killed by a related algorithm: they are explicitly parked when the biology does not supply a useful, identifiable intervention.

| Topic | Classification / disposition | Nearest checked prior and reason |
| --- | --- | --- |
| Behavioral-timescale synaptic plasticity | **TESTED** | [Cone, Clopath and Costa, 2025](https://doi.org/10.1101/2025.06.12.659336) develops BTSP credit assignment and task-learning examples. One-shot plasticity is not missing. |
| Excitability-dependent engram co-allocation | **TESTED at the allocation/interference-control level; exact temporal linking parked** | [SCoMMER, 2023](https://arxiv.org/abs/2301.05058) and [Stochastic Engrams, 2025](https://arxiv.org/abs/2503.21436) test allocation/gating in learners. [Delamare et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11112642/) simulates excitability-dependent overlap. These do not prove the exact Cai mechanism is fully implemented. |
| Retrospective offline co-reactivation, included in engram topic | **BIOLOGY-MODEL ONLY / park exact rule** | [Zaki et al., online 2024, print 2025](https://www.nature.com/articles/s41586-024-08168-4) provides causal rodent evidence for linking across days. [2026 fear-memory model](https://doi.org/10.1371/journal.pcbi.1013251) is a close computational follow-up. A visible single-story task lacks episodic separation; adding salience, a temporal tag and an offline update together would confound three changes. |
| Reconsolidation | **TESTED** | [Bottlenecked Transformers, revised 2026](https://arxiv.org/abs/2505.16950) consolidate/reconsolidate selected KV segments and test reasoning. This is a computational analogue, not molecular reconsolidation. |
| Synaptic tagging and capture | **TESTED** | [AVIM, Chen et al., IJCNN 2021](https://arxiv.org/abs/2007.08855) incorporates STC in continual audio/visual learning; [Luboeinski and Tetzlaff, 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC7977149/) tests improved recall in recurrent models. |
| Representational drift as a useful feature | **TESTED** | [Natrajan and Fitzgerald, PNAS 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12625983/) tests robustness from drift; [Pashakhanloo and Koulakov, ICML 2023](https://proceedings.mlr.press/v202/pashakhanloo23a.html) studies SGD-induced drift. Natural drift's purpose remains unsettled. |
| Rotation / orthogonal sensory and memory codes | **TESTED** | [Hebbian context gating, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC9851563/) and [orthogonal-rotational working-memory model, 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC12828889/) are task-model precedents. |
| Activity-silent working memory | **TESTED** | [Masse et al., Nature Neuroscience 2019](https://www.nature.com/articles/s41593-019-0414-3) trains recurrent networks with short-term synaptic mechanisms on working-memory tasks. Not interchangeable with anatomically silent synapses. |
| Schema-dependent fast assimilation | **TESTED** | [McClelland, 2013](https://doi.org/10.1037/a0033812) explicitly models rapid schema-consistent learning within complementary learning systems; [schema/encoding model](https://pubmed.ncbi.nlm.nih.gov/31686197/) adds a later neural implementation. |
| Awake ripple selection/tagging of later replay | **UNTESTED exact transfer rule / park; general prioritization TESTED** | [Yang et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11068097/) identifies which experiences are later replayed. [Mattar and Daw, 2018](https://www.nature.com/articles/s41593-018-0232-z) already tests prioritized memory access. Yang's correlation is not itself a deployable optimal selection rule; calling the two mechanisms identical would overstate the kill. |
| Prefrontal dimensionality switching | **TESTED broad control; exact phrase underspecified** | [Zhang et al., 2025](https://www.nature.com/articles/s41467-025-58011-1) tests a thalamocortical task model; [rapid context inference, 2024](https://www.nature.com/articles/s41467-024-52289-3) already uses trained RNNs. A changed PCA dimension alone is not a module. |
| Cortical traveling waves | **TESTED** | [Keller and Welling, ICML 2023](https://proceedings.mlr.press/v202/keller23a.html); [Muller et al., ICLR 2024](https://openreview.net/pdf?id=p4S5Z6Sah4); [Karuvally et al., ICML 2024](https://proceedings.mlr.press/v235/karuvally24a.html). Task-learning and memory precedents directly kill the gap. |
| Nucleus reuniens coordination | **BIOLOGY-MODEL ONLY / park exact circuit** | [2023 beta-synchronization study](https://doi.org/10.1038/s41467-023-40044-z); [2025 hippocampo-cortical dialogue model](https://doi.org/10.7554/eLife.90826.3). Exact nucleus-specific benefit in an ML learner not found; generic thalamic routing already known and our single-operator toy has no competing systems to coordinate. |
| Claustrum filtering / temporal integration | **BIOLOGY-MODEL ONLY / park** | [2026 functional-connectome study](https://doi.org/10.1016/j.celrep.2025.116821) and [temporal-integration model](https://pmc.ncbi.nlm.nih.gov/articles/PMC13218724/) are relevant biological modeling. Segmenting a claustrum scan with deep learning does not implement claustral computation. No well-isolated creativity rule. |
| Cerebellar contribution to creativity | **BIOLOGY-MODEL ONLY / park conceptual account** | [Pictionary fMRI study, 2015](https://doi.org/10.1038/srep10894) is correlational. [A neurocomputational model of creative processes, 2022](https://doi.org/10.1016/j.neubiorev.2022.104656) supplies a theoretical account; task-level implementation details not verified here. Forward models are already covered. |
| Acetylcholine encoding/retrieval switching | **TESTED** | [Hasselmo, 1993](https://doi.org/10.1162/neco.1993.5.1.32) already demonstrates the interference-control idea in associative memory; publication verified in the [author's list](https://www.bu.edu/hasselmo/publications.html). [2025 cholinergic sleep-state model](https://doi.org/10.1371/journal.pcbi.1013097) is a recent task-model extension. |
| Reduced latent inhibition | **TESTED inhibition/attention models; creativity claim parked** | [Learning to ignore, 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC3895228/) models attention and learning. [Carson et al., 2003](https://doi.org/10.1037/0022-3514.85.3.499) is an association with creative achievement, not evidence that indiscriminately admitting distractors improves invention. |
| Semantic-network flexibility in creative people | **BIOLOGY-MODEL ONLY for descriptive creativity account / park** | [Kenett et al., 2014](https://doi.org/10.3389/fnhum.2014.00407) is a behavioral network comparison; [2016 random-walk model](https://alab.psych.wisc.edu/papers/files/Kenett16CreativityRW.pdf) models search. Neural ideation papers also exist (IJCNN 2015/2016; metadata checked). No clean causal neural mechanism to import. |
| Spontaneous activity as a learned prior | **TESTED** | [SORN, 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2773171/), [learning-induced spontaneous statistics, 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4694925/), and [reward-modulated SORN](https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2015.00036/full) implement/test closely related learning principles. |
| Additional candidate: non-Hebbian path-vector episodic memory | **LIGHTLY TESTED / park** | [Pang and Recanatesi, Science Advances 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11844740/) already demonstrates sequence recall and policy learning. This is a theoretical learning rule, not a newly observed brain mechanism; it requires a rich state-space/world-model task. No matched-compute modern baseline established here. |

Parked does not mean disproven. It means lower value for this model than the three explicit proposals, or too imprecise a mechanism to justify building.

## Recommended order and what success would mean

**Finish 19 as registered → investigate/fix STOP in a separate one-change experiment → test the BARR-inspired retention rule → build branching/episodic tasks only if those capabilities become priorities.** Do not splice the new hook into ongoing experiment 19. Do not bundle a new STOP method into this preregistration.

Experiment 20 deliberately stays at c≤3. It can therefore run against the frozen current v4 even if longer-chain stopping remains unresolved. The priority recommendation concerns engineering effort, not a claim that the BARR hypothesis requires a solved STOP bug. Adopting a future STOP repair as the common base would require a new frozen version before any 20 runs.

The top pick is ranked by **cost, fit and falsifiability**, not by closeness to original thought. If Ben's only priority is generating genuinely new operations, none of these is a justified immediate addition to the present toy.

## What we must not claim

- Nobody knows how brains produce original thought. Recording a neural correlate, perturbing a memory circuit, and demonstrating human creativity are different evidential steps.
- Standard transformers do not have a proven categorical inability to generate original ideas. Our measured baseline failures are about this architecture, supervision, training budget and distribution.
- No claim of general intelligence, consciousness, human-like imagination, or a biological mechanism being “the missing ingredient.”
- Our operator was trained with gold intermediate people. It is not label-free. Simulator answers, intermediate targets, and visible-goal checks are supplied information.
- The current task recombines a known lookup primitive. A longer chain, a preserved skill, a better memory index or two successful candidate trials does not invent a new operation.
- UNTESTED means “not found by these searches,” not “never implemented.” Proposals, name changes, unindexed work and inaccessible methods can defeat a negative claim.
- No “first AI use of BARR” claim: the 2024 AI perspective predates this design. No “first barcode task model” claim: Fang predates it.
- No causal claim from D-versus-T alone: operator pretraining and supervision differ. No success rescued by mean accuracy, a lucky seed, extra updates, training on held-out types, or selected checkpoints.
- No guarantee of a <30-minute complete run. The bounded **wave** protocol is specified; actual throughput has not been measured.

## Comparison with Fable, consulted last

I read REPORT.md and UNTESTED-MECHANISMS.md and the six gap reports' verdicts, evidence and gap/priority sections after the independent search. Their reference lists are not substitutes for verified primary sources.

I agree with the six gap reports' central correction: self-generated practice, restructuring, exploration control, two-phase sleep, promise/value signals and growth/turnover all have AI precedents. Their habit/progress/halting/turnover suggestions were already on the table and are not re-proposed here. I also agree with the newer report's caution about search versus novelty and the need for a diverse-search control.

I disagree with **barcode = biology-model only**: Fang explicitly evaluates binding/recall performance, so under Ben's definitions it is lightly tested. SCoMMER and stochastic-engram work are closer precedents for activity-based allocation than the newer report acknowledges, although they do not eliminate every detail of Zaki's retrospective linking. The exact offline circuit's evidence should not inherit “replicated” from older co-allocation findings.

I lower the fit ratings. Cross-story linking and episodic indexing require earlier stories to be hidden or separated; theta search requires meaningful alternatives. Neither exists in today's unary, visible-story task. Adding a shared temporal key, a salience gate and a Hebbian update together would not isolate one cause. “Backwards only, never forwards” is also too universal: Zaki tested an order dependence in particular protocols, not a law of all memory linking.

Finally, REPORT.md's equation of original thought with replay/select/compress is a useful hypothesis, not an established explanation. Its original combined dream-and-macro proposal changes several things at once. Experiment 19 already narrows that question; experiment 20 must remain separate.

## Search audit and references

All substantive references are linked at the claim or elimination they support. The following ledger makes the negative searches reproducible. Access date throughout: 2026-09-20. Search-engine “published” ages were not used to assign a paper's year; primary publication metadata takes precedence.

### Citation trails

OpenAlex work IDs below make the public cited-by query reproducible: `https://api.openalex.org/works?filter=cites:WORK_ID&per-page=200&sort=cited_by_count:desc`. Counts are index snapshots, include some duplicate versions, and are not exhaustive literature totals.

| Topic / anchor | Work ID | Screened / indexed | Learning/venue follow-through |
| --- | --- | --- | --- |
| BTSP, Bittner 2017 | W2751166226 | 200 / 796 | BTSP task-learning preprints and dendritic network models; venue query below |
| Theta, Vollan 2025 | W4407087309 | 56 / 56 | Ji model; NeurIPS motion-planning paper |
| Theta, Ji model | W4407320080 | 22 / 22 | NeurIPS 2025 path integration inspected |
| Barcode, Chettih 2024 | W4393307763 | 75 / 75 | Fang versions deduplicated; Pang task model; related learning preprints |
| Co-allocation, Cai 2016 | W2404947714 | 200 / 1078 | Delamare, SCoMMER, stochastic-engram venue/arXiv follow-up |
| Offline linking, Zaki | W4404105428 | 38 / 38 | 2026 contextual-fear neural model |
| Engram model, Delamare | W4393393520 | 20 / 20 | Same fear model and overlapping-assembly models |
| Reconsolidation, Nader 2000 | W1608785134 | 200 / 2736 | Targeted search reached Bottlenecked Transformers; direct citation dependence not assumed |
| Tag/capture, Frey–Morris 1997 | W2011882079 | 200 / 1781 | Synaptic task models; AVIM via targeted search |
| Drift, Deitch 2021 | W3193877526 | 200 / 249 | Artificial-network geometry; ICML and PNAS follow-up |
| Rotation, Libby–Buschman 2021 | W3143658323 | 200 / 237 | Hebbian context gating and trained working-memory RNNs |
| Silent memory, Rose 2016 | W2558227737 | 200 / 639 | Synaptic working-memory task networks |
| Schema, Tse 2007 | W2067765425 | 200 / 1309 | CLS/schema models; targeted learning venue search |
| Ripple selection, Yang 2024 | W4393279565 | 109 / 109 | Computational replay/BTSP follow-ups; prioritize-learning search |
| PFC switching, Nigro preprint | W4389766048 | 9 / 9 | Separate primary-model/venue searches; not inferred from a general PFC review |
| Traveling waves, Davis 2020 | W3091926688 | 200 / 281 | ICML/ICLR wave-learning papers |
| Reuniens, 2023 synchronization | W4384820089 | 58 / 58 | eLife dialogue model; venue hits not verified task implementations |
| Claustrum, 2026 connectome | W7122738742 | 6 / 6 | Computational circuit follow-up; segmentation hits excluded |
| Cerebellum, Pictionary 2015 | W2269999235 | 128 / 128 | AAAI Pictionary models classify sketches, not cerebellar computation; 2022 creative-process account separately |
| Acetylcholine, Hasselmo 1993 | W2098251281 | 107 / 107 | Associative-memory learning already in anchor and follow-ups |
| Latent inhibition, Carson 2003 | W2099618981 | 200 / 684 | Attention/conditioning task models from targeted search |
| Semantic flexibility, Kenett 2014 | W2106154564 | 200 / 405 | IJCNN 2015/2016 ideation papers; creativity-scoring ML excluded as implementation evidence |
| Learned spontaneous prior, Berkes 2011 | W2162679451 | 200 / 856 | SORN, active-inference and spontaneous-statistics modeling |
| BARR, Karaba 2024 | W4401607177 | 37 / 37 | 2024 AI perspective; Selfless/SCoMMER through targeted venue search |
| Non-Hebbian paths, Pang 2025 | W4407802699 | 8 / 8 | Task implementation is already in the anchor; no stronger venue implementation located |

The drift/cerebellum metadata queries initially failed and were rerun. An initial dimensionality query matched a general PFC review; it was discarded and replaced by the specific primary preprint above. This matters because a loose title match must not become false citation evidence.

**Unresolved/access-limited details:** the [OpenReview theta-citing PDF](https://openreview.net/pdf/71aa4ba3c6e7b9911bb8fdf2f13201a68455f478.pdf) could not be identified/read beyond indexed references; some ripple/thalamic venue PDFs were challenge-gated. Zeng's full methods were inaccessible. The cerebellar creative-process account's executable-task status was not established. IJCNN semantic-ideation papers were checked as bibliographic records, not used to claim a measured benefit. These limitations weaken negative classifications; they are not evidence that no implementation exists.

### Exact query ledger

Each topic's nearest prior and outcome are recorded above. Queries are copied from this session, including unproductive/name-collision searches. Extra citation-title searches and direct primary-paper opens were also used; only the reproducible minimum and key adversarial follow-ups are enumerated here.

#### BTSP

1. `"behavioral timescale synaptic plasticity" "neural network"`
2. `"behavioural timescale synaptic plasticity" "deep learning"`
3. `"BTSP" "reinforcement learning"`
4. `"behavioral timescale" "continual learning"`
5. `"behavioral timescale synaptic plasticity" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### theta

1. `"alternating theta" "computational model"`
2. `"theta sweeps" "reinforcement learning"`
3. `"left right" "theta" "neural network" future`
4. `"theta sequences" "transformer" alternatives`
5. `"alternating" "theta" "reinforcement learning" -site:wikipedia.org`
6. `"A systems model of alternating theta sweeps" cited`
7. `"Theta-paced flickering between place-cell maps" model neural`
8. `"theta sweeps" "antithetic"`
9. `"alternating theta sweeps" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### barcode

1. `"hippocampal" "barcode" "neural network"`
2. `"Chettih" "deep learning" barcode`
3. `"memory barcodes" "computational model"`
4. `"barcode" "episodic memory" "transformer"`
5. `"Chettih" site:arxiv.org memory transformer`
6. `"Chettih" site:proceedings.neurips.cc`
7. `"barcodes" site:openreview.net hippocampus`
8. `"Unifying spatial and episodic representations"`
9. `"hippocampal barcode" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### engram

1. `"engram co-allocation" "neural network"`
2. `"memory linking" "excitability" "deep learning"`
3. `"offline co-reactivation" "computational model"`
4. `"Zaki" "memory linking" "continual learning"`
5. `"engram allocation" "continual learning"`
6. `"intrinsic excitability" "deep learning" memory`
7. `"offline co-reactivation" "neural network"`
8. `"retrospective memory linking" "reinforcement learning"`
9. `"engram" "excitability" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### reconsolidation

1. `"memory reconsolidation" "neural network"`
2. `"reconsolidation" "deep learning"`
3. `"retrieval induced plasticity" "continual learning"`
4. `"reconsolidation" "transformer"`
5. `"memory reconsolidation" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### tagging

1. `"synaptic tagging and capture" "neural network"`
2. `"synaptic tagging" "deep learning"`
3. `"synaptic tagging" "continual learning"`
4. `"synaptic capture" "reinforcement learning"`
5. `"synaptic tagging" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### drift

1. `"representational drift" "neural network" learning`
2. `"representational drift" "deep learning" benefit`
3. `"representational drift" "continual learning"`
4. `"representational drift" "reinforcement learning"`
5. `"representational drift" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### orthogonal

1. `"memory sensory" "orthogonal" "neural network"`
2. `"orthogonalization" "working memory" "deep learning"`
3. `"rotational dynamics" "continual learning" memory`
4. `"memory codes" "rotation" "computational model"`
5. `"sensory" "memory" "orthogonal" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### silent

1. `"activity silent working memory" "neural network"`
2. `"activity-silent" "deep learning"`
3. `"short term synaptic plasticity" "reinforcement learning" working memory`
4. `"activity-silent" "transformer"`
5. `"activity-silent" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### schema

1. `"schema" "Tse" "neural network" assimilation`
2. `"schema dependent" "deep learning"`
3. `"fast assimilation" "continual learning"`
4. `"schema" "Tse 2007" "computational model"`
5. `"schema" "Tse" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### ripple

1. `"Yang" "Buzsaki" "2024" "memory" selection`
2. `"sharp wave ripple" "selection" "neural network"`
3. `"ripple tagging" "reinforcement learning"`
4. `"sharp-wave" "memory selection" "deep learning"`
5. `"sharp wave ripples" "tagging" "computational model"`
6. `"Selection of experience for memory" machine learning replay -site:reddit.com`
7. `"Yang" "Buzsáki" "memory" site:proceedings.neurips.cc`
8. `"Yang" "Buzsaki" "memory" site:openreview.net`
9. `"Selection of experience for memory" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### dimensionality

1. `"prefrontal" "dimensionality switching" "neural network"`
2. `"dimensionality" "compression expansion" "deep learning" cortex`
3. `"adaptive dimensionality" "reinforcement learning" prefrontal`
4. `"prefrontal" "dimensionality" "computational model" flexibility`
5. `"prefrontal" "dimensionality" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### waves

1. `"cortical travelling waves" "neural network"`
2. `"traveling waves" "deep learning" brain`
3. `"travelling waves" "reinforcement learning"`
4. `"traveling waves" "transformer" cortical`
5. `"traveling waves" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### reuniens

1. `"nucleus reuniens" "neural network"`
2. `"nucleus reuniens" "deep learning"`
3. `"reuniens" "reinforcement learning"`
4. `"nucleus reuniens" "computational model"`
5. `"nucleus reuniens" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### claustrum

1. `"claustrum" "neural network" learning`
2. `"claustrum" "deep learning"`
3. `"claustrum" "transformer"`
4. `"claustrum" "computational model"`
5. `"claustrum" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### cerebellum

1. `"cerebellum" "creativity" "neural network"`
2. `"cerebellar" "creative" "deep learning"`
3. `"cerebellum" "imagination" "reinforcement learning"`
4. `"cerebellar" "creativity" "computational model"`
5. `"cerebellar" "creativity" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### acetylcholine

1. `"acetylcholine" "encoding retrieval" "neural network"`
2. `"cholinergic" "encoding retrieval" "deep learning"`
3. `"Hasselmo" "reinforcement learning" acetylcholine`
4. `"acetylcholine" "transformer" memory`
5. `"Hasselmo" "encoding" "retrieval" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### inhibition

1. `"latent inhibition" "neural network"`
2. `"reduced latent inhibition" "deep learning"`
3. `"latent inhibition" "reinforcement learning"`
4. `"latent inhibition" "computational model" creativity`
5. `"latent inhibition" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### semantic

1. `"semantic network flexibility" "neural network"`
2. `"Kenett" "deep learning" creativity`
3. `"semantic network" creativity "reinforcement learning"`
4. `"creative foraging" "computational model"`
5. `"Kenett" "creativity" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### spontaneous

1. `"spontaneous activity" "learned prior" "neural network"`
2. `"Berkes" "deep learning" spontaneous`
3. `"spontaneous activity" "prior" "reinforcement learning"`
4. `"Berkes 2011" "computational model"`
5. `"Berkes" "spontaneous" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### BARR

1. `"barrage of action potentials" "neural network"`
2. `"BARR" "hippocampal" "deep learning"`
3. `"hippocampal" "reactivation" "reset" "continual learning"`
4. `"A hippocampal circuit mechanism to balance memory reactivation during sleep" "computational model"`
5. `"BARR" "selective inhibition" "neural network"`
6. `"barrages of action potentials" "continual learning"`
7. `"activity dependent" "dropout" "continual learning"`
8. `"activity based" "dropout" "SCoMMER"`
9. `"BARR" "hippocampal" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`

#### nonhebbian

1. `"non-Hebbian code" "episodic memory" "neural network"`
2. `"sequence-specific" "non-Hebbian" "deep learning"`
3. `"Pang" "episodic memory" "reinforcement learning"`
4. `"non-Hebbian code for episodic memory" "computational model"`
5. `"non-Hebbian code for episodic memory" (site:proceedings.neurips.cc OR site:proceedings.mlr.press OR site:openreview.net OR site:arxiv.org)`
