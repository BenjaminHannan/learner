# Sleep research, round 2: turning search wins into skills

**Scope.** This covers new ideas only. It leaves out what round 1 already covered: STaR/ReST-EM stalling after round 1, Absolute Zero, the hint ladder / reverse curriculum (in `design/research/2026-09-18-novel-mechanisms.md`), and DreamCoder chunking with a smuggling guard. The plan's "wins plus variants, capped at 40%" is taken as given.

**Labels.** SHOWN = a paper's result (these were checked at abstract level only) or something seen in the repo code. SUGGESTED = argued. UNTESTED = my idea.

## Plain summary for Ben
- **Why 3-step gets no training signal.** The reasoner's RL step can't learn from a question it always gets wrong. When all 8 tries fail, the training signal is exactly zero. That is one likely reason 3-step chains stay at 0/30. A checked win is the only thing that can break the tie.
- **What to count.** Count distinct *kinds* of solution, not the number of wins. Test on kinds it never saw.
- **How to avoid getting lazy.** Aim practice at what it almost-but-not-quite solves, and throw away what it already always gets right.

## Repo facts this relies on (SHOWN, from code)
- The reasoner is a one-decision policy: an answer action plus support bits for which facts it used. It has no written-out thought steps.
- `rl_loss` in `scripts/claude_rsn294_run.py` computes `adv = (R - R.mean(0)) / (R.std(0) + 1e-4)` over G=8 tries. If all 8 tries get the same reward, the advantage is 0 and the RL term gives no gradient.
- `wins.jsonl` exists only in the plan (`360-sleep-plan.md`). No code writes or reads it yet.
- There is no halting or stop-token code in the 294 runner.

---

## Card experiments (small loop reasoner, synthetic notebooks)

### 1. Put the checked win inside the RL group (mixed-policy GRPO)
**What.** When all G tries on a problem fail, swap one try for the code-checked solution: the answer plus its support bits. Its probability ratio is capped so the reasoner can't just copy it rigidly. This gives a problem that was always failed a positive advantage instead of zero.

**Evidence.**
- LUFFY (arXiv 2504.14945): mixing off-policy traces into zero-RL groups, with "policy shaping" through regularised importance sampling, gave +7.0 on average across 6 math benchmarks and +6.2 out of distribution. SHOWN.
- On-policy RL cannot learn beyond what the model can already produce (the paper's framing). SUGGESTED.
- DAPO (arXiv 2503.14476) filters out groups where every try gets the same reward for the same reason. SHOWN at abstract level.

**Fit.** A few lines in `rl_loss`. It costs the same as 296 (about $2.09).

**First experiment.**
- Arms: the 296 recipe with 3-step questions added to the RL mix, (a) as it is today vs (b) with win injection when all 8 tries fail. Everything else identical, 3 seeds.
- Pass: on a fresh blind 3-step panel, (b) scores at least 12/30 and at least (a) + 6.
- Wrong if: (b) is within 2 of (a), or dev 3-step accuracy rises while the fresh panel stays flat.
- Secondary arm, to report but not to decide on: plain copy-phase SFT on 3-step gold. If SFT matches (b), the injection trick adds nothing over supervision.

**How it could fool us.** On cards, the "win" is just the generator's gold, so this tests the mechanism, not whether search pays off. The fresh panel must come from a generator version frozen before the run.

### 2. Count skeletons, not wins; test on skeletons it never saw
**What.** Reduce each win to its skeleton: the chain of relation operations plus the final operation (for example parent→sibling→count), with every name removed. Sleep then builds each skeleton into hundreds of fresh-symbol notebooks in the 296 style, and code re-solves every answer. The real question is how many *distinct* skeletons are needed before the reasoner solves new combinations of the same building blocks.

**Evidence.**
- RFT (arXiv 2308.01825): gains grow with the number of distinct reasoning paths, not with raw sample count, and help weaker models more. SHOWN.
- ReST-EM overfits small problem sets (round 1). SHOWN.
- Wang et al. (arXiv 2405.15071): transformers learn composition only after grokking and fail to generalise it systematically out of distribution. The authors suggest sharing weights across layers would help. SHOWN (the fix itself is SUGGESTED).
- The loop reasoner shares weights across passes, so it is a plausible fit. UNTESTED.

**First experiment (a dose-response).**
- Train on 1, 4 or 16 3-step skeletons.
- Test on a blind panel of *held-out* skeletons built only from primitives it has seen.
- Pass: held-out accuracy rises with dose, and at 16 skeletons it reaches at least 50% of in-skeleton accuracy.
- Wrong if: in-skeleton accuracy is at least 25/30 while held-out stays at or below 5/30. That would mean it learned the templates, not the rule.

**How it could fool us.** Held-out skeletons that share an order-2 prefix with training ones are only half new. Register the exact list of held-out skeletons before training.

### 3. Spend search where it almost fails (difficulty-aware win allocation)
**What.** Plain rejection sampling mostly collects wins on easy problems. Instead, sleep gives each skeleton or problem family a share of practice in proportion to how often the reasoner fails it, and throws away families it always solves.

**Evidence.**
- DART-Math (arXiv 2407.13690): vanilla rejection tuning is badly biased toward easy queries. Giving hard queries more tries beat it with smaller datasets. SHOWN.
- B-STaR (arXiv 2412.17256): exploration (diversity) decays quickly across self-improvement rounds, and monitoring it plus adjusting settings helped. SHOWN.
- Online difficulty filtering (arXiv 2504.03380) keeps problems whose pass rate is in the middle band. SHOWN at abstract level.

**Fit.** A weight on the sampling side. No extra compute.

**First experiment.**
- Arms: uniform mix vs a mix weighted by failure rate. Failure rates are measured on a separate *training-side* probe set, never on the panel.
- Pass: 3-step and 4-step fresh accuracy gain at least 4/30, and 1-2 step accuracy drops no more than 1/30.
- Wrong if: the hard-weighted arm gains nothing, or loses 1-2 step skill (forgetting).

**How it could fool us.** If the difficulty probe shares items or templates with the panel, the practice gets shaped to the test.

### 4. Learn when to stop from hindsight (only after extra passes help)
**What.** Expert iteration trains a fast network to match the output of slow search, and uses that network to guide the next search. Applied to passes: run 12 passes, find the earliest pass after which the checked answer is right and *stays* right, and use that pass as the target for the thinking-stop token.

**Evidence.**
- ExIt (arXiv 1705.08439) beat REINFORCE on Hex, and its tree search trained from scratch beat MoHex 1.0. SHOWN.
- PonderNet (arXiv 2107.05407) learns halting and extrapolates on parity. SHOWN.
- Using hindsight stop labels for halting is UNTESTED.

**Gate.** Don't run this until more passes measurably help: 12 passes must beat 4 passes by at least 3/30 on fresh 2-step items. Today they don't.

**First experiment.**
- Pass: average passes used at most 60% of 12, accuracy loss at most 1/30, and a Spearman correlation of at least 0.3 between hop count and passes used.
- Wrong if: the stop pass tracks question length or notebook size but not hop count (partial correlation with hop count below 0.1).

**How it could fool us.** It could learn "long question means think longer" as a surface cue. Vary question wording independently of hop count.

---

## Village / agent model (real user notebooks, few wins, no generator)

### 5. Reuse misses by relabelling them, with a cap
**What.** Borrowed from HER. A failed attempt often cites rows that form a valid chain answering a *different* question. Code builds that question and checks the answer, and the pair becomes a practice item. This turns a rare-success day into many practice items built from the user's own facts. Facts stay in the input and are never closed-book targets.

**Evidence.**
- HER (arXiv 1707.01495): goal relabelling makes sparse-reward tasks learnable. SHOWN.
- HIR (arXiv 2302.05206): relabelling the instruction to match the output improved instruction following. SHOWN.
- Applying this to notebook chains is UNTESTED.

**Fit.** Inference plus code only, so under $0.10 per night.

**First experiment.**
- Run 10 simulated days with a frozen fresh blind bank of user questions.
- Pass: relabelled items stay at most 25% of the mix, and the next-morning solve rate on *new* blind questions gains at least 3 points over a twin fed an equal count of generic 296 practice.
- Wrong if: the gain disappears against that twin. That would mean it is just extra practice (the plan's control (b)).

**How it could fool us.** Relabelled questions are easier than the one actually asked, which pulls practice toward easy wins. Keep the cap and the difficulty weighting from idea 3.

## Recommended order
1 (it removes a structural zero-gradient) → 2 (answers "how many wins") → 3 → 5 → 4 (only after the pass gate). Each needs its own frozen fresh panel. None trains facts into weights.

**Sources:** [LUFFY](https://arxiv.org/abs/2504.14945), [DART-Math](https://arxiv.org/abs/2407.13690), [RFT scaling](https://arxiv.org/abs/2308.01825), [Grokked transformers](https://arxiv.org/abs/2405.15071), [B-STaR](https://arxiv.org/abs/2412.17256), [ExIt](https://arxiv.org/abs/1705.08439). DAPO 2503.14476, online difficulty filtering 2504.03380, PonderNet 2107.05407, HER 1707.01495 and HIR 2302.05206 are cited from memory and were not checked in this run.