# Gap #1 — Spontaneous, unprompted thought

Checked 2026-09-20. Research only (web search + reading). Everything below is paraphrased from sources I actually opened; where I could not verify a
detail I say so.

---

## 1. Verdict (≤80 words)

**Tried at small scale, not mainstream.**

The "AI only computes when prompted" half of the claim is basically right at the *architecture* level — no mainstream model has a forward pass that
starts by itself. But "nothing is steered by its own open problems" is wrong: since 2025 there is a whole crop of systems (Absolute Zero, R-Zero,
Self-Questioning LMs, MAGELLAN, sleep-time compute) that generate their own problems while idle. They are outer loops, not architecture, and they
reliably collapse onto one narrow problem type. Also: the brain half is weaker than the claim says.

---

## 2. What the brain does — and how good the evidence is

Split the claim into three parts, because they have very different evidence quality.

**(a) "The brain computes with no input." — STRONG.**
This one is solid and not really contested. Raichle's "dark energy" work is the standard citation: most of the brain's energy budget goes to ongoing
internal signalling, and the extra energy caused by whatever is happening in the outside world at that moment is a tiny slice (he puts task-evoked
change at roughly 0.5–1% of total). Whatever else is true, a brain is not idle between inputs. This is a measurement, not a theory.

**(b) "That ongoing activity is 'thought' and lives in the default mode network." — MODERATE, correlational.**
Christoff et al. (2016, *Nature Reviews Neuroscience*) is the framework everyone cites: mind-wandering is thought that drifts because deliberate and
automatic constraints are weak, and DMN plus executive regions are both active during it. It is a framework paper, not an experiment. And there is a
direct caution: Kucyi et al. (PNAS 2016) found spontaneous DMN activity tracked behavioural variability *independently* of whether people reported
mind-wandering — i.e. DMN activity is not a clean readout of "person is daydreaming". Treat DMN = spontaneous thought as a useful correlation, not a
mechanism.

**(c) "Spontaneous thought drifts toward your unresolved problems." — WEAK-TO-MODERATE. This is the part the claim leans on, and it is the shakiest.**

- **Klinger's current-concerns theory** (committing to a goal starts a latent process that makes you notice, recall and dream about cues tied to that
  goal) is long-standing and thought-sampling based. It is a theory supported by correlational experience-sampling, not by intervention. I did not find
  a modern large preregistered test of it.
- **Zeigarnik effect** (unfinished tasks stay in mind) — the memory version is essentially dead. A 2025 meta-analysis in *Humanities and Social Sciences
  Communications* reports that across 37 studies excluding Zeigarnik's own, the ratio of interrupted-to-completed items recalled is 0.99 — no effect.
  What does survive is the *resumption* tendency (~67% resume vs a 50% baseline). So "open goals nag you into going back" has some support; "open goals
  are better remembered" does not.
- **Baird et al. 2012** (undemanding task during incubation boosts creative problem solving, and that context produced more mind-wandering) is the
  headline incubation study — *and it did not replicate*. A 2025 preregistered study (Scientific Reports, s41598-025-09736-y) compared 0-back, 2-back,
  mindfulness and no-break incubation on a story-writing task and found **no significant difference in creative improvement between incubation
  conditions**. It did find a *within-subject correlation*: more mind-wandering during the break predicted more improvement — but only for people who
  got the **same** prompt back afterwards, not a new one. That last detail is the one piece of real evidence for "drift is steered by the problem you
  are still holding", and it is correlational.

**Honest summary of the brain side:** ongoing self-generated activity = strong. Content steered by unresolved problems = plausible, mostly
correlational, with the most famous demonstration failing to replicate. Do not build a research programme on the assumption that this is a settled
brain fact.

---

## 3. What AI has already done (closest work, 2023–2026 first)

Sorted roughly by how close it gets to "unprompted computation steered by the system's own open problems".

| # | Work | What it showed | How close |
|---|---|---|---|
| 1 | **Absolute Zero / AZR** — Zhao et al., 2025, [arXiv:2505.03335](https://arxiv.org/abs/2505.03335) (NeurIPS 2025) | One model both *proposes* code-reasoning tasks and solves them; a code executor is the verifier. Reaches SOTA on math+code with literally zero human-written training problems. | Very close on "picks its own problems", but it is an RL training loop, not an architecture, and needs an external executor as ground truth. |
| 2 | **R-Zero** — Huang et al., 2025, [arXiv:2508.05004](https://arxiv.org/abs/2508.05004) (ICLR 2026) | Splits the base model into Challenger and Solver; Challenger is rewarded for posing problems right at the edge of what the Solver can do (keeps questions where 3–7 of 10 samples agree). +6.49 math / +7.54 general on Qwen3-4B-Base. | "Edge of my own ability" is a direct machine version of "my unresolved problems". |
| 3 | **Self-Questioning Language Models** — 2025, [arXiv:2508.03682](https://arxiv.org/abs/2508.03682) | Model writes its own questions from a topic prompt and trains on them; no curated dataset. Improves downstream benchmarks. | Same family. Still needs a human-given topic seed. |
| 4 | **Sleep-time compute** — Lin, Snell, Packer, Wooders, Stoica, Gonzalez, 2025, [arXiv:2504.13171](https://arxiv.org/abs/2504.13171) | Model thinks about a context *before* any query arrives; ~5× less test-time compute for equal accuracy, up to +13% (Stateful GSM-Symbolic) / +18% (Stateful AIME). | This is the "thinks while idle" half — but explicitly steered by **anticipated user queries**, not by its own open problems. |
| 5 | **MAGELLAN** — Gaven, Carta, Romac, Colas, Lamprier, Sigaud, Oudeyer, ICML 2025, [arXiv:2502.07709](https://arxiv.org/abs/2502.07709) | Autotelic LLM agent predicts its own *learning progress* across a large semantic goal space and picks goals accordingly; only method that fully mastered the evolving goal space. | The cleanest "choose what to work on from a model of my own competence". |
| 6 | **OMNI / OMNI-EPIC** — Zhang et al. 2023 [arXiv:2306.01711](https://arxiv.org/abs/2306.01711); Faldor, Zhang, Cully, Clune 2024 [arXiv:2405.15568](https://arxiv.org/abs/2405.15568) (ICLR 2025) | A foundation model judges which next task is *interesting and learnable*, and OMNI-EPIC writes the next environment as code. | Open-ended self-generated agenda, but interestingness is borrowed from human priors baked into the FM. |
| 7 | **Prioritized Experience Replay** — Schaul, Quan, Antonoglou, Silver, ICLR 2016, [arXiv:1511.05952](https://arxiv.org/abs/1511.05952) | Replay the transitions where your prediction was most wrong (TD error). Beat uniform replay on 41/49 Atari games. | The oldest and most *mainstream* version of "internal processing steered by unresolved error" — but offline, and it re-uses old data rather than generating anything. |
| 8 | **Earlier open-ended line** — POET (Wang, Lehman, Clune, Stanley 2019, [arXiv:1901.01753](https://arxiv.org/abs/1901.01753)); Voyager (Wang et al. 2023, [arXiv:2305.16291](https://arxiv.org/abs/2305.16291)); DreamerV3 (Hafner et al. 2023, [arXiv:2301.04104](https://arxiv.org/abs/2301.04104)) | POET: system breeds its own environments + solvers. Voyager: LLM agent runs its own curriculum and grows a skill library in Minecraft, no human in the loop. DreamerV3: trains in imagined rollouts of a learned world model; first to get Minecraft diamonds from scratch. | Self-set agendas and "thinking in a dream" both exist, but all three still sit inside an environment that feeds them observations. |
| 9 | **Gwern, "LLM Daydreaming", July 2025**, [gwern.net/ai-daydreaming](https://gwern.net/ai-daydreaming) | Essay, not a result. Proposes a day-dreaming loop: sample two random concepts from memory, have a generator hunt for a non-obvious link, have a critic score it, feed survivors back into memory. Estimates a ~20× "daydreaming tax". States plainly that no LLM system does this. | This is *exactly* the claim being checked, written up by someone else 14 months ago. An open-source daemon implementing it exists ([caraulani/llm-daydreaming](https://github.com/caraulani/llm-daydreaming)); I did not find published results from it. |
| 10 | **"What Do LLM Agents Do When Left Alone?"** — Szeider, 2025, [arXiv:2509.21224](https://arxiv.org/abs/2509.21224) | 18 runs, 6 frontier models in a continuous reason-and-act loop with persistent memory and self-feedback and *no* task. Three stable behaviour patterns emerged (multi-cycle projects; probing their own reasoning; theorising about their own nature), and they were strongly model-specific. | Empirical "what happens with no prompt", but the loop is scaffolding around a frozen model, not a mechanism inside it. |

**Negative results — important, and they all point the same way:**

- **Curriculum / diversity collapse.** Mishra, "Preventing Curriculum Collapse in Self-Evolving Reasoning Systems", March 2026,
  [arXiv:2603.13309](https://arxiv.org/html/2603.13309). Measured R-Zero's self-generated question pool with semantic clustering: active clusters fell
  89 → 65, Gini rose to 0.90, and one cluster swallowed 951 questions (~50× the mean) — almost all near-identical polynomial-divisibility problems.
  Surface wording stays varied while the actual content narrows ("diversity illusion"). Their fix (Prism: cluster-diversity reward + solver-initialised
  questioner + edge-of-solvability gating) wins on 6 of 7 benchmarks by ~3–4 points for +1.7% compute. **Takeaway: self-generated agendas need an
  external anchor or they eat themselves.**
- **Self-improvement can self-regress** — [arXiv:2606.21090](https://arxiv.org/pdf/2606.21090) (2026) documents a rise-then-collapse failure mode in
  self-improvement loops. I only read the search summary of this one, so treat the details as unverified.
- The structural reason is simple and worth remembering: once every self-proposed problem is solved 0% or 100% of the time, the proposer gets no
  gradient and the loop dies. The "Goldilocks zone" is the whole game.

---

## 4. The real gap

Three things are genuinely missing. Only the third is a big deal.

1. **It is always an outer loop, never the model.** In every system above, a *script* decides when the model runs, hands it a "propose a problem"
   prompt, catches the output, and calls a verifier. Nothing in the weights says "start". Sleep-time compute is the clearest case: the model does think
   while nobody is asking, but a scheduler triggers it and the target is *the user's likely next question*. There is no architecture where a forward
   pass is initiated by the system's own internal state. Gwern's July 2025 essay says the same thing and, as far as I found, is still true.
2. **Steering by "my own open problems" vs "my own learning progress" is not the same thing.** R-Zero and MAGELLAN steer toward *learnable* problems —
   things right at the edge of solvable. A person ruminating on an unsolved problem is often steering toward something they have repeatedly *failed* at,
   which is the opposite of edge-of-solvable. Nobody I found selects self-generated thought by "this is the thing I keep getting stuck on", with stuck
   defined by the system's own trace history (early stops, contradictions, repeated dead ends) rather than by a reward curve.
3. **Everything needs an oracle.** AZR needs a code executor, R-Zero needs majority vote, OMNI-EPIC needs a foundation model's taste, PER needs a reward
   signal. The brain's version supposedly runs without an external checker. Every attempt that removed the external anchor collapsed onto one narrow
   problem type (the Prism result). **This is the honest research question, and it is the one the original claim skips:** it is not "can a model think
   unprompted" — that's easy, just loop it — it is **"what keeps unprompted thought from degenerating, without an external verifier?"** That question is
   genuinely open.

---

## 5. Design proposals — how to actually build this

Three distinct options, ranked. All are small enough for a Mac + one consumer GPU and a <30-minute wave. None of them overlaps the already-proposed
dream phase (trace splicing → macro compression) or the stall-triggered gain head.

**Read this first — the honesty caveat that applies to all three.** Our toy's question space is tiny: 16 entities × hop counts 1–6 × relations
{8,9,10} ≈ **288 possible questions**. "Open-ended self-generated problems" is close to degenerate in a space you can enumerate in a millisecond. So the
real control for every option below is not "no self-generation" — it is **exhaustive or uniform-random enumeration of the same space at matched
compute**. If uniform beats or ties the clever proposer, the mechanism has shown nothing, and that is the single most likely outcome. Any of these
options tells us something about *our dispatcher*; none of them will tell us much about the general claim until the space is big enough that you cannot
just enumerate it. Say that out loud in any write-up.

---

### Option A — Learning-progress proposer ("what should I practise next?")   ← **build this first**

**(a) Plain words.** Right now a human hands the dispatcher its practice problems, all 1–3 hops long, and it learns the lazy rule "make three calls,
then stop". Option A gives the system a little coach that picks its own practice problems. The coach keeps a scorecard of how well the dispatcher is
doing on each *kind* of question (1-hop with relation 8, 4-hop with relation 9, …) and hands out more of whatever the dispatcher is *currently getting
better at fastest*. Nobody tells it that 4-hop questions exist as a target; it has to find that they are worth practising. If it works, the "3 calls
then stop" bug fixes itself, because once 3-hop is mastered the score stops improving there and the coach moves on.

**(b) Concrete design.**
- **Module:** `ProblemProposer`. A learning-progress bandit over question classes. Class = (hop count k ∈ 1..6) × (target relation r ∈ {8,9,10}) = 18
  arms. State per arm: running success rate over a sliding window, plus the slope of that rate (learning progress, absolute value). Sampling:
  softmax over |slope| with a small uniform floor (ε ≈ 0.1) so a class is never permanently starved.
- **When it runs:** between training batches, on the generation side. No user question involved — the system decides what to think about.
- **Inputs:** the dispatcher's own recent per-class success history. **Outputs:** a batch of concrete questions (start entity, k, r) plus the ground-truth
  answer, which the *world generator already knows* — this is the toy's free verifier.
- **Learned vs fixed:** the bandit statistics are learned online; the arm structure and the question grammar are fixed (human-supplied — see artefact
  risk). Operator and dispatcher train exactly as now.
- **Params:** ~54 floats (18 arms × {rate, slope, count}). Effectively zero. Optional learned variant: 18×32 embedding + 2-layer MLP ≈ 3–5k params — do
  the bandit first, only add the net if the bandit works.
- **Wiring:** sits *upstream* of the existing RLOO loop. The dispatcher and the ~79k-param lookup operator are untouched. One new line in the training
  loop: `batch = proposer.sample()` instead of `batch = fixed_curriculum.sample()`.

**(c) At LLM scale.** This is R-Zero/Prism: a learning-progress or cluster-diversity signal over topic clusters decides which self-generated problems
enter the next RL batch. Already done; the scale-up is not novel, which is a point in favour of it working and against it being interesting.

**(d) Toy test.**
- **Task:** hints removed (the broken regime). Train with the proposer for a fixed wall-clock budget. Evaluate on a held-out set of 4–6 hop questions,
  64 cells, entity combinations never seen in training.
- **Controls:** (i) **matched-compute uniform** — same total gradient steps, same number of generated questions, sampled uniformly over all 18 classes;
  (ii) **matched-compute fixed curriculum** — the current 1–3 hop regime, same step count; (iii) **exhaustive** — every one of the 288 questions, same
  step count. Control (i) is the one that matters.
- **Pass mark (pre-register):** held-out 4–6 hop ≥ **32/64** in ≥2 of 3 seeds, **and** ≥ 16 cells better than matched-compute uniform. Baseline today is
  4/64.
- **What would show it does not help:** uniform matches within 8 cells. That means the toy space is simply too small for "what to think about" to be a
  real decision, and the mechanism is untestable here.
- **Main artefact risk:** *we* wrote the grammar that allows k up to 6. The proposer is not discovering that longer chains exist, it is enumerating a box
  we built. Mitigation: report separately what fraction of the gain comes from "longer chains were reachable at all" (uniform control captures this) vs
  "they were ordered well" (proposer minus uniform). Second risk, straight from Prism: the slope signal is noisy, one arm wins by luck and the
  curriculum collapses. Log per-arm sample counts and a Gini coefficient every run; a Gini > 0.85 is a failure, not a success.
- **Build cost: SMALL–MEDIUM.** Half a day. One new file, ~120 lines, no change to the operator or dispatcher.

---

### Option B — Unresolved-problem memory ("keep chewing on what I got stuck on")

**(a) Plain words.** Give the system a to-do list of questions it did badly on, and let it re-attempt them while nothing else is happening. "Did badly"
is not measured against the answer key — it is measured by the system disagreeing with *itself*: ask the same question by two different routes (different
LINK traversal order, or re-deriving the intermediate entity) and see whether the two answers match. Items where it contradicts itself go to the top of
the list. This is the closest thing to "the unfinished problem nags at you", and unlike Option A it needs no answer key, which is the property we
actually care about.

**(b) Concrete design.**
- **Module:** `OpenProblemBuffer` + `SelfConsistencyScorer`.
- **When it runs:** idle steps interleaved with normal training (say 1 idle step per 4 normal steps).
- **Inputs:** completed dispatcher episodes (question, call sequence, final answer). **Outputs:** a priority-ordered replay batch, plus a
  pseudo-label = the majority answer across ≥3 independent routes, used as the training target.
- **Priority:** `p = 1 − (agreement fraction across routes)`, plus a small recency/staleness term. Sampled with the usual PER-style
  `P(i) ∝ p_i^α`, α ≈ 0.6, with importance weights so the gradient stays unbiased.
- **Learned vs fixed:** priority rule is **fixed** (hand-written, no params) in v1. Optional v2: a 1-layer surprise head on the dispatcher hidden state
  predicting disagreement, ~2k params — only if v1 shows the buffer helps.
- **Params:** ~0 for v1.
- **Wiring:** reads dispatcher episode traces; writes a replay batch back into the same RLOO update. The lookup operator is frozen during idle steps and
  acts as the route-executor for the consistency check.
- **Distinct from the already-proposed dream phase:** the dream phase splices traces to *compress* known-good behaviour into macros. This one selects and
  *re-attempts* behaviour that failed, and its verifier is self-agreement, not the frozen operator's approval of a spliced trace.

**(c) At LLM scale.** Idle-GPU rehearsal of past conversations/tasks ranked by self-consistency entropy across resampled reasoning paths, distilled back
with a LoRA. Close to sleep-time compute but pointed at the model's own weak spots instead of the user's likely next question.

**(d) Toy test.**
- **Task:** same broken regime. Measure steps-to-criterion (criterion = 90% on 1–3 hops held-out) and held-out 4–6 hop accuracy.
- **Controls:** (i) **uniform replay, matched replay count** (this is the real control — PER vs uniform); (ii) no replay, matched gradient steps;
  (iii) **oracle-priority replay** using true correctness, as a ceiling — if self-consistency priority ≈ oracle priority, the self-verifier works.
- **Pass mark:** ≥30% fewer steps to criterion than uniform replay in ≥2 of 3 seeds, **and** self-consistency priority within 20% of the oracle ceiling.
- **What would show it does not help:** uniform replay ties, or self-consistency correlates with true correctness at r < 0.3 — meaning the model's
  disagreement-with-itself is noise, and the whole no-external-verifier idea does not survive contact with the toy.
- **Main artefact risk:** **leakage.** If priority is computed with anything that touches the evaluation set, the result is circular. Buffer must be
  built only from training questions, evaluation strictly held out. Second risk: with only 288 questions the buffer saturates and "prioritised" becomes
  "everything", which silently turns it into the uniform control.
- **Build cost: SMALL.** A few hours. Mostly bookkeeping.

---

### Option C — Idle mode inside the dispatcher ("thinking with nothing on the input")

**(a) Plain words.** The other two options are a script deciding what the model works on. This one puts the mechanism *inside the model*. We add a
special "nothing happened" input — an idle token. When the dispatcher is fed the idle token instead of a question, it still runs, but its output head
switches: instead of emitting the next lookup call, it emits a **question**. Those self-generated questions are then answered by the frozen lookup
operator and used as training data. So the model is genuinely computing with no external input, and what it chooses to think about comes out of its own
hidden state, which carries a record of what it has recently been failing at. This is the only one of the three that is actually "unprompted thought at
the architecture level", and it is the only one that would be new relative to what is already published.

**(b) Concrete design.**
- **Module:** `IdleHead` on the existing dispatcher. Two additions: (i) a learned idle-input embedding `e_idle` (d ≈ 64); (ii) a question head, a linear
  map from the dispatcher's hidden state to question slots: 16 start-entity logits + 6 hop-count logits + 3 relation logits = 25 outputs.
- **When it runs:** interleaved idle steps, same schedule as B. Input is `e_idle`; the recurrent/controller state is *carried over* from recent real
  episodes (this is the load-bearing bit — it is what makes the self-generated question depend on recent failures rather than being a fixed
  distribution).
- **Inputs:** idle embedding + carried hidden state. **Outputs:** one question (entity, k, r).
- **Learned vs fixed:** idle embedding and question head are learned; reward for the idle head = the dispatcher's improvement on a held-out probe after
  training on the generated question (a one-step learning-progress reward, estimated with the same RLOO machinery already in the repo). Lookup operator
  frozen during idle steps.
- **Params:** 64 (idle embedding) + 64×25 + 25 ≈ **1.7k new params**. Tiny next to the 15–24k dispatcher.
- **Wiring:** same dispatcher body, second head. No change to the ~79k operator.

**(c) At LLM scale.** A learned idle/self-prompt token that lets a transformer run a forward pass with no user turn and write a question into its own
context, trained with a learning-progress reward. I found nobody doing this in the weights — closest published thing is Quiet-STaR's learned
start-of-thought / end-of-thought tokens ([arXiv:2403.09629](https://arxiv.org/abs/2403.09629)), which insert *rationales between real tokens*, not
thought with no input at all. That is the genuinely novel direction here.

**(d) Toy test.** Three claims, all pre-registered, tested in order — do not proceed to the next if the previous fails:
- **C1 validity:** ≥80% of idle-generated questions are well-formed and answerable in the current story. Failure here means the head just emits garbage.
- **C2 steering (the actual claim):** correlation between the idle head's sampling rate for class *c* and the dispatcher's current error rate on *c*
  must be **≥ 0.4**, measured at 3 checkpoints, in ≥2 of 3 seeds. This is the "steered by its own open problems" test and it is the one that matters.
- **C3 usefulness:** held-out 4–6 hop accuracy beats matched-compute uniform (same idle-step count, questions sampled uniformly) by ≥12 cells of 64.
- **What would show it does not help:** C2 correlation ≈ 0 — the head learned a fixed distribution that ignores the hidden state, which would mean the
  "unprompted" part is real but the "steered by my own problems" part is not. That is a genuinely informative negative and worth publishing internally.
- **Main artefact risk:** diversity collapse (the Prism failure), i.e. the head converges to emitting one question class forever because that class once
  gave a good learning-progress reward. Track Gini over emitted classes every run; abort at Gini > 0.85. Second risk: the carried hidden state leaks the
  *answer*, not just the difficulty, making C3 trivially pass — check by zeroing the carried state and confirming C2 collapses.
- **Build cost: MEDIUM–LARGE.** 2–3 days. New head, new reward path, new interleaved schedule, and the RLOO credit assignment for a one-step
  learning-progress reward is fiddly and noisy.

---

### Ranking and what I would build first

| Rank | Option | Build cost | Novelty vs published work | Chance it moves the known bug |
|---|---|---|---|---|
| **1** | **A — learning-progress proposer** | small–medium | low (it's R-Zero shrunk) | **high** — directly attacks "3 calls then stop" |
| 2 | C — idle mode in the dispatcher | medium–large | **high** — the only architecture-level version | medium |
| 3 | B — unresolved-problem memory | small | low (it's PER + self-consistency) | low–medium |

**Build A first.** Reasons, in order: (1) it is the only one that attacks the bug we already know about — the dispatcher's "3 calls then stop" rule
exists precisely because a human curriculum stopped at 3 hops, and A removes that human; (2) it is ~120 lines and zero new parameters, so a negative
result costs half a day instead of three; (3) its matched-compute uniform control is the cheapest possible way to find out whether our toy's question
space is even big enough for this whole line of research to be testable — and if uniform ties, **that finding kills A, B and C at once**, which is worth
knowing before spending three days on C. Then C if A shows the space is big enough to matter, because C is the only one that would be new. B is a good
cheap add-on to either, not a standalone.

---

## 6. Priority for us: **3 / 5**

Option A is cheap and hits a bug we already have, but the toy's 288-question space is small enough that a uniform-random proposer may match it exactly,
in which case we learn nothing about the actual claim — so it is worth one afternoon, not a research programme.

---

## 7. References

**Brain side**
- Raichle, "The brain's dark energy" (2006) / "The restless brain" (Phil Trans R Soc B 2015) — https://royalsocietypublishing.org/rstb/article/370/1668/20140172/22507/The-restless-brain-how-intrinsic-activity
- Christoff, Irving, Fox, Spreng, Andrews-Hanna, "Mind-wandering as spontaneous thought: a dynamic framework", Nature Reviews Neuroscience 2016 — https://scottbarrykaufman.com/wp-content/uploads/2016/09/Christoff-et-al.-2016.pdf
- Kucyi et al., "Spontaneous default network activity reflects behavioral variability independent of mind-wandering", PNAS 2016 — https://www.pnas.org/doi/10.1073/pnas.1611743113
- Baird et al., "Inspired by distraction: mind wandering facilitates creative incubation", Psychological Science 2012 — https://pubmed.ncbi.nlm.nih.gov/22941876/
- "Mind wandering during creative incubation predicts increases in creative performance in a writing task", Scientific Reports 2025 (preregistered; no between-condition effect) — https://www.nature.com/articles/s41598-025-09736-y · https://pubmed.ncbi.nlm.nih.gov/40634381/
- "Interruption, recall and resumption: a meta-analysis of the Zeigarnik and Ovsiankina effects", Humanities & Social Sciences Communications 2025 — https://www.nature.com/articles/s41599-025-05000-w
- Klinger & Cox, "Motivation and the Goal Theory of Current Concerns" (book chapter; year/edition not verified) — https://www.semanticscholar.org/paper/Motivation-and-the-Goal-Theory-of-Current-Concerns-Klinger-Cox/41185c295acb253200005b84eb84229f44e12882
- Mattar & Daw, "Prioritized memory access explains planning and hippocampal replay", Nature Neuroscience 2018 — https://www.nature.com/articles/s41593-018-0232-z

**AI side**
- Zhao et al., "Absolute Zero: Reinforced Self-play Reasoning with Zero Data", 2025 — https://arxiv.org/abs/2505.03335
- Huang et al., "R-Zero: Self-Evolving Reasoning LLM from Zero Data", 2025 — https://arxiv.org/abs/2508.05004
- "Self-Questioning Language Models", 2025 — https://arxiv.org/abs/2508.03682
- Lin, Snell, Wang, Packer, Wooders, Stoica, Gonzalez, "Sleep-time Compute: Beyond Inference Scaling at Test-time", 2025 — https://arxiv.org/abs/2504.13171
- Gaven, Carta, Romac, Colas, Lamprier, Sigaud, Oudeyer, "MAGELLAN", ICML 2025 — https://arxiv.org/abs/2502.07709
- Colas, Karch, Sigaud, Oudeyer, "Autotelic Agents with Intrinsically Motivated Goal-Conditioned RL: a Short Survey", JAIR 2022 — https://arxiv.org/abs/2012.09830
- Zhang et al., "OMNI", 2023 — https://arxiv.org/abs/2306.01711 ; Faldor, Zhang, Cully, Clune, "OMNI-EPIC", 2024 (ICLR 2025) — https://arxiv.org/abs/2405.15568
- Schaul, Quan, Antonoglou, Silver, "Prioritized Experience Replay", ICLR 2016 — https://arxiv.org/abs/1511.05952
- Wang, Lehman, Clune, Stanley, "POET", 2019 — https://arxiv.org/abs/1901.01753
- Wang et al., "Voyager: An Open-Ended Embodied Agent with LLMs", 2023 — https://arxiv.org/abs/2305.16291
- Hafner et al., "Mastering Diverse Domains through World Models" (DreamerV3), 2023 — https://arxiv.org/abs/2301.04104
- Zelikman et al., "Quiet-STaR", 2024 — https://arxiv.org/abs/2403.09629
- Gwern, "LLM Daydreaming", July 2025 — https://gwern.net/ai-daydreaming ; open implementation: https://github.com/caraulani/llm-daydreaming
- Szeider, "What Do LLM Agents Do When Left Alone? Evidence of Spontaneous Meta-Cognitive Patterns", 2025 — https://arxiv.org/abs/2509.21224
- Mishra, "Preventing Curriculum Collapse in Self-Evolving Reasoning Systems" (Prism), March 2026 — https://arxiv.org/html/2603.13309
- "Self-Improvement Can Self-Regress: The Rise-and-Collapse Failure Mode of LLM", 2026 — https://arxiv.org/pdf/2606.21090 *(abstract only, details unverified)*
