# Sleep research, round 2: how deep to think, and when to stop

Scope: everything below is a **card experiment** on the loop reasoner (`scripts/claude_rsn294_core.py` LoopThinker, runner lineage 294 → 296 → 353). Village or agent use is covered only in the last section. Labels: **SHOWN** means a paper result, **SUGGESTED** means the paper argues it, **UNTESTED** means my idea. Where I only read an abstract, I say "abstract".

## Two blockers in the code (read before planning any "longer than practised" test)

1. **The question can't hold a 4- or 5-step chain.** `MAX_HOPS = 3`, and each hop relation gets its own learned slot embedding (`S[1+MAX_WHO+i]`, core.py:45 and :420). A 4-step question can't be encoded at all. Each hop also carries a fixed per-position tag (hop 1, hop 2, hop 3), and fixed position tags like that are a known cause of poor length generalisation (Kazemnejad et al. 2023, arXiv 2305.19466, SHOWN for absolute position encodings on decoder models). The fix is to give all hop relations one shared role embedding. That is a separate one-change job. Until it's done, **the only extrapolation we can test is: train on 1-2 steps, test on 3.**
2. **The answer head reads only the last pass** (core.py:496-502). No per-pass exit is possible yet. Every halting idea below needs a readout at every pass, with the heads shared across passes. This costs almost nothing.

All experiments below assume 353 passes first, i.e. the loop learns its copy phase once the step embedding is removed.

---

## Idea 1. Training that doesn't depend on the path (progressive loss plus random starting state)

**What.** In sleep training, run a random number of passes with no gradient, starting from a randomly perturbed state. Then run a few more passes with gradient and score only the end. This teaches the loop to keep improving until it settles on an answer, with no rule tied to "pass number t", so extra passes stop hurting and start helping on harder items.

**Evidence.**
- Bansal et al. 2022 (arXiv 2202.05826), SHOWN: recurrent nets with input recall plus a "progressive loss" extrapolated from small to much larger mazes and prefix-sum problems by thinking longer. They settled to a fixed point over thousands of passes with no overthinking.
- Anil et al. 2022 (arXiv 2211.09961, NeurIPS), SHOWN: generalisation to harder problems tracks "path independence", meaning the loop reaches the same end state from any starting state. Changes that promote it helped, and changes that penalise it hurt.
- Geiping et al. 2025 (arXiv 2502.05171), SHOWN at 3.5B: random unroll depth, random starting state, and backprop through only the last passes.
- Our `inject` already keeps the input in view each pass, which is Bansal's "recall" (SUGGESTED match).

**Fit.** Changes only the training loop and adds no parameters. Backprop through the last k = 4 passes only, so a 5090 run stays at about 296 cost (~$2 per arm).

**First experiment (card).** Change: 353 plus progressive loss plus random starting state. Twin: 353 as it is. Both are trained on **1-2 steps only** (no 3-step items at all). Fresh blind panel of 3-step items, built after the recipe is frozen, scored at 6, 12, 24 and 48 passes.
- **Pass:** 3-step ≥ 12/30 at the best pass count ≤ 48. Score at 48 passes ≥ score at 12. 2-step ≥ 27/30. Answer agreement between two random starting states ≥ 95%.
- **Proved wrong if:** 3-step ≤ 3/30 at every pass count, or 48 passes scores below 12 (overthinking comes back).

**How it could fool us.** 3-step items built from the same row templates can be solved by pattern-matching templates. The panel generator needs chain relations the practice data never put next to each other.

## Idea 2. Build the thinking path and the stop decision separately; train the stop head last, frozen, and on correctness only

**What.** First train the loop to hold a usable answer at every pass. Use a fixed prior over which passes are scored (for example uniform over passes ≥ 2), not a learned halting gate. Only then add a small stop head. The rest of the network is frozen while it trains, and it predicts "is my current answer right?"

**Evidence.**
- Popescu et al. 2026 (arXiv 2607.20519), abstract, SHOWN in their synthetic tasks: a learned exit gate both picks the stop and re-weights which passes get trained, so it bends the path itself. Fixed-prior depth supervision gave difficulty-aware paths, and simple confidence readouts matched or beat learned gates on the compute-versus-accuracy trade-off.
- TRM (Jolicoeur-Martineau 2025, arXiv 2510.04871), SHOWN: a 7M, 2-layer recursive net trained its halt head with binary cross-entropy on "is the current answer correct".
- Geiping 2502.05171, SHOWN: stop when the change in the answer between passes (the KL between successive passes) falls below a threshold. No head is needed.
- PonderNet (Banino et al. 2021, arXiv 2107.05407), SHOWN: a geometric prior on halting made learned halting stable on parity extrapolation.

**Keeping the stop head from becoming a shortcut (UNTESTED design).**
- **(a) What it can see.** The stop head reads only signals about how the thinking is going: how much the state changed since the last pass, the answer's entropy, and the KL to the previous pass. It never sees the question header. Otherwise it can simply count the filled relation slots ("3 slots, so stop at pass 3"), which is a surface rule and says nothing about 4 steps.
- **(b) No say over training.** Train it with the network frozen (stop-gradient), so it can't reshape the path.
- **(c) Stop threshold set with a guarantee.** Choose the threshold on a held-out practice split using the risk-control method in CALM (Schuster et al. 2022, arXiv 2207.07061, SHOWN for early exit in language models): exiting early must cost ≤ 1 point of accuracy against running all passes.

**First experiment (card).** Change: stop head per (a)-(c) on top of the Idea 1 winner. Test: a counterfactual panel.
- Chains that break at hop 1 (a fact is missing, so the right answer is "I don't know") but still show 3 relations in the header.
- Chains padded with 30-40 distractor rows but the same number of steps.
- **Pass:** broken chains stop ≥ 1 pass earlier on average than complete 3-step chains. Stopped-early accuracy is within 1 point of full-depth accuracy. The stop pass correlates more with "answer settled" than with slot count (partial correlation ≥ 0.3).
- **Proved wrong if:** the stop pass is the same for broken and complete chains (the head is counting slots).

## Idea 3. Stop decision in the GRPO practice phase, with its own normalisation and no cost for thinking yet

**What.** If sleep's RL phase ever pays a price per pass, the stop action gets its own advantage normalisation, separate from the answer's. Early nights charge nothing for thinking.

**Evidence.**
- Thinkless (Fang et al. 2025, arXiv 2505.13379, NeurIPS), SHOWN: with plain GRPO the think/no-think control token collapsed. Splitting the control-token loss from the answer loss ("decoupled GRPO") fixed it.
- Stochastic depth from a learned stop policy (arXiv 2606.29983), abstract, SHOWN: lowered run-to-run spread when extrapolating on binary addition and Dyck-1, but did not guarantee the right algorithm.

**Reward-hacking risk specific to our reward.** Honest "I don't know" pays +0.3 (runner docstring). A pass cost could therefore teach "stop early and say I don't know" on hard-but-answerable items. UNTESTED rule: charge compute only on correct answers, and track the rate of "I don't know" when the fact *was* present as a hard fail line.

**First experiment.** Only after Idea 2 passes. Change: add a 0.01-per-pass cost with decoupled normalisation.
- **Pass:** mean passes drop ≥ 25% with blind accuracy within 1 point.
- **Proved wrong if:** "I don't know" with the fact present rises by ≥ 2/30.

## Idea 4. Sleep spends extra thinking, and daytime keeps what it found

**What.** At night there's no latency limit. For day items the reasoner got wrong, re-run it at 4× the passes from several random starting states. Keep only answers the code checks as right, and train on them at the normal daytime pass budget. The deep night-time search becomes daytime skill.

**Evidence.**
- SUGGESTED by Geiping (more passes help on harder items) and Bansal.
- The self-improvement loop of Lee et al. is already in round 1, so don't count it twice. What's new here is using *depth* as the search tool, not the creative generator.

**Fit.** Inference only, about minutes of GPU time. Episodes go into the planned 40% cap for model-made data.

**First experiment (card).** Change: one night of deep re-solve on the day's 2-step failures only.
- **Pass:** fresh blind 2-step +3/30 over a twin given the same number of generic practice episodes (this matches 363's twin (b)).
- **Proved wrong if:** the gain appears only on re-solved items and not on the blind panel (it memorised them).

**How it could fool us.** Day items that resemble the panel. Build the panels only after the freeze, from fresh facts.

---

## Village and agent (keep separate; after card PASSes only)

UNTESTED: "never settled by the maximum pass count" (KL still high) is a natural **"I'm stuck"** signal for handing the problem to the creative generator. In the village, the thing to measure is whether that hand-off fires on items the reasoner truly fails (precision ≥ 0.8 on a blind set). Card scores are not evidence for this.

## For Ben (plain language)

Right now the reasoner either can't think longer usefully, or doesn't know when to stop.
- **Idea 1:** train it so its thinking settles on the same answer however it starts. Papers show that kind of net keeps getting better with more thinking time.
- **Idea 2:** build the "stop" button last, and let it look only at "has my answer stopped changing?" If it can see the question, it will just count words.
- **Idea 3:** if we ever charge for thinking, watch that it doesn't dodge by saying "I don't know".
- **Idea 4:** at night, think 4× longer on yesterday's misses, and train on the answers the checker confirms.

One snag first: the question format holds only 3 steps, so "longer chains than practised" means practising 2 and testing 3 until that's fixed.

Sources:
- [2202.05826](https://arxiv.org/abs/2202.05826)
- [2211.09961](https://arxiv.org/abs/2211.09961)
- [2502.05171](https://arxiv.org/abs/2502.05171)
- [2510.04871](https://arxiv.org/abs/2510.04871)
- [2607.20519](https://arxiv.org/abs/2607.20519)
- [2606.29983](https://arxiv.org/html/2606.29983v1)
- [2505.13379](https://arxiv.org/abs/2505.13379)
- [2409.15647](https://arxiv.org/abs/2409.15647)
- [2502.10954](https://arxiv.org/abs/2502.10954)

Also cited, from memory without re-checking the page: 2107.05407, 2207.07061, 2305.19466.

Files read:
- /home/user/learner/scripts/claude_rsn294_core.py (lines 395-510)
- /home/user/learner/scripts/claude_rsn294_run.py
- /home/user/learner/design/v3/30-modes/360-sleep-plan.md
- /home/user/learner/design/v3/30-modes/353-loop-no-step-embedding.md