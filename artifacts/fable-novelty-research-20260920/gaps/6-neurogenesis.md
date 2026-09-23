# Gap check #6 — Growing new neurons for new memories

Checked 2026-09-20. Research only (web search + reading). Every reference below is one I actually opened or saw in
search results; where I could not open the paywalled original I say so.

---

## 1. Verdict (≤ 80 words)

**Already well covered** — and one half of the claim is simply false.

"AI networks are a fixed size" has not been true for 35 years and is not true today: model growth is now standard
practice in LLM pre-training (depthwise stacking gave a reported 54.6% speed-up at 7B). Growth helps with *capacity
and forgetting*. Nobody, in brains or machines, has shown growth produces **novel ideas**. And adult human
neurogenesis itself is still genuinely contested.

---

## 2. What the brain does — and how good the evidence is

### 2a. Does the adult human hippocampus make new neurons at all? — **contested, unresolved in 2026**

This is the weakest link in the whole claim, and the memory note stated it as settled fact. It is not.

| Study | Year | Method | Conclusion |
|---|---|---|---|
| [Sorrells et al., *Nature*](https://www.nature.com/articles/nature25975) | 2018 | Immunostaining, 59 human samples | New neurons drop sharply through childhood, **undetectable** in adults |
| [Boldrini et al., *Cell Stem Cell*](https://www.cell.com/cell-stem-cell/fulltext/S1934-5909(18)30121-8) | 2018 | Autopsy, 28 healthy people aged 14–79 | Neurogenesis **persists into the eighth decade** |
| [Moreno-Jiménez et al., *Nature Medicine*](https://www.nature.com/articles/s41591-019-0375-9) | 2019 | Tissue from ages 43–87 | Newborn neurons present to the ninth decade; drop sharply in Alzheimer's |
| Franjic et al., *Neuron* | 2022 | Single-nucleus RNA-seq | **No** adult neurogenic trajectory detected |
| [Zhou et al., *Nature*](https://www.nature.com/articles/s41586-022-04912-w) | 2022 | Single-nucleus RNA-seq | Immature granule cells present across the lifespan |
| [Dumitru, Paterlini et al. (Frisén lab), *Science*](https://www.science.org/doi/10.1126/science.adu9575) | 2025 | snRNA-seq + flow cytometry + machine learning + spatial (RNAscope/Xenium), ages 0–78 | Proliferating progenitors **found** in adult dentate gyrus — but *huge* person-to-person variation; some adults had many, some had almost none |
| [Disouky, Lazarov et al., *Nature*](https://www.nature.com/articles/s41586-026-10169-4) | 2026 | Single-cell + chromatin accessibility; young, aged, preclinical AD, AD, "superagers" | Neurogenesis stalls in AD; **superagers** (80+ with young memory) had the most immature neurons |

Read honestly: two studies using *the same* single-cell method in the same year (2022) reached opposite conclusions.
The 2025 *Science* paper is the strongest positive evidence so far, and even it reports that some adults appear to have
essentially none. So the correct statement is: **adult human hippocampal neurogenesis probably exists, at a low and
highly variable rate, and the field is still arguing.** Rodent neurogenesis is not in doubt — the dispute is about
humans.

Evidence quality: **moderate and contested.** Do not write "the brain adds new neurons in adulthood" as a settled
premise in anything we publish.

### 2b. Does it support pattern separation? — **moderate, rodent-only, causal**

- [Clelland et al., *Science* 2009](https://www.science.org/doi/10.1126/science.1173215): knocking out neurogenesis in
  mice impaired discrimination of *nearby* locations only. Necessity.
- [Sahay et al., *Nature* 2011](https://www.nature.com/articles/nature09817): boosting survival of adult-born neurons
  improved discrimination of overlapping contexts, while leaving object recognition and spatial learning normal.
  Sufficiency.
- [Hippocampus meta-analysis, 2017](https://onlinelibrary.wiley.com/doi/10.1002/hipo.22746) (I could not open the full
  text; from the abstract and secondary sources): most of the literature supports the effect, two studies diverge.
- Counter-example that gets quoted less: [Groves et al., *PLOS Genetics* 2013](https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1003718)
  ablated neurogenesis in rats pharmacogenetically and found **no effect** on spatial processing.

So: real causal rodent evidence, with a known dissent, and a live critique that the behavioural "pattern separation"
tasks may not measure pattern separation at all.

### 2c. Does adding neurons cause FORGETTING? — **strong, and it cuts against the claim**

[Akers et al., *Science* 2014](https://www.science.org/doi/10.1126/science.1248903) is the important one. Raising
neurogenesis *after* a memory was formed made adult mice **forget** it. Lowering neurogenesis in infant mice
*prevented* the normal infant forgetting. In guinea pigs and degus — species that make most granule cells before birth
— infants don't normally show this forgetting, but artificially adding neurogenesis induced it.

So new neurons are not a free "extra notebook". Adding them **degrades existing memories**. The memory-note framing
("so new experiences are stored without blurring into old ones") tells only half the story.

### 2d. Cognitive flexibility and creativity? — **speculative; the creativity link is basically absent**

[Anacker & Hen, *Nat. Rev. Neurosci.* 2017](https://www.nature.com/articles/nrn.2017.45) is a **review proposing a
hypothesis**: young adult-born neurons inhibit the dentate gyrus via local interneurons → sparser representations →
less memory interference → easier reversal learning → less anxiety/depression. It is a well-argued model, not a
demonstration.

On creativity specifically: I searched the divergent-thinking / creative-idea-generation literature and it is about
prefrontal cortex, default-mode network, alpha-band EEG, aperiodic "neural noise" and dopamine. **Adult neurogenesis
does not appear in it.** Nobody has shown a hippocampal-neurogenesis → novel-idea-generation link in humans. That part
of the claim is invented connective tissue.

---

## 3. What AI has already done

Eight works, closest first. The short version: growth is old, it works, and it is now mainstream at the largest scale.

1. **Cascade-Correlation** — Fahlman & Lebiere, NIPS 1989/1990.
   [PDF](https://papers.nips.cc/paper/207-the-cascade-correlation-learning-architecture.pdf). Starts with no hidden
   units and adds one at a time, freezing each one's input weights when it is added. This is literally
   "grow the network as the task demands" and it is 36 years old.

2. **NEAT** — Stanley & Miikkulainen, *Evolutionary Computation* 2002.
   [Semantic Scholar](https://www.semanticscholar.org/paper/d03c916d49268d48fde3b76a68e64af7761835e7). Evolves both
   weights and topology from a minimal starting network, complexifying by mutation. Still in use — there is a 2024
   GPU-tensorized version, [TensorNEAT](https://arxiv.org/abs/2404.01817).

3. **Net2Net** — Chen, Goodfellow & Shlens, ICLR 2016. [arXiv:1511.05641](https://arxiv.org/abs/1511.05641).
   *Function-preserving* transformations: widen or deepen a trained net so its output is unchanged at the moment of
   growth, then keep training. This is the technical trick that makes every later growth method work.

4. **Progressive Neural Networks** — Rusu et al., 2016. [arXiv:1606.04671](https://arxiv.org/abs/1606.04671). Adds a
   frozen "column" per task with lateral connections. Zero forgetting by construction; parameters grow linearly with
   tasks, which is its known flaw.

5. **Dynamically Expandable Networks (DEN)** — Yoon et al., ICLR 2018.
   [arXiv:1708.01547](https://arxiv.org/abs/1708.01547). Adds *only the necessary number* of units per task, splits
   and duplicates drifting units, timestamps them. The direct ancestor of every "grow on demand" continual-learning
   paper since.

6. **Neurogenesis Deep Learning** — Draelos et al., IJCNN 2017.
   [IEEE](https://ieeexplore.ieee.org/document/7965898/). The explicitly neurogenesis-branded one: adds neurons to an
   autoencoder for new MNIST/NIST classes plus "intrinsic replay". Small scale (MNIST-class), and it addresses the
   stability–plasticity problem — i.e. forgetting, not invention.

7. **Firefly Neural Architecture Descent** — Wu, Liu, Stone & Liu, NeurIPS 2020.
   [PDF](https://proceedings.neurips.cc/paper/2020/file/fdbe012e2e11314b96402b32c0df26b7-Paper.pdf), and
   **GradMax** — Evci et al., ICLR 2022. [arXiv:2201.05125](https://arxiv.org/abs/2201.05125),
   [code](https://github.com/google-research/growneuron). Both answer "*where* and *how* do I add a neuron" in a
   principled way: Firefly by steepest descent over candidate structures, GradMax by initializing new neurons via SVD
   to maximize their gradient norm so they actually learn something.

8. **LLM model growth (2022–2025) — this is the one that kills the "fixed size" claim.**
   - bert2BERT (ACL 2022) and **LiGO** (ICLR 2023) grow a small trained model into a large one along all dimensions.
   - **Masked Structural Growth**, ICLR 2024. [arXiv:2305.02869](https://arxiv.org/abs/2305.02869) — ~2× faster LM
     pre-training via staged, one-dimension-at-a-time growth.
   - **Stacking Your Transformers** (G_stack), NeurIPS 2024. [arXiv:2405.15319](https://arxiv.org/abs/2405.15319),
     [site](https://llm-stacking.github.io/) — systematically compares four atomic growth operators; depthwise
     stacking wins, with a reported **54.6% speed-up at 7B parameters** and gains on eight NLP benchmarks.
   - **Orthogonal growth of Mixture-of-Experts**, 2025. [arXiv:2510.08008](https://arxiv.org/abs/2510.08008) — growing
     MoE models by adding experts mid-pre-training.

**Also directly relevant: the "turnover / replacement" side, which is the strongest AI result in this whole area.**

- **Loss of plasticity in deep continual learning** — Dohare, Hernandez-Garcia, Lan, Rahman, Mahmood & Sutton,
  *Nature* 2024. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11338828/),
  [code](https://github.com/shibhansh/loss-of-plasticity). Standard deep nets **lose the ability to learn** over long
  task sequences (ImageNet binary tasks: 89% early → ~77%, about linear-model level, by task 2000). Their fix,
  *continual backpropagation*, continually re-initializes a small fraction of low-utility units — a direct machine
  analogue of neuronal turnover — and it keeps learning going, in their words, seemingly indefinitely. This is a
  high-profile, replicated-style result at real scale.
- **ReDo / the dormant neuron phenomenon** — Sokar et al., ICML 2023.
  [arXiv:2302.12902](https://arxiv.org/abs/2302.12902). RL agents accumulate dead neurons; periodically resetting them
  improves performance on Atari.
- **Plasticity Injection** — Nikishin et al., NeurIPS 2023.
  [PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/75101364dc3aa7772d27528ea504472b-Paper-Conference.pdf).
  Restores plasticity *without changing the parameter count* — a useful control: it shows some "growth" benefits are
  really plasticity benefits.
- **Adult neurogenesis acts as a neural regularizer** — Tran, Santoro, Liu, Josselyn, Richards & Frankland, *PNAS*
  2022, 119(45). [PNAS](https://www.pnas.org/doi/10.1073/pnas.2206704119). Put a neurogenesis-like process into a CNN
  and found it worked about as well as **dropout**. That is the honest ceiling on the mechanism as of 2022: a decent
  regularizer, not a new capability.
- **Sparse Distributed Memory is a Continual Learner** — Bricken et al., ICLR 2023.
  [arXiv:2303.11934](https://arxiv.org/abs/2303.11934). The pattern-separation-inspired route *without* growth: a
  Top-K sparse MLP (motivated by dentate-gyrus-style inhibition) is already a strong continual learner. Relevant
  because it suggests sparsity, not growth, may be the part of the biology that transfers.

**Negative / cautionary results (important):**

- **Growth-induced forgetting** — Zhao et al., 2024. [arXiv:2408.10566](https://arxiv.org/abs/2408.10566). Applying
  model growth badly in task-agnostic continual learning *causes severe degradation of what was already learned.*
  Growth is not free — mirroring Akers 2014 in biology.
- **Adding experts can hurt** — [Theory on Mixture-of-Experts in Continual Learning, ICLR 2025](https://arxiv.org/abs/2406.16437):
  more experts means more rounds to converge and does not necessarily improve performance.
- **Fair-comparison problem.** Expansion methods add parameters, so beating a smaller fixed baseline proves nothing.
  Several 2023–2025 papers now explicitly control hidden dimension or use an oversized static baseline. Any experiment
  we run must do this.
- **Recent 2026 work exists but is small-scale**: e.g. [NORACL](https://arxiv.org/abs/2604.27031) (Raghunathan,
  Metzner, Kriener, Payvand, 2026) grows networks when it detects representational and plasticity saturation, matching
  oracle-sized baselines with fewer parameters; PS-SNN and NG-SNN (2026) do pattern-separation-style expandable spiking
  nets. Active niche, modest scale.

---

## 4. The real gap

Three things, ranked by how real they are.

1. **Growth for novel-idea generation has never been tested — because there is no reason to think it works.**
   Every single AI growth result above is measured on *capacity* or *forgetting*: accuracy on new tasks, retention of
   old tasks, pre-training loss, wall-clock speed-up. I found **zero** work claiming structural growth improves
   compositional generalization, out-of-distribution reasoning, exploration, or the invention of new operations. The
   brain side is equally empty (§2d). So this is "genuinely open" in the uninteresting sense: open because nobody has a
   hypothesis for why it would be true. Do not write this up as an opportunity.

2. **Growth triggered by a model's own detected failure, rather than by a human-supplied task boundary, is thin.**
   Most methods grow at task boundaries someone tells them about. DEN, Firefly and NORACL are the exceptions.
   A trigger that fires on *"my verifier keeps rejecting this kind of step"* — as opposed to *"a new task started"* —
   is genuinely under-explored. This is the only part of the topic I'd call a real research gap.

3. **What is NOT a gap: everything in the original claim.** "AI networks are a fixed size; structural growth is not
   part of mainstream architectures" is wrong. Frontier labs grow models during pre-training (§3.8), add experts to
   MoEs mid-training, and reset units to restore plasticity (*Nature* 2024). The memory note is out of date by roughly
   a decade.

---

## 5. Design proposals — putting this mechanism into models

Three distinct options. All three honour the same constraints: Mac + one consumer GPU, each experiment < 30 min,
pre-registered pass marks, one change at a time.

Before the options, the honest framing: **the biology has two separable halves.** Half A is *growth* (add capacity so
new things fit). Half B is *turnover* (adding/replacing units erases over-consolidated old traces — Akers 2014). Half B
is better evidenced in biology *and* has the stronger AI track record (Dohare 2024, Sokar 2023, forget-and-relearn).
Our known bug is a Half-B problem, not a Half-A problem. That drives the ranking.

---

### Option 1 — **Turnover resets for the dispatcher** (break the "3 calls then stop" habit) — *my pick*

**(a) Plain words.** Our dispatcher has a bad habit: it makes exactly three lookups and stops, because three was the
longest chain it ever practised. In the brain, brand-new neurons joining a circuit actively wipe out old
over-practised memories (that's why babies forget everything). So: every so often, take the small handful of the
dispatcher's units that are pulling the least weight, scrub them back to random, and carry on training. The
over-learned "count to three" habit lives in the most-settled weights; scrubbing forces the controller to re-derive its
stopping rule from what it can actually see in the story, instead of reciting a number.

**(b) Concrete design.**
- **Module:** none. It's a hook in the dispatcher's RLOO training loop. Zero new parameters.
- **When it runs:** training only, every N optimizer updates (start N = 200). Never at inference.
- **Inputs:** per-hidden-unit running statistics. **Output:** an in-place weight edit.
- **Rule:** utility of unit *i* = running mean |activation_i| × Σ|outgoing weights_i| (the continual-backprop utility,
  Dohare 2024). Reset the bottom ρ = 1–5%: re-randomize incoming weights, **zero the outgoing weights** so the
  function is exactly unchanged at the instant of the reset (this is the Net2Net function-preserving idea — without
  it you are just injecting noise). A freshly reset unit is immune from re-reset for M = 500 steps ("maturation").
- **Variant B** (cheaper, blunter — *later-layer forgetting*, Zhou et al. ICLR 2022): every N updates re-initialize
  the **entire STOP head** and keep the action head. Directly targets the stopping rule.
- **Learned vs fixed:** nothing new is learned. ρ, N, M and the utility rule are fixed hyperparameters.
- **Params:** +0 trainable. ~2 floats of bookkeeping per hidden unit (≈ 50–200 floats total).
- **Wiring:** operator stays frozen throughout — this only touches the 15–24k-param dispatcher. Nothing else in the
  pipeline changes, which is exactly why it is safe to try first.

**(c) At LLM scale.** This *is* continual backprop / ReDo: reset low-utility or dormant units on a schedule during
long fine-tuning or RL post-training runs, to stop the policy collapsing onto a memorized pattern.

**(d) Falsifiable toy test.**
- **Task:** the no-hints dispatcher setting. Train on 1–3 hop chains as now; evaluate 1–6 hops. Current baseline:
  64/64 up to 3 hops, **4/64 beyond**.
- **Controls (all same seeds, same number of gradient steps — the reset costs ≈ 0 extra FLOPs, so matched compute is
  matched steps):**
  (i) identical run, no resets;
  (ii) **noise control** — perturb the *same* units with Gaussian noise of matched norm instead of resetting, to rule
  out "any perturbation works";
  (iii) **entropy-bonus control** — the standard RL fix for a collapsed policy, tuned, so we don't just rediscover
  exploration bonus and call it neurogenesis;
  (iv) reset *high*-utility units instead of low, to check the utility ranking is load-bearing.
- **Pass mark (pre-register):** ≥ 32/64 (50%) at 4–6 hops in ≥ 2 of 3 seeds, **and** 1–3 hop accuracy ≥ 60/64, **and**
  beating the entropy-bonus control by ≥ 10 points at 4–6 hops.
- **Would show it doesn't help:** 4–6 hop accuracy stays < 16/64, or control (iii) matches it, or control (ii) matches
  it.
- **Main artefact risk:** resets are just an exploration boost in disguise — control (iii) is the guard. Second risk:
  resets make training spiky and we cherry-pick a lucky checkpoint — so evaluate at a **fixed step count**, never
  best-of.

**(e) Build cost: SMALL.** One training hook plus a sweep. 4 arms × 3 seeds, each well under 30 min.

---

### Option 2 — **Grow-on-demand entity slots** (for the bigger toy with more names)

**(a) Plain words.** Today the model has exactly 16 name-shaped boxes, hammered into its weights during training. A
17th name is simply unthinkable to it. Instead, give it a stack of blank boxes and a rule: when a name shows up that
doesn't match any box you're already using, grab a blank one, fill it in from the sentence where the name first
appeared, and use that box from then on. Capacity then grows with *the story in front of it*, not with the training
run.

**(b) Concrete design.**
- **Module:** a "slot bank" between the story encoder and the lookup operator.
- **Inputs:** the story's rows. **Outputs:** S slot vectors (S = 64, comfortably more than any story needs) plus a
  mention→slot index map.
- **When it runs:** at read time, on every story, train and test alike.
- **Mechanism:** match each entity mention against occupied slots; on a miss, allocate the next free slot and
  initialize it from a small learned encoder applied to the row where the name first appeared (2-layer MLP, d = 64).
- **Learned vs fixed:** the slot initializer and a key projection are learned (~15–20k params). The allocation rule
  (first-come; a slot is never reused within a story) and S are fixed.
- **Params:** +~20k. The operator's own count is roughly unchanged (~79k) — its key/value projections now read slot
  vectors instead of 16 learned ID embeddings.
- **Wiring:** the dispatcher is **untouched** — it still emits (entity, relation) pairs; "entity" is now a slot index
  rather than a global ID.

**(c) At LLM scale.** This is a pointer/copy mechanism or a per-context entity cache: entities allocated at inference
time rather than getting permanent vocabulary entries.

**(d) Falsifiable toy test.**
- **Task:** train on stories using only names 0–15. Test on structurally identical stories using names 16–31, never
  seen in training.
- **Controls:** (i) the honest fixed-size baseline — current system with the ID table widened to 32 but names 16–31
  never trained (expected: near chance); (ii) **matched-param** — fixed-size model given the same ~20k extra params as
  extra operator width; (iii) **shuffled-name control** — permute the training names at test time, to confirm the slot
  system isn't just memorizing ID identity.
- **Pass mark:** unseen-name 1–3 hop accuracy ≥ 90% of the in-vocabulary accuracy; baseline (i) below 25% of it.
- **Would show it doesn't help:** unseen-name accuracy < 50% of in-vocab, **or** baseline (i) already passes — in
  which case the fixed table was never the problem and we should stop.
- **Main artefact risk:** the win comes from the *hand-written symbol-matching rule*, not from anything learned. We'd
  be proving that hard-coded pointers work — true, but not a finding. **Guard:** also report a variant where matching
  must be learned from embeddings instead of exact symbol equality, and report both numbers.

**(e) Build cost: MEDIUM.** Touches the operator's input path and needs a new unseen-name data split.

**Honest caveat:** calling this "neurogenesis" is a stretch. The actual content is *make entity identity
content-addressed instead of weight-stored*. If that's what we want, we should say that plainly rather than dress it in
biology — and we should first check whether a plain pointer/copy mechanism (cheaper, no growth) already does it.

---

### Option 3 — **Grow a second operator when the first one stalls**

**(a) Plain words.** Right now the system knows exactly one skill: "look up relation r for person X". If the world
throws a question at it that this skill physically cannot answer, there's nowhere to put a new skill — it just fails
forever. Option 3 gives it a trigger: when the checker keeps rejecting the same kind of step, photocopy the existing
skill, let the copy specialize on the cases that keep failing, and give the controller a new button to press. This is
the only option that is genuinely about *gaining a new operation*, which is what the "grow to invent things" story
actually promises.

**(b) Concrete design.**
- **Module:** an operator bank (list of operators) + a growth trigger + a dispatcher action head that can be extended.
- **When it runs:** between training rounds, never mid-step.
- **Trigger inputs:** per-step verification failure rates from the frozen operator/verifier, clustered by
  (relation, position-in-chain). **Output:** a decision to clone, or not.
- **Rule:** if failure rate on a cluster > τ for K consecutive rounds → clone operator O → O′ as an **exact copy**
  (function-preserving), add small random perturbation to O′ only, **freeze O**, train O′ on the failing cluster,
  append one action to the dispatcher.
- **Learned vs fixed:** O′'s weights and the extended dispatcher head are learned; τ, K, the clone rule, and the
  failure-clustering are fixed.
- **Params:** +~79k per grown operator; dispatcher +~a few hundred (one extra action row).
- **Wiring:** the dispatcher's action space changes size mid-training — that's the fiddly part, and the main reason
  this is expensive.

**(c) At LLM scale.** MoE upcycling / adding experts mid-training (cf. arXiv:2510.08008), but with a
verifier-failure-driven trigger instead of a fixed schedule.

**(d) Falsifiable toy test.** Needs a task where one operator *provably* cannot suffice, otherwise the result is
meaningless. Phase 1: today's world. Phase 2: add reverse-LINK questions ("who links **to** X?"), which the forward
operator cannot express. Measure phase-2 accuracy and phase-1 retention.
- **Controls:** (i) **matched-param** — a two-operator model trained on both phases from scratch, same total params
  (if this matches, growth is just "more params"); (ii) **matched-compute** — single operator at 2× width, same FLOPs;
  (iii) **random-time growth** — grow at a random round instead of when triggered. Control (iii) tests the *actual*
  scientific claim, which is that the trigger carries information.
- **Pass mark:** ≥ 90% on phase 2 **and** ≥ 90% retention on phase 1, **and** triggered growth beats random-time
  growth by ≥ 15 points on phase 2.
- **Would show it doesn't help:** control (i) or (ii) matches it (growth is just capacity), or control (iii) matches
  it (the trigger is decoration).
- **Main artefact risk:** we build an elaborate mixture-of-experts and report the parameter increase as a discovery.
  Controls (i)–(iii) exist precisely to prevent that. Second risk, documented in
  [arXiv:2408.10566](https://arxiv.org/abs/2408.10566): the act of growing itself damages phase-1 performance, so
  retention must be a *pass condition*, not a footnote.

**(e) Build cost: LARGE.** New relation family in the generator, operator-bank plumbing, a resizable dispatcher action
space, 5 arms × 3 seeds.

---

### Ranking, and what I'd build first

**1 → 2 → 3.**

**Build Option 1 first.** Three reasons. (a) It is the only one of the three aimed at a failure we have *actually
observed* — the controller's "3 calls then stop" habit is a textbook over-consolidated policy, and unit turnover is the
published fix for exactly that (Dohare 2024 in *Nature*; Sokar 2023; Zhou 2022 forget-and-relearn). (b) It adds **zero
parameters**, which sidesteps the fair-comparison trap that makes most growth results unconvincing. (c) It is a
half-day of work, fits the < 30 min per run budget with room for four control arms, and if it fails it fails cleanly
and cheaply.

Option 2 is worth doing **only** when the bigger-name toy is actually built and we have measured that the fixed
16-entity table is what breaks — and even then, try a plain pointer mechanism before a growth mechanism. Option 3 is
the intellectually interesting one and the only real gap identified in §4, but it is a large build resting on a
premise we haven't established, so park it.

**Does this topic fit our toy at all?** Partly, and less than the claim suggests. We have never observed a
capacity failure. Our two observed failures are a *habit* failure (the 3-call ceiling) and a *transfer* failure
(held-out combinations without hints). Growth addresses neither. Turnover plausibly addresses the first. Be honest
about that distinction in any write-up.

---

## 6. Priority score

**2 / 5** for the topic as stated (structural growth). The claim's premise is false, the biology is contested, and the
creativity link doesn't exist. Do not build a growth mechanism.

**But Option 1 alone is a 4 / 5** — it is cheap, parameter-free, aimed squarely at our known dispatcher bug, and has
a *Nature* 2024 result behind it. Worth a slot in the next experiment wave, filed under "plasticity / habit-breaking"
rather than "neurogenesis".

---

## 7. References

Neuroscience:
- Sorrells et al. (2018) *Nature* 555:377–381 — https://www.nature.com/articles/nature25975
- Boldrini et al. (2018) *Cell Stem Cell* — https://www.cell.com/cell-stem-cell/fulltext/S1934-5909(18)30121-8
- Moreno-Jiménez et al. (2019) *Nature Medicine* — https://www.nature.com/articles/s41591-019-0375-9
- Zhou et al. (2022) *Nature* — https://www.nature.com/articles/s41586-022-04912-w
- Franjic et al. (2022) *Neuron* — seen only via secondary sources; exact URL unverified
- Dumitru, Paterlini et al. (Frisén lab) (2025) *Science* — https://www.science.org/doi/10.1126/science.adu9575
  (paywalled; details via https://news.ki.se/new-research-confirms-that-neurons-form-in-the-adult-brain)
- Disouky, Lazarov et al. (2026) *Nature* — https://www.nature.com/articles/s41586-026-10169-4
  (summary via https://www.alzforum.org/papers/human-hippocampal-neurogenesis-adulthood-ageing-and-alzheimers-disease)
- Clelland et al. (2009) *Science* 325:210 — https://www.science.org/doi/10.1126/science.1173215
- Sahay et al. (2011) *Nature* 472:466 — https://www.nature.com/articles/nature09817
- Groves et al. (2013) *PLOS Genetics* — https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1003718
- Akers et al. (2014) *Science* 344:598–602 — https://www.science.org/doi/10.1126/science.1248903
- Pattern-separation meta-analysis (2017) *Hippocampus* — https://onlinelibrary.wiley.com/doi/10.1002/hipo.22746
  (abstract only; full text not accessible)
- Anacker & Hen (2017) *Nat. Rev. Neurosci.* 18:335–346 — https://www.nature.com/articles/nrn.2017.45

AI — growth:
- Fahlman & Lebiere (1990) Cascade-Correlation — https://papers.nips.cc/paper/207-the-cascade-correlation-learning-architecture.pdf
- Stanley & Miikkulainen (2002) NEAT — https://www.semanticscholar.org/paper/d03c916d49268d48fde3b76a68e64af7761835e7
  ; GPU version (2024) https://arxiv.org/abs/2404.01817
- Chen, Goodfellow & Shlens (2016) Net2Net, ICLR — https://arxiv.org/abs/1511.05641
- Rusu et al. (2016) Progressive Neural Networks — https://arxiv.org/abs/1606.04671
- Draelos et al. (2017) Neurogenesis Deep Learning, IJCNN — https://ieeexplore.ieee.org/document/7965898/
- Yoon et al. (2018) DEN, ICLR — https://arxiv.org/abs/1708.01547
- Wu, Liu, Stone & Liu (2020) Firefly, NeurIPS — https://proceedings.neurips.cc/paper/2020/file/fdbe012e2e11314b96402b32c0df26b7-Paper.pdf
- Evci et al. (2022) GradMax, ICLR — https://arxiv.org/abs/2201.05125
- Masked Structural Growth (2024) ICLR — https://arxiv.org/abs/2305.02869
- Stacking Your Transformers (2024) NeurIPS — https://arxiv.org/abs/2405.15319
- Orthogonal growth of MoE (2025) — https://arxiv.org/abs/2510.08008
- NORACL (2026) — https://arxiv.org/abs/2604.27031

AI — turnover, sparsity, negative results:
- Dohare et al. (2024) *Nature* 632 — https://pmc.ncbi.nlm.nih.gov/articles/PMC11338828/ ; code https://github.com/shibhansh/loss-of-plasticity
- Sokar et al. (2023) ReDo, ICML — https://arxiv.org/abs/2302.12902
- Nikishin et al. (2023) Plasticity Injection, NeurIPS — https://proceedings.neurips.cc/paper_files/paper/2023/file/75101364dc3aa7772d27528ea504472b-Paper-Conference.pdf
- Tran et al. (2022) Adult neurogenesis acts as a neural regularizer, *PNAS* 119(45) — https://www.pnas.org/doi/10.1073/pnas.2206704119
- Bricken et al. (2023) Sparse Distributed Memory is a Continual Learner, ICLR — https://arxiv.org/abs/2303.11934
- Zhou, Vani, Larochelle & Courville (2022) Fortuitous Forgetting in Connectionist Networks, ICLR — https://arxiv.org/abs/2202.00155
- Zhao et al. (2024) Overcoming Growth-Induced Forgetting — https://arxiv.org/abs/2408.10566
- Theory on Mixture-of-Experts in Continual Learning (2025) ICLR — https://arxiv.org/abs/2406.16437
