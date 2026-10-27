# Sleep research, round 2: keeping each night's gains and consolidating them like a brain (2026-09-25)

I checked the repo before writing. The reasoner trainer uses AdamW with weight decay 0.01. It keeps no averaged copy of the weights and has no KL term (`scripts/claude_rsn294_run.py:127`). Nights, day replay, practice school, win episodes, the 40% cap and the undo gate are already planned (360). EWC, Tadros, generative replay, TIES and O-LoRA already appear in `34-gpt-xhigh…`, `sleep-research-2026-09-24.md` job F and exp 42b. I cover those only in the skip list at the end.

**Every idea below is a small card experiment on the 30M loop reasoner.** None touches the village model. Before any of them, the loop reasoner has to pass its copy phase (the step-embedding fix). Otherwise there is nothing worth keeping across nights.

---

## 1. Shrink-and-perturb at the start of each night (the brain idea that sleep scales weights down)

**What.** Before each night's training, multiply every weight by about 0.8 and add a little noise. Then train as usual. This is the ML version of the idea that sleep scales synapses down (Tononi and Cirelli, Neuron 2014). It stops a model trained night after night from going stiff and learning worse.

**Evidence.**
- SHOWN: warm-starting from old weights generalises worse than training from scratch, and shrink-and-perturb closes that gap (Ash and Adams, NeurIPS 2020, arXiv 1910.08475).
- SHOWN: across thousands of tasks, deep nets slowly lose the ability to learn. On ImageNet binary tasks accuracy fell from 89% to 77% by task 2000. Shrink-and-perturb almost removes the loss, but it only works in a narrow range of settings (Dohare et al., Nature 632, 2024; arXiv 2306.13812).
- SHOWN: lower weight norm goes with the switch from memorising to generalising, i.e. grokking (Omnigrok, arXiv 2210.01117; Power et al., arXiv 2201.02177).
- SUGGESTED: the same pressure could favour rules over surface patterns.

**Fit.** Four lines of code and no extra compute.

**First experiment (UNTESTED).** Two twins, 3 seeds each, 6 nights. Each night is new 2-step and 3-step practice from the recombination generator.
- Arm A: plain warm start.
- Arm B: shrink 0.8 plus noise at 1e-3 times the init scale.
- Arms get equal steps and equal data.
- Measure 1: on night 6, the accuracy gained within one fixed-size training block on a brand-new puzzle type (plasticity).
- Measure 2: on night 6, accuracy on a fresh blind panel generated after the recipe is frozen.
- **Pass:** B beats A by at least 5 points on plasticity, in all 3 seeds.
- **Proves it wrong:** A is no worse at night 6 than at night 1, so plasticity loss never showed up at 6 nights and the fix has nothing to fix. Or B loses at least 3 points on old skills.
- Cost: about $1 on the 5090.

**How it could fool us.** The shrink factor gets tuned on the blind panel. Fix it at 0.8 in advance and tune nothing.

## 2. Two-speed weights: a slow averaged copy is the one that answers

**What.** Keep a fast copy that trains each night and a slow copy that is a running average of the fast one (for example slow = 0.7·slow + 0.3·fast after each night). Only the slow copy answers questions. This mirrors the brain's split between fast learning and slow, stable cortex.

**Evidence.**
- SHOWN: CLS-ER keeps averaged copies of the weights at two speeds and adds a consistency loss. It beat plain replay on the standard continual-learning image benchmarks (Arani et al., ICLR 2022, arXiv 2201.12604).
- SHOWN: mixing fine-tuned weights with the starting weights keeps the new skill and raises robustness to shifted data (WiSE-FT, arXiv 2109.01903).
- SHOWN: averaging the last few checkpoints speeds up and steadies training (LAWA, arXiv 2209.14981).

**Fit.** Close to free: one extra 120 MB copy of the weights and one line at commit time. The self-check gate would judge the averaged copy.

**First experiment (UNTESTED).** Reuse arm A's runs from idea 1 and compute the averaged copy from them afterwards (0.3 mix, fixed in advance).
- **Pass:** over nights 1-6, the averaged copy's worst night-to-night drop on old skills is at most half the fast copy's.
- **Pass:** on night 6, the averaged copy is within 2 points of the fast copy on the fresh blind panel.
- **Proves it wrong:** the averaged copy trails the fast one by more than 2 points on the fresh blind panel. Then averaging only slows learning down.

**How it could fool us.** The mix weight gets picked on the test panel. Pick it only on a random held-out slice of the day log (rule 6 in 41).

## 3. Anchor to yesterday on replay, and use KL as a forgetting meter

**What.** On old practice inputs, add a loss that keeps today's output probabilities close to yesterday's, including the thinking-stop token at every pass. Also log the KL divergence (how far today's answers drift from yesterday's) on a fixed probe set as a one-number warning of forgetting.

**Evidence.**
- SHOWN: Learning without Forgetting distils the old model's outputs on inputs from the new task (arXiv 1606.09282).
- SHOWN: Dark Experience Replay stores the old logits next to the replayed examples and beat plain replay (arXiv 2004.07211).
- SHOWN: at equal new-task scores, on-policy RL forgets less than supervised fine-tuning. Across methods, forgetting is predicted by the KL from the base model on the new task's data (RL's Razor, arXiv 2509.04259).
- SUGGESTED: this matters here because sleep plans a supervised copy phase followed by GRPO. The stop decision is a learned behaviour that plain replay only scores through the final answer.

**Fit.** Store yesterday's stop-token probabilities and answer logits with each replay example. That costs a few MB and one extra forward pass per replay batch.

**First experiment (UNTESTED).** Arm C is A plus a KL-to-yesterday loss on the replay batches (weight 1.0, fixed).
- Measure 1: average old-skill accuracy after 6 nights.
- Measure 2: whether the thinking length still tracks difficulty. Use the Spearman rank correlation between number of passes and number of steps on a fresh blind panel.
- **Pass:** C keeps at least 3 more points of old skill than A.
- **Pass:** C's rank correlation is at least 0.1 higher than A's.
- **Pass:** C is no more than 2 points behind A on the new skill.
- **Proves it wrong:** C's new-skill score drops by more than 2 points. Then the anchor is freezing learning.
- **Meter check:** the probe-set KL should rank the 18 runs (3 seeds × 6 nights) by forgetting with Spearman above 0.6. If it doesn't, drop KL as a gate signal.

**How it could fool us.** If yesterday's model was wrong, anchoring keeps it wrong. Anchor only on replay items whose logged answer passed the exact checker.

## 4. Similarity-weighted replay: replay old items that look like the new ones

**What.** Don't replay a uniform sample of old practice. Mostly replay old items whose internal representation is close to tonight's new material, because those are the ones the new learning is most likely to overwrite.

**Evidence.**
- SHOWN: similarity-weighted interleaved learning matched the accuracy of full interleaving, with little interference, while showing far fewer old items per epoch (Saxena, Shobe and McNaughton, PNAS 119(27), 2022). That was on image classifiers.
- This is not the surprise-ranked replay that failed in exp 42. It ranks by closeness in representation, not by loss.

**Fit.** Take the mean hidden state at the last pass for each buffered puzzle and pick the replay items by cosine similarity. The cost is small.

**First experiment (UNTESTED).** Each night the replay budget is cut to 25% of A's.
- Arm D1 fills that budget with the most similar items.
- Arm D2 fills it with a uniform random sample.
- **Pass:** D1 keeps at least 4 more points of old skill than D2, in all 3 seeds.
- **Proves it wrong:** D1 is at most 1 point better than D2. Uniform replay is a known strong baseline (Hayes 2021).

**How it could fool us.** Similarity computed on the test panel. Compute it only on the buffer and tonight's practice.

## 5. A standard multi-night scorecard that every idea above uses

**What.** Every night, score the model on every earlier night's held-out skill and on the next night's skill it hasn't practised yet. That gives a nights × skills grid of accuracies (GEM, Lopez-Paz and Ranzato, arXiv 1706.08840, defines the backward-transfer and forward-transfer scores on this grid). Add one plasticity row: a new puzzle type learned within a fixed step budget.

**Why.** "Improves over time" is a claim across many nights. Today we only measure single nights. This grid separates three things: learning, forgetting and losing the ability to learn.

**Fit.** Pure evaluation, a few CPU minutes, no training. Build it once, before any of ideas 1-4 run.

**How it could fool us.** Scoring on the practice generator's own outputs. Each skill's test items must come from a panel frozen before night 1 and generated from a seed nobody has seen.

---

## Skip for now, with reasons

- **EWC/SI.** SHOWN: in the class-incremental setting, weight-penalty methods fail where replay works (van de Ven et al., arXiv 1904.07734). We already have exact replay.
- **Generative replay.** The practice generator is exact code, so a learned generator adds only errors.
- **Tadros sleep replay and WSCL (arXiv 2401.08623).** Shown only on spiking or image models with small gains. Porting them to a looped transformer is a research project, not a $4 job.
- **LoRA isolation.** Exp 42b already found no sample-efficiency gain. Keep it only as a rollback tool (job F).
- **Merging nightly deltas (TIES).** Only worth it after idea 2 shows averaging helps.

## Order and budget

1. Idea 5, $0.
2. Ideas 1, 2 and 3 together: one 6-night run, 3 seeds, arms A, B and C. Idea 2 is computed from A afterwards. About $3.
3. Idea 4 only if old-skill forgetting in arm A is real, meaning a drop of at least 5 points. About $1.

Each arm changes one thing against A. Pass marks are registered before any run. Nothing here trains facts into weights: the notebook rows stay in the input.

## Plain summary for Ben

When you train a model night after night, three things can go wrong. It forgets old skills. It slowly gets worse at learning anything new. Or it memorises instead of finding rules. Brains seem to deal with these in sleep: they shrink connections a bit, keep a slow stable copy alongside a fast learner, and replay old memories that resemble the new ones.

Each of these has a cheap ML version with real results behind it: shrink-and-perturb, weight averaging, anchoring to yesterday, and similarity-based replay. None of them has been tested on a model like ours. The first step costs nothing: a grid that measures learning, forgetting and ability to learn across nights. Then one run of about $3 tests the first three ideas at once, each against the same plain baseline.

Sources: [RL's Razor, arXiv 2509.04259](https://arxiv.org/abs/2509.04259) · [SWIL, PNAS 2022](https://www.pnas.org/doi/abs/10.1073/pnas.2115229119) · [Dohare et al., arXiv 2306.13812](https://arxiv.org/abs/2306.13812) · [Dohare et al., Nature 2024 (researchgate)](https://www.researchgate.net/publication/383279739_Loss_of_plasticity_in_deep_continual_learning)