# Sleep round 2: synthesis of 5 reports, ranked (2026-09-25)

Labels: SHOWN = a paper's result, or checked in repo code. SUGGESTED = argued. UNTESTED = our idea. Many citations were checked at abstract level only or cited from memory by the reporters (Kuo 2606.29983 and Popescu 2607.20519 are abstract-only). Treat every SHOWN as "the paper says so", not "it will work here".

## A code check that changes the ranking

Two reports (amortize, dreams) explain the 0/30 on 3-step chains the same way: every one of the 8 tries fails, so the GRPO advantage `(R-mean)/(std+1e-4)` is zero (run.py:110, SHOWN). **That is not the main cause today.** `COPY_KINDS` and `ALL_KINDS` (run.py:42-43) leave out `value3`. It appears only in scoring (run.py:219). The 296 and 353 runners reuse this runner through runpy. So the 294 → 296 → 353 line never trains on a 3-step item, and 0/30 is a zero-shot extrapolation result (SHOWN). The zero-gradient problem only starts once 3-step items join RL, so it drops to #5.

Two other code facts limit every "longer than practised" test (SHOWN, core.py):
- `MAX_HOPS = 3`, and each hop has its own position slot. A 4-step question cannot be encoded.
- The answer head reads only the last pass.

Until those change, extrapolation means: train on 1-2 steps, test on 3.

## 1. Top 5 new ideas

### #1 Minimal-pair twins, with a shortcut-hunting probe first (start now)
**What.** Each practice puzzle comes with 2-4 twins made by code, each changing one row: delete a hop row (answer becomes "I don't know"), change a hop value (answer changes), add a near-miss row, or reorder rows (answer stays the same). A shortcut gives the same answer across a pair, so it loses reward on one of them.
**Evidence.**
- Counterfactually edited data reduced reliance on spurious cues (Kaushik, ICLR 2020, 1909.12434). SHOWN.
- It was no better than the same amount of ordinary data on NLI (Huang 2010.04762). SHOWN. The evidence is mixed.
- Adversaries rewarded by regret gave more robust transfer (PAIRED 2012.02096). SHOWN.
**First experiment.**
- Step A ($0, CPU): a bandit over about 8 of 296's `_style` distractor knobs, run against the 296 checkpoint for 2,000 samples. Every item is re-solved by `solve()`.
  - Pass: some setting drops accuracy by at least 30 points.
  - Wrong: no setting drops it by more than 10. That means distractors are not the weakness; skip Step B.
- Step B (about $2): twins against a twin model given the same number of unpaired episodes. One edit type is held out for the panel only.
  - Pass: blind flip consistency (both answers of a pair right) at least +15 points; false answers on missing-hop items at most half the twin's; 2-step not below the twin.
  - Wrong: practice pair accuracy at least 95% but blind flip consistency within 5 points of the twin.
**Could fool us.** Twins made by our own code share its quirks. The probe will find generator bugs before real weaknesses.

### #2 Path-independent loop training (progressive loss plus random start) (blocked on 353)
**What.** Run a random number of passes with no gradient, starting from a perturbed state. Then run a few passes with gradient and score only the end. The block cannot count passes, so it has to learn a step that is safe to repeat, and extra passes should stop hurting.
**Evidence.**
- Recurrent nets trained this way extrapolate to much larger mazes and prefix sums with no "overthinking" (Bansal, NeurIPS 2022, 2202.05826). SHOWN.
- Generalisation to harder problems tracks path independence (Anil, NeurIPS 2022, 2211.09961). SHOWN.
- Random unroll depth works at 3.5B (Geiping 2502.05171). SHOWN.
- The existing per-pass `inject` plays Bansal's "recall" role. SUGGESTED.
**First experiment (about $2 per arm).** 353 plus this change, against 353 alone. Both train on 1-2 steps only. The panel is fresh blind 3-step items scored at 6, 12, 24 and 48 passes.
- Pass: 3-step at least 12/30 at some pass count; score at 48 passes at least the score at 12; 2-step at least 27/30; at least 95% answer agreement across two random starts.
- Wrong: 3-step at most 3/30 at every pass count, or 48 passes scores below 12.
**Could fool us.** It could settle stably on a shortcut. The panel must use relation pairs the practice never put next to each other.

### #3 One hop per pass, then hold (free per-pass labels from the solver) (blocked on 353 and needs a readout at every pass)
**What.** The exact solver already knows which row each hop uses. Train the row-pointer head so pass t points at the row for hop min(t, k), and supervise the answer at every pass from k onward, so extra passes cannot change it. This also gives the thinking-stop token its label: the first pass after which the answer is right and stays right. That label is also amortize's hindsight stop label, merged in here.
**Evidence.**
- Intermediate hints help on some algorithmic tasks and not others (CLRS 2205.15659; Ibarz 2209.11142). SHOWN.
- Easy-to-hard extrapolation by adding passes (Schwarzschild 2106.04537; Fan 2409.15647). SHOWN.
- The "hold" rule. UNTESTED.
**First experiment (about $2).** Against the same model and data without the per-pass loss. Train on 1-2 hops only.
- Pass: blind 3-step at least 15/30; 2-step at least 27/30.
- Wrong: practice pointer accuracy at least 95% while blind 3-step is at most 5/30.
**Could fool us.** It could count the filled relation slots to guess k instead of following the chain. Check on chains that break at hop 1 but still show 3 relations.

### #4 Count kinds of chain, not wins: held-out skeleton dose-response (start now on the 296 plain model)
**What.** A skeleton is a chain's order of relations plus its final operation, with all names removed. Train 3-step items built from 1, 4 or 16 skeletons, then test on skeletons never seen that use only familiar pieces. This measures directly whether the model learns the rule or the template, and how many distinct kinds sleep needs to collect.
**Evidence.**
- Gains grow with the number of distinct reasoning paths, not raw sample count (RFT 2308.01825). SHOWN.
- Transformers fail systematic out-of-distribution composition (Wang 2405.15071). SHOWN. The authors' suggestion that weight sharing across layers helps is SUGGESTED.
**First experiment (about $2; the model has never seen `value3`, so this is also the plain "add 3-step to training" baseline).**
- Register the held-out skeleton list before training. No held-out skeleton may share a 2-relation prefix with a training one.
- Pass: held-out accuracy rises with dose, and at 16 skeletons reaches at least 50% of in-skeleton accuracy.
- Wrong: in-skeleton at least 25/30 while held-out stays at most 5/30.
**Could fool us.** Held-out skeletons that are only half new. Drift of the generator toward panel skeletons.

### #5 Break all-fail ties once 3-step items are in RL (after #4 adds them)
**What.** Once hard items join GRPO, pick practice where the pass rate is in the middle band rather than uniformly. When all 8 tries still fail, swap in one checked solution with a capped probability ratio.
**Evidence.**
- Difficulty filtering: GRPO improvement is bounded below by the variance of success across tries (2504.03380). SHOWN.
- Allocating more samples to hard queries beat plain rejection tuning (DART-Math 2407.13690). SHOWN.
- Mixing off-policy traces into RL groups: +7.0 across 6 math benchmarks (LUFFY 2504.14945). SHOWN.
**First experiment.**
- $0 first: on the #4 checkpoint, sample 8 tries on 3-step training-side items and log the share of groups with zero reward spread. If it is below 30%, stop: ties are not the bottleneck.
- Otherwise (about $2): uniform sampling against middle-band sampling, 3 seeds. Pass rates are measured on a training-side probe, never the panel.
  - Pass: fresh 3-step +4/30; 1-2 step drops at most 1/30.
  - Wrong: the share of groups with nonzero spread rises but blind 3-step does not.
- Win injection comes only after that, with a plain supervised-on-gold arm. On cards the "win" is the generator's gold answer, so injection must beat that arm to count.
**Could fool us.** The difficulty probe sharing templates with the panel.

## Dropped or deferred
- **Stop-head design.** Train it last on a frozen network. It sees only settling signals (state change, entropy, KL between passes), never the question header. Set the threshold with CALM (2207.07061). Give the stop decision its own GRPO normalisation (Thinkless 2505.13379). Charge for passes only on correct answers, because an honest "I don't know" pays +0.3 (run.py docstring, SHOWN) and a pass cost could teach dodging. This is the right design, **gated** on more passes helping by at least 3/30.
- **Deep re-solve of the day's misses at night.** Gated on the same condition.
- **Relabelling failed chains (HER).** On cards the generator can already make any question, so relabelling adds nothing there. It is village-only, capped at 25%.
- **Operator library (DreamCoder).** It is covered by #4's held-out operator pairs, and a 30M network cannot call library functions.
- **Forgetting ideas.** These are only meaningful once there are nights to forget:
  - the multi-night scorecard ($0, build it before 363's multi-night runs);
  - a slow averaged copy (computed afterwards, free);
  - shrink-and-perturb (Dohare, Nature 2024), deferred until a 6-night run shows plasticity loss;
  - KL-to-yesterday as a forgetting meter.
- **Similarity-weighted replay.** Only if old skills drop by at least 5 points.
- **Grokking / high weight decay.** Dropped. Fresh data every step is not the finite-data setting where grokking was shown.

## 2. Blocked vs can start now
- **Start now ($0 or the 296 plain model):**
  - #1 Step A probe ($0), then Step B;
  - #4 skeleton dose-response;
  - #5 zero-spread count ($0, after #4);
  - the multi-night scorecard ($0).
- **Blocked on 353 passing its copy phase:** #2, #3, the stop head, deep re-solve, the averaged copy, shrink-and-perturb, and the KL anchor.
- **Also blocked on code changes:** #3 and the stop head need a readout at every pass. Any 4-step test needs a shared hop role embedding in place of the per-position slots (one change, its own job).

## 3. Ownership
- **Reasoner training recipe (sleep research thread):** #1 Step B, #2, #3, #4, #5, the stop head.
- **Nightly sleep cycle (Fix-sleep thread, plan 360):**
  - #1's flip-consistency score as a line in the 364 self-check;
  - "I don't know when the fact was present" as a hard-fail line in 364;
  - the multi-night scorecard, and the averaged copy as the answering model at commit;
  - the placebo arm and held-out families in 363 (see section 4);
  - relabelling and deep re-solve (village, later);
  - #5's middle-band sampling as the practice-school scheduler, once the card test passes.

## 4. How these sharpen plan 360 and round 1
- **363 twins (a) and (b).** Add a placebo arm P: the same pipeline with rewards shuffled across the batch. Random rewards "improved" Qwen2.5 on math (2506.10947, SHOWN); the gain vanished on a clean synthetic benchmark (2507.10532, SHOWN).
  - Wrong: P reaches at least 60% of sleep's gain.
  - Also send 25% of structure types (hashed from kind + relation path + step count) to the panel only.
  - Report pass@1 and pass@64. RL can narrow pass@k (2504.13837, SHOWN), so a win at pass@1 with a loss at pass@64 means sharpening, not a new skill.
- **Practice-school ladder 2 → 3 → 4.** 4-step cannot be encoded yet (`MAX_HOPS = 3`). Training on 3 also removes the only extrapolation test, so keep one arm that trains on 1-2 steps and tests on 3.
- **Wins plus variants, capped at 40%.** Count distinct skeletons, not wins (#4). The cap stays.
- **Self-check (364).** Add flip consistency and the "I don't know with the fact present" line. The current gate re-asks the day's questions, which are practice.
- **Round 1 hint ladder and STaR stall.** #3 supervises the internal state at each pass rather than putting hints in the input, so it is a different mechanism. B-STaR (2412.17256, SHOWN) says to log practice diversity each night to catch the stall early.

## 5. For Ben
1. Big finding: the reasoner has never practised a 3-step question, so 0 out of 30 is a test of something it was never taught.
2. First, cheap: build puzzle twins that differ by 1 fact, so a lazy trick gets one of each pair wrong.
3. Second, cheap: teach 3-step with 1, 4 and then 16 kinds of chain, and test on kinds it never saw, to check it learns rules and not templates.
4. Once the loop model can learn at all, train it so thinking longer never hurts, with 1 step of the chain per thinking round.
5. Each test costs about 2 dollars or nothing, and each has its pass mark written down before it runs.
6. Sleep only counts if it beats 3 lookalikes: no sleep, plain extra practice, and "sleep" with scrambled grades.

Files checked: /home/user/learner/scripts/claude_rsn294_run.py (lines 42-43, 110, 127, 219), /home/user/learner/scripts/claude_rsn294_core.py (lines 38, 45, 154), /home/user/learner/scripts/claude_rsn296_run.py, /home/user/learner/scripts/claude_rsn353_run.py, /home/user/learner/design/v3/30-modes/360-sleep-plan.md