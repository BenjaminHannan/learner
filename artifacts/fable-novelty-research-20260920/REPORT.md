# How the brain makes new thoughts — and the one piece to add to our model next

Research report, 2026-09-20. Written for Ben. Plain language on purpose.

---

## A. Short answer

The brain does not pull ideas out of nowhere. It stores experience in **parts that can be pulled apart and snapped back together** — a "shape of the problem" part and a "what's in it" part. Then, **offline** (rest and sleep), the hippocampus replays those parts in orders that never actually happened: forward bits of one memory glued to backward bits of another, or a familiar plan re-filled with new contents. Most of those made-up combinations are junk, so a second system **checks them and keeps the few that work**, and the useful ones get compressed into new reusable chunks. Original thought = **recombine offline, then select, then compress**.

**What I recommend adding first: an offline "dream" phase.** Between training rounds, with no new data, the dispatcher splices its own past successful call-traces into plans it never practised, runs them against stories it has already seen, keeps the ones that check out, and turns any repeating pattern into a new named macro-action. That one module attacks our exact known bug (the controller that "counts to 3") *and* is the cleanest measurable definition of novelty we can get in our toy world.

---

## B. Mechanism table

| # | Mechanism (what the brain does) | Strongest evidence | Evidence quality | Existing ML analogue | How it maps onto operator + dispatcher | Build cost |
|---|---|---|---|---|---|---|
| 1 | **Generative / recombinant replay.** During rest and sleep the hippocampus replays place-cell sequences. Crucially it replays paths the animal never took — a forward piece of one route spliced to a backward piece of another — and in humans it re-orders newly seen objects into the order implied by a learned *rule*, not the order they were shown in. | Gupta et al. 2010, *Neuron* — rats replay never-experienced shortcut trajectories ([PubMed](https://pubmed.ncbi.nlm.nih.gov/20223204/), [PDF](http://redishlab.neuroscience.umn.edu/papers/2010_Gupta_Replay_Neuron.pdf)). Liu, Dolan, Kurth-Nelson & Behrens 2019, *Cell* — human replay reorganises experience along learned structure, with a factorised code ([Cell](https://www.cell.com/cell/fulltext/S0092-8674(19)30640-3)). Schwartenbeck et al. 2023, *Cell* — generative replay during compositional inference ([Cell](https://www.cell.com/cell/fulltext/S0092-8674(23)01025-5)). He et al. 2026, *Nature Neuroscience* — hippocampal ripples reshape mPFC into the inferred compositional structure ([Nature Neuro](https://www.nature.com/articles/s41593-026-02291-3)). | **Strong that replay happens and is not a literal recording; moderate that it is the causal engine of new ideas.** Sequence decoding is statistical and noisy; a well-known dissenting result argues replay reflects specific past experience rather than the upcoming plan (Gillespie et al. 2021, [Neuron](https://www.cell.com/neuron/fulltext/S0896-6273(21)00573-0)). Human MEG "replay" is an inference from a decoder, not direct recording. | Generative replay for continual learning (van de Ven, Siegelmann & Tolias 2020, [Nat Comms](https://www.nature.com/articles/s41467-020-17866-2)); experience-replay buffers with hindsight relabelling. | An offline phase that splices stored dispatcher traces into never-practised call sequences (e.g. LINK->LINK->LINK->LINK->READ when only 3 hops were practised), runs them on already-seen stories, keeps the ones that verify. | **Small-medium** |
| 2 | **Factorised "structure x content" codes.** Entorhinal cortex carries the *shape* of the space (grid-like, where-am-I-in-the-pattern) while hippocampus binds that shape to the *specific stuff* at each spot. Because the two are separate, a known shape can be re-bound to brand-new contents and you get correct answers with zero new practice. | Whittington et al. 2020, *Cell* — Tolman-Eichenbaum Machine; factorisation + conjunction reproduces grid, place, band, border and object-vector cells and generalises to new environments ([PubMed](https://pubmed.ncbi.nlm.nih.gov/33181068/), [bioRxiv full text](https://www.biorxiv.org/content/10.1101/770495v2.full)). Liu et al. 2019 (above) shows the factorised code ~50 ms *before* the sensory code in humans. | **Strong.** Grid and place cell data are direct single-unit recordings; TEM is a model that reproduces them and makes tested predictions. The weak link is how literally "role-filler binding" maps onto human abstract reasoning. | Role-filler / vector-symbolic binding; slot attention; Lake & Baroni 2023 meta-learning for compositionality ([Nature](https://www.nature.com/articles/s41586-023-06668-3)); a 2026 hippocampal-entorhinal world model reporting structural reuse ([arXiv 2605.15733](https://arxiv.org/pdf/2605.15733)). | We already have a weak version: one shared lookup operator reused at every step = content swapped into a fixed role. Strengthen it by making the dispatcher emit an explicit **plan skeleton** (sequence of roles) separate from the **bindings** (which entity, which relation), so skeletons can be re-bound to unseen relations. | **Medium** |
| 3 | **Generate then evaluate (two networks taking turns).** Free-associative generation (default-mode network) is coupled to deliberate filtering (executive-control network); more creative people switch between them more. This is the brain's version of "throw out many guesses, keep the good ones" — Campbell's blind-variation-and-selective-retention idea. | Beaty et al. 2015, *Sci Rep* ([link](https://www.nature.com/articles/srep10964)); Beaty et al. 2018, *PNAS* — creative ability predicted from functional connectivity ([PNAS](https://www.pnas.org/doi/10.1073/pnas.1713532115)); 2025 *Communications Biology* multi-site study, N = 2433, DMN-ECN switching predicts creativity but not IQ ([link](https://www.nature.com/articles/s42003-025-07470-9)); covert-neurofeedback study claiming causal evidence, *Cerebral Cortex* 2025 ([link](https://academic.oup.com/cercor/article/35/4/bhaf065/8108110)). Theory: Simonton's BVSR update ([PDF](https://simonton.faculty.ucdavis.edu/wp-content/uploads/sites/243/2022/11/2022BVSRupdateCRJerrata.pdf)). | **Moderate, and mostly correlational.** Almost all of it is fMRI connectivity vs. scores on the Alternate Uses Task, a thin proxy for real creativity. One neurofeedback study claims causality; that is a single result. BVSR itself is contested — critics argue variation is "partially sighted", not blind. | Best-of-N sampling with a verifier; RL with verifiable rewards; MCTS proposal + value head. | The dream phase needs both halves: a **proposer** (splice/perturb past traces) and a **checker** (run the plan with the frozen operator on real story rows; keep only self-consistent, terminating plans). Do not skip the checker — that is what makes it selection rather than noise. | **Small** |
| 4 | **Deliberately injected variability, turned up when things stall.** A songbird has a dedicated circuit (LMAN) whose only job is to add noise to its song so it can explore; silence that circuit and the song becomes rigid and stops improving. In mammals, tonic locus-coeruleus / noradrenaline activity rises when the current strategy stops paying and pushes the animal to explore; humans use both "directed" (go where I am uncertain) and "random" exploration. | Ölveczky, Andalman & Fee 2005, *PLOS Biology* — inactivating LMAN removes vocal experimentation ([link](https://journals.plos.org/plosbiology/article?id=10.1371%2Fjournal.pbio.0030153)); 2024 *eLife* lesion study on song-syntax variability ([link](https://elifesciences.org/articles/93272)). Aston-Jones & Cohen 2005, *Annu Rev Neurosci* — adaptive gain theory ([PubMed](https://pubmed.ncbi.nlm.nih.gov/16022602/)). Badre et al. 2012, *Neuron* — RLPFC and uncertainty-driven exploration ([link](https://www.sciencedirect.com/science/article/pii/S089662731200075X)); Tomov et al. — dissociable correlates of directed vs random exploration ([PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7217879/)). | **Strong in songbirds (causal lesion / inactivation).** **Moderate in mammals** — adaptive gain is an influential theory with good supporting data, but the human pupil-diameter evidence is indirect. | Entropy bonuses; epsilon schedules; intrinsic curiosity, e.g. Random Network Distillation ([arXiv 1810.12894](https://arxiv.org/abs/1810.12894)). | Give the dispatcher a tiny **gain head**: when its own step-to-step progress signal stalls (the read keeps failing), raise action entropy and the willingness to take one more hop instead of stopping. Directly targets the "count to 3 then quit" bug. | **Small** |
| 5 | **Compressing what worked into a new reusable chunk (new "primitive").** Sleep looks like it does two different jobs: NREM pulls out the common rule across related memories (gist / abstraction), REM makes unusual associations. After a night's sleep, people are about twice as likely to spot a hidden shortcut rule they had not noticed before. Developmentally, children behave like programmers refactoring code — inventing new concepts and reusing them. | Wagner et al. 2004, *Nature* — sleep inspires insight, number-reduction task ([Nature](https://www.nature.com/articles/nature02223)). Lewis, Knoblich & Poe 2018, *TiCS* — NREM abstracts gist, REM forms novel links ([Cell Press](https://www.cell.com/trends/cognitive-sciences/abstract/S1364-6613(18)30070-6)). Rule, Tenenbaum & Piantadosi 2020, *TiCS*, "The Child as Hacker" ([Cell Press](https://www.cell.com/trends/cognitive-sciences/fulltext/S1364-6613(20)30174-1)). | **Moderate and partly contested.** Wagner 2004 is famous but the sleep->insight effect does not always replicate — a 2018 *Frontiers* study found no sleep benefit for classical insight problems ([link](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2018.00072/full)). The NREM/REM division of labour in Lewis et al. is a **theory paper**, not a direct measurement. "Child as hacker" is a framework, not data. | DreamCoder's wake-sleep library learning: extract repeated sub-programs, add them to the library ([PLDI 2021](https://dl.acm.org/doi/10.1145/3453483.3454080)). | After the dream phase verifies plans, mine the surviving traces for repeated skeletons and add each as a **named macro-action** in the dispatcher's action set (e.g. `FOLLOW_LINKS_UNTIL_READABLE`). Costs a few thousand parameters. | **Medium** |
| 6 | **Analogy — mapping the relations, ignoring the surface.** Rostrolateral PFC activity scales with how many relations you must hold and integrate at once; this is the machinery behind "A is to B as C is to ?". | Christoff et al. 2001 — RLPFC in relational integration ([PubMed](https://pubmed.ncbi.nlm.nih.gov/11697945/)); *Cerebral Cortex* 2010, rostral PFC specialisation for analogy sub-processes ([link](https://academic.oup.com/cercor/article/20/11/2647/339406)); Parsons 2022, *Cognitive Science* ([link](https://onlinelibrary.wiley.com/doi/10.1111/cogs.13116)). | **Moderate, correlational.** fMRI activation differences between conditions; very few causal (lesion / stimulation) results, and tDCS attempts at the related right-ATL insight effect returned nulls ([PLOS One 2017](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0184749)). | Structure-mapping engines; graph matching; relational bottlenecks in neural nets. | A "same-shape-different-stuff" trainer: detect that story A's LINK-chain has the same shape as story B's, and transfer B's solved plan to A. Real, but in our toy world it is mostly a special case of #2 + #1. | **Medium-large** |

### Why standard transformers are weak here (the contrast our claim rests on)

- **They match paths, they do not run rules.** Analyses from 2023-2026 find transformers solve multi-step problems by linearised subgraph matching against training-time paths, so they collapse on computation graphs wider or deeper than trained — even with step-by-step supervision ("Faith and Fate", [NeurIPS 2023 PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/deb3c28192f979302c157cb653c15e90-Paper-Conference.pdf); [arXiv 2502.15277](https://arxiv.org/pdf/2502.15277) shows an internally non-compositional solution even when test accuracy looks decent).
- **The reversal curse.** Trained on "A is B", they do not learn "B is A" (Berglund et al. 2023, [arXiv 2309.12288](https://arxiv.org/abs/2309.12288)). That is a ready-made novelty probe for our LINK rows.
- **Depth extrapolation is fixable with architecture, which supports our thesis.** Recurrent-depth transformers do show systematic generalisation and depth extrapolation (5-hop -> 10-hop) via a grokking-like three-stage progression ([arXiv 2604.07822](https://arxiv.org/abs/2604.07822), 2026) — i.e. re-using one computation many times is the ingredient, which is exactly what our shared operator does.
- **Novelty in big models is contested too.** Recent benchmarks find top LLMs beat the average human on divergent-thinking scores but not the most creative humans, and that "diverse" is easily confused with "random" ([Sci Rep 2025](https://www.nature.com/articles/s41598-025-25157-3); [Nat Comms 2026](https://www.nature.com/articles/s41467-026-70245-1)). Lesson for us: any novelty metric must also score *correctness*, not just "different".

---

## C. Top recommendation in detail

### C1. The module: an offline **DREAM phase** (recombine -> verify -> compress)

Think of it as the model going to sleep between study sessions. It gets no new stories and no new answers. It only re-uses what it already has.

**When it runs.** After each wake (normal RLOO training) wave, for a fixed small budget — say 2 minutes of the 30-minute experiment.

**Inputs.**
1. The stories the model has already seen (rows only — no answer key).
2. A buffer of the dispatcher's own successful call-traces from wake training. A trace is a list like `[LOOKUP(p0, LINK) -> p1, LOOKUP(p1, LINK) -> p2, LOOKUP(p2, r8) -> v]`.

**Step 1 — Recombine (the Gupta-2010 splice + the Liu-2019 rebind).** Two proposal operators, both cheap and purely mechanical:
- *Splice*: take the first k calls of trace A and the last m calls of trace B; if the entity types line up, concatenate. This is how you get a 5-hop plan out of two 3-hop plans, with nobody ever showing you a 5-hop question.
- *Rebind*: strip a trace to its **skeleton** (`LINK, LINK, READ ?r`) and re-fill it with a different starting person and a different final relation drawn from a story the model has seen. This is the factorised-code move.

**Step 2 — Verify (the selection half).** Run the proposed plan with the **frozen** lookup operator over the actual story rows. Keep it only if every hop resolves to a row that exists, the chain terminates, and the final read succeeds. Nothing outside the model's own already-seen data is consulted. Kept plans become `(question, answer)` items for the next wake wave — the model's **self-made practice set**.

**Step 3 — Compress (the DreamCoder sleep step).** Count skeletons among surviving plans. Any skeleton appearing more than a threshold (say 20 times) is added to the dispatcher's discrete action set as a named macro, e.g. `REPEAT_LINK_THEN_READ(r)`. Cap the library at 8 macros; evict by usage.

**Learned vs fixed.**
- Lookup operator (~79k): **frozen** during dreaming. It is the verifier; if it also trains here, you have added training, not novelty.
- Dispatcher (~15-24k): **learned in the wake phase only**, on wake data plus the dream-verified items.
- Macro library: **grown discretely**, not by gradient. Each macro adds one embedding row plus one logit; budget ~+2-6k parameters total. Keep the whole system under ~110k.
- Proposal operators: **hand-written and fixed** for v1. (Learning the proposer is v2 — see risks.)

### C2. The toy experiment (pre-register this before running anything)

**Task.** Standard fable world: 16 entity IDs, relations 8/9/10 + LINK. Wake training uses chains of length **1-3 only**, and only relations 8 and 9 as the final read.

**Held-out novelty sets (locked before training, never used for tuning):**
- **N-DEPTH**: chains of length **5 and 7**, final relation 8 or 9. Never practised, never supplied by a human.
- **N-REL**: chains of length 1-3 ending in relation **10**, which appears in story rows but is never the answer target during wake training. (Our reversal-curse-style probe of rebinding.)
- **N-BOTH**: length 5 **and** relation 10. The hard cell.

**What counts as novel.** Not "the output is unusual" — that is the trap the LLM creativity benchmarks fell into. Novel = **correct on a question type the model was never trained on, where the routine needed to answer it was assembled by the model itself during a phase with no new data and no new labels.** Concretely: N-DEPTH accuracy, plus the readable content of the macro library.

**Arms (all matched on wall-clock and on gradient steps):**

| Arm | Description | Purpose |
|---|---|---|
| **A. Dream** | operator + dispatcher + full dream phase | the hypothesis |
| **B. No-dream, matched compute** | same model, dream off, extra wake gradient steps so total updates match A | rules out "it is just more training" |
| **C. Dream-without-verify** | propose spliced plans, skip the verification filter, train on all of them | isolates the *selection* half |
| **D. Dream-without-compress** | propose + verify, but no macro library | isolates the *abstraction* half |
| **E. Plain transformer** | same stories, same token budget, same total number of training examples as A sees (wake + dream-verified) | the standard-model control |

5 fixed seeds per arm, all reported. No arm sees N-DEPTH / N-REL / N-BOTH during training.

**Suggested pass mark (pre-registered):**
1. **Primary:** Arm A >= **60%** on N-DEPTH (length 5), and >= **3x** Arm B's N-DEPTH accuracy, in **>= 4 of 5 seeds**, with Arm B <= 25%.
2. **Secondary:** Arm E (plain transformer) <= **15%** on N-DEPTH. If the plain transformer also solves it, the finding is that the task is too easy, not that our module works.
3. **Mechanism check:** at least **2** macros in A's final library are readable (from their behaviour on fixed probe stories) as a genuine loop-until-done routine, and ablating those macros drops N-DEPTH by >= 20 points.
4. **Stretch:** A beats B on N-BOTH — the "combination never practised in two ways at once" cell.

**Curriculum sub-experiment (cheap, worth it).** Train a *fresh* dispatcher only on A's self-proposed verified questions vs. on the same number of *randomly generated* questions with an identical length distribution. If the self-proposed set wins on N-DEPTH, the proposals carry real information about what the model needs to practise — a small, honest version of "the model asked itself a useful question."

### C3. What a **negative** result looks like (state it now, believe it later)

- Arm A ~= Arm B within seed noise -> the dream phase is just extra optimisation; drop it.
- Arm A ~= Arm C -> verification adds nothing, so the "selection" story is wrong and this is really data augmentation.
- Arm A ~= Arm D -> the macro library is decoration; the gain comes from longer examples alone. Still a result, but a much smaller claim: "offline splicing is a useful augmentation", not "the model invented an operation."
- The library fills with duplicates, one-step trivia, or macros nothing ever calls -> no abstraction happened.
- Gains on N-DEPTH but nothing on N-REL and N-BOTH -> we extended depth, we did not get compositional rebinding.

### C4. The biggest risk that "novelty" is fake, and the controls

1. **Label leakage through the verifier (the main danger).** If verification consults an oracle that knows the answers to 5-hop questions, the dream phase is secretly a labelled training set. *Control:* the verifier is the **frozen learned operator plus the story rows the model has already read** — nothing else. No ground-truth answer key, no privileged world simulator, and relation 10 never used as a verification target. Put an explicit assertion in the code that the dream phase cannot read the held-out sets, and log every data source it touches.
2. **"It is just more training."** *Control:* Arm B with matched gradient steps and matched wall-clock. Report both matched-steps and matched-time versions if they differ.
3. **"It is just longer examples."** *Control:* Arm C (no verify), plus, if time allows, an arm where length-5 questions **with correct answers** are hand-supplied to Arm B. If hand-supplied length-5 training scores the same, the dream phase is a convenience, not a new capability — say so plainly.
4. **Test-set contamination by iteration.** Lock N-DEPTH / N-REL / N-BOTH and the pass marks in a committed file **before** the first run. Tune only on a separate dev split of practised lengths.
5. **Seed cherry-picking.** 5 fixed seeds, all reported, pass mark expressed as "4 of 5", no post-hoc seed swaps.
6. **Reading the library too generously.** "Readable macro" must be judged from the macro's *behaviour* on probe stories, not from a name we gave it.

### C5. Runner-up: a **stall-triggered gain head** (LMAN / adaptive-gain analogue)

Much smaller, and worth doing if the dream phase is too big a jump. Add ~1-2k parameters to the dispatcher: a head that reads a running "am I making progress?" signal (did the last read fail? is the current entity one I already visited?) and outputs a temperature / entropy scale over actions plus a bias on CONTINUE vs STOP. Trained with the same RLOO objective.

Why it is interesting: the known failure is that the controller learns "stop after 3", which is exactly a **fixed gain** policy. Adaptive gain says the opposite — when utility stops accruing, do not quit; vary and keep searching. *Pass mark:* on unpractised length 5, the gain-head model beats a fixed-entropy control by >= 20 points in >= 4/5 seeds, with no additional data. *Failure signal:* it just makes the controller take max-length walks everywhere and hurts length 1-3 accuracy — so always report short-chain accuracy alongside.

The two combine well later: the gain head decides *when to keep going*, the dream phase supplies *the routines worth going with*.

---

## D. What we should NOT claim

**About the neuroscience:**
- Nobody has shown that replay *causes* a new idea. The strongest results show replay contains never-experienced sequences and that those sequences are structured by learned rules. That is compatible with "replay is the engine of imagination" and also with "replay is map maintenance, and the shortcut sequences are a side effect." A well-cited 2021 result explicitly argues replay reflects past experience rather than upcoming plans.
- Human "replay" is decoded from MEG/EEG/iEEG by classifiers. It is a statistical inference, not a recording of thoughts.
- The creativity-network literature is almost entirely **correlational** and leans on the Alternate Uses Task, a weak stand-in for real originality. The one causal-flavoured neurofeedback study is a single 2025 paper.
- Sleep-and-insight does not replicate cleanly. Wagner 2004 is real and important; it is also not a settled effect.
- The NREM-abstracts / REM-associates split is a well-argued **hypothesis**, not a measured fact.
- There is no accepted neural account of where a genuinely new *concept* (as opposed to a new combination of old ones) comes from. Anyone who tells you otherwise is selling something.

**About what our toy could show:**
- A pass would show: *in a 16-entity, 4-relation world, an offline recombine-verify-compress phase lets a ~100k-parameter system answer a question type it never practised, where a matched-data transformer cannot.* That is a real, honest, toy-scale claim.
- It would **not** show that the model is creative, that it invented a concept, that this scales, or that this is how brains work. It is an existence proof that a brain-inspired offline phase beats matched training, in one tiny world.
- "Novel" in our sense is **recombination inside a fixed vocabulary of operations**. Even with macros, the model is composing LOOKUP calls. Inventing a genuinely *new primitive operation* is out of reach of this design, and we should not describe macros as new operations.
- Our toy world is self-verifiable, which is exactly why the dream phase can work at all. Real domains are not. Do not generalise from this.
- Per the standing rule: claims <= evidence. Toy and village stay separate.

---

## E. References

All links below were retrieved by web search on 2026-09-20, and bibliographic details come from the publisher or index pages listed. Where I could not confirm a detail from the page itself, I flag it. Nothing here is invented.

**Replay, preplay, generative replay**
1. Gupta, van der Meer, Touretzky & Redish (2010). Hippocampal replay is not a simple function of experience. *Neuron*, 11 March 2010. https://pubmed.ncbi.nlm.nih.gov/20223204/ · PDF: http://redishlab.neuroscience.umn.edu/papers/2010_Gupta_Replay_Neuron.pdf
2. Ólafsdóttir, Barry, Saleem, Hassabis & Spiers (2015). Hippocampal place cells construct reward related sequences through unexplored space. *eLife* e06063. https://elifesciences.org/articles/06063
3. Liu, Dolan, Kurth-Nelson & Behrens (2019). Human replay spontaneously reorganizes experience. *Cell* 178(3), 640-652. https://www.cell.com/cell/fulltext/S0092-8674(19)30640-3
4. Kurth-Nelson, Behrens, Wayne, Miller, Luettgau, Dolan, Liu & Schwartenbeck (2023). Replay and compositional computation. *Neuron* 111(4), 454-469. https://www.cell.com/neuron/fulltext/S0896-6273(22)01125-4 · preprint https://arxiv.org/abs/2209.07453
5. Schwartenbeck et al. (2023). Generative replay underlies compositional inference in the hippocampal-prefrontal circuit. *Cell* 186, 4885-4897. https://www.cell.com/cell/fulltext/S0092-8674(23)01025-5 · https://pubmed.ncbi.nlm.nih.gov/37804832/
6. He, Wang, Zhang, Xiao, Hu, Schwartenbeck, Bakermans, Behrens & Liu (2026). Human hippocampal ripples coordinate planning sequences and compositional representations in neocortex. *Nature Neuroscience* 29, 1711-1721. https://www.nature.com/articles/s41593-026-02291-3 — the article page redirects to a login, so volume/pages come from the publisher listing and secondary coverage, not the article itself.
7. Gillespie et al. (2021). Hippocampal replay reflects specific past experiences rather than a plan for subsequent choice. *Neuron*. https://www.cell.com/neuron/fulltext/S0896-6273(21)00573-0 — **included as the dissenting view.**

**Factorised / compositional codes**
8. Whittington, Muller, Mark, Chen, Barry, Burgess & Behrens (2020). The Tolman-Eichenbaum Machine: unifying space and relational memory through generalization in the hippocampal formation. *Cell*, November 2020. https://pubmed.ncbi.nlm.nih.gov/33181068/ · full text https://www.biorxiv.org/content/10.1101/770495v2.full
9. Zhang, Lyu, Liu & Wu (2026). Structure abstraction and generalization in a hippocampal-entorhinal inspired world model. arXiv, submitted 15 May 2026. https://arxiv.org/pdf/2605.15733 — **preprint, peer-review status not verified.**

**Imagination / construction**
10. Hassabis, Kumaran, Vann & Maguire (2007). Patients with hippocampal amnesia cannot imagine new experiences. *PNAS*. https://www.pnas.org/doi/10.1073/pnas.0610561104
11. Schacter, Addis & Buckner (2008). Episodic simulation of future events. *Annals of the New York Academy of Sciences*. https://nyaspubs.onlinelibrary.wiley.com/doi/10.1196/annals.1440.001 — I could **not** independently verify the original Schacter & Addis (2007) *Phil. Trans. R. Soc. B* article details by search, so I cite this overview instead.

**Creativity networks / generate-and-select**
12. Beaty, Benedek, Kaufman & Silvia (2015). Default and executive network coupling supports creative idea production. *Scientific Reports* 5:10964. https://www.nature.com/articles/srep10964
13. Beaty et al. (2018). Robust prediction of individual creative ability from brain functional connectivity. *PNAS*. https://www.pnas.org/doi/10.1073/pnas.1713532115
14. (2025). Dynamic switching between brain networks predicts creative ability. *Communications Biology*. https://www.nature.com/articles/s42003-025-07470-9 — N = 2433 across 10 samples; **full author list not captured.**
15. (2025). Enhancing creativity with covert neurofeedback: causal evidence for default-executive network coupling in creative thinking. *Cerebral Cortex* 35(4), bhaf065. https://academic.oup.com/cercor/article/35/4/bhaf065/8108110 — **author list not captured.**
16. Simonton. The blind-variation and selective-retention theory of creativity (update). https://simonton.faculty.ucdavis.edu/wp-content/uploads/sites/243/2022/11/2022BVSRupdateCRJerrata.pdf · earlier: Simonton (2011), DOI 10.1037/a0022912, https://journals.sagepub.com/doi/abs/10.1037/a0022912 — **journal name for the 2011 paper not verified.** Original idea: Campbell (1960), cited throughout Simonton's papers; I did not retrieve Campbell's original article directly.

**Insight and sleep**
17. Wagner, Gais, Haider, Verleger & Born (2004). Sleep inspires insight. *Nature* 427, 352-355. https://www.nature.com/articles/nature02223
18. (2018). Sleep does not promote solving classical insight problems and magic tricks. *Frontiers in Human Neuroscience*. https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2018.00072/full — **author list not verified**; included as the non-replication.
19. Lewis, Knoblich & Poe (2018). How memory replay in sleep boosts creative problem-solving. *Trends in Cognitive Sciences* 22(6), 491-503. https://www.cell.com/trends/cognitive-sciences/abstract/S1364-6613(18)30070-6
20. Kounios & Beeman (2014). The cognitive neuroscience of insight. *Annual Review of Psychology*. https://psychology.northwestern.edu/people/faculty/core/profiles/ann_rvw_psy_2014.pdf
21. (2017). Anodal transcranial direct current stimulation of the right anterior temporal lobe did not significantly affect verbal insight. *PLOS One*. https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0184749 — null result; **author list not captured.**

**Exploration and neuromodulation**
22. Ölveczky, Andalman & Fee (2005). Vocal experimentation in the juvenile songbird requires a basal ganglia circuit. *PLOS Biology*. https://journals.plos.org/plosbiology/article?id=10.1371%2Fjournal.pbio.0030153
23. (2024). Lesions in a songbird vocal circuit increase variability in song syntax. *eLife* 93272. https://elifesciences.org/articles/93272 — **author list not captured.**
24. Aston-Jones & Cohen (2005). An integrative theory of locus coeruleus-norepinephrine function: adaptive gain and optimal performance. *Annual Review of Neuroscience* 28, 403-450. https://pubmed.ncbi.nlm.nih.gov/16022602/
25. Badre, Doll, Long & Frank (2012). Rostrolateral prefrontal cortex and individual differences in uncertainty-driven exploration. *Neuron*. https://www.sciencedirect.com/science/article/pii/S089662731200075X
26. Tomov, Truong, Hundia & Gershman. Dissociable neural correlates of uncertainty underlie different exploration strategies. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7217879/ — **journal and year not verified** from the page.

**Analogy / relational integration**
27. Christoff et al. (2001). Rostrolateral prefrontal cortex involvement in relational integration during reasoning. https://pubmed.ncbi.nlm.nih.gov/11697945/ — **journal not verified** (likely *NeuroImage*).
28. (2010). Specialization of the rostral prefrontal cortex for distinct analogy processes. *Cerebral Cortex* 20(11), 2647. https://academic.oup.com/cercor/article/20/11/2647/339406 — **author list not captured.**
29. Parsons (2022). The neural correlates of analogy component processes. *Cognitive Science*. https://onlinelibrary.wiley.com/doi/10.1111/cogs.13116

**Program induction / library learning / compositional ML**
30. Ellis et al. (2021). DreamCoder: bootstrapping inductive program synthesis with wake-sleep library learning. *PLDI 2021*. https://dl.acm.org/doi/10.1145/3453483.3454080 · https://www.cs.cornell.edu/~ellisk/documents/dreamcoder_with_supplement.pdf
31. Rule, Tenenbaum & Piantadosi (2020). The child as hacker. *Trends in Cognitive Sciences* 24(11), 900-915. https://www.cell.com/trends/cognitive-sciences/fulltext/S1364-6613(20)30174-1
32. Lake & Baroni (2023). Human-like systematic generalization through a meta-learning neural network. *Nature*. https://www.nature.com/articles/s41586-023-06668-3 · code https://github.com/brendenlake/MLC
33. van de Ven, Siegelmann & Tolias (2020). Brain-inspired replay for continual learning with artificial neural networks. *Nature Communications*. https://www.nature.com/articles/s41467-020-17866-2
34. Zhao et al. (2025). Absolute Zero: reinforced self-play reasoning with zero data. NeurIPS 2025 (listed as spotlight). https://arxiv.org/pdf/2505.03335 · https://github.com/LeapLabTHU/Absolute-Zero-Reasoner
35. Burda, Edwards, Storkey & Klimov (2018). Exploration by random network distillation. https://arxiv.org/abs/1810.12894

**Why transformers struggle / novelty benchmarks**
36. Dziri et al. (2023). Faith and fate: limits of transformers on compositionality. NeurIPS 2023. https://proceedings.neurips.cc/paper_files/paper/2023/file/deb3c28192f979302c157cb653c15e90-Paper-Conference.pdf
37. Berglund, Tong, Kaufmann, Balesni, Stickland, Korbak & Evans (2023). The reversal curse: LLMs trained on "A is B" fail to learn "B is A". https://arxiv.org/abs/2309.12288
38. (2025). Analyzing the inner workings of transformers in compositional generalization. https://arxiv.org/pdf/2502.15277 — **preprint; authors not captured.**
39. Kohli, Parthasarathy, Sun & Yao (2026). Loop, think, & generalize: implicit reasoning in recurrent-depth transformers. arXiv, April 2026 (revised August 2026). https://arxiv.org/abs/2604.07822 — **preprint.**
40. (2025). Divergent creativity in humans and large language models. *Scientific Reports*. https://www.nature.com/articles/s41598-025-25157-3 — **author list not captured.**
41. (2026). Evaluating LLMs' divergent thinking capabilities for scientific idea generation with minimal context. *Nature Communications*. https://www.nature.com/articles/s41467-026-70245-1 — **author list not captured.**
