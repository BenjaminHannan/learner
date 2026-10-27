# Gap check #4 — Two kinds of sleep doing different jobs

Research date: 2026-09-20. Method: web search + reading. Every reference below is one I actually opened or saw in
search results; where I could not verify a detail (author list, volume, venue) I say so.

---

## 1. Verdict (78 words)

**Tried at small scale, not mainstream — and the brain claim is weaker than it sounds.**

AI has already built two-phase offline learning several times: DreamCoder has an abstraction sleep and a dream sleep
with ablations showing both matter; Deperrois et al. 2022 built explicit NREM-perturbed and REM-adversarial dreaming;
Singh/Norman/Schapiro 2022 alternate NREM and REM. So "no architecture alternates two functionally different offline
phases" is false. Meanwhile the headline sleep-and-insight studies have a bad replication record.

---

## 2. What the brain does — and how good the evidence is

### 2a. The claim as Fable stated it

Two parts: (i) NREM/slow-wave sleep replays memories and pulls out the general rule ("gist", schema); (ii) REM sleep
is where far-fetched links between unrelated memories get made. The tidy version comes from Lewis, Knoblich & Poe
(2018), their "BiOtA" proposal.

Important: **Lewis et al. 2018 is an opinion/theory paper in Trends in Cognitive Sciences, not an experiment.** It
assembles other people's results into a story. Treating it as evidence is a category error — it is a hypothesis.

### 2b. Evidence quality, piece by piece

| Sub-claim | Evidence | My rating |
|---|---|---|
| NREM replay exists and helps memory stick | Decades of rodent sharp-wave-ripple replay work; targeted memory reactivation (TMR) during slow-wave sleep reliably improves recall across many labs | **Strong** |
| NREM/sleep helps extract gist/rules | Real but mixed; see failures below | **Moderate, contested** |
| REM specifically builds far/remote associations | One influential behavioural study (Cai et al. 2009), plus theory | **Speculative** |
| NREM and REM do *different* things at all | Good recent rodent evidence, but the difference is not the one BiOtA predicts | **Moderate** |

### 2c. The replication problem (this is the part to take seriously)

- **Wagner et al. 2004, "Sleep inspires insight" (Nature)** — the famous Number Reduction Task result. A later
  attempt (Debarnot et al. 2017) only *partly* reproduced the effect on discovering the hidden rule. I saw this
  reported in reviews; I did not read the Debarnot paper itself, so treat that detail as second-hand.
- **Schönauer et al. 2018 (Frontiers in Human Neuroscience)** — tested a nap on classical insight problems and magic
  tricks. Found **no benefit at all**. This is a direct, published null against the general "sleep gives you insight"
  story.
- **Lacaux et al. 2021 (Science Advances)** — claimed N1 (the drowsy edge of sleep) tripled the chance of finding a
  hidden rule. A **preregistered replication attempt presented at CCN 2024 found no N1 effect**, and instead found a
  benefit of **N2** sleep. (I read the CCN PDF; I could not verify the author list from the page I fetched.)
- **Löwe, Petzka, Tzegka & Schuck 2025 (PLOS Biology)** — preregistered, N=90 (68 analysed), 20-minute nap: **N2 sleep**
  promoted "aha" moments (85.7% vs 55.5% awake). Note what this does to the BiOtA story: N2 is *light NREM*, not REM,
  and the nap was too short to reach REM at all. So the best-powered recent insight result points at NREM, not REM.
- **TMR on problem solving is mixed.** Sanders, Osburn, Paller & Beeman 2019 (Psychological Science) cued unsolved
  puzzles with sounds during sleep: 31.7% of cued puzzles solved next morning vs 20.5% uncued. But a 2021 Frontiers in
  Behavioral Neuroscience paper titled "Sleep Facilitates Problem Solving With No Additional Gain Through Targeted
  Memory Reactivation" found sleep helped and **cueing added nothing** (author list not verified by me).
- **Konkoly et al. 2026 (Neuroscience of Consciousness)** — deliberately provoked dreams about unsolved puzzles during
  REM using sound cues, 20 participants / 35 nights. Cued puzzles did get into dreams more, and puzzles that appeared
  in dreams were solved more often — but there was **no overall main effect of cueing on solving**, and the supporting
  result was post-hoc. Small, suggestive, not decisive.
- **REM's role in memory has long been attacked head-on.** Vertes & Siegel's critique (Science, 2001, and follow-ups)
  points out that drugs and brain lesions that suppress REM for long periods do not produce obvious memory deficits.
  This argument has never been cleanly answered.
- **Cai et al. 2009 (PNAS)** — the REM-and-remote-associates study everyone cites. It is a single study from one lab
  in 2009. I found no direct replication in my searches. Given the base rates in this literature, treat it as
  unreplicated.

### 2d. Rodent evidence for distinct NREM vs REM replay

This is the strongest leg, but it does not say what BiOtA wants it to say.

- **Bollmann, Baracskay, Stella & Csicsvari 2025 (Neuron), "Sleep stages antagonistically modulate reactivation
  drift"** — rats, ~20 hours of tracked CA1 assembly reactivation. NREM **accelerated** the drift of replayed patterns
  toward the patterns used in the later recall session; REM **pushed back against** that drift. So the two stages
  genuinely do opposite things — but here REM is the *conservative* one, not the creative one. That is roughly the
  reverse of the popular picture.
- A 2024 bioRxiv preprint (Cardiff/other; author list not verified) reports that REM-sleep reactivation is real and is
  shaped by whether the preceding experience was novel or anxiety-inducing. Preprint, so weight accordingly.
- **Satchell et al. 2025 (PLOS Computational Biology)** — a simulation showing that the low-acetylcholine (NREM) and
  high-acetylcholine (REM) states can play *sequential, complementary* roles in consolidation. Again: a model, not
  data.

### 2e. Honest summary

"Sleep has two stages that do different things to memory" is a **moderate**-quality claim with real rodent support.
"NREM extracts the rule and REM makes wild connections" is **speculative**, is built substantially on studies that
failed to replicate, and the single best recent preregistered insight experiment points at NREM (N2), not REM.

---

## 3. What AI has already done

Prioritising the closest work. Scale noted because most of it is small.

1. **DreamCoder — Ellis et al., PLDI 2021; journal version Phil. Trans. R. Soc. A 2023.**
   [arXiv:2006.08381](https://arxiv.org/abs/2006.08381) ·
   [Royal Society](https://royalsocietypublishing.org/rsta/article/381/2251/20220050/112456/DreamCoder-growing-generalizable-interpretable)
   **This already is the two-stage idea.** Its sleep is explicitly split into *sleep-abstraction* (refactor solved
   programs, compress recurring sub-expressions into new library primitives — i.e. rule extraction) and
   *sleep-dreaming* (train a neural recognition model on replayed solved tasks **and on "fantasies"** — programs
   sampled from the library prior — i.e. made-up experience). **Ablations:** removing either phase hurts; in LOGO
   graphics and tower building neither ablation exceeds ~60% of held-out tasks while the full system reaches near
   100%. Scale: small symbolic domains, dozens–hundreds of tasks.

2. **Deperrois, Petrovici, Senn & Jordan 2022, "Learning cortical representations through perturbed and adversarial
   dreaming" (eLife 11:e76384).** [eLife](https://elifesciences.org/articles/76384) ·
   [arXiv:2109.04261](https://arxiv.org/abs/2109.04261)
   The most directly on-point AI work. A GAN-ish cortical model with three states: wake, **NREM = perturbed dreaming**
   (replay episodic memories with perturbations → makes latent representations robust), **REM = adversarial dreaming**
   (generate brand-new virtual inputs by mixing/recombining → this is what produces good semantic concepts). The paper
   attributes *different* benefits to each phase. Scale: small convolutional networks on standard natural-image
   datasets. Basically the hypothesis Fable thinks is missing, already implemented and published four years ago.

3. **Singh, Norman & Schapiro 2022 (PNAS), "A model of autonomous interactions between hippocampus and neocortex
   driving sleep-dependent memory consolidation."** [PNAS](https://www.pnas.org/doi/10.1073/pnas.2123432119) ·
   [code](https://github.com/schapirolab/SinghNormanSchapiro_PNAS22)
   Complementary-learning-systems model that **autonomously alternates NREM and REM**. NREM: hippocampus drives
   cortex to reinstate strong versions of *recent* memories. REM: hippocampus disconnects, cortex freely explores its
   own attractors, replaying *remote* knowledge. Ablations are the interesting part: NREM-only produces catastrophic
   loss of old knowledge; a blocked schedule (all NREM then all REM) is much worse than alternating. So in this model
   **the alternation itself, not just the presence of both, is load-bearing.** Scale: tiny (15 exemplars, 3
   categories; 10 items per environment).

4. **Wake-Sleep Consolidated Learning (WSCL), IEEE TNNLS 2024.** [arXiv:2401.08623](https://arxiv.org/pdf/2401.08623)
   Continual image classification with a wake phase plus a sleep phase split into **NREM** (replay + synaptic
   consolidation on stored episodes) and **REM** ("dreaming" on previously-unseen inputs to pre-stretch the feature
   space). Reports gains on CIFAR-10/100, Tiny-ImageNet, FG-ImageNet. (Author list not verified by me.)

5. **Wake-Sleep algorithm — Hinton, Dayan, Frey & Neal, Science 1995.** The ancestor of all of this. Two phases, but
   they are wake (recognition) and sleep (generation) — *not* two different sleeps. Included so the lineage is clear.

6. **Tadros, Krishnan & Bazhenov 2022, "Sleep-like unsupervised replay reduces catastrophic forgetting in artificial
   neural networks" (Nature Communications 13:7742).**
   [Nature Comms](https://www.nature.com/articles/s41467-022-34938-7) · [code](https://github.com/tmtadros/SleepReplayConsolidation)
   **Single, undifferentiated** sleep phase: offline local Hebbian plasticity with noisy input, no stored data.
   Recovers tasks that were otherwise forgotten. Useful as the "one phase is already quite good" baseline.

7. **Brain-inspired / generative replay — van de Ven et al. 2020 (Nature Communications).**
   [link](https://www.nature.com/articles/s41467-020-17866-2) — replay of internally generated hidden representations.
   One phase. This is the mainstream of "AI replay" and Fable is right that it is undifferentiated.

8. **Sleep-time compute — Lin, Snell, Wang, Packer, Wooders, Stoica & Gonzalez 2025.**
   [arXiv:2504.13171](https://arxiv.org/abs/2504.13171) — LLM agents think offline about context before queries
   arrive; ~5× reduction in test-time compute for equal accuracy, up to 13–18% accuracy gains on stateful benchmarks.
   Single undifferentiated offline phase, at real scale.

9. **"Language Models Need Sleep" — Behrouz, Hashemi & Mirrokni, 2026 preprint.**
   [arXiv:2606.03979](https://arxiv.org/html/2606.03979v1) — LLM-scale, explicitly two offline phases: an NREM-like
   consolidation/distillation from fast unstable parameters into slow stable ones, and a REM-like "dreaming" phase
   that generates and filters synthetic data for self-improvement. Caveat: a near-identically titled preprint also
   appears at arXiv:2605.26099 and I could not reconcile the two; treat venue/date as unconfirmed.

10. **Overfitted brain hypothesis — Hoel 2021 (Patterns).**
    [Cell/Patterns](https://www.cell.com/patterns/fulltext/S2666-3899(21)00094-5) — dreams as biological noise
    injection / data augmentation against overfitting. Theory only, no implementation, and it explains *one* phase.

Also relevant but not searched in depth this round: **Dreamer**-family world models learn policies from imagined
rollouts — again, a single undifferentiated imagination phase. (I did not re-verify a citation for this in this
session.)

**Negative results, honestly:** on the brain side there are clear nulls (Schönauer 2018; the 2021 TMR null; the CCN
2024 non-replication). On the AI side I found **no** published paper that tried splitting offline learning into two
phases and reported it *not* helping. That absence is itself a warning sign — it is what publication bias looks like.

---

## 4. The real gap

Fable's claim as written is **wrong**: several architectures do alternate two functionally different offline phases,
and DreamCoder's abstraction-sleep / dream-sleep pair is almost exactly the proposed idea, published in 2021 with
ablations.

What genuinely has *not* been done, as far as I can find:

1. **Matched-compute evidence that the split is what helps.** Every ablation above *deletes* a phase. Nobody asks the
   fair question: given a fixed offline budget (same gradient steps, same number of generated samples), does splitting
   it into two differently-objectived phases beat spending it all on one mixed phase? Without that control, "two
   phases help" may just mean "more, or more varied, offline data helps".
2. **Nothing applies the split to a controller / program-induction setting.** All the two-phase work is
   representation learning (images, categories) or symbolic library growth. None of it targets the failure our
   dispatcher has: a controller that has learned "make exactly 3 calls" because 3 was the longest chain it practised.
3. **No REM-analogue built on cross-episode splicing with an external verifier.** DreamCoder's fantasies are samples
   from a learned library prior. Deperrois's REM mixes latent codes. Nobody generates offline experience by
   *joining a trace from one episode to a trace from a completely different episode and then checking the join against
   ground truth*. That specific move — "far association, then verify" — is the useful, testable core of the BiOtA
   story, and it is the one piece with no AI implementation I could find.
4. **No test of whether the split needs to be interleaved in a practical learner.** Singh et al. 2022 show alternating
   beats blocked — in a tiny biologically-motivated model, not in anything you would ship.

So: the gap is narrow and specific. It is **not** "two-phase sleep is unexplored". It is "nobody has checked, at
matched compute, whether a verified far-splice phase plus a compression phase beats one mixed offline phase, in a
system whose failure mode is chain-length generalisation".

---

## 5. Design proposals — how you would actually build this

First, an honest framing note. Our toy has no emotion, no schemas, no episodic richness. The only part of the
NREM/REM distinction that maps onto it is **how far apart the things you recombine are**: recombine within one story
(near) vs across two unrelated stories (far). Everything else in the sleep literature is decoration for us. I have
written the three options around that.

Reminder of the target bug: with the bookkeeping hints removed, the dispatcher gets 64/64 up to 3 hops and 4/64
beyond — it has learned "call three times, then stop", because 3 was its longest practised chain.

---

### Option 1 — "Splice far, compress near": two alternating dream phases *(recommended — build this first)*

**(a) Plain words.** Right now the plan is one dream phase: cut up the model's own solved traces, stick pieces
together, check them, and squeeze what works into shortcuts. Option 1 says do that in two different moods that take
turns. In the **far mood**, you deliberately glue together bits from *two different stories* that share nothing —
the end of one chain happens to be a person who appears in the other story, so you staple them and get a chain longer
than anything the model ever practised. You check it against the actual rows of the story; if it checks out, it
becomes a new training example. In the **near mood**, you look at the chains you kept, find the step-patterns that
keep repeating, and pack them into one-button shortcuts (macros) the dispatcher can press. The far mood makes the
model's homework harder; the near mood makes the model's hands faster. They need different data and different
objectives, so making them separate phases is not just cosmetic.

**(b) Concrete design.**
- **Where it sits:** a new offline stage between dispatcher training rounds. Lookup operator **frozen** throughout
  (that is what makes verification trustworthy).
- **Buffer:** dispatcher rollouts stored as traces `[(row selected, operator output, entity state)]` plus the source
  story.
- **Phase R (far, runs first):** sample two traces from *disjoint* stories/entity sets. Find a type-compatible
  junction — the output of trace A is a person ID that is a valid input to trace B. Splice → a candidate chain of
  length `k_A + k_B`. **Verify** by re-running the frozen operator against the ground-truth rows of the merged story;
  discard anything that does not check. Keep verified chains, especially those longer than 3 hops. Output: new
  supervised/RL training chains at depths never practised.
- **Phase N (near, runs second):** over the verified chain set, mine frequent contiguous sub-sequences (simple
  n-gram count over action types is enough at this scale). Promote the top-k into **macro actions**: an embedding
  row + a fixed composition of operator calls. Then distil the dispatcher's policy so it prefers the shorter macro
  action sequence over the long one (a description-length objective).
- **Learned vs fixed:** learned = dispatcher policy (existing 15–24k params) + macro embedding table
  (~8 macros × ~64 dims ≈ **0.5–2k new params**). Fixed = lookup operator (~79k), the splicing rules, the verifier.
- **Alternation:** R, N, R, N … with a fixed step budget per phase.
- **Rough new params: ~1–2k.** Essentially free.

**(c) At LLM scale.** Two alternating offline passes over an agent's own solved traces: one pass splices traces from
*different past sessions* into longer composite tasks and keeps only those a verifier confirms (a self-generated
curriculum of harder problems); a second pass mines recurring sub-procedures out of the kept traces and names them as
reusable tools/skills, then distils the policy onto the shorter tool-using solution.

**(d) Falsifiable toy test.**
- **Task:** existing world, dispatcher trained on 1–3 hop chains, **hints removed**. Eval on held-out 4-, 5- and
  6-hop questions.
- **Arms (all with identical total offline gradient steps *and* identical number of verified generated samples):**
  1. No dream phase (baseline; expect ≈4/64 beyond 3 hops).
  2. **One mixed dream phase** — splicing and compression interleaved in a single buffer with one combined objective.
     *This is the already-proposed dream phase and is the control that matters.*
  3. **Two alternating phases** (R then N then R …).
  4. **R-only** (far splice, no macros).
  5. **N-only** (compression on unspliced traces).
- **Pass mark (pre-register):** arm 3 must reach **≥60% on 4–6 hop questions in ≥2 of 3 seeds**, *and* beat arm 2 by
  **≥15 percentage points** averaged over seeds. The headline claim is only "splitting helps" if arm 3 > arm 2 at
  matched compute.
- **What would show it does not help:** arm 3 ≈ arm 2 (the split is decoration — spend the compute on one phase); or
  arm 4 ≈ arm 3 (the far-splice phase is doing all the work and the compression phase is decoration). Either outcome
  is a clean, publishable-to-Ben negative.
- **Main artefact risk:** the R phase *manufactures* 4–6 hop training chains, so results on 4–6 hops are no longer
  zero-shot depth generalisation. The honest claim is "the system bootstraps its own longer-chain training data
  without new labels", **not** "it generalises to unseen depths". Report it that way or the result is fake. Second
  risk: verification leakage — verify against ground-truth story rows, never against the operator's own confidence.
  Third risk: any length-diverse data might fix the stopping bug, which is exactly what arm 4 tests.
- **Runtime:** dispatcher is tiny; all five arms × 3 seeds should fit well inside the 30-minute rule on the Mac.

**(e) Build cost: small-to-medium.** The splicer + verifier is the real work (maybe 150 lines); macros are an embedding
table and an action-space extension.

---

### Option 2 — "Fast path + explorer": NREM distils, REM explores beyond it

**(a) Plain words.** This is the textbook complementary-learning-systems idea. In the **NREM phase**, everything the
model can already do reliably (say, 1–3 hop questions) gets compressed into a small, fast, one-shot network — a
"reflex" that answers those in a single step without the dispatcher looping. In the **REM phase**, the dispatcher
goes exploring, but now it can call the reflex as a single move. Because three hops now costs one move, a six-hop
question only needs two moves — which the dispatcher *has* practised. Depth stops being the thing it counts.

**(b) Concrete design.**
- **NREM (consolidation):** train a small student network (~20–40k params) to map (story rows, question at depth ≤3)
  → answer, using verified dispatcher traces as targets. Frozen operator supplies the targets; no new labels.
- **REM (exploration):** add the student as a new action in the dispatcher's action set ("resolve up to 3 hops in one
  call"). Continue RLOO training on chains that are longer than 3, where the only way to succeed in few moves is to
  use the student. Student **frozen** during REM; dispatcher learns when to call it.
- **Learned:** student (~20–40k) + dispatcher policy + one extra action embedding. **Fixed:** lookup operator.
- **Why it is two phases and not one:** the student must be stable while the dispatcher learns to trust it; training
  both at once is a moving-target problem. The alternation is doing real work, which is exactly Singh et al.'s point.

**(c) At LLM scale.** Distil verified multi-step agent traces into a single-shot model (standard reasoning
distillation), then let the planner treat that model as a one-call subroutine and search over *longer* plans — offline
distillation and online exploration alternating rather than running together.

**(d) Falsifiable toy test.** Same eval (4–6 hops, hints removed). Arms: (1) baseline; (2) dispatcher given extra
RLOO steps equal to the student's training cost, no student (**matched compute**); (3) NREM+REM as above; (4) student
trained but dispatcher *not* retrained (tests whether the exploration phase matters). Pass mark: arm 3 ≥60% on 4–6
hops in ≥2/3 seeds and ≥15 points over arm 2. Failure signal: arm 3 ≈ arm 2, or the dispatcher never calls the
student. **Artefact risk:** the student may simply memorise the 16-entity world, so hold out entity *combinations*
(the same held-out-cell protocol already used) and check the student on those; also the "one call = 3 hops" trick
could be a re-parameterisation of counting rather than genuine depth-invariance — test at 7–10 hops, where even the
trick runs out, to see whether anything real was learned.

**(e) Build cost: medium.** A second network, a new action type, two training loops.

---

### Option 3 — "Adversarial dreamer": a generator that invents hard questions *(build last, if at all)*

**(a) Plain words.** Copy Deperrois's REM directly: train a small generator whose job is to invent stories and
questions the dispatcher gets *wrong* but that are still solvable (checked by the frozen operator). NREM = replay real
traces so the model stays honest; REM = train against the generator's nastiest solvable inventions.

**(b) Concrete design.** Generator: ~10–20k params, outputs (entity graph, relation rows, question). Reward = the
dispatcher fails AND the frozen operator can verify a correct answer exists. Dispatcher trains on the mix. Generator
learned; operator fixed; alternate generator and dispatcher updates.

**(c) At LLM scale.** A task-proposer model trained adversarially against a solver, fenced by a verifier — close to
existing self-play curriculum work, so the least novel of the three.

**(d) Falsifiable toy test.** Same eval. Control that kills it: **random hard-question sampling** at matched compute —
because our world is procedurally generated, we can sample arbitrarily deep questions for free. Pass mark: adversarial
generation beats random hard sampling by ≥10 points. **What would show it does not help:** random sampling matches it,
which I think is the likely outcome. **Artefact risk:** generator collapse onto one degenerate question type;
reward hacking by producing unsolvable-but-unverifiable items.

**(e) Build cost: large.** Adversarial training is fiddly and seed-sensitive — bad fit for the 30-minute rule.

---

### Ranking

1. **Option 1** — build first. Cheapest (~1–2k new params), directly attacks the known "3 calls then stop" bug, and
   the far-splice-then-verify move is the one genuinely unimplemented piece in the literature. Crucially, its
   experiment is designed so a *negative* result (split = decoration) is just as informative as a positive one.
2. **Option 2** — build second if Option 1's far-splice works, since it is the natural way to turn verified long
   chains into something durable. More params, more machinery, higher memorisation risk.
3. **Option 3** — probably skip. In a toy with a known procedural generator, an adversarial question inventor is
   competing against free random sampling, and I expect it to lose.

**Direct answer to the brief's question — is splitting the dream phase decoration?** Mostly, *unless* the two phases
genuinely need different data-generation rules. In Option 1 they do (cross-story splicing vs within-set subsequence
mining), so the split is at least meaningful. But I would not claim it helps until arm 3 beats arm 2 at matched
compute. Treat the split as the *hypothesis under test*, never as an assumption baked into the design.

---

## 6. Priority score: **3 / 5**

The two-phase sleep framing is not new and is not the value here; the value is the far-splice-and-verify generator of
longer-than-practised chains, which targets our one known bug — but the "two phases" part may well turn out to be
decoration, so run it as a controlled comparison, not a headline feature.

---

## 7. References

**Sleep science**
- Lewis, Knoblich & Poe (2018). How memory replay in sleep boosts creative problem-solving. *Trends in Cognitive
  Sciences* 22(6):491–503. [PubMed](https://pubmed.ncbi.nlm.nih.gov/29776467/) ·
  [PDF](https://somby.ceu.edu/sites/somby.ceu.edu/files/attachment/basicpage/6/knoblich2018howmemoryreplayinsleepboostscreativeproblem-solving.pdf) — *opinion paper, not evidence.*
- Wagner, Gais, Haider, Verleger & Born (2004). Sleep inspires insight. *Nature* 427:352–355.
  [Semantic Scholar](https://www.semanticscholar.org/paper/Sleep-inspires-insight-Wagner-Gais/aeb0a8348758eb07ba02d1bf9ffb7421624f73e2) — replication record poor.
- Schönauer, Brodt, Pöhlchen, Breßmer, Danek & Gais (2018). Sleep does not promote solving classical insight problems
  and magic tricks. *Frontiers in Human Neuroscience* 12:72.
  [Frontiers](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2018.00072/full) — **null result.**
- Cai, Mednick, Harrison, Kanady & Mednick (2009). REM, not incubation, improves creativity by priming associative
  networks. *PNAS* 106(25):10130–10134. [PNAS](https://www.pnas.org/doi/10.1073/pnas.0900271106) — single study,
  no replication found.
- Lacaux et al. (2021). Sleep onset is a creative sweet spot. *Science Advances* 7:eabj5866.
  [Science Advances](https://www.science.org/doi/10.1126/sciadv.abj5866)
- "Sleep Inspires Insight: a Preregistered Study", CCN 2024.
  [PDF](https://2024.ccneuro.org/pdf/29_Paper_authored_CCN_2024.pdf) — **failed to replicate the N1 effect**; found N2
  instead. Author list not verified by me.
- Löwe, Petzka, Tzegka & Schuck (2025). N2 sleep promotes the occurrence of 'aha' moments in a perceptual insight
  task. *PLOS Biology*. [PLOS](https://journals.plos.org/plosbiology/article?id=10.1371%2Fjournal.pbio.3003185) —
  preregistered, N=90; points at NREM, not REM.
- Sanders, Osburn, Paller & Beeman (2019). Targeted memory reactivation during sleep improves next-day problem
  solving. *Psychological Science*. [SAGE](https://journals.sagepub.com/doi/abs/10.1177/0956797619873344)
- "Sleep facilitates problem solving with no additional gain through targeted memory reactivation" (2021).
  *Frontiers in Behavioral Neuroscience* 15:645110.
  [Frontiers](https://www.frontiersin.org/journals/behavioral-neuroscience/articles/10.3389/fnbeh.2021.645110/full) —
  **TMR null.** Authors not verified by me.
- Konkoly et al. (2026). Creative problem-solving after experimentally provoking dreams of unsolved puzzles during REM
  sleep. *Neuroscience of Consciousness* 2026(1):niaf067.
  [Oxford](https://academic.oup.com/nc/article/2026/1/niaf067/8456489) — N=20, no overall main effect.
- Bollmann, Baracskay, Stella & Csicsvari (2025). Sleep stages antagonistically modulate reactivation drift. *Neuron*.
  [Cell](https://www.cell.com/neuron/fulltext/S0896-6273(25)00167-9) ·
  [PubMed](https://pubmed.ncbi.nlm.nih.gov/40132588/) — best evidence that NREM and REM do different things; the
  direction is not the one BiOtA predicts.
- Satchell, Butel-Fry, Noureddine, Simmons, Ognjanovski, Aton & Zochowski (2025). Cholinergic modulation of neural
  networks supports sequential and complementary roles for NREM and REM states in memory consolidation. *PLOS
  Computational Biology*. [PLOS](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1013097)
- Vertes & Siegel (2001/2005), the REM-sleep-memory-consolidation critique. *Science* 294 and follow-ups.
  [Science](https://www.science.org/doi/10.1126/science.1063049) — REM suppression without memory loss.

**AI**
- Ellis et al. (2021). DreamCoder. *PLDI 2021*; journal version *Phil. Trans. R. Soc. A* 2023.
  [arXiv](https://arxiv.org/abs/2006.08381) ·
  [Royal Society](https://royalsocietypublishing.org/rsta/article/381/2251/20220050/112456/DreamCoder-growing-generalizable-interpretable) —
  abstraction sleep + dream sleep, both needed by ablation.
- Deperrois, Petrovici, Senn & Jordan (2022). Learning cortical representations through perturbed and adversarial
  dreaming. *eLife* 11:e76384. [eLife](https://elifesciences.org/articles/76384) ·
  [arXiv](https://arxiv.org/abs/2109.04261) — NREM perturbed + REM adversarial dreaming.
- Singh, Norman & Schapiro (2022). A model of autonomous interactions between hippocampus and neocortex driving
  sleep-dependent memory consolidation. *PNAS*. [PNAS](https://www.pnas.org/doi/10.1073/pnas.2123432119) ·
  [code](https://github.com/schapirolab/SinghNormanSchapiro_PNAS22) — alternation beats blocked scheduling.
- Wake-Sleep Consolidated Learning (2024). *IEEE TNNLS*. [arXiv:2401.08623](https://arxiv.org/pdf/2401.08623)
- Hinton, Dayan, Frey & Neal (1995). The wake-sleep algorithm for unsupervised neural networks. *Science* 268:1158–1161.
- Tadros, Krishnan & Bazhenov (2022). Sleep-like unsupervised replay reduces catastrophic forgetting in artificial
  neural networks. *Nature Communications* 13:7742.
  [Nature](https://www.nature.com/articles/s41467-022-34938-7) · [code](https://github.com/tmtadros/SleepReplayConsolidation)
- van de Ven, Siegelmann & Tolias (2020). Brain-inspired replay for continual learning with artificial neural
  networks. *Nature Communications*. [Nature](https://www.nature.com/articles/s41467-020-17866-2)
- Lin, Snell, Wang, Packer, Wooders, Stoica & Gonzalez (2025). Sleep-time compute: beyond inference scaling at
  test-time. [arXiv:2504.13171](https://arxiv.org/abs/2504.13171)
- Behrouz, Hashemi & Mirrokni (2026). Language models need sleep. [arXiv:2606.03979](https://arxiv.org/html/2606.03979v1) —
  preprint; a similarly titled preprint at arXiv:2605.26099 could not be reconciled with it.
- Hoel (2021). The overfitted brain hypothesis. *Patterns*.
  [Cell](https://www.cell.com/patterns/fulltext/S2666-3899(21)00094-5) — theory, one phase.
