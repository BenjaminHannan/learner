# Brain mechanisms for new ideas that AI has (probably) never tried

Research date: 2026-09-20. ~25 web searches. Everything here was found and checked; guesses are flagged.

---

## 1. Short answer

Three mechanisms survived. The best one is **memory linking by shared excitability**: when your brain
stores something, the same neurons stay extra-excitable for hours, so the *next* thing you learn gets
written into partly the same cells. Two separate experiences end up sharing a handle, and later a
strong event can reach back and link them offline — backwards in time only. Computational
neuroscientists have modelled this, but I found no AI system that uses it to make a learner better at
a task. Second: **left–right alternating theta sweeps** — the brain rhythmically samples two
alternative futures, including places it has never been, on a fixed internal beat rather than because
either looks good. Third: **hippocampal "barcodes"** — random index codes mixed into the same cells
that carry content. Absence of evidence is weak evidence; treat "untested" as "I ran 4–7 searches and
found nothing".

---

## 2. Survivor table

| # | Mechanism | Class | Confidence it is truly untested | Evidence quality (biology) | Fit to our toy (1–5) |
|---|-----------|-------|-------------------------------|---------------------------|----------------------|
| S1 | Memory linking by shared excitability / co-allocation + retrospective offline co-reactivation | BIOLOGY-MODEL ONLY | Medium (7 kill queries, no ML use; nearest ML is temporal-contiguity retrieval in EM-LLM) | **Strong** — replicated, causal (optogenetic/chemogenetic, CREB manipulation), rodent + some human | **5** |
| S2 | Left–right alternating theta sweeps / intrinsic rhythmic serial sampling of alternatives | BIOLOGY-MODEL ONLY | Medium-low (5 kill queries; functionally adjacent to beam search, which is everywhere) | **Moderate-strong** — clear recordings, replicated across labs; function is inferred, not causally proven | **4** |
| S3 | Hippocampal "barcodes": random index codes intermixed with content in the same units | BIOLOGY-MODEL ONLY | Medium-low (4 kill queries; sparse distributed memory / key-value memory is close prior art) | **Moderate** — one striking species (chickadee), one lab, not yet replicated elsewhere; correlational + decoding | **3** |

Nothing reached **UNTESTED** (no model at all). All three have computational-neuroscience models; none
of those models was used to make a learning system better at a task the way we would use it.

---

## 3. Survivors in detail

### S1 — Memory linking by shared excitability (co-allocation), and retrospective offline linking

**What the brain does, plainly.** After you learn something, the neurons that stored it stay unusually
easy to fire for several hours (driven partly by the protein CREB). Whatever you learn next tends to
land in those same, still-twitchy neurons. So two experiences that happened within a few hours share a
chunk of their storage, and recalling one makes you more likely to recall the other. Beyond ~a day the
excitability has faded and the two memories stay separate (Cai et al. 2016, Nature; Rashid et al. 2016
— Rashid not read directly, flagged). Newer work adds a second, offline route: a strong, scary event
makes the brain, during later rest, replay *both* the new memory and a neutral memory from two days
earlier at the same time, which links them — and it only works backwards in time, never forwards
(Zaki et al. 2024, Nature; chemogenetically blocking the hippocampus during that offline window
blocked the linking but left the original memory intact). A related paper reports the locus coeruleus
(a noradrenaline hub) regulating memory linking (Neuron 2022 — abstract seen via search, full text not
read).

**Evidence quality.** Strong. Causal manipulations in both directions (raise excitability → force
linking; block offline activity → prevent linking), multiple labs, and a human behavioural counterpart
(memories close in time get linked and co-updated). The *function* claim — that this is how the brain
builds bridges between separately-learned things — is interpretation, not proof.

**Why it might matter for new ideas.** New ideas are usually two old things joined. This mechanism is a
cheap, content-blind way for the brain to pre-wire bridges between things that were never experienced
together, using only *when* they were learned. It also has a built-in gate: only salient events
trigger the offline version, and only backwards.

**Honest counter-argument.** Time-of-encoding is a dumb proxy for relatedness. In a brain with a rich
stream of experience it may mostly create junk links; the brain may tolerate that because the cost is
low. In a toy model with clean data it could just add noise — or worse, act as a shortcut cue that
leaks which rows belong together, and look like a win for the wrong reason.

**Why it may be untested in ML.** (a) The neuroscience only became crisp recently (2016 → 2024/25);
(b) ML already has a socially-accepted answer for "link related things" — attention and embedding
similarity — so nobody reaches for a time-based tag; (c) the offline, retrospective, salience-gated
version has no natural home in a standard training loop, which has no concept of "hours ago".

**Kill-search log (7 queries, 0 ML implementations found).**
1. `memory allocation neuronal excitability CREB co-allocation machine learning continual learning model` → neuroscience only.
2. `arxiv engram allocation intrinsic excitability inspired artificial neural network memory linking` → **Delamare, Tomé & Clopath 2024, J. Neurosci.** — rate-based RNN with excitability + Hebbian plasticity reproducing engram overlap. Biology model; no task benefit tested.
3. `"memory linking" OR "co-allocation" engram overlap inspired deep learning transformer compositional inference arxiv` → only a name collision ("Engram" = an LLM lookup module, unrelated).
4. `"temporal memory linking" OR "memory linking" shared ensemble time window neural network model artificial agent task performance` → neuroscience only.
5. `hippocampus excitability tag shared context vector deep learning episodic memory binding across episodes inference NeurIPS ICLR` → nearest hit is EM-LLM (below).
6. `Cai 2016 shared ensemble memory linking cited by computational model artificial intelligence deep network implementation` → comp-neuro citations only.
7. `excitability-based memory allocation catastrophic forgetting "context gating" Hebbian tag deep network` → context-gating continual-learning work (below), not excitability-based linking.

**Nearest prior work (be honest about these).**
- **EM-LLM** (Fountas et al., ICLR 2025): retrieval mixes similarity with *temporal contiguity* — it pulls in events adjacent in time. That is the retrieval half of the idea, but it is a fixed read-time rule, not a write-time shared tag that decays, and there is no salience-gated offline linking.
- **Hebbian context gating** (Flesch et al., PLOS Comp Biol 2023) and context-dependent gating for continual learning: use context tags to *separate* tasks. Same machinery, opposite goal (separate, not link), and the tag is task identity, not a decaying clock.
- **Delamare et al. 2024**: the biology model. It shows overlap emerges; it never asks whether overlap makes a learner better.

**Design for our model — "excitability tags + retrospective offline linking".**
- *Module.* A tag bank of K=32 learned vectors (32-dim), plus a slowly-decaying tag state. Extra params ≈ 1–2k (tag table + one blend scalar α + one link rate).
- *Inputs/outputs.* Input: the rows of the story currently being encoded, and a step counter. Output: modified row keys `key_i = content_key_i + α · tag_t`, where `tag_t` is a mixture of the current tag and the previous episodes' tags with exponential decay over a window W (e.g. W = 3 stories). Stories close in training time share tag mass; distant ones do not.
- *When it runs.* (a) At encoding, every time rows are written. (b) Offline: after any training episode whose advantage/loss is in the top 10% ("salient"), run one pass that co-activates that story's rows with rows from the previous W stories and applies a small Hebbian nudge making their keys more similar — **backwards only**, matching Zaki.
- *Learned vs fixed.* Tag vectors learned; decay window, salience threshold and Hebbian rate fixed (pre-registered, not tuned per seed).
- *Toy test.* Split the knowledge: facts about X in story A, the LINK X→Y in story B, facts about Y in story C, never co-presented. Ask 2-hop questions that must join across stories. Controls: (i) tags off; (ii) tags on but *never overlapping* across time (random per story) — this matches params and compute exactly and isolates the sharing, not the tag; (iii) one global tag on everything (controls for "just add a constant vector"); (iv) matched-compute baseline with the offline pass run but with the Hebbian nudge zeroed.
- *Pass mark (pre-register).* ≥ +15 points cross-story 2-hop accuracy over control (ii), in ≥ 4 of 5 seeds, with ≤ 3 points loss on within-story 1-hop.
- *What would show it does NOT help.* No gap vs control (ii); or gains vanish once distractor rows share tags as often as target rows; or gains only appear when W is tuned per seed.
- *Main artefact risk.* The tag becomes a "same batch" giveaway. Mitigate by forcing equal tag overlap between target and distractor rows, and by evaluating on entity pairs held out from training.
- *Build cost.* Small: one encoder change + one offline hook. Each run well under 30 min on the Mac.

---

### S2 — Left–right alternating theta sweeps (intrinsic rhythmic sampling of alternatives)

**What the brain does, plainly.** As a rat moves, its place/grid cells don't just code where it is —
about 8 times a second, the represented position shoots out ahead of the animal like a searchlight, and
the searchlight swings **left, then right, then left**, on a fixed internal rhythm. It sweeps over
places the animal has never visited, and the alternation happens whether or not either side matters
(Vollan et al. 2025, Nature). A systems model reproduces it from firing-rate adaptation in a ring
attractor: the side you just swept gets tired, so the next cycle goes the other way (Current Biology
2024 — title and mechanism verified, author list not read, flagged). A cortical cousin: visual
attention alternates between two objects at about 4 Hz even when you are told to hold still on one
(Fiebelkorn et al. 2013, Current Biology; theta-rhythmic sampling replicated since).

**Evidence quality.** Moderate-strong for the phenomenon (clean population recordings, replicated,
plus a mechanistic model). Weak-to-moderate for the *function* — nobody has causally shown that
blocking the alternation makes animals worse at considering alternatives.

**Why it might matter for new ideas.** The alternation is not driven by value. It is a metronome that
forces the system to hold up the option it did *not* pick, including options never experienced. That
is a structural anti-tunnel-vision device: the second-best idea gets airtime on schedule, not on merit.

**Honest counter-argument.** In practice this may be beam search with worse bookkeeping. ML already
evaluates several branches routinely; the only genuinely new bits are (a) the alternation is intrinsic
and adaptation-driven rather than value-driven, and (b) it covers options that were never taken. If
adaptation-driven alternation ties matched-compute beam-2, the mechanism adds nothing.

**Why it may be untested.** The key paper is from 2025; and the effect is described in spatial
navigation terms, so ML readers see "grid cells", not "a scheduler for candidate hypotheses".

**Kill-search log (5 queries, 0 ML implementations found).**
1. `alternating theta sweeps reinforcement learning agent planning neural network implementation` → continuous-attractor biology models only.
2. `"theta sweep" OR "theta sweeps" arxiv deep reinforcement learning model agent inspired` → nothing (one unrelated "Theta-Resonance" RL paper, name collision).
3. `rhythmic attentional sampling 4 Hz alternation Fiebelkorn machine learning neural network model implementation` → a fronto-parietal spiking model (eLife 2021), no ML use.
4. `forced alternation between candidate plans exploration reinforcement learning oscillatory gating rhythm deep RL brain-inspired` → nearest is "Curious Meta-Controller" (arXiv 1905.01718), which alternates between model-based and model-free control, not between candidate actions on a rhythm.
5. `"cycle skipping" theta alternation computational model machine learning sampling alternatives serial sampling` → biology models only.

**Nearest prior work.** Beam search and two-branch rollouts (standard practice, no citation needed);
adaptation/repetition penalties in decoding, which suppress recently used options — the closest
functional analogue, and the reason my confidence here is only medium-low.

**Design for our model — "sweep-then-commit dispatcher".**
- *Module.* A sweep wrapper on the dispatcher: each decision step gets two internal sub-cycles plus a tiny 2-way comparator head (~1–3k params) and an adaptation vector over lookup options (fixed decay, no params).
- *Inputs/outputs.* Sub-cycle 1: run the top-1 lookup **virtually** (operator executes, result buffered, nothing committed). Sub-cycle 2: subtract the adaptation vector so the just-swept option is suppressed and a different option wins; run it virtually too. Comparator then picks one to commit; the adaptation state carries across steps.
- *When it runs.* Every dispatcher step, in training and test.
- *Learned vs fixed.* Comparator head learned; strict alternation schedule and adaptation decay fixed.
- *Toy test.* 4-hop chains when practice only covered 1–3 steps, with no hand-supplied bookkeeping hints — i.e. aimed straight at the "make 3 calls then stop" bug. Controls: matched-compute beam-2 dispatcher (same 2× operator calls, value-driven not rhythm-driven); ablation with adaptation strength = 0 (comparator alone); ablation with comparator replaced by argmax (rhythm alone).
- *Pass mark (pre-register).* ≥ +20 points on 4-hop over the current dispatcher **and** ≥ +10 points over matched-compute beam-2, in 4 of 5 seeds.
- *What would show it does NOT help.* Parity with beam-2 (then it is just "consider two options"); or the comparator-only ablation matching the full system (then the rhythm is irrelevant).
- *Main artefact risk.* Doubling operator calls alone improves accuracy — which is exactly why the beam-2 control is mandatory, not optional.
- *Build cost.* Medium: needs a virtual-execution path in the dispatcher so a lookup can run without committing. Half a day, runs under 30 min.

---

### S3 — Hippocampal "barcodes": random index codes intermixed with content

**What the brain does, plainly.** When a chickadee hides a seed, its hippocampus fires a sparse,
essentially random, high-dimensional pattern — a "barcode" — unique to that hiding event. The same
pattern briefly returns when the bird retrieves that specific cache. Strikingly, the *same neurons*
also carry ordinary place tuning: index and content are mixed together in one population rather than
kept in separate systems (Chettih et al. 2024, Cell). A follow-up recurrent-network model generates
barcodes from chaotic dynamics and binds them to content with Hebbian plasticity, and shows this
supports more memories with less interference on simulated caching tasks (Fang, Lindsey, Abbott,
Aronov & Chettih, eLife).

**Evidence quality.** Moderate. Beautiful data, but one lab, one unusual species, and the "it is an
index" claim is interpretation from decoding, not a causal test.

**Why it might matter for new ideas.** A content-free random handle lets you store and later recombine
events that are nearly identical in content without them blurring together — the raw material for
"these two almost-identical situations differed in one way" thinking.

**Honest counter-argument.** ML has had random index codes for decades (sparse distributed memory,
key-value memory). The only fresh part is intermixing index and content in one population and
generating the index from chaotic recurrent dynamics — which may be a biological constraint, not a
benefit.

**Kill-search log (4 queries; a biology model exists, no ML-task use found).**
1. `random barcode index code binding machine learning hippocampus inspired transformer memory 2025` → the eLife model; it explicitly relates itself to transformer attention but benchmarks nothing from ML.
2. `Chettih barcode cited by arxiv machine learning key-value memory index code deep network experiment` → Tyulmankov et al. "Biological learning in key-value memory networks" (arXiv 2110.13976) and Gershman et al. "Key-value memory in the brain" (arXiv 2501.02950) — theory papers, not barcode implementations.
3. `random sparse index key episodic memory neural network improves task performance separate index from content arxiv 2025` → sparse memory-augmented networks, SDM — close cousins, different mechanism.
4. (fetched) eLife 103512 full text → evaluated on simulated cache-presence / cache-location tasks only; no ML baselines.

**Design for our model — "barcode row index".**
- *Module.* A fixed random sparse code generator (64 dims, 8 active) seeded by row slot and story id, not by row content; row key becomes `[content_key ; β · barcode]` with β learned (≈ 100 extra params, plus a fixed random matrix).
- *When it runs.* At row encoding; the operator may address rows by content, by barcode, or both.
- *Toy test.* Adversarial stories containing near-duplicate rows (same relation, confusable values, different people). Controls: no barcode; barcode with β frozen at 0; content-key dimension increased by 64 to match capacity.
- *Pass mark.* ≥ +15 points on the confusable-row eval, ≤ 2 points loss elsewhere, 4 of 5 seeds.
- *What would show it does NOT help.* The capacity-matched control closes the gap — meaning it was extra dimensions, not indexing.
- *Main artefact risk.* The barcode leaks row identity and turns retrieval into lookup-by-ID.
- *Build cost.* Smallest of the three; a couple of hours.

---

## 4. Eliminated candidates (with the paper that killed each)

| Candidate | Killed by |
|---|---|
| Behavioural-timescale synaptic plasticity (BTSP), one-shot place fields | Multilayer ANNs trained with BTSP rules for image classification, and BTSP applied to hyperdimensional computing (bioRxiv 2025.05.15.654220); "Credit assignment via BTSP" (bioRxiv 2025.06.12.659336); review in J. Neurosci. 45(46) 2025 |
| Synaptic tagging and capture / behavioural tagging | Luboeinski & Tetzlaff, Comms Biol 2021 (STC in recurrent nets improves recall); neuromodulator-dependent STC in spiking nets (2022); reviewed for continual learning in arXiv 2405.16922 |
| Silent synapses / filopodia as a reserve for new learning | "Brain-inspired continual pre-trained learner via silent synaptic consolidation" (arXiv 2410.05899) |
| Locus-coeruleus "network reset" (Bouret & Sara 2005) | Surprise-modulated learning rates (arXiv 1606.05642); "Lifelong RL via neuromodulation" (arXiv 2408.08446) |
| Sharp-wave-ripple selection of what gets replayed (Yang et al., Science 2024) | Functionally equivalent to prioritised experience replay, which is standard ML; ripple-tagging adds ordering detail, not a new principle |
| Theta-phase separation of encoding vs retrieval (Hasselmo SPEAR) | Ketz, Morkonda & O'Reilly, PLOS Comp Biol 2013 — theta-coordinated error-driven learning, a working learning model |
| Rotational dynamics orthogonalising memory from input (Libby & Buschman 2021) | Duncker et al., NeurIPS 2020 (orthogonal-subspace dynamics for continual learning); "Learning sculpts orthogonal task manifolds" (bioRxiv 2026) |
| Reconsolidation / editable retrieved memories | "Brain-inspired continual learning — robust feature distillation and re-consolidation" (arXiv 2404.14588) |
| Ripple-driven recombination of building blocks for planning | He, Liu, Behrens et al., Nat. Neurosci. 2026 — and this is the compositional-replay experiment already being built here; not re-proposed |
| Ripples aligning new experience to a grid-like schema (Neuron 2025) | Covered by existing replay + schema/TEM work in ML |
| Firing-rate adaptation as a novelty driver on its own | Repetition/diversity penalties in decoding and tabu-style search are the same idea; folded into S2 instead |
| Latent inhibition ↔ creativity | Not killed by an ML paper, dropped for weak, largely correlational human evidence and no clear mapping to our toy |

---

## 5. Honest limits

- **Absence of evidence is weak.** I ran 4–7 targeted searches per survivor plus general sweeps (~25
  total). A web search engine is not Google Scholar; I could not crawl true "cited-by" trails, so an
  obscure workshop paper or a 2026 preprint could kill any of these tomorrow.
- **Every survivor has a comp-neuro model.** None is virgin territory. The untested claim is narrower:
  *nobody used it as a mechanism to make a learning system better at a task.*
- **Nearest-prior-work honesty.** S1 is adjacent to temporal-contiguity retrieval (EM-LLM) and context
  gating; S2 is adjacent to beam search and repetition penalties; S3 is adjacent to sparse distributed
  memory. If Ben wants a clean novelty claim, S1 is the strongest, and the *retrospective,
  salience-gated offline linking* part is the least-covered piece of it.
- **Unverified details, flagged:** author lists for the Current Biology 2024 theta-sweep model, the
  Neuron 2022 locus-coeruleus memory-linking paper, and Rashid et al. 2016 were seen only in search
  snippets, not read directly. The Zaki 2024 Nature paper is dated 2024 online / 2025 in print.
- **Nobody knows how brains produce original thought.** Every "why it might matter" above is my
  reasoning, not an established finding.

---

## 6. References

Biology
- Chettih, Mackevicius, Hale & Aronov (2024). Barcoding of episodic memories in the hippocampus of a food-caching bird. *Cell*. https://www.cell.com/cell/fulltext/S0092-8674(24)00235-6
- Fang, Lindsey, Abbott, Aronov & Chettih. Barcode activity in a recurrent network model of the hippocampus enables efficient memory binding. *eLife*. https://elifesciences.org/articles/103512
- Vollan, Gardner, Moser & Moser (2025). Left–right-alternating theta sweeps in entorhinal–hippocampal maps of space. *Nature* 639:995–1005. https://www.nature.com/articles/s41586-024-08527-1
- A systems model of alternating theta sweeps via firing rate adaptation (2024). *Current Biology*. https://www.cell.com/current-biology/fulltext/S0960-9822(24)01174-6 *(authors not verified)*
- Fiebelkorn et al. (2013). Rhythmic sampling within and between objects despite sustained attention at a cued location. *Current Biology*. https://www.sciencedirect.com/science/article/pii/S0960982213013389
- Cai et al. (2016). A shared neural ensemble links distinct contextual memories encoded close in time. *Nature*. https://www.nature.com/articles/nature17955
- Zaki et al. (2024/25). Offline ensemble co-reactivation links memories across days. *Nature*. https://www.nature.com/articles/s41586-024-08168-4 · open copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC11666460/
- Delamare, Tomé & Clopath (2024). Intrinsic neural excitability biases allocation and overlap of memory engrams. *J. Neurosci.* 44(21). https://www.jneurosci.org/content/44/21/e0846232024
- The locus coeruleus as a regulator of memory linking (2022). *Neuron*. https://www.sciencedirect.com/science/article/pii/S0896627322008194 *(authors not verified)*
- Yang, Sun, Huszár, Hainmueller & Buzsáki (2024). Selection of experience for memory by hippocampal sharp wave ripples. *Science* 383:1478–1483. https://www.science.org/doi/10.1126/science.adk8261
- Libby & Buschman (2021). Rotational dynamics reduce interference between sensory and memory representations. *Nat. Neurosci.* https://www.nature.com/articles/s41593-021-00821-9
- Vardalaki, Chung & Harnett (2022). Filopodia are a structural substrate for silent synapses in adult neocortex. *Nature*. https://www.nature.com/articles/s41586-022-05483-6
- Bouret & Sara (2005). Network reset: a simplified overarching theory of locus coeruleus noradrenaline function. *TiNS*. https://www.cell.com/trends/neurosciences/abstract/S0166-2236(05)00243-2
- He, Wang, Zhang, ... Behrens & Liu (2026). Human hippocampal ripples coordinate planning sequences and compositional representations in neocortex. *Nat. Neurosci.* https://www.nature.com/articles/s41593-026-02291-3
- Human hippocampal ripples align new experiences with a grid-like schema (2025). *Neuron*. https://www.cell.com/neuron/fulltext/S0896-6273(25)00555-0

Machine learning (nearest prior work / eliminations)
- Fountas et al. (2025). Human-inspired episodic memory for infinite-context LLMs (EM-LLM). *ICLR*. https://arxiv.org/abs/2407.09450
- Flesch et al. (2023). Modelling continual learning in humans with Hebbian context gating. *PLOS Comp Biol.* https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1010808
- Duncker et al. (2020). Organizing recurrent network dynamics by task-computation to enable continual learning. *NeurIPS*. https://proceedings.neurips.cc/paper/2020/hash/a576eafbce762079f7d1f77fca1c5cc2-Abstract.html
- BTSP endows hyperdimensional computing with flexible retrieval (2025). bioRxiv. https://www.biorxiv.org/content/10.1101/2025.05.15.654220v2.full
- Credit assignment via behavioral timescale synaptic plasticity (2025). bioRxiv. https://www.biorxiv.org/content/10.1101/2025.06.12.659336
- Behavioral timescale synaptic plasticity: a burst in the field of learning and memory (2025). *J. Neurosci.* 45(46). https://www.jneurosci.org/content/45/46/e1332252025
- Luboeinski & Tetzlaff (2021). Memory consolidation and improvement by synaptic tagging and capture in recurrent neural networks. *Comms Biol.* https://www.nature.com/articles/s42003-021-01778-y
- Theories of synaptic memory consolidation and intelligent plasticity for continual learning (2024). https://arxiv.org/pdf/2405.16922
- Brain-inspired continual pre-trained learner via silent synaptic consolidation (2024). https://arxiv.org/pdf/2410.05899
- Ketz, Morkonda & O'Reilly (2013). Theta-coordinated error-driven learning in the hippocampus. *PLOS Comp Biol.* https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003067
- Brain-inspired continual learning: robust feature distillation and re-consolidation (2024). https://arxiv.org/pdf/2404.14588
- Lifelong reinforcement learning via neuromodulation (2024). https://arxiv.org/pdf/2408.08446
- Tyulmankov et al. (2021). Biological learning in key-value memory networks. https://arxiv.org/abs/2110.13976
- Gershman et al. (2025). Key-value memory in the brain. https://arxiv.org/abs/2501.02950
- Curious meta-controller: adaptive alternation between model-based and model-free control (2019). https://arxiv.org/pdf/1905.01718
