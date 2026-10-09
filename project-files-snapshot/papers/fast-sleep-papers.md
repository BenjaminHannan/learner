# Fast sleep: literature pass (memory sleep, composition, gating, consolidation, verification)

Date: 2026-10-07. Papers only: no code read, nothing run, no GPU. Scope: the small card experiments (B2 model, C2 task). Whole-model (village) claims are kept apart in their own short section.

## Summary for Ben (high-school senior)

1. Today's cheap sleep is a notebook of solved puzzles. The papers say a notebook works best when you only trust a match you have double-checked.
2. The cheapest double-check we have: run the notebook's suggested program on the examples inside the prompt and keep it only if every example comes out right.
3. Our "answer note" safety rule was set from only 24 rows. The standard maths says that gives about a 4% (not 1%) chance of firing on an unrelated task; about 1,000 unrelated rows are needed, and our exact calculator can make those for free.
4. To learn more per entry: keep the ones the model got wrong, merge near-duplicates, and make extra entries by hiding one example at a time and relabelling failed tries.
5. No paper shows a notebook of one-step programs solving two-step rules. The nearest ideas: let the notebook help the second night's sampling find two-step programs, or "dream up" chained puzzles from stored steps.
6. Moving notebook knowledge into the weights should be rare and cheap: retrain only the output heads on saved states, mixed with old add/mult, instead of all weights.

## How to read the labels

Nothing below has been run on our model, so the label grades how close the evidence is, not whether it worked for us.
- shown: demonstrated in a setting close to ours (program synthesis with an exact executor, or maths that holds for any exchangeable scores).
- suggested: demonstrated elsewhere (big language model, vision, RL, translation) with a plausible bridge to us.
- untested: an idea the paper does not show, or the mechanism differs enough that transfer is a guess.
Scale tags in the citation: [LM] language model, [vis] vision, [prog] program synthesis, [MT] translation, [RL], [theory], [neuro].

Verification: every citation below was checked against the arXiv API on 2026-10-07 (title, authors, date). Abstracts read for all. Full text read for the numbers I quote from: Kaiser 2017, Drozdov 2022, He 2021, Papernot 2018, Angelopoulos and Bates 2021, CodeIt, AlphaCode, Akyurek 2024, Lin 2025. The three 2026 papers (Mouchon, Li, Lee) are abstract-only and unreplicated.

---

## Q1. Making a kNN notebook learn more per write

| Citation | Finding (one line) | Relevance to us | Label |
|---|---|---|---|
| Khandelwal et al. 2020, ICLR, arXiv 1911.00172, kNN-LM [LM] | Interpolating a trained LM with a kNN distribution over stored (hidden state, next token) pairs gave a 2.9-point perplexity gain (to 15.79) on Wikitext-103 with no training. | Our notebook is a kNN-LM over (thinker state, op/slot). The mixing weight is fixed. | suggested |
| Grave et al. 2017, ICLR, arXiv 1612.04426, continuous cache [LM] | Storing past hidden activations as keys, with the next word as value, and mixing a dot-product lookup works without training the cache. | Ancestor of our design; hidden-state keys need no retraining. | suggested |
| Xu et al. 2023, arXiv 2301.02828, Why do kNN-LMs work? [LM] | Three causes: a different input representation for the prediction, approximate kNN search, and the softmax temperature of the kNN distribution. | Our two knobs, key choice and softmax(sim/0.05), are probably where gain-per-entry lives. Exact top-16 is not sacred. | suggested |
| Drozdov et al. 2022, arXiv 2210.15859 [LM] | kNN-LM helps most when retrieved items are semantically close; one interpolation weight per bucket of top-1 retrieval distance (32 buckets best, tuned on validation) gave about 4% perplexity gain. | Graded trust versus our all-or-nothing gate plus fixed +50. Also explains why memory only helps repeated shapes: gain sits in the high-similarity buckets. | suggested |
| Zheng et al. 2021, ACL (short), arXiv 2105.13022, Adaptive kNN-MT [MT] | A small Meta-k network, trained on few samples, picks how many neighbours to use per token, because a fixed k lets noisy neighbours hurt. | Our k=16 is fixed; off-shape neighbours in the top 16 dilute the vote. | suggested |
| He et al. 2021, arXiv 2109.04212, Efficient kNN-LM [LM] | Adaptive retrieval, datastore pruning and dimension reduction give up to 6x faster inference at comparable quality. | Many stored entries are redundant; the notebook can be pruned. | suggested |
| Kaiser et al. 2017, ICLR, arXiv 1703.03129, Learning to Remember Rare Events [vis/MT] | Write rule: if the nearest neighbour already returns the right value, only average its key with the query and reset its age; otherwise write a new slot over the oldest. Keys are trained with a margin triplet loss (margin 0.1) on cosine similarity. | Direct template for a write policy (merge duplicates, write on miss) and for training keys cheaply. | suggested |
| de Masson d'Autume et al. 2019, NeurIPS, arXiv 1906.01076 [LM] | Episodic memory plus sparse replay and local adaptation for lifelong language learning; storing only a random subset cut memory 50-90% at minimal loss. | Most writes are redundant; supports filtering writes. | suggested |
| Sprechmann et al. 2018, ICLR, arXiv 1802.10542, Memory-based Parameter Adaptation [vis/LM] | Retrieve neighbours at test time and take a few high-learning-rate steps on them, then reset. | Middle path between voting and sleep fine-tune; costs per query. | suggested |
| Wu et al. 2022, ICLR, arXiv 2203.08913, Memorizing Transformers [LM] | An approximate kNN lookup into a non-differentiable (key, value) memory improves steadily up to 262K tokens, and the model uses newly defined functions and theorems at test time. | Closest "memory at inference instead of a weight update" for symbolic content. Their retrieval was trained jointly; ours is added after training. | suggested |
| Zhong et al. 2022, EMNLP, arXiv 2205.12674, TRIME [LM] | Training with in-batch examples as memory cut Wikitext-103 perplexity 18.70 to 15.37; they call test-time-only memory suboptimal. | Our keys were never trained to be retrievable. Relevant only if the base is ever retrained. | suggested |
| Rubin et al. 2022, arXiv 2112.08633, EPR [LM] | Train the retriever with downstream feedback: label candidates positive or negative by whether they raise the output likelihood. | Train a small key projection with an executor label ("did the neighbour's program fit the examples"); keys are cached, so it is cheap. | suggested |
| Butt et al. 2024, ICML, arXiv 2402.04858, CodeIt [prog] | Hindsight relabelling (a failed program becomes a correct example for the outputs it actually computes) plus prioritised replay: ARC policy-only 49/400 versus 24/400 without relabelling (Table 2); 15% solved. | Our night keeps only tries that fit every example. Relabelling would turn the rest into extra records. | shown (program synthesis with an executor) |
| Akyurek et al. 2024, arXiv 2411.07279 (v2 retitled "...for Few-Shot Learning"), TTT [LM 1B-8B] | Build training tasks from the prompt's own examples by leave-one-out, add augmentations, train a per-task LoRA: up to 6x accuracy on ARC (53.0% at 8B). Their appendix: about 12 h on one A100 for 100 tasks. | (a) Leave-one-out turns one prompt into k records. (b) Weight-based TTT is strong but far above our 1 TFLOP budget. | suggested |
| Hardt and Sun 2024, ICLR, arXiv 2305.18466 [LM] | Fine-tuning on about 20 retrieved neighbours, one step each, at test time improves many LM tasks; index quality matters. | "Sleep on neighbours per query" is the weight-based cousin of our vote; more expensive. | suggested |
| Schlag et al. 2021, ICML, arXiv 2102.11174, linear transformers are fast weight programmers [LM/synthetic] | Purely additive writes saturate memory capacity; a delta-rule write (correct the existing key-to-value mapping instead of adding) raises capacity. | Write by correcting the nearest entry, not appending. | suggested |
| Ramsauer et al. 2021, ICLR, arXiv 2008.02217, modern Hopfield [theory] | Softmax retrieval is attention; low inverse temperature averages many patterns, high retrieves one. Ours is beta = 20. | At this beta we pick one nearest program, never a blend. That suits single shapes and is wrong for blended composition. | suggested |
| Ba et al. 2016, arXiv 1610.06258, fast weights; Miconi et al. 2018, ICML, arXiv 1804.02464, differentiable plasticity [LM/RL] | Hebbian outer-product memory stores recent associations in weights; trained end to end. | A lossy fixed-size notebook. No evidence found that it beats kNN for exact symbolic recall. | untested |
| Sun et al. 2024, arXiv 2407.04620, TTT layers; Behrouz et al. 2024, arXiv 2501.00663, Titans [LM] | Hidden state is a model updated at test time; Titans writes more where "surprise" (gradient) is large. | Write the records where the base heads were wrong, not those they already got right. | suggested |
| Vinyals et al. 2016, arXiv 1606.04080, Matching Networks; Snell et al. 2017, arXiv 1703.05175, Prototypical Networks [vis] | Attention over a labelled support set needs no fine-tuning; averaging a class's examples into one prototype works well in few-shot. | One prototype per (step, op, slot) instead of many near-copies. | suggested |
| Parvez et al. 2021, arXiv 2108.11601, REDCODER; Zhou et al. 2022, arXiv 2207.05987, DocPrompting [prog] | Retrieved code or docs improve NL-to-code generation (DocPrompting +2.85 pass@1, 52% relative on CoNaLa with CodeT5). | These retrieve text for a model to read. We retrieve a decision (op/slot). Weak fit. | untested |

What raises gain per stored example, from the above (all suggested for our setting):
- Write where the base was wrong; merge near-duplicates (Kaiser, d'Autume, Titans, delta rule).
- Make several records per solved question: leave-one-out and hindsight relabelling (Akyurek, CodeIt).
- Trust by similarity bucket, not a cliff (Drozdov, Zheng).
- Key quality and temperature matter more than quantity (Xu, TRIME, EPR).
- Memory gain is capped by shape coverage: the high-similarity buckets carry it (Drozdov). This matches our "only repeated shapes" finding.

---

## Q2. Composing stored programs / library learning

| Citation | Finding (one line) | Relevance to us | Label |
|---|---|---|---|
| Ellis et al. 2021, PLDI, arXiv 2006.08381, DreamCoder [prog] | Wake-sleep: wake solves tasks; sleep has two halves, abstraction (grow a library by refactoring solved programs) and dreaming (train the recogniser on replayed and imagined tasks). | Our night is "wake" and memory sleep only stores. The missing halves are compress and dream. Compression needs found programs; unsolved multi-step kinds give it nothing. | suggested |
| Bowers et al. 2023, POPL, arXiv 2211.16605, Stitch [prog] | Top-down corpus-guided abstraction: 3-4 orders of magnitude faster and 2 orders less memory than DreamCoder's, with comparable or better compression; robust to early stopping. | Compressing a few hundred 7-step programs is trivial in cost. It can only find "square then add" if such records exist. | suggested |
| Grand et al. 2024, ICLR, arXiv 2310.19791, LILO [prog] | LLM synthesises, Stitch compresses, AutoDoc names abstractions; the names help the synthesiser use them. | A named macro-op (e.g. SQ = mult x x) would need new op-head classes. | untested |
| Cao et al. 2023, POPL, arXiv 2212.04596, babble [prog] | E-graphs plus anti-unification find abstractions up to equivalences (e.g. commutativity). | Commutative ops (add a b = add b a) split votes across operand orders. Check in the code whether operand order is canonicalised before storing. | untested |
| Stengel-Eskin et al. 2024, arXiv 2401.16467, ReGAL [prog] | Gradient-free library learning by execution-verified refactoring; CodeLlama-13B improved 11.5 pts on LOGO and 26.1 on dates. | Same spirit as memory sleep: no gradient, verified by execution. | suggested |
| Zenkner et al. 2024, arXiv 2405.17514, AbstractBeam [prog] | Library learning plus execution-guided bottom-up search solves more tasks with fewer candidates than the same search without it. | Library plus search, not library alone. | suggested |
| Shi et al. 2022, arXiv 2203.10452, CrossBeam [prog] | A neural policy chooses how to combine already-executed sub-programs bottom-up, seeing their execution results; explores a much smaller space. | Our 7 result slots are such a pool of executed sub-results. Closest structural match to two-step composition. | suggested |
| Shi et al. 2023, ICLR 2024, arXiv 2307.13883, ExeDec [prog/LM] | Predict the next execution subgoal (the intermediate value), then the sub-program that reaches it. Much better compositional generalisation on RobustFill and DeepCoder; helps LLM prompting too. | Retrieve by "which value should this result slot hold" as well as by state. | suggested |
| Reed and de Freitas 2016, ICLR, arXiv 1511.06279, NPI [prog] | A persistent key-value program memory lets a model compose low-level programs into higher-level ones and learn new tasks on top of old ones. | Closest architecture to a notebook of programs, but keys are trained jointly and need traces. | suggested |
| Levy et al. 2022, arXiv 2212.06800, diverse demonstrations [LM]; Ye et al. 2023, arXiv 2302.05698, CEIL [LM] | When test outputs contain unseen structure, nearest examples are insufficient; pick examples that together cover every sub-structure of the target. | Step-level retrieval could pull step 1 from one kind and step 2 from another. Choose neighbours for coverage, not similarity alone. | suggested |
| Nye et al. 2020, NeurIPS, arXiv 2003.05562 [prog] | Training a model to induce an explicit rule program from a few examples beat neural meta-learning on SCAN and number-word tasks. | Supports our program-writing design. | suggested |
| Li et al. 2024, arXiv 2411.02272 [prog] | On ARC, induction (write the function) excels at precise computation and composing several concepts; transduction (predict the output) handles fuzzy cases; the ensemble nears human level. | Multi-step rules are where the program route should win, if the heads can write them. A direct-answer path is complementary, not a substitute. | suggested |
| Wang et al. 2024, ICLR, arXiv 2309.05660, Hypothesis Search; Qiu et al. 2023, arXiv 2310.08559 [LM] | Propose rules, turn them into programs, verify against the examples, refine with interpreter feedback; LMs propose well but apply poorly. | The verify-with-examples loop (see Q5). | suggested |
| Zelikman et al. 2022, arXiv 2203.14465, STaR; Singh et al. 2023, arXiv 2312.06585, ReST-EM [LM] | Sample, keep what is verified correct, retrain, repeat. Scales without human data where an automatic check exists. | Our night is round 1 of this loop; nothing iterates it. | suggested |
| Lake 2019, NeurIPS, arXiv 1906.05381, meta seq2seq [small] | Memory-augmented nets meta-trained over many episodes solve several SCAN compositional tests. | Needs training on composition episodes, not just storing. | suggested |
| Wang et al. 2023, arXiv 2305.16291, Voyager; Cai et al. 2023, arXiv 2305.17126, LATM; Wang et al. 2024, arXiv 2409.07429, Agent Workflow Memory (+24.6% and +51.1% relative on Mind2Web and WebArena) [LM] | Skill, tool or workflow libraries grow from verified solutions and are reused. | Text libraries read by an LLM; our heads cannot read a library. | untested |

Which of these would let single-shape programs solve two-step rules like x*x+k? Nothing off the shelf. Three mechanisms exist, none tried on a notebook:
1. Compose executed sub-results with execution feedback in view (CrossBeam, ExeDec). Closest to our slots.
2. Dream composites from the library and train or store them (DreamCoder dreaming).
3. Bootstrap: memory lifts step-1 accuracy, so the next night's sampling can finally find whole programs (STaR/CodeIt-style loop).

Not found: any paper showing a kNN notebook of single-step programs composing into multi-step programs without weight training. WISE (2405.14768, Q3) reports that retrieval-style memory generalises poorly, which matches our result (suggested).

---

## Q3. Safe gating and calibration

| Citation | Finding (one line) | Relevance to us | Label |
|---|---|---|---|
| Angelopoulos and Bates 2021, arXiv 2107.07511, gentle intro to conformal [theory] | Split conformal threshold is the ceil((n+1)(1-alpha))/n quantile of calibration scores; coverage over random calibration sets is Beta(n+1-l, l) with l = floor((n+1)alpha); guideline of about 1000 calibration points. | Derived by me from their formula (the paper does not discuss n=24): with n=24 and alpha=0.01 the level is 25/24 > 1, so no finite 1% threshold exists below n=99. A "0.99 quantile" of 24 rows is about the maximum; a fresh unrelated row beats the max of 24 exchangeable rows with probability 1/25 = 4% (4-8% with interpolation). This fits the one-seed answer-note harm. | shown (maths, needs exchangeable calibration rows) |
| Vovk 2012, arXiv 1209.2673, conditional validity of inductive conformal predictors [theory] | Marginal validity does not give per-group validity; the paper studies several conditional versions and ways to get them. | Calibrate per step and per task kind, not pooled. | shown (maths) |
| Gibbs, Cherian, Candes 2023, arXiv 2305.12616 [theory] | Exact finite-sample coverage simultaneously over every pre-specified subgroup. | Treat each unrelated task kind as a group to protect. | suggested |
| Bates et al. 2023, Ann. Statist., arXiv 2104.08279, conformal p-values for outliers [theory] | Compare a new point's score with a reference set to get a valid outlier p-value; also gives a calibration-conditional version and false-discovery control. | Our gate asks "is this row unlike the skills rows?". That is this problem. A p-value replaces a hand-picked quantile. | shown (framework) |
| Papernot and McDaniel 2018, arXiv 1803.04765, Deep kNN [vis] | kNN over every layer's representations; nonconformity = number of neighbours disagreeing with the candidate label, summed over layers; calibrated on a separate held-out set to give credibility; flags off-manifold inputs. | Agreement gating: require top-k neighbours to agree across steps. Calibrate on rows that are not in the notebook (leave-one-out), else self-matches inflate similarity. | suggested |
| Sun et al. 2022, ICML, arXiv 2204.06507, deep nearest-neighbour OOD [vis] | Nearest-neighbour distance on normalised features beat a Mahalanobis baseline by 24.77% FPR@TPR95 on ImageNet-1k, no distribution assumption. | Supports a cosine nearest-neighbour score as a strong gate. Baselines that use the model's own outputs (max softmax 1610.02136, Mahalanobis 1807.03888, energy 2010.03759) are weaker or equal there. | suggested |
| Geifman and El-Yaniv 2017, NeurIPS, arXiv 1705.08500, selective classification [vis] | Choose a confidence threshold that bounds the error rate among accepted examples with high probability. | Our goal "no skills harm" is a risk bound on fired rows, not a fire rate. | suggested |
| Angelopoulos et al. 2022, arXiv 2208.02814, conformal risk control; Angelopoulos et al. 2021, arXiv 2110.01052, Learn then Test [theory] | Calibrate a threshold so a chosen loss (here: harm) is bounded in expectation (CRC) or with high probability (LTT, with multiple-testing over candidate thresholds). | Target "harm rate among unrelated rows <= alpha" directly for the answer note. The executor labels synthetic prompts for free. | suggested |
| Rouzrokh et al. 2024, arXiv 2404.04287, CONFLARE [LM] | Conformal similarity cutoff so the true chunk is retrieved with probability 1-alpha. | It controls recall on relevant queries. We also need the opposite tail: false firing on unrelated queries. Use both: a lower bound from relevant rows (keeps gain), an upper bound from unrelated rows (keeps safety). | suggested |
| Mallen et al. 2022, arXiv 2212.10511; Yoran et al. 2023, arXiv 2310.01558; Asai et al. 2023, arXiv 2310.11511, Self-RAG [LM] | Retrieval hurts when the model already knows or the context is irrelevant; fixes: popularity-based adaptive retrieval, filtering, training with irrelevant context, learning when to retrieve. | Retrieval harm on unrelated inputs is real and needs calibration on irrelevant retrievals. | suggested |
| Hartvigsen et al. 2022, arXiv 2211.11031, GRACE [LM]; Mitchell et al. 2022, arXiv 2206.06520, SERAC [LM]; Wang et al. 2024, arXiv 2405.14768, WISE [LM] | GRACE: a codebook of keys, each with its own deferral radius, many sequential edits with little harm elsewhere. SERAC: memory plus a learned "in scope?" classifier. WISE: a router between main and side memory; says retrieval-only memory generalises poorly and parameter edits lose locality. | Per-entry radius set against the nearest skills row; a small scope classifier on cached states as a trained gate. WISE names our trade-off: local and safe, but no generalisation. | suggested |

How to gate a final-answer memory so it never fires on unrelated tasks. Strictly "never" is only available through a per-prompt check; statistics give "at most alpha, with confidence 1-delta". In order of strength:
1. Check against the prompt's own examples (Q5): fire only if the resulting program fits every example. No calibration set needed (shown for program filtering by AlphaCode; untested as a memory gate).
2. Calibrate on at least 1,000 held-out unrelated prompts with the conformal level or Learn-then-Test, per step and per kind (shown as maths).
3. Agreement across top-k neighbours and across steps (Deep kNN; suggested).
4. Per-entry radius against the nearest skills row (GRACE; suggested).

Not found: any paper on gating a final-answer memory specifically; the above are the closest analogues.

---

## Q4. Cheap consolidation (notebook into weights, rarely)

| Citation | Finding (one line) | Relevance to us | Label |
|---|---|---|---|
| McClelland, McNaughton, O'Reilly 1995, Psychological Review 102(3):419-457 [neuro] | Fast sparse hippocampal storage plus slow cortical learning by interleaved replay avoids catastrophic interference. | Notebook = hippocampus, fine-tune = cortex, "half skills replay" = interleaving. Supports consolidating rarely and always mixed with old data. | suggested |
| Kumaran, Hassabis, McClelland 2016, Trends in Cognitive Sciences 20(7):512-534 [neuro] | Updated theory: replay also supports generalisation; cortex can learn fast when new information fits existing structure. | New kinds that fit existing shapes (square is near mult) may consolidate cheaply. | suggested |
| Shin et al. 2017, NeurIPS, arXiv 1705.08690, deep generative replay [vis] | A generator replays samples of old tasks, so no data is stored. | Our exact executor is a perfect generator of add/mult prompts: replay fresh synthetic skills rows, not a fixed 512. | suggested |
| van de Ven et al. 2020, Nature Communications (doi 10.1038/s41467-020-17866-2), brain-inspired replay [vis] | Replay hidden representations produced by the network's own feedback, not raw inputs; state of the art without storing data. | Replay latent states = our keys. | suggested |
| Pellegrini et al. 2020, arXiv 1912.01100, latent replay; Hayes et al. 2020, arXiv 1910.02509, REMIND [vis] | Freeze lower layers, store compressed intermediate activations, train only the layers above. REMIND beat other methods under the same memory budget on incremental ImageNet. | Direct template: train only the heads on cached thinker states. | suggested |
| Buzzega et al. 2020, NeurIPS, arXiv 2004.07211, Dark Experience Replay [vis] | Store logits and match them while learning; a simple strong baseline. | Soft targets from old head outputs on replayed rows, not just hard labels. | suggested |
| Arani et al. 2022, ICLR, arXiv 2201.12604, CLS-ER [vis] | Slow and fast semantic memories (weight averages) interact with an episodic buffer. | A cheap slow copy: average of sleep updates. | suggested |
| Yang et al. 2022, arXiv 2205.00479, kNN-KD [MT] | Distil the kNN-augmented teacher's distribution into the base model offline; beats kNN-MT at base-model speed. | Exactly "notebook into weights": use memory-augmented head outputs as soft targets. | suggested |
| Lin et al. 2025, arXiv 2510.15103, Sparse Memory Finetuning [LM with memory layers] | Update only memory slots highly used by the new data relative to background data (TF-IDF). NaturalQuestions F1 fell 89% (full fine-tune), 71% (LoRA), 11% (sparse) at the same new-knowledge learning. | Choose what to update by specificity to new versus old data. We have no memory layers, so the mapping is a guess. | untested |
| Biderman et al. 2024, arXiv 2405.09673, LoRA learns less and forgets less [LM] | LoRA underperforms full fine-tuning on the target but keeps the base model's skills better; full fine-tuning learns perturbations of rank 10-100x typical LoRA ranks. | Low-rank sleep forgets less but under-learns; the notebook can cover what LoRA misses. | suggested |
| Mukherjee et al. 2025, arXiv 2505.11711 [LM] | RL updates only 5-30% of parameters, and fine-tuning that subnetwork alone recovers the result. | Hints that a small masked update can suffice. Shown for RL only. | untested |
| Shenfeld et al. 2025, arXiv 2509.04259, RL's Razor; Chen et al. 2026, ICML, arXiv 2510.18874, Retaining by Doing; Yang et al. 2024, ACL, arXiv 2402.13669, SDFT [LM] | Forgetting tracks the KL shift from the base on the new task; training on self-generated (on-policy or self-distilled) data forgets less than SFT on outside data. | Our W records are self-sampled and filtered, yet full fine-tune forgets add/mult. So suspect replay size, step size, or updating all weights. Cheap diagnostic: log KL on skills prompts each night. | suggested |
| Ilharco et al. 2023, ICLR, arXiv 2212.04089, task arithmetic [vis/LM] | A fine-tune's weight delta can be scaled, added or negated. | Keep each night's delta and merge a scaled copy to cap forgetting. | suggested |
| Mitchell et al. 2022 (SERAC), Hartvigsen et al. 2022 (GRACE), Wang et al. 2024 (WISE), Das et al. 2024, arXiv 2403.11901, Larimar [LM] | Memory-based editors write without gradients; WISE adds a side parametric memory with a router and puts different edits in different parameter subspaces. | "Bridge between memory and weights" designs. | suggested |
| Gutierrez et al. 2024, arXiv 2405.14831, HippoRAG [LM] | Hippocampus-inspired graph retrieval; single-step retrieval matches iterative retrieval at 10-30x lower cost on multi-hop QA. | Links between memory entries as a route to composition. Speculative. | untested |
| Mouchon 2026, arXiv 2606.31495 [vis, abstract only, single seed] | A memory that writes only on high surprise, with periodic offline replay into a slow readout; replaying only a recent window was worse than no replay. | Write on surprise; replay old and new together. | suggested |
| Li et al. 2026, arXiv 2608.22215, Dual-Layer Agentic Memory [LM, abstract only] | A write router (no write, write new, write update) pruned up to 68% of redundant memory and kept over 98% of QA exact match; periodic fine-tune consolidation. | Supports dedupe on write and rare consolidation. | suggested |
| Lee et al. 2026, arXiv 2605.26099, Do language models need sleep? [LM, abstract only] | A sleep phase turns context into fast weights with N offline passes; more passes help deeper reasoning. | Different mechanism (fast weights in state-space blocks). | untested |

---

## Q5. Verification in the loop at inference

| Citation | Finding (one line) | Relevance to us | Label |
|---|---|---|---|
| Li et al. 2022, AlphaCode, arXiv 2203.07814 [prog] | Sample very many programs and filter by the example tests in the prompt; filtering removes about 99% of samples, yet thousands of candidates can remain, so passing the examples does not prove correctness. | This is our night's filter, applied at inference. Ambiguity caveat: random examples must be able to separate the rules (x*x versus 2*x agree at x=2). | shown |
| Brown et al. 2024, arXiv 2407.21787, Large Language Monkeys [LM] | Coverage grows log-linearly with samples over four orders of magnitude; with an automatic verifier it turns into accuracy (SWE-bench Lite 15.9% to 56% at 250 samples); voting and reward models plateau. | We hold a perfect verifier (the prompt's examples plus an exact executor). Cost is linear in the number of tries. | suggested |
| Snell et al. 2024, arXiv 2408.03314 [LM] | Allocate test-time compute by difficulty; verifier-guided search beats a bigger model at equal compute in some regimes. | Adaptive N: stop at the first candidate that fits all examples. | suggested |
| Chen et al. 2022, arXiv 2207.10397, CodeT [prog] | Pick among candidates by agreement between candidate programs and tests (dual execution agreement). | Adds consensus beyond pass/fail when several candidates fit. | suggested |
| Ni et al. 2023, arXiv 2302.08468, LEVER [prog/LM] | A small verifier on (input, program, execution result), combined with generator probability, marginalising over programs with the same execution result; +4.6 to +10.9 points. | Tie-break among candidates that all fit by their executed answer, with no learning needed. | suggested |
| Wang et al. 2022, arXiv 2203.11171, self-consistency [LM] | Sample many reasoning paths and take the majority answer. | Vote over executed answers of candidates that fit every example. | suggested |
| Ellis et al. 2019, NeurIPS, arXiv 1906.04604, Write, Execute, Assess [prog] | Execute partial programs and use the intermediate state to guide the next step. | Step-level check: our executor exposes every result slot after each step. | suggested |
| Chen et al. 2023, arXiv 2304.05128, Self-Debugging [LM] | Use execution feedback to repair a program iteratively. | Our model cannot read executor output unless it is fed back into the loop. Untested as a repair step. | untested |
| Shi et al. 2022 (CrossBeam), Shi et al. 2023 (ExeDec) | Execution-guided search and subgoals shrink the search needed to verify. | Cheaper than blind sampling for multi-step programs. | suggested |

Cost, honestly: the exact integer executor is near free. The price is extra thinker forward passes (8 rounds each) per try, so N tries cost about N times one decode. That is still far below any weight update, but I cannot put a TFLOP figure on it without the model size. Two things to keep apart: "first-try" is a different metric from "first-try with an internal check", so report both. Memory can also supply the candidates: the programs stored with the top few distinct neighbours are diverse proposals that a verifier can sort.

---

## Candidate changes to memory sleep (at most 8; card experiments only; one change at a time)

Pass marks below are proposals. Fix them before any run.

**C1. Verify before firing (executor check as the gate).**
- Change: when memory biases a prompt's program, run that program through the exact executor on the prompt's examples. Keep the memory bias only if every example fits; otherwise use the base program. The answer note fires only after this check.
- Why: AlphaCode (example filter removes about 99%), CodeT, LEVER, Large Language Monkeys, Deep kNN (agreement).
- Expected effect: skills harm near zero by construction, including the bad seed; allows loosening the gate to recover recall on last_digit-like kinds.
- Cost: no training; one extra decode and execute only on prompts where memory fires.
- Wrong if: any seed shows skills drop over 0.5 pt (false passes), or DEV gain falls below 0.8 of today's memory-sleep gain (check too strict). Log the false-pass rate on unrelated rows.

**C2. Recalibrate every gate on enough unrelated rows.**
- Change: calibrate each step gate and the answer-note gate on at least 1,000 held-out unrelated prompts (skills rows not in the notebook plus fresh executor-made add/mult/other prompts), conformal level ceil((n+1)(1-alpha))/n, alpha 0.01 (0.001 for the answer note), per step and per kind where n allows. Report the realised false-fire rate on fresh rows.
- Why: Angelopoulos and Bates; Vovk; Bates et al.; Learn then Test; Deep kNN (calibration set separate from the store). Derived: n=24 gives about 4-8% false fire.
- Expected effect: false-fire at or below alpha on fresh rows; small seed-to-seed spread; answer note can be switched back on safely.
- Cost: forward passes on 1,000-5,000 prompts once; below one night's sampling.
- Wrong if: the bad seed still shows skills harm with n at least 1,000 and alpha 0.001. Then the harm is not gate miscalibration (maybe a shift between calibration and DEV skills rows).

**C3. Graded trust instead of a cliff.**
- Change: replace the fixed +50 x vote share above one threshold with a vote weight per similarity bucket (4-16 buckets), each weight set from how often the top-1 neighbour was right, estimated leave-one-record-out.
- Why: Drozdov (32 buckets, about 4% perplexity), Zheng (adaptive k), Xu (temperature).
- Expected effect: recovers near-miss rows (the 50-85% last_digit spread) with harm flat.
- Cost: negligible (counting).
- Wrong if: no DEV gain beyond one standard error over 3 seeds with skills drop unchanged. Watch for overfitting with small n.

**C4. Write policy: merge near-duplicates and write on miss.**
- Change: when writing a step, if the nearest existing entry has the same value and cosine above tau, average the keys and bump a count; always append when the base heads were wrong or the neighbour's value differs. Canonicalise commutative operand order first (check whether the code already does).
- Why: Kaiser; d'Autume; delta-rule writes (Schlag); prototypes (Snell); Li 2026; babble.
- Expected effect: smaller notebook; vote share no longer dominated by duplicate-heavy shapes (e.g. 512 old add/mult versus a few new ones); more gain per entry.
- Cost: one neighbour search per write, trivial.
- Wrong if: DEV gain drops over one standard error at equal entries, or rare-shape accuracy falls (averaging blurs distinct shapes).

**C5. More records per solved question (test (a) and (b) separately).**
- Change: (a) leave-one-out: for a W record with k examples, make k variants that hide one example, run the thinker on each variant, and store its step states with the same forced program. (b) Hindsight relabel: take a try that did not fit, run its program on the example inputs, build a prompt whose examples are that program's own outputs, store (new prompt states, that program).
- Why: Akyurek (leave-one-out, up to 6x with TTT); CodeIt (24/400 without relabelling versus 49/400 with).
- Expected effect: several to many keys per night for one forward pass each; better coverage around each shape; (b) can create records for shapes never solved.
- Cost: one thinker pass per added record; estimate 0.3-1x of memory sleep, to be measured.
- Wrong if: gain per TFLOP does not improve at equal cost, or (b) raises skills harm (pollution from the model's own wrong programs).

**C6. Memory-guided second night.**
- Change: after the first memory sleep, rerun the 32-try sampling with memory on, keep newly fitting programs, write them (with C4 dedupe), stop after two rounds.
- Why: DreamCoder wake loop; STaR, ReST-EM, CodeIt (iteration raises the solved set).
- Expected effect: if memory fixes step 1 of sq_plus or affine (a square-like shape), whole-program success becomes possible and the first W records for those kinds appear. This is the best-grounded route to the 0% kinds.
- Cost: one more sampling pass; cost relative to the 1 TFLOP is unknown, measure first.
- Wrong if: round 2 finds zero new fitting programs for sq_plus and affine at 32 tries and their DEV stays 0%. Then step-1 help does not unlock whole programs; go to C7.

**C7. Dream composition records (higher risk).**
- Change: take two single-shape programs from this night's records, chain them (first result feeds the second, fresh constants), execute to make example pairs, form prompts in the C2 format, run the thinker, and write step states with forced ops and slots for both steps. Compose generically from the night's own shapes; never hand-build the held-out kinds (that would leak).
- Why: DreamCoder dreaming; CrossBeam; ExeDec; Levy et al. (cover every sub-structure).
- Expected effect: step 2 finds a matching entry once step 1 is done; a chance for sq_plus above 0.
- Cost: forward passes on a few hundred synthetic prompts.
- Wrong if: memory fires on under 5% of real sq_plus/affine DEV prompts, or accuracy stays 0% with at least 200 dream records per composition (key mismatch). Then composition needs weights, not a notebook.

**C8. Head-only latent-replay consolidation, run rarely.**
- Change: freeze the looped controller; train only the op, pointer, slot and answer heads on cached thinker states (the notebook keys) with the forced labels, mixed 1:1 with fresh executor-made add/mult rows, plus logit matching to pre-sleep head outputs on old rows; run when the notebook passes N entries or every k nights; then drop the consolidated entries.
- Why: latent replay, REMIND, brain-inspired replay, DER, kNN-KD, CLS theory (interleave), LoRA forgets less.
- Expected effect: part of the notebook gain moves into weights at a tiny fraction of the 20-40 TFLOP fine-tune, with little add/mult forgetting since the controller is untouched.
- Cost: head matmuls on cached states, no backprop through 8 rounds; measure (expected well under 1% of full fine-tune).
- Wrong if: head-only recovers under half the notebook's DEV gain, or add/mult drops over 1 pt. Then the controller must change (a low-rank controller update is the next rung, with the KL-on-skills diagnostic).

Ranking by promise: C1, C2, C6, C5, C8 first; C3 and C4 cheap follow-ups; C7 high risk, high reward.

---

## Whole-model (village) claims, kept apart

These are large-LM results. They apply only if the village model ever gets a notebook; do not mix them with card results.
- Memory layers: Lample et al. 2019, arXiv 1907.05242 (product keys); Berges et al. 2024, arXiv 2412.09764 (memory layers at scale); Lin et al. 2025 (sparse memory finetuning, Q4).
- Test-time training and memory modules at LM scale: Akyurek 2024, Sun 2024, Behrouz 2024 (Q1). Test-time training is strong but costly (about 12 h per 100 tasks on an A100 in Akyurek's setup).
- Editing and agent memories: GRACE, SERAC, WISE, Larimar, HippoRAG, AWM (Q3, Q4).

## Not found

- A kNN notebook of single-step programs composing into multi-step programs without weight training.
- A gate designed for a final-answer memory. Closest: conformal retrieval cutoffs (CONFLARE), risk control, Deep kNN.
- Hebbian or fast-weight memories beating kNN for exact symbolic recall.
- Any result at our scale (a small model, about 1 TFLOP): every number above comes from larger or different settings, so every transfer is a hypothesis.
