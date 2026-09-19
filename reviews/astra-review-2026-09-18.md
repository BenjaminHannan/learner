# Astra research review of Premonition (2026-09-18)

Verbatim, as pasted by Ben. Its Experiment 1 changes were adopted into `design/06-premonition-mini-spec.md` §10.

---

**Verdict:** Premonition’s core idea is sound, but the full design contains far more machinery than the evidence currently justifies. A small recurrent reasoner with explicit memory is a credible route to efficient reasoning; it is also a well-established research direction, so the contribution must come from measured advantages. Experiment 1, with §9 applied, can establish a useful result about memory-assisted reasoning. It cannot establish lifelong learning. Your strongest opportunity is a small system that **learns new procedures progressively faster while retaining old procedures under fixed storage and compute budgets**. I would pursue that directly and postpone the growing codebook, private-language RL, learned sleep clock, and drives.

I read the spec, including §9’s overrides, the decisions and research memos, and relevant implementation. I checked the literature below; I did not run training. Numerical targets below are my proposed research criteria, not predicted results.

**1. The core thesis**

“Small reasoner + external store” is credible because reusable computation and storing arbitrary information impose different demands. Remembering a new person’s location should not require gradient descent over millions of weights.

But “will a well-tuned transformer with retrieval always match it?” has no general answer. A transformer can implement your controller, and your think block already uses transformer layers. Your potential advantage is a useful **inductive bias under a particular resource budget**, not an exclusive capability unavailable to transformers.

The closest prior art is older than your comparison list:

| Work | What it establishes—and what remains yours to demonstrate |
|---|---|
| **Sukhbaatar, Szlam, Weston & Fergus, 2015, End-to-End Memory Networks; Miller et al., 2016, Key-Value Memory Networks** | Recurrent, multi-hop reasoning over external memory, including separate addressing and value representations, already exists. Premonition-mini is conceptually close to this family. These should influence your simplest baseline. [Memory Networks](https://arxiv.org/abs/1503.08895), [Key-Value Memory Networks](https://aclanthology.org/D16-1147/) |
| **Borgeaud et al., 2022, RETRO** | Explicit retrieval can substantially reduce the parameter count needed for competitive language modeling. It does not establish continual acquisition of reasoning skills. Your live, mutable episode store differs from RETRO’s large retrieval corpus. [Paper](https://proceedings.mlr.press/v162/borgeaud22a/borgeaud22a.pdf) |
| **Berges et al., 2025, Memory Layers at Scale; Cheng et al., 2026, Engram** | Separating some storage from dense computation can improve the compute–accuracy tradeoff. Their memory includes trained parameters; it is not equivalent to your instantly written factual cards. Neither validates your proposed consolidation process. [Memory Layers](https://proceedings.mlr.press/v267/berges25a.html), [Engram](https://arxiv.org/abs/2601.07372) |
| **Behrouz, Zhong & Mirrokni, Titans, 2024/2025; Behrouz et al., 2025, Nested Learning** | Test-time neural memory updates and multiple update timescales are close conceptual precedents. Titans first appeared December 2024. These papers support investigating adaptive memory, but do not establish that your cards, sleep schedule, or skills/facts boundary are superior. [Titans](https://arxiv.org/abs/2501.00663), [Nested Learning](https://abehrouz.github.io/files/NL.pdf) |
| **Wang et al., 2025, HRM; Jolicoeur-Martineau, 2025, TRM** | Small recurrent networks can solve substantial structured problems. Recurrence and deep supervision are relevant ingredients. Their puzzle results are not evidence of lifelong learning or general language understanding. TRM’s ablations also warn against attributing gains to an elaborate biological story. [HRM](https://arxiv.org/abs/2506.21734), [TRM](https://arxiv.org/html/2510.04871v1) |
| **Balestriero & LeCun, 2025, LeJEPA; Nam et al., 2026, Causal-JEPA** | Predictive latent learning and object-level masking have substantive precedents. Applying them to village entities is a reasonable experiment; benefits for your text reasoning and continual learning remain **uncertain**. [LeJEPA](https://arxiv.org/abs/2511.08544), [Causal-JEPA](https://arxiv.org/abs/2602.11389) |
| **Behrouz, Hashemi, Javanmard & Mirrokni, 2026, Language Models Need Sleep** | Consolidation, replay, upward distillation, and generated practice already form an explicit “sleep” research program. Your transaction mechanism is an engineering distinction whose learning benefit needs an ablation. [Paper](https://arxiv.org/abs/2606.03979) |
| **Lee, McLeish, Goldstein & Fanti, 2026, Do Language Models Need Sleep?** | A different paper: offline recurrence consolidates context into fast weights before clearing the attention cache. This concerns context processing and compute allocation, rather than automatically establishing persistent acquisition of general skills. [Paper](https://arxiv.org/abs/2605.26099) |

The fast/slow learning inspiration itself is established in **McClelland, McNaughton & O’Reilly’s complementary learning systems theory, 1995**. [Paper](https://pubmed.ncbi.nlm.nih.gov/7624455/)

**Your honest novelty today is modest at the mechanism level.** The combination could still produce valuable research. The strongest contribution would be a reproducible result showing that a particular memory/update design improves continual procedural learning at bounded cost. I would not claim that the exact combination is unprecedented without a more exhaustive search.

**2. Experiment 1**

It is a sensible first engineering experiment. A win would convince me that your implementation has a useful advantage on this task. Its persuasiveness depends heavily on the comparator.

**The single most valuable change: combine C2 and E into one strong baseline.**

Give a transformer reasoner:

- The same anonymization and copying infrastructure.
- The same oracle evidence supervision.
- Iterative retrieval, with later requests conditioned on earlier retrieved information.
- Comparable answer supervision and a comparable opportunity to spend additional reasoning steps.

Call it **C\***. Test a roughly parameter-matched version and the existing roughly 5M-parameter version.

**Beating retrieval without pointers and pointers without retrieval does not establish that your combination beats a transformer given both.** Matching evidence labels alone also does not match the benefit of repeatedly supervising answers during reasoning.

There is a related training issue in the revised design: Core training retains previous answers, whereas evaluation removes them. Train a question-centered baseline on a label-free prefix with **only the current answer as the target**. That avoids penalizing the baseline for relying on information available during training but absent during evaluation.

For a cheap diagnostic, also run E with a context long enough to fit the approximately 2.2k-token visits. This tests whether the apparent architectural gain mainly reflects the imposed 736-token window.

**Before full comparisons, run the oracle-evidence diagnostic.** Give both reasoners the correct evidence lines during training and evaluation, as an explicitly privileged diagnostic:

- Target **≥95% on familiar operators at depths 1–3**, with fresh names.
- Then measure depths 4–6 separately.
- If performance is poor with correct evidence, retrieval is not the main problem.
- If oracle-evidence performance is strong but ordinary performance collapses, work on retrieval and binding.

This diagnostic is likely to save more money than adding another architectural component.

The village is artificial, but that is acceptable. It resembles the role played by **Weston et al.’s bAbI tasks, 2015**: controlled tests of prerequisites for reasoning. The limitation is that success establishes those prerequisites under the generator’s assumptions. [Paper](https://arxiv.org/abs/1502.05698)

Your held-out split currently bundles substantial changes. The scheduler (`learnlab/village/scheduler.py:10`) holds out R8, reserves mixed-family derivations for test, and increases depth. Consequently, “held-out accuracy” mixes:

- New names.
- New wording.
- Greater depth.
- New combinations of known rules.
- A new rule family.

Report these separately before reporting their intersection. A model’s failure to understand an entirely untrained operator is different from its failure to compose familiar operators.

Two measurement changes would strengthen the result:

- Report **both twins correct**, plus invariance on questions whose answers should remain unchanged.
- Use at least **three precommitted training seeds** for the primary comparison. Visit bootstrapping does not measure training instability.

Sixty visits is a minimum coverage rule, not a power calculation. Illustratively, if paired visit-level differences have standard deviation 0.30, a normal approximation gives a one-sided 99% uncertainty margin of about **9 points at 60 visits**, versus **2.2 points at 1,000**. Estimate the actual variance in a pilot.

**My stop rules:**

- If D and C\* are equivalent within approximately 3 points and C\* is cheaper, adopt C\* as the core.
- If D beats D-noask but not C\*, retain the memory conclusion; drop the claim that your controller is superior.
- If neither model reliably solves shallow questions with gold evidence after a bounded tuning effort, stop architectural expansion and fix the representation, objective, or task.

None of these outcomes refutes explicit memory as a direction.

**3. Architecture weak points**

These are the five decisions I would distrust most.

| Decision | Likely failure | Better first alternative |
|---|---|---|
| **Growing discrete codebook followed by RL in that language** | You simultaneously learn representations, their semantics, and a policy operating on them. Permanent IDs do not guarantee permanent meanings. Large quantization error can indicate nuisance variation rather than a missing concept. | Use continuous recurrent states first. If discrete execution is needed, start with a small fixed vocabulary of typed operations and pointers. Add learned codes only after demonstrating a measurable benefit over this baseline. |
| **Sleep-only updates plus many sleep mechanisms at once** | Benefits become impossible to attribute; delayed updates can slow adaptation. Replay, resets, perturbations, distillation, and dreaming may interfere. | Keep periodic update batches if you like the operational separation. Start with ordinary supervised updates plus replay. Compare periodic versus frequent updates at equal total compute before learning a sleep schedule. |
| **A strict skills/facts boundary** | Procedures contain assumptions; schemas encode statistical facts. Trying to eliminate all factual information from weights can also eliminate useful generalization. | Make the boundary operational: unpredictable, mutable bindings must remain externally correctable; reusable regularities may enter weights. Test random rebinding and corrections rather than demanding semantically “fact-free” weights. |
| **Treating contextual card vectors as isolated propositions** | A card can contain information from earlier lines because its embedding comes from the recurrent reader. Removing one source card need not remove that source’s information. Provenance becomes weaker than the diary pointer suggests. | Compare line-local card encoding with contextual encoding. Preserve exact source text and explicit timestamps. Use complete re-encoding after source interventions when testing causal dependence. |
| **Fixed, rule-based name binding into 16 IDs** | It solves spelling under your grammar, not general reference resolution. The capacity bound and perfect capitalization conventions become hidden task assumptions. | Keep it as a controlled preprocessing component shared by all contenders. Later test variable-sized entity tables, aliases, ambiguous references, and objects/places as entities. Do not mix those changes into the first reasoning experiment. |

The contextual-card concern follows directly from the card writer (`premonition/model.py:171`) pooling recurrent reader outputs. It is a limitation on interpretation, not an assertion that the implementation is incorrect.

**JEPA:** because your simulator supplies exact targets, first compare against ordinary prediction of observable state changes conditioned on actions. Predicting the next scene without conditioning on the event can mainly train a model of the narrator’s randomness. Entity masking may help, but hiding an entity is not automatically equivalent to a causal intervention.

**Drives:** start with uniform sampling, a simple success-band curriculum, and uniform replay. Learning-progress scheduling should earn its complexity against those controls. It can mistake noisy fluctuations or recovery from forgetting for useful progress.

**4. The smallest convincing continual-learning experiment**

I would build a **20-lesson procedural-learning stream**. New names and locations alone are insufficient: a frozen interpreter with a growing database can handle those.

Each lesson should introduce a new learnable rule composition or procedure—for example, a permission-dependent transfer, nested containment update, or conditional routing rule—using primitives the model can already understand.

Use:

- **20 lessons**, with **64 labeled support visits per lesson**.
- Fresh names and factual bindings in every visit.
- **128 independent probe visits per lesson**, with new bindings.
- Evaluations after **0, 1, 2, 4, 8, 16, 32, and 64** support visits.
- Three training seeds and balanced lesson orders.
- A fixed episodic-storage budget, initially **2 MiB**, including readable diary material, cards, replay examples, and indexes.
- A separate declared cap on total persistent state—for example **64 MiB** for a roughly 2M-parameter learner—including optimizer state, EWC statistics, and adapters.

These are starting budgets; measure actual serialization sizes before locking them.

The existing life generator (`learnlab/village/scheduler.py:914`) provides revisits and cross-visit evidence. It is useful infrastructure, but it needs a procedural curriculum to test the stronger claim.

**Separate learning opportunities from evaluation.** During support phases, the learner may update according to its algorithm. During query probes, weights and persistent stores are read-only. Freezing everything throughout the lifetime would prevent the behavior you want to test.

Run these update methods on the same backbone first:

| Method | Purpose |
|---|---|
| Sequential fine-tuning | Establishes interference without protection. |
| Fine-tuning with reservoir replay | The main practical baseline to beat. |
| EWC | Tests parameter protection. |
| LoRA per task | Tests separation through additional capacity. Count all adapters; expose any oracle task-routing advantage. |
| Frozen weights with retrieval | Tests whether improvements require weight learning. |
| Premonition’s periodic consolidation | Start with replay plus one additional proposed mechanism. |

Then run the strongest ordinary replay method on C\*, so architectural and learning-algorithm gains remain distinguishable.

Replay is a substantive competitor, not a token baseline: **Rolnick et al., 2019** found strong continual-learning performance from experience replay, including bounded buffers. EWC comes from **Kirkpatrick et al., 2017**. [Replay](https://arxiv.org/abs/1811.11682), [EWC](https://arxiv.org/abs/1612.00796)

**The decisive probe:** compare early and late checkpoints on the **same fresh tasks with the same support information and fresh episode memory**. Rebuild cards from identical raw inputs using each checkpoint’s compatible encoder. Discard probe adaptations afterward.

If the late checkpoint learns faster there, accumulated episode answers cannot explain the entire gain.

Track these metrics:

| Metric | What to measure |
|---|---|
| **Acquisition efficiency** | Labeled visits required to reach 80% accuracy. Report failures to reach the threshold explicitly. |
| **Forward transfer** | Improvement on new tasks relative to the initial checkpoint, given identical support data and adaptation compute. |
| **Forgetting** | For each old procedure, its best previous probe accuracy minus its current accuracy. Report mean and worst procedure. |
| **Prequential accuracy** | Accuracy before receiving each new example’s answer or correction. |
| **Fact maintenance** | Old-fact accuracy, stale-answer rate, and recovery after corrections—reported separately from procedural retention. |
| **Lifetime cost** | Training, sleep, retrieval, re-encoding, evaluation gates, persistent bytes, and latency. |

The accuracy matrix across lessons follows the evaluation tradition of **Lopez-Paz & Ranzato, 2017**. Also measure ability to learn late tasks: forgetting and loss of plasticity are distinct, as emphasized by **Dohare et al., 2024**. [GEM](https://arxiv.org/abs/1706.08840), [Plasticity](https://www.nature.com/articles/s41586-024-07711-7)

Old-procedure probes should supply fresh facts in context. Otherwise good scores might merely show that the database retained old answers.

**5. What would be genuinely impressive for $50–200**

I would aim for this result:

> Across 20 sequential procedural lessons, a model with at most 3M trained parameters reaches 80% accuracy on fresh tasks using half as many labeled visits as the strongest tuned replay baseline, while retaining at least 85% old-procedure accuracy with no more than a 3-point average decline, under matched lifetime compute and fixed storage.

Require:

- The acquisition advantage across three seeds and balanced task orders.
- Fresh-memory probes demonstrating that persistent learned changes matter.
- Worst-procedure forgetting reported, not hidden by the average.
- A positive confidence bound on the primary improvement.
- Replication on a second task family.

**Those are ambitious targets, not a forecast.** Achieving them would be much more interesting than a 2M model beating a window-limited transformer on a custom benchmark.

A worthwhile smaller result would be **≥80% accuracy on held-out depth-4–6 reasoning after training at depths 1–3**, with a clear advantage over C\* at matched compute and robust counterfactual behavior. That would support efficient compositional reasoning, while leaving lifelong learning unclaimed.

Using your quoted rental rates, $50–200 buys roughly **100–500 GPU-hours** before ancillary costs. The binding constraint is likely to be experimental clarity and engineering time. I would spend the budget on strong controls, seeds, and replication before increasing model size.

**6. The next five experiments**

These are **spending caps**, calculated conservatively at your quoted $0.50/hour. They are not runtime predictions; profile a short run first.

| Order | Question and comparison | GPU cap | Success criterion | If it fails |
|---|---|---:|---|---|
| **1. Establish a solvable task** | Corrected-tokenizer A/E; D and a transformer supplied with oracle evidence. Include a full-visit E pilot. | **$5 / 10 h** | ≥95% on familiar depth-1–3 reasoning with gold evidence; fresh-name handling works. | Fix training/data/representation. Add no mechanisms. |
| **2. Test the memory advantage** | D versus D-noask, C\*, and a simple soft-attention memory network. Three seeds for finalists. | **$15 / 30 h** | D earns its store relative to D-noask and offers a meaningful accuracy or measured cost advantage over C\*. | Adopt the simpler competitive system; retain only supported claims. |
| **3. Test whether recurrence generalizes** | Train shallow; test deeper. Compare 1/2/4/8 reasoning steps, separate retrieval from reasoning with gold-evidence probes, vary distance independently of depth. | **$20 / 40 h** | Additional steps improve unseen-depth accuracy, and the best recurrent setting improves the accuracy–compute frontier. | Drop adaptive halting or excess loops; investigate explicit relational structure. |
| **4. Test continual procedural learning** | The 20-lesson stream above, first isolating the update method on one backbone. | **$50 / 100 h** | Faster acquisition than tuned replay, bounded forgetting, and gains surviving fresh-memory probes. | Keep ordinary replay. If retrieval explains everything, describe the system as adaptive memory rather than improved skill learning. |
| **5. Replicate outside the village** | Freeze architectural choices; test on an independent benchmark such as CLUTRR, with identical adaptation allowances for contenders. | **$30 / 60 h** | The advantage retains its sign across seeds and is practically meaningful on a second reasoning family. | Limit the claim to village-style event reasoning and identify the dependency causing failure. |

**CLUTRR, Sinha et al., 2019**, tests relation extraction and generalization to held-out compositions, making it a useful independent check. Training the same architecture there tests methodological generality; transferring village-trained weights is a separate, harder claim. [Paper](https://aclanthology.org/D19-1458/)

The full caps total **$120**. Reserve another approximately **$40** for failed runs and necessary reruns. At a hard $50 ceiling, prioritize experiments 1, 2, and a smaller version of 4. Defer the complete recurrence sweep and external replication.

**7. Blind spots and the simpler design**

- **The old baseline results cannot carry the architectural argument.** The tokenizer failure affected both inputs and outputs. The corrected baseline might improve substantially; its result is still unknown.
- **Your depth label is not a uniform measure of computational difficulty.** The oracle counts different operations differently, and plan depth includes location derivation rather than simply plan length. Report evidence count, rule applications, plan length, and distractor count alongside depth.
- **Lower trust does not solve stale inference.** If “Tavi is at the mill” was derived from an earlier premise, correcting that premise must invalidate dependent conclusions. Derived cards need dependency/version tracking, not just a confidence discount.
- **A told-ledger cannot determine general answerability.** A fact may never have been explicitly stated but may be derivable. Conversely, a ledger hit does not prove that the model still possesses the information. Use it as provenance bookkeeping, not a universal knowledge oracle.
- **A transaction can avoid forgetting by refusing to learn.** Report sleep acceptance rate, acquisition of new skills, and compute spent on rejected updates. A system that rolls back every difficult change is stable but unsuccessful.
- **All learned memory parameters count as parameters.** Sparse knowledge slots, adapters, and codebook vectors cannot disappear from the model-size claim because they are called “memory.” Report total and active parameters separately.
- **Memory efficiency depends on workload.** Count building the store and amortize it over 1, 10, and 100 questions per visit. Your design may be especially attractive for repeated queries; that is a legitimate advantage if measured.
- **A readable decoder is not a faithful explanation by default.** Validate intermediate states through interventions and executable consequences. Fluent decoded thoughts can remain misleading even when answer accuracy improves.
- **Passing leak detectors is not proof of generalization.** They exclude specific shortcuts. A second generator and independently constructed challenge set are stronger protection against optimizing to your own benchmark.

The design I would expect to deliver much of the benefit is:

**Shared entity normalization → line encoder with timestamps → explicit memory → four shared attention/reasoning steps → answer/copy head**, trained with answer supervision, optional evidence supervision, and ordinary bounded replay.

With approximately 140 cards, soft attention over the entire store is a serious baseline. It avoids making discrete top-k optimization a prerequisite for testing the memory thesis. If answer-only soft retrieval works while straight-through top-k fails, that is evidence about optimization—not evidence that oracle supervision is fundamentally necessary.

My next GPU job would be the corrected E baseline and the gold-evidence comparison. My next implementation priority would be C\*, followed by the continual-learning probes. The codebook and sleep machinery should wait for those results.
