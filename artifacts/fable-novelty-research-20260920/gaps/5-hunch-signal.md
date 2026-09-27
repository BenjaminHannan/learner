# Gap check #5 — the "I'm getting warmer" feeling before the answer exists

Researched 2026-09-20. Everything below is from searches run today; where I could not verify a detail I say so.

---

## 1. Verdict (<= 80 words)

**Already well covered.** The claim "AI has confidence over answers but no learned sense of promise for
half-formed ideas" is wrong as written. Value networks score unfinished games; process reward models score
unfinished reasoning; Process Advantage Verifiers reward *progress* (change in chance of eventual success) —
that is a computational warmth signal, and it works. Also, the brain evidence cuts the other way: for real
insight problems humans show **no** gradual warmth. One narrow strand is genuinely thin (below).

---

## 2. What the brain does — the actual evidence

**Warmth ratings (Metcalfe & Wiebe 1987).** People rated "how close am I?" every 15 s on a 1–7 scale.
On algebra-style (non-insight) problems warmth climbed smoothly toward the solution. On classic insight
problems it stayed flat and then jumped. Feeling-of-knowing predicted success on algebra problems but
**not** on insight problems, and people badly over-predicted their own insight performance.
Quality: **moderate**, and it says the opposite of what the claim implies. The memory note in the brief was
right to flag this: warmth exists for *step-by-step* search, which is exactly the regime AI already models.

**Partial non-replication (Hedne, Norman & Metcalfe 2016, Frontiers in Psychology, n = 51).** Using magic
tricks as problems, insight-labelled solutions were more accurate and more confident — but there was **no**
warmth-rating difference between insight and non-insight solutions. The authors blame their own measure:
70% of trials were dropped, leaving only 3–4 warmth points per trial versus ~40 in the 1987 study.
Quality: **weak evidence either way**, but it means the 1987 warmth dissociation has not been cleanly
replicated by the same lab in a new paradigm.

**Coherence intuition (Bowers et al. 1990, "Dyads of Triads").** This is the strongest piece. People shown
three words judge whether the triad has a hidden common associate at ~80% accuracy while naming the
associate only ~20% of the time. So a "there is something here" signal exists *before* and *independent of*
the answer. Quality: **strong** — repeatedly reproduced (Bolte & Goschke; Ilg et al.; Topolinski & Strack;
Remmers et al., per the review I read). Caveat: I read the Bowers numbers secondhand in a review, not in the
1990 original.
Mechanism caveat: Topolinski & Strack argued the signal is **processing fluency plus affect**, not a real
peek at the solution, and showed it disappears when people try to use it deliberately ("where there's a
will, there's no intuition"). So it may be a cheap heuristic rather than a search-guiding evaluator.

**Aha as internal reward (Tik et al. 2018, Human Brain Mapping, 7 T fMRI, n = 24).** Remote-associates task.
Nucleus accumbens, VTA, caudate, hippocampus and thalamus were more active on solved than unsolved trials,
and NAcc activity scaled with self-rated insight strength. Quality: **moderate-to-weak** — one small-N fMRI
study, correlational, no independent replication that I found. Reverse inference ("NAcc active ⇒ dopamine
reward") is a known weak link.

**Oh, Chesebrough, Erickson, Zhang & Kounios 2020 (NeuroImage).** EEG during anagrams; an insight-related
reward-like signal appeared in people scoring high on reward sensitivity, early enough that the authors argue
it is not just a conscious after-the-fact "nice, I solved it". Quality: **moderate**, correlational,
individual-differences design.

**The feeling is not reliable (Danek & Wiley 2017, Frontiers in Psychology, n = 70; Laukkonen et al.).**
"False insights" are real — a full Aha! with certainty, pleasure and surprise attached to a *wrong* answer.
Semantic priming can be used to induce them on purpose. Quality: **moderate and important** — it means the
human signal is not a clean, trustworthy value function.

**Net read of the biology.** Two different signals get blurred together in the claim:
1. a **distance-to-goal** signal (warmth) — real for analytic search, absent for insight;
2. a **there-is-structure-here** signal (coherence intuition) — real, robust, fires without the answer, and
   possibly just fluency;
3. an **aha reward pulse at the moment of restructuring** — plausible, small-N, and demonstrably fires on
   wrong answers too.

---

## 3. What AI has already done

Prioritising 2023–2026. All links checked today.

| Work | What it showed |
|---|---|
| **AlphaZero** — Silver et al., *Science* 2018 ([science.org](https://www.science.org/doi/10.1126/science.aar6404), [PDF](https://gwern.net/doc/reinforcement-learning/model/alphago/2018-silver.pdf)) | The value head is literally a learned estimate of promise for a *half-finished* game, learned from self-play with no human labels, and it steers search. This alone falsifies the strong form of the claim. |
| **"Let's Verify Step by Step"** — Lightman et al. 2023 ([arXiv:2305.20050](https://arxiv.org/abs/2305.20050), [PRM800K](https://github.com/openai/prm800k)) | 800k human step-level labels; scoring *partial* reasoning chains beat scoring only final answers (78% on a MATH subset). The first big "promise over unfinished ideas" system for language. |
| **Process Advantage Verifiers** — Setlur et al. 2024 ([arXiv:2410.08146](https://arxiv.org/abs/2410.08146), ICLR 2025) | The closest thing to warmth in AI. The reward for a step is defined as **progress**: how much that step changed the probability of eventually being right, measured under a separate "prover" policy. >8% more accurate and 1.5–5× more compute-efficient than outcome-only search; 5–6× better sample efficiency in online RL. |
| **DeepConf** — Meta 2025 ([arXiv:2508.15260](https://arxiv.org/abs/2508.15260)) | Uses the model's *own local confidence* over a sliding window of tokens to kill an unfinished reasoning trace mid-generation. 99.9% on AIME 2025 with GPT-OSS-120B while cutting tokens by up to 84.7%. This is "abandon a cold trail" implemented at frontier scale. |
| **"Language Models (Mostly) Know What They Know"** — Kadavath et al. 2022 ([arXiv:2207.05221](https://arxiv.org/abs/2207.05221)) | Models can be trained to output P(IK) — the chance they know the answer — *without producing the answer*. That is the machine version of Bowers-style coherence intuition, and it gets better with scale. |
| **Negative result: PRM lessons** — Zheng et al. 2025 ([arXiv:2501.07301](https://arxiv.org/abs/2501.07301), ACL Findings) | Cheap Monte-Carlo step labels give worse PRMs than LLM-judge or human labels, because the completion model can rescue a bad step. Best-of-N evaluation of PRMs is itself biased. |
| **Negative result: PRMs don't transfer** — PRM survey 2025 ([arXiv:2510.08049](https://arxiv.org/abs/2510.08049)), reporting ProcessBench and PRMBench | PRMs often fail outside GSM8K/MATH, and are strongly biased: one model is 90.8% accurate on correct steps but 42.9% on wrong ones; another is the reverse (93.0% / 22.7%). They reward fluency and local plausibility as much as correctness — i.e. machine "false insights". |
| **Learning-progress curiosity** — Graves et al. 2017 ([arXiv:1704.03003](https://arxiv.org/abs/1704.03003)); Kim et al. 2020 γ-Progress ([arXiv:2007.07853](https://arxiv.org/abs/2007.07853)) | Schmidhuber's compression-progress idea actually built: pick the next task by how fast you are improving. Graves roughly halved training time on some LSTM curricula; γ-Progress directed attention to learnable dynamics and avoided the white-noise trap. |
| **Negative result: curiosity is fragile** — Burda et al., Large-Scale Study of Curiosity ([ICLR 2019](https://dblp.org/rec/conf/iclr/BurdaEPSDE19.html)); RND ([arXiv:1810.12894](https://arxiv.org/pdf/1810.12894)); Mavor-Parker et al. ([arXiv:2102.04399](https://arxiv.org/pdf/2102.04399)); "Beyond Noisy-TVs" 2025 ([arXiv:2509.25438](https://arxiv.org/html/2509.25438v1)) | The "noisy TV": a pure surprise/interest signal gets captured by random junk. Even RND, long assumed robust, is susceptible. This is the main reason aha-as-reward has not become mainstream. |
| **OMNI / OMNI-EPIC** — Zhang, Lehman, Stanley & Clune 2023–25 ([arXiv:2306.01711](https://arxiv.org/abs/2306.01711), [OMNI-EPIC](https://arxiv.org/html/2405.15568v2)) | Uses a foundation model as a **model of interestingness** to pick which tasks are worth learning; beat uniform sampling *and* learning-progress-alone on Crafter, BabyAI, AI2-THOR. Note what this concedes: learning progress by itself was not enough. |
| **AlphaEvolve** — DeepMind 2025 ([arXiv:2506.13131](https://arxiv.org/abs/2506.13131), [blog](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/)) | Evolutionary search over code where automated evaluators keep the promising mutants; found a 48-multiplication 4×4 complex matrix multiply, beating Strassen-derived 49. But the "promise" here is a hand-written scorer, not a learned feel. |
| **Curiosity for LLM RL** — CDE 2025 ([arXiv:2509.09675](https://arxiv.org/abs/2509.09675)) | Perplexity + critic-variance as an exploration bonus inside RLVR; ~+3 points on AIME. Small but real; the 2025 wave is active. |
| **PonderNet** — Banino et al. 2021 ([arXiv:2107.05407](https://arxiv.org/abs/2107.05407)) | Learns a halting distribution — "how long is this worth thinking about" — differentiably, with lower-variance gradients than REINFORCE. Directly relevant to our stop-decision bug. |
| **NazoNazo riddle benchmark** — Mizumoto et al. 2025 ([arXiv:2509.14704](https://arxiv.org/abs/2509.14704)) | 38 frontier LLMs on Japanese riddles: humans 52.9%, reasoning models 17.6%, non-reasoning 7.6%. 5–39% of wrong answers were **verification failures** — the model generated the right answer and then failed to recognise it. A concrete machine deficit in "knowing it when you see it". |

---

## 4. The real gap

The claim as written does not survive. What is left is narrower, and I'd rate it "tried at small scale, not
mainstream" rather than open:

1. **Promise signals in AI are almost always tethered to a known verifier.** A value net knows "win"; a PRM
   knows "matches the gold answer". Human coherence intuition fires on a word triad with no verifier
   available. The closest machine version, P(IK), still needs labelled question/answer pairs to train on.
   Nobody I found trains a promise signal purely from *internal* structure (does my own state converge?)
   with no external correctness label — except curiosity methods, which measure novelty, not convergence.
2. **The aha pulse is not used to change what gets learned.** Schmidhuber proposed exactly this in
   1990–2010 ([idsia page](https://people.idsia.ch/~juergen/creativity.html),
   [IEEE TAMD](https://dl.acm.org/doi/abs/10.1109/TAMD.2010.2056368)). Modern descendants (Graves, γ-Progress,
   CDE) use progress to decide **what task to attempt next** or **how much to explore**. Almost nobody uses a
   progress/surprise spike at the moment of a solution to decide **how hard to learn from that trajectory**.
   That is a different lever — a learning-rate/credit lever, not an action lever.
3. **Verification failure is a measured, open deficit.** NazoNazo shows models producing the answer and not
   recognising it, 5–39% of the time. Humans have a reward pulse that says "that's it". Models have a
   verifier trained on the same distribution that produced the error.

Honest counter-note: (1) and (3) are being actively worked on by well-funded labs in 2025–26. This is not
virgin territory; it is a crowded area where the specific "no verifier, signal from internal convergence"
corner is thinner than the rest.

---

## 5. Design proposals — how to actually put this in a model

Three options, ranked at the end. None of them is the already-proposed dream phase or the stall-triggered
gain head.

### Option A — Progress head ("am I getting warmer?") on the dispatcher

**(a) Plain words.** Right now the controller only finds out whether it did well at the very end: right
answer or wrong answer. That's like only being told your exam grade, never which questions you got right.
We add a small second network — a coach — that looks at the controller's situation after each lookup and
guesses "what's the chance we end up right from here?" Then we pay the controller for *raising* that number,
step by step. A redundant lookup that tells us nothing raises it by zero, so the "always make 3 calls" habit
stops paying. This is our version of Setlur's Process Advantage Verifier.

**(b) Concrete design.**
- Module: a critic/value head `V(s)` — 2-layer MLP on the dispatcher's hidden state (say 64 → 64 → 1),
  **~4–5k params**.
- Inputs: the dispatcher's hidden state (question embedding + accumulated retrieved values). **Deliberately
  excluded: the step counter and the number of calls made so far.** This is the whole point — the head must
  not be able to implement "3 calls then stop".
- Output: one scalar, predicted probability of finishing correctly from here.
- Trained: on the RLOO rollouts we already generate — each rollout's terminal correctness is a free Monte
  Carlo label for every state it visited. No new data collection. Loss: MSE (or BCE) to the rollout return.
- Per-step shaped reward: `r_t = V(s_{t+1}) - V(s_t)`, plus the usual terminal correctness reward.
- When it runs: every controller step during training. Optionally at test time as a stop rule — stop when
  predicted progress for the best available call is ≤ 0.
- Learned vs fixed: head and dispatcher learned; the ~79k lookup operator stays frozen.
- Wiring: sits beside the dispatcher, reads its state, writes into the RLOO advantage. The operator is
  untouched, so the held-out-combination transfer we already have is not put at risk.

**(c) At LLM scale.** This *is* a PRM / PAV: score each reasoning step by how much it moved the probability
of eventual success, and use that as dense RL reward instead of a single end-of-answer reward.

**(d) Falsifiable toy test.**
- Task: train dispatcher on 1–3 hop chains as now; evaluate on 4, 5 and 6 hops, held out.
- Controls: (i) **matched compute** — baseline gets the same number of gradient steps and an equal-sized
  *dummy* head whose output is not used, so parameter count and wall-clock match; (ii) **shuffled-value
  control** — same head, but its outputs are randomly permuted within the batch before shaping; must not
  help; (iii) the existing no-hints baseline (4/64 beyond 3 hops).
- Pass mark (pre-register): ≥ 32/64 correct at 4 hops and ≥ 16/64 at 5–6 hops, with the shuffled control
  staying ≤ 10/64, across 3 seeds.
- What would show it doesn't help: 4-hop accuracy stays under ~10/64, or the shuffled control matches the
  real head (meaning we only added optimisation noise).
- Main artefact risk: **the head learns the step count implicitly** from state drift and re-invents the same
  counting heuristic. Mitigations: hide the counter, add a probe that tries to decode step index from the
  head's input (if decodable above ~60%, the test is void), and evaluate only on chain lengths never trained.

**(e) Build cost: small.** A day or less of code; fits inside the 30-minute-per-run budget.

---

### Option B — Coherence head ("is there anything here at all?")

**(a) Plain words.** Bowers' experiment is the one solid human result: people can tell that three words share
a hidden connection about 80% of the time while only naming the connection 20% of the time. So we build the
same thing: a tiny network that reads the question and the story rows *before any lookup happens* and says
"yes, this is answerable" or "no, the chain is broken" — without solving it. Then the controller uses that to
decide how much effort to spend, instead of always spending exactly three calls.

**(b) Concrete design.**
- Module: a coherence/feasibility head — pooled attention over story rows conditioned on the question
  embedding, then 2 layers to a scalar. **~6–8k params**.
- Inputs: question (start entity, hop count is *not* given, target relation) + the story row embeddings.
  Also available mid-search: the set of rows retrieved so far.
- Output: (i) `P(answerable)` before any lookup; (ii) a running **convergence score** mid-search — how
  peaked the distribution over candidate answer entities is across retrieved rows.
- Trained: self-supervised from our own rollouts — label = did any rollout ever solve it. Same free-label
  trick as A. Analogue of Kadavath's P(IK).
- When it runs: once at question time, then after each lookup.
- Learned vs fixed: head learned; operator frozen. The convergence score can be a **fixed computed statistic**
  (entropy over candidate entities) — cheaper, fully interpretable, and a good ablation against the learned
  version.
- Wiring: output is concatenated into the dispatcher's state and also gates a "keep going / stop / declare
  unanswerable" action. This gives the controller a reason to continue that is not "I've made 3 calls".
- Requires a small data change: add **unanswerable** questions (broken LINK chain, missing relation row) to
  the generator. That is good hygiene anyway — right now the controller never has to consider giving up.

**(c) At LLM scale.** A P(IK)-style head, or DeepConf's local-confidence gate: decide before/early in a trace
whether this problem is worth more tokens.

**(d) Falsifiable toy test.**
- Task: mixed set, 50% answerable (1–6 hops), 50% unanswerable by construction.
- Controls: (i) **hand-statistic baseline** — a non-learned rule that just checks whether a LINK row exists
  for the start entity. The learned head must beat it; (ii) matched-compute dummy head; (iii) shuffled labels.
- Pass mark: AUC ≥ 0.75 for answerable-vs-not **before any lookup**, while solve-rate on the answerable
  half does not drop; and on 4–6 hop answerable questions the gated controller beats Option A alone by
  ≥ 8/64 cells.
- What would show it doesn't help: the hand statistic matches the learned head (our world is too structured
  for the result to mean anything), or gating just makes the controller stop earlier and lose accuracy.
- Main artefact risk: **our toy world is small enough that answerability is trivially computable**, so a head
  that "works" proves nothing about intuition. This is the reason B is ranked second, not first — the
  hand-statistic control is the experiment, really.

**(e) Build cost: small–medium.** Needs the unanswerable-question generator, which is new code.

---

### Option C — Aha-as-reward: surprise that pays off changes how hard we learn

**(a) Plain words.** This is the Schmidhuber idea, and it's the one that nobody has really built. Right now
every rollout teaches the model the same amount. But when a person tries something unexpected and it suddenly
works, they get a jolt, and they remember that one moment far better than a thousand boring ones. So: keep a
small predictor that guesses what a lookup will return. When a lookup's result is *surprising* AND the
progress head from Option A then says that step made real progress, we mark that trajectory and learn from it
harder. "Unexpected and useful" gets the biggest weight.

**(b) Concrete design.**
- Module: a **next-result predictor** `P(value | state, chosen call)` — small attention read, **~8–10k
  params** — plus a scalar weighting rule (no params).
- Inputs: dispatcher state + the call it chose. Output: predicted returned value distribution.
- Surprise `u_t` = negative log-likelihood of the value actually returned.
- Aha signal `a_t = u_t * max(0, ΔV_t)` where `ΔV_t` is Option A's progress. High only when a step was both
  unexpected and productive. Normalise per batch.
- Use: multiply the RLOO advantage for that trajectory by `(1 + λ·mean_t a_t)`, λ tuned once. So it changes
  **how much we learn from a trajectory**, not which action we take. That is the lever nobody pulls.
- When it runs: during training only, after each rollout batch.
- Learned vs fixed: predictor and dispatcher learned; operator frozen; λ fixed.
- Requires Option A to exist first (it needs ΔV).

**(c) At LLM scale.** Weight RL trajectories by "surprisal × verified progress" — learn hardest from the
reasoning steps that the model did not expect but that turned out to move it toward a correct answer.

**(d) Falsifiable toy test.**
- Task: same 1–3 train / 4–6 held-out hop setup, run **on top of Option A**, so A is the baseline.
- Controls: (i) **matched-compute** A-only run with the same number of episodes; (ii) **random reweighting**
  with the same mean and variance as the aha weights — this is the crucial control, because any reweighting
  scheme acts a bit like a learning-rate change; (iii) an A-only run with **tuned learning rate and entropy
  bonus**, since those are the cheap ways to get the same effect.
- Pass mark: reaches A's final 4-hop accuracy in ≤ 60% of the episodes, **or** beats A by ≥ 12/64 cells at
  5–6 hops, on 3 seeds, while both controls stay within noise of A.
- What would show it doesn't help: random reweighting does as well (it was just a learning-rate trick), or
  the surprise term is dominated by rows the operator is simply noisy about.
- Main artefact risk: the **noisy-TV failure** in miniature — surprise gets captured by whatever part of the
  toy world is most random rather than most informative. The `max(0, ΔV)` gate is specifically there to block
  that, and the random-reweighting control is what proves the gate matters.

**(e) Build cost: medium.** Predictor plus a reweighted RLOO path plus three controls; likely two or three
30-minute waves.

---

### Ranking and what I'd build first

**A > B > C.**

**Build A first.** Reasons: (1) it attacks the known blocking bug directly — "make 3 calls then stop" is a
credit-assignment failure, and dense progress reward is the textbook fix for credit-assignment failure;
(2) it is the cheapest thing on the list and needs no new data generator; (3) it is the prerequisite for C,
which cannot be measured without it; (4) it is a *known-good* technique at large scale (Setlur's PAVs:
>8% accuracy, 1.5–5× compute efficiency), so if it fails in our toy that is itself informative about the
toy rather than about the idea.

Be honest in the write-up: A is **not** a novelty claim. It is us importing a standard critic. The novelty,
if any, is in C.

**Then B**, because it adds unanswerable questions to the eval — which we need anyway, since a controller
that has never had to give up cannot be tested on whether it knows when to stop.

**C last**, because it is the only genuinely under-built idea here and therefore the one most likely to be
an artefact; it deserves a solid A baseline and its two controls before anyone reads anything into it.

---

## 6. Priority score

**4 / 5.** Option A is the most direct known fix for the "3 calls then stop" bug that currently blocks
dependable multi-hop, and it is cheap — but be clear with Ben that A and B are re-implementations of
well-established machinery, not a novelty story; only C (aha-as-learning-weight) is thin ground.

---

## 7. References

Brain:
- Metcalfe, J. & Wiebe, D. (1987). Intuition in insight and noninsight problem solving. *Memory & Cognition*.
  [PubMed](https://pubmed.ncbi.nlm.nih.gov/3600264/) ·
  [PDF](https://www.columbia.edu/cu/psychology/metcalfe/PDFs/Metcalfe%20Wiebe%201987.pdf)
- Hedne, M., Norman, E. & Metcalfe, J. (2016). Intuitive Feelings of Warmth and Confidence in Insight and
  Noninsight Problem Solving of Magic Tricks. *Frontiers in Psychology* 7:1314.
  [Frontiers](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2016.01314/full)
- Bowers, K. et al. (1990), Dyads of Triads coherence task — numbers read secondhand in:
  Search and Coherence-Building in Intuition and Insight Problem Solving (review).
  [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5447020/)
- Topolinski, S. & Strack, F. Where there's a will — there's no intuition. *Journal of Memory and Language*
  (year ~2008, **not verified**).
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0749596X08000132)
- Tik, M., Sladky, R., Luft, C.D.B., Willinger, D., Hoffmann, A., Banissy, M.J., Bhattacharya, J. &
  Windischberger, C. (2018). Ultra-high-field fMRI insights on insight. *Human Brain Mapping*. n = 24.
  [PubMed](https://pubmed.ncbi.nlm.nih.gov/29665228/) ·
  [Wiley](https://onlinelibrary.wiley.com/doi/10.1002/hbm.24073)
- Oh, Y., Chesebrough, C., Erickson, B., Zhang, F. & Kounios, J. (2020). An insight-related neural reward
  signal. *NeuroImage*. [PubMed](https://pubmed.ncbi.nlm.nih.gov/32194279/)
- Danek, A. & Wiley, J. (2017). What about false insights? *Frontiers in Psychology* 7:2077, n = 70.
  [PDF](https://www.amorydanek.de/wp-content/uploads/2018/02/Danek-2017-What-about-false-insights.pdf)
- Laukkonen, R. et al. The dark side of Eureka (year/venue **not verified**).
  [PDF](https://tangenlab.com/pdf/laukkonen_2020_eureka_aha_facts.pdf) ·
  Eliciting false insights with semantic priming: [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9166882/)

AI:
- Silver, D. et al. (2018). A general RL algorithm that masters chess, shogi and Go. *Science* 362(6419).
  [Science](https://www.science.org/doi/10.1126/science.aar6404)
- Lightman, H. et al. (2023). Let's Verify Step by Step. [arXiv:2305.20050](https://arxiv.org/abs/2305.20050)
- Setlur, A. et al. (2024). Rewarding Progress: Scaling Automated Process Verifiers for LLM Reasoning.
  [arXiv:2410.08146](https://arxiv.org/abs/2410.08146) · [ICLR 2025 poster](https://iclr.cc/virtual/2025/poster/30649)
- Zheng, Z. et al. (2025). The Lessons of Developing Process Reward Models in Mathematical Reasoning.
  [arXiv:2501.07301](https://arxiv.org/abs/2501.07301)
- A Survey of Process Reward Models (2025). [arXiv:2510.08049](https://arxiv.org/pdf/2510.08049)
- Deep Think with Confidence (DeepConf), Meta 2025. [arXiv:2508.15260](https://arxiv.org/abs/2508.15260)
- Kadavath, S. et al. (2022). Language Models (Mostly) Know What They Know.
  [arXiv:2207.05221](https://arxiv.org/abs/2207.05221)
- Schmidhuber, J. (2010). Formal Theory of Creativity, Fun, and Intrinsic Motivation (1990–2010).
  *IEEE TAMD*. [ACM](https://dl.acm.org/doi/abs/10.1109/TAMD.2010.2056368) ·
  [overview page](https://people.idsia.ch/~juergen/creativity.html)
- Graves, A. et al. (2017). Automated Curriculum Learning for Neural Networks.
  [arXiv:1704.03003](https://arxiv.org/abs/1704.03003)
- Kim, K. et al. (2020). Active World Model Learning with Progress Curiosity (γ-Progress).
  [arXiv:2007.07853](https://arxiv.org/abs/2007.07853)
- Burda, Y., Edwards, H., Pathak, D., Storkey, A., Darrell, T. & Efros, A. (2019). Large-Scale Study of
  Curiosity-Driven Learning. ICLR. [dblp](https://dblp.org/rec/conf/iclr/BurdaEPSDE19.html) ·
  RND: [arXiv:1810.12894](https://arxiv.org/pdf/1810.12894)
- Mavor-Parker, A. et al. (2021). How to Stay Curious while Avoiding Noisy TVs.
  [arXiv:2102.04399](https://arxiv.org/pdf/2102.04399)
- Beyond Noisy-TVs: Noise-Robust Exploration via Learning Progress Monitoring (2025).
  [arXiv:2509.25438](https://arxiv.org/html/2509.25438v1)
- Zhang, J., Lehman, J., Stanley, K. & Clune, J. (2023). OMNI: Open-endedness via Models of human Notions of
  Interestingness. [arXiv:2306.01711](https://arxiv.org/abs/2306.01711) ·
  OMNI-EPIC: [arXiv:2405.15568](https://arxiv.org/html/2405.15568v2)
- AlphaEvolve (2025). [arXiv:2506.13131](https://arxiv.org/abs/2506.13131) ·
  [DeepMind blog](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/)
- CDE: Curiosity-Driven Exploration for Efficient RL in LLMs (2025).
  [arXiv:2509.09675](https://arxiv.org/abs/2509.09675)
- Banino, A. et al. (2021). PonderNet: Learning to Ponder.
  [arXiv:2107.05407](https://arxiv.org/abs/2107.05407)
- Mizumoto, A. et al. (2025). NazoNazo: Japanese Children's Riddles as a Benchmark for Machine Insight and
  Metacognition. [arXiv:2509.14704](https://arxiv.org/abs/2509.14704)
