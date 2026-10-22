# Adversarial review: MIR-style replay ("practise the old puzzles the next update would damage")

Claude, 2026-09-27, answering Ben's adversarial-review prompt. The prompt assumed a reviewer with no repo access. I do have access, so I checked the details it listed as missing. Labels used throughout:

- **[prompt]**: a number from Ben's prompt.
- **[repo]**: read from code or saved results in this repo. Paths are in the source list at the end.
- **[paper]**: read from the primary paper or its official code.
- **shown / suggested / untested**: how strong a claim is.

The small puzzle reasoner is the only system discussed. Nothing here concerns the village model or any language model.

---

## 0. Three facts the prompt did not have, and why they matter

1. **Grid forgetting is concentrated in grids with many blank cells (shown [repo]).** I re-scored the saved per-puzzle answers from both replay-scheduling experiments (script: `scripts/claude_mirreview_grid_forgetting.py`, read-only). My recomputed scores match the saved results exactly for every arm, seed and phase. Among 5×5 test grids solved after phase A, the share lost by the end of C was:

   | blank cells | baseline (seeds 41–46) | late replay (seeds 41–46) |
   |---|---|---|
   | fewer than 10 | 4/240 (2%) | 1/240 (0.4%) |
   | 10–12 | 35/315 (11%) | 12/315 (4%) |
   | 13–15 | 108/272 (40%) | 55/270 (20%) |
   | 16 or more | 201/352 (57%) | 114/349 (33%) |

   The blank count alone separates lost from kept grids with an AUROC of about 0.80 in all four arms. (AUROC is the chance that a random lost puzzle has more blanks than a random kept one. 0.5 means no signal, 1.0 means perfect.) Within a seed, the two arms lose the same puzzles 2.2× more often than chance. After matching on blank count, that ratio falls to about 1.3. **So there is a real "which puzzles" target, but most of it is plain difficulty.** A virtual update isn't needed to find difficulty.

2. **Late replay's final gain came with a deeper dip in the middle (shown [repo]).** Mean grids5 by phase was 196.5 → 177.0 → 138.8 for the baseline and 195.7 → **125.8** → 167.0 for late replay. One seed fell to 89 after B, then recovered to 159. The grid skill was not erased. It came back when grid practice increased during C.

3. **Details the prompt listed as missing (shown [repo], replay runs in `artifacts/codex-autoroute-20260927/`):**
   - **Loss and rounds.** Each step's loss, averaged over the gradient rounds, is the cross-entropy over all answer cells in the batch plus 0.5 × a stop-head term. The stop-head target is whether the whole puzzle is right at that round. Total rounds are drawn from 1 to 16. The gradient covers the last 1 to min(total, 6) rounds, about 3 on average.
   - **Optimizer.** AdamW with β = (0.9, 0.95), weight decay 0.1 and gradient clipping at 1.0. The optimizer is fresh each phase, with a 100-step warm-up and then cosine decay to zero.
   - **Stopping.** The answer is read at the first round, from round 3 on, where the stop head says > 0.5 and the answer has not changed for three rounds. Otherwise it is read at round 48.
   - **Batches.** Every batch has one size, drawn before the puzzles are made. Grid batches are 4×4 or 5×5; sum batches have 1 to 4 digits.
   - **Where grids come from.** Training and replay grids are re-dressed copies of **3,000 fixed base puzzles per size**, made at the start of the run. Re-dressing means rows and columns shuffled, sometimes transposed, and symbols renamed. Test grids are new bases. Every grid has a unique solution.
   - **Addition after mazes.** Final sums4 is known. It was 193.0 (baseline) and 196.7 (late) in the timing test, and 193.8 and 192.3 in the size test. No seed fell below 184.
   - **Stopping losses.** After C, about 9–10 of the 200 grids per seed were solved at some round but read at the wrong one. Grids that were correct at any round numbered 148.5 (baseline) and 176.2 (late); own-stop scores were 138.8 and 167.0. The mean round at which grid answers were read was about 20 (baseline) and 12 (late). Training never goes past round 16.
   - **Repeatability.** Phase A was not bit-for-bit repeatable across arms on the Mac GPU. For example, seed 61 ended A at 192 in one arm and 194 in the other.

---

## A. Is the argument actually supported?

### A1. What the supplied experiments establish

- **shown:** without replay, grids collapse from about 199 to 0 after addition training [prompt].
- **shown:** with full replay, grids survive partly. Final grids5 is about 128–144 against about 196 after A [prompt].
- **shown:** holding the total at 325 grid replay batches, moving them later raised final grids5 by 28.2 and T by 30. T was higher in all 6 paired seeds [prompt]. Per-seed gains in grids5 were +27, +29, +41, +34, +13 and +25 [repo].
- **shown:** giving every grid replay slot to 5×5 grids raised final grids5 by 12.2 and T by 8.8. T was higher in only 3 of 6 seeds. Per-seed grids5 gains were +1, +30, −6, +16, +24 and +8 [repo]. This is weak and noisy.
- **not established by any experiment:** anything about choosing replay examples by predicted damage. No experiment selected examples by their loss or by a predicted change in loss.

### A2. What the literature establishes, in its own settings (verified against the paper and its official code)

MIR (Aljundi et al., NeurIPS 2019):

| | MIR as published | This proposal |
|---|---|---|
| Setting | Online, single pass. Image classification where new classes arrive over time and one output layer covers every class seen so far. | Offline phases of 1,500–2,500 steps. Whole-grid exact answers. |
| Old data | A stored buffer of real past examples (reservoir sampling) | Freshly generated old-kind puzzles. Grids come from a fixed stored pool of 3,000 bases per size. |
| What retrieval can choose | Any stored example, so in effect **which old classes** to rehearse | A fixed count per old kind, and each batch is one size. Only **which same-size puzzles** is left to choose. |
| Virtual step | One plain SGD step on the incoming batch, at the training learning rate (0.05 or 0.1) | Not fixed. The real optimizer is AdamW with momentum, clipping and a warm-up/cosine schedule. |
| How the choice is used | Retrieved examples are trained **in the same SGD step** as the incoming batch, so their gradients directly offset the damage | Separate replay steps, one every 5–20 steps |
| Candidates | 50 random from the buffer; the top 10 are kept (20%) | Not fixed |
| Score | Loss after minus loss before. On MNIST they used a variant that compares with the best loss the example ever had, which needs stored history. | Loss after minus loss before |

Results [paper]. The score is final accuracy (higher is better); forgetting (lower is better) is in brackets.

- **Split MNIST:** ER 82.1 [15.0], MIR 87.6 [7.0].
- **Permuted MNIST:** ER 78.9 [3.8], MIR 80.1 [3.9]. No gain on forgetting.
- **Split CIFAR-10**, by memories per class:
  - 20: ER 27.5 [50.5], MIR 29.8 [50.2]
  - 50: ER 33.1 [35.4], MIR 40.0 [30.2]
  - 100: ER 41.3 [23.3], MIR 47.6 [17.4]
- **MiniImagenet:** ER 24.7 [23.5], MIR 25.2 [18.0].
- **5 updates per incoming batch** (CIFAR-10, 100 memories per class): ER 42.4, MIR 49.3. Both methods got the extra updates.

In the ER-MIR experiments I found **no comparison with choosing the examples with the highest current loss**, and no ER run given MIR's extra compute.

The gains were largest in class-incremental splits. There, one plausible reading is that part of the forgetting is the shared output layer favouring new classes, and retrieval can target the specific old classes being hurt. (**suggested**; this is my reading, not the paper's claim.) The gains were smallest on Permuted MNIST, where every task shares the same labels.

Other papers:

- **Prabhu et al., CVPR 2023** (ImageNet2K, Continual Google Landmarks). Selection strategies that cost extra forward passes (Max Loss, Uncertainty, KMeans) were charged for them with fewer training iterations. On that basis they did worse than simple uniform or class-balanced sampling. MIR itself was not in that comparison. It is a different scale and setting, but it is a warning that "smart selection" often stops helping once its compute is counted.
- **Toneva et al., ICLR 2019.** In ordinary single-task training, a large number of examples are never forgotten once learned, and which ones is stable across seeds. The examples forgotten most often are those with wrong labels or unusual, hard-to-classify features. Here the generators check every answer, so wrong labels are not a risk. Atypical (very hard) puzzles are. The same-puzzle overlap between arms in section 0 fits their finding that forgetting hits consistent examples.

### A3. What is only inference about this model

That one virtual step here predicts which old puzzles will be lost over the rest of the phase. That selecting them beats random or difficulty-based choice. That this survives AdamW, looping and learned stopping. All **untested**.

### A4. Untested

Everything about predicted-damage selection in this model. Also the whole prompt-side argument from the timing result (see C1).

### The strongest fair case for the proposal

- The replay budget is tiny. There are 325 grid batches in the 4,000 steps of B and C, about 8%. Random replay wastes most of it: grids with fewer than 10 blanks are almost never lost (0.4–2%) **[shown, repo]**, yet they are about 20% of candidates. MIR's founding argument ("retraining on examples that aren't being hurt is wasteful") fits this measured fact.
- There is a real within-kind target: lost grids are predictable, and the same puzzles tend to be lost across runs **[shown, repo]**.
- Candidates are generated with checked answers, so hard-example selection won't chase mislabelled data. The known failure mode from Toneva et al. is largely absent.
- It adds no weights. It needs no task label at test time (it runs only during sleep). It changes one thing. It is cheap to test on a free CPU.
- A plausible mechanism: maze training may re-tune the loop dynamics that long deduction chains rely on. Many-blank grids need the longest chains, and the slower stopping of degraded grids (a read round of about 20 against about 12) fits this. A damage score could find exactly those grids. **suggested, untested.**

### The three most serious weaknesses

**1. It pulls the wrong lever for the evidence in hand.** The one big, reliable effect so far (+28, 6 of 6 seeds) came from putting more grid practice into the phase where grids are being damaged, at a fixed total. The late arm fell to 126 after B and recovered to 167. So the final grid score is driven mainly by **dose and recency within the last phase**, and grid skill comes back quickly with practice. The proposal holds dose and timing fixed and only reshuffles which same-size grids fill the same slots. At best that works on a smaller effect.

**2. It removes the parts of MIR that plausibly produced MIR's gains.**
- (a) MIR could choose among old classes. Here the per-kind allocation is fixed and each batch is one size, so only within-kind, same-size choice is left. The main thing that varies there is difficulty.
- (b) MIR trains the retrieved examples in the same SGD step as the damaging batch. Here replay is a separate AdamW step taken 5–20 steps apart.
- (c) MIR's one-step SGD preview is an honest forecast of its next update. With AdamW (β1 = 0.9), clipping and a cosine schedule, a one-step preview is a different object (see B5).

Even in MIR's own paper the gains were uneven: no forgetting gain on Permuted MNIST, and almost none on CIFAR-10 with 20 memories per class.

**3. The score will probably collapse to "current difficulty plus noise".** For a small step Δθ, the change in loss on puzzle x is about ∇ℓ(x)·Δθ: the dot product of that puzzle's gradient (the direction that would lower its loss) with the update. For cross-entropy, a puzzle's gradient is larger the more wrong the model is. So the damage score is (how wrong now) × (how opposed its gradient is to the update). If maze training hurts all hard grids in roughly the same direction, the second factor is similar across grids and damage ≈ current loss. The measured concentration in 0 (AUROC 0.80 from blank count alone) says difficulty is most of the signal. A batch of 64 new puzzles is also a noisy stand-in for the next 5–20 steps of drift.

### Does a one-step loss increase identify what is forgotten hundreds of steps later?

Probably only partly, and in three ways that can mislead:

- **Temporary noise.** One batch's gradient differs a lot from the average drift. A puzzle can rank high because of one batch's quirks, and that ranking changes on the next batch.
- **Difficult examples.** As shown above, the score scales with current error. High damage then mostly means "hard". The cheap control is to select by current loss.
- **Conflicts worth accepting.** Some damage comes from shared weights being re-purposed for mazes. Defending every such grid can slow maze learning, so the maze guardrail must be kept. The reverse also happens: a grid's round-16 loss can rise while it is still solved by round 20 and read correctly by the stop rule. That is damage that doesn't count.

What matters for the final score is what happens during the last few hundred steps of C, which is the lesson of the timing result. A forecast one step ahead doesn't reach that far.

---

## B. Could the selection signal mislead in this model?

**B1. Repeated rounds and truncated gradients.**
- The virtual step's direction depends on its random depth draw (1–16 rounds, gradient through the last 1–6). Early-round and late-round errors pull the weights differently. If the virtual step uses a different draw or batch from the real next step, part of the ranking is that draw.
- Weight changes compound through the shared blocks. A change can leave the round-8 answer intact and break the round-20 answer. Grids after C are read at about round 20 (baseline), and training never goes past 16.
- Fix: the virtual step uses the exact next new-kind batch and round draw. Before/after losses are measured at a fixed depth of 16 rounds on identical puzzles.

**B2. Learned stopping.** About 9–10 grids per seed are lost to reading the wrong round, not to failing to solve. Answer-cell loss at a fixed depth cannot see stop-head damage. Adding the stop-head term to the score mixes two different things into one ranking. Fix: score on answer loss only (decided in advance), and log stop-head damage and the any-round/own-stop gap separately.

**B3. Randomness and precision.**
- With identical puzzles, fixed depth and no-grad passes, the before/after difference is deterministic apart from the virtual batch. That leftover noise should be measured by scoring the same pool with two different virtual batches.
- The learning rate is about 1e-5 at the start of warm-up and about 1e-7 in the last cosine steps. Loss changes there fall toward FP32 rounding, and the ranking becomes noise.
- Fix: use a fixed virtual step size of 1e-3, the peak learning rate. The first-order ranking does not depend on step size.

**B4. Whole-puzzle accuracy against cell loss.**
- A grid fails if any single cell is wrong. The training loss averages over cells, and the number of blanks varies widely.
- A summed per-puzzle loss favours many-blank grids by construction. A per-cell mean dilutes a one-cell failure in a big grid. Neither measures "about to flip".
- Puzzles that are already wrong can score high damage but cannot be "forgotten".
- Fix: pre-declare the per-cell mean. Record the blank counts of the chosen grids and what fraction of them are currently solved.

**B5. AdamW state.**
- With β1 = 0.9, a real step is about 90% the momentum from roughly the last 10 batches and about 10% the new batch. Clipping at 1.0 shifts that mix, and the fresh optimizer at each phase start takes large early steps.
- A plain-SGD virtual step (MIR-faithful) asks "what does this one batch do?". A virtual step on a copy of the AdamW state asks "where is the optimizer heading?". They rank puzzles differently.
- This is the most important unfixed choice. I choose the AdamW copy, because it is what actually happens and momentum is the lasting drift. Clipping and weight decay are included, and the step size is fixed as in B3. The SGD version is logged on the probe set for comparison only.

**B6. Fresh candidates against stored examples.**
- MIR scores stored real examples. Its better MNIST variant compares against each example's best-ever loss, which fresh puzzles don't have.
- Here "fresh" grids are really disguised copies of 3,000 stored bases per size, and the tests use new bases. Selection may rehearse the same few hard bases again and again, improving memory of those bases rather than the general skill.
- Fix: log the base ID of each chosen grid and report how often bases repeat. Score only on new-base tests (already the case).

**B7. Representative performance against over-selection.**
- Choosing the top 25% by damage will concentrate on hard grids. That fits the data, since easy grids are rarely lost.
- It can starve middle-difficulty grids, and it can starve 4×4 grids. 4×4 retention has **never been measured**: the size-targeting run gave 4×4 zero replay and did not score it.
- Fix: keep the per-batch size draw random, as now, so size mix can't change. Add a grids4 test.

**B8. The learned front end.** The front end mixes 4 learned context rows based on the average input embedding. Its agreement with the true kind was only 204–427 of 600 **[repo, report-only]**. If part of grid forgetting is grids drifting toward another kind's context, that hits all grids alike, and per-puzzle ranking cannot target it. Fix: log grid inputs' context weights after A, B and C.

### Which open decisions are essential and which are harmless

Essential, because each changes what the score means:

1. Virtual optimizer: SGD, or a copy of AdamW including clipping.
2. Virtual step size under warm-up and cosine decay.
3. Which new-kind batch and round draw the virtual step uses, and **scoring at the replay step itself**. The provisional recipe selects "for the next scheduled replay batch", which could be 5–20 steps stale.
4. Scoring loss, depth and normalization: answer loss only, 16 rounds, per-cell mean.
5. Candidate pool size, which sets how strongly selection pushes.
6. Keeping the size draw random. Otherwise it quietly repeats the 5×5-only experiment.

Harmless: how the copy is implemented, tie-breaking, whether L and M share the "before" pass, and the exact probe-set size.

---

## C. Is there a cheaper explanation or competitor?

**C1. The timing result does not motivate example selection.** It shows that *when* replay happens (dose in the damaging phase) matters a lot. The late arm's dip-and-recovery shows grid skill is quickly relearnable. That supports allocating replay better in time and by kind. It is closer to MIR's original lever (which old classes) than to the proposal, which fixes the per-kind allocation. The evidence that does support within-kind selection is new (fact 1 in section 0), and it points first to **difficulty**.

**C2. Competitors, from cheapest:**
- **(i) Current-loss selection from the same pool (L).** It costs one forward pass per candidate and no virtual step. The data say it has a real target. **Essential now.**
- **(ii) Random choice from the same pool (R).** This is ordinary replay, and it is the baseline.
- **(iii) More, or later, grid replay.** This changes allocations, so it is a separate experiment.
- **(iv) Compute-matched replay (R given MIR's extra compute as more replay steps).** Needed only if MIR beats both R and L, to answer "is it worth its cost?" rather than "is the signal real?".

**C3. Separating "predicted damage is useful" from "extra exposure or compute".**
- Trained-on data are equal across arms (same replay count and kinds), so "extra old-puzzle exposure" is not the confound.
- The confound is **information from inspecting more candidates**. L inspects the same 256 candidates as M, without the virtual step, so **M against L is the test of the damage signal itself**.
- M against R alone would be uninterpretable.

**C4. Baseline: the late schedule.**
- It is the best recipe on the registered metric (6 of 6 seeds). The question that matters is whether selection adds anything on top.
- On the original schedule, MIR might look good merely by partly making up for too-thin grid practice in C, which timing already fixes.
- There is headroom: about 33 points below 200.
- Rerun it; don't reuse old numbers. Its 498.67 was chosen on reused development sets.
- Caveat: the late schedule buys its final score with a deeper dip after B. Over many sleeps, every phase is some earlier phase's middle. Record grids5 after B as well. MIR also acts during B, so if it works, it should **raise grids5 after B**. That is a pre-declared secondary prediction.

---

## D. The smallest informative experiment

One experiment in two stages. Stage 1 costs almost nothing and can kill the idea before any new training arm runs.

**Fixed in every arm:**
- Model: 1,646,750 weights, the learned front end, loss, round sampling, stop rule.
- Training: phases A 2,500 / B 2,500 / C 1,500 steps, batch 64, the optimizer and schedule as in fact 3 of section 0.
- **Late schedule:** B has 125 grid replay batches; C has 200 grid and 75 sums replay batches. Each replay batch's size is drawn at random first.
- Three separate random streams, identical across arms: new-kind batches, round draws, and candidate pools.
- **Phase A is trained once per seed and saved.** All arms branch from that checkpoint. This removes the Phase-A mismatch seen on the Mac GPU.
- New seed numbers, never used before.

**Arms (at every replay step, draw a pool of 256 old-kind puzzles of the drawn size):**
- **R:** train on a random 64 from the pool.
- **L:** train on the 64 with the highest current per-cell answer loss at 16 rounds.
- **M:** at the replay step itself:
  1. Copy the weights and the AdamW state.
  2. Apply one full AdamW step, with clipping and weight decay and a fixed step size of 1e-3, on **the exact new-kind batch and round draw the real run will use next**.
  3. Score every candidate as loss after minus loss before (per-cell answer loss, 16 rounds, identical inputs, no-grad).
  4. Train on the top 64 with the real optimizer, then throw the copies away.

**Stage 1: forecasting gate** (2 seeds, arm R only, training unchanged)
- At 10 evenly spaced replay steps in B and 10 in C, take a fixed probe set of 512 grids (half 4×4, half 5×5; never trained on). Compute:
  - current loss;
  - the M damage score using the next new-kind batch;
  - the damage score using a second, different batch;
  - the realized loss change on each probe grid by the next grid replay step, and by the end of the phase.
- Pass needs both of these, fixed now:
  - **Stable:** the median rank correlation (Spearman) between the two batches' damage scores is at least 0.5.
  - **Beyond difficulty:** at the next-replay-step horizon, Spearman(damage, realized change) minus Spearman(current loss, realized change) has a median of at least +0.10, and is positive at 28 or more of the 40 checkpoints.
- If either fails, stop. **This version** is rejected: "a one-step preview doesn't forecast this model's forgetting better than current loss."
- Report only: Spearman(damage, current loss), the end-of-phase horizon, answers flipping from right to wrong, the plain-SGD version of the score, and 24-round scoring on a subsample.

**Stage 2: graded test** (only if Stage 1 passes)
- Arms R, L and M × 6 seeds. The 2 Stage-1 R runs are reused only if a quick check shows the logging leaves the weights identical; otherwise they are rerun.
- **Pass marks, on the sealed fresh tests, per-200 scale:**

| Mark | Requirement |
|---|---|
| **P1: beats ordinary replay** | Final grids5, M − R: mean at least +10, and M > R in at least 5 of 6 seeds |
| **P2: beats difficulty-only selection** | Final grids5, M − L: mean at least +5, and M ≥ L in at least 4 of 6 seeds |
| Guardrail: sums4 after B | at least 195 (the original bar) |
| Guardrail: final sums4, after C | mean at least R − 3, and every seed at least 185 |
| Guardrail: final maze7 | mean at least R − 10 (the original bar) |
| Guardrail: final grids4 | mean at least R − 5 (new) |
| Guardrail: T | T = grids5 + final sums4 + maze7. M > R in at least 5 of 6 seeds |
| Report only | grids5 after B (predicted: M > R), grids6, sums6, the any-round/own-stop gap, stop rounds, context weights, what was chosen |
| Project bar (unchanged, graded separately) | final grids5 mean at least 180 and every seed at least 160 |

- **Verdict rules:**
  - **Supported (this version):** P1, P2 and every guardrail pass.
  - **Rejected (this version):** M − R below +3, or M − L at or below 0, or any guardrail fails.
  - **Otherwise inconclusive.** No extra seeds or tweaks afterwards; a changed version is a new registration.
  - A failure rejects *one-step, AdamW-preview, within-kind damage selection at a fixed allocation*. It does not reject replay selection in general.

**Power, honestly.** The paired seed-to-seed spread of final grids5 differences was about 9–14 in the two past replay tests **[repo]**. With 6 seeds, a true +10 effect clears "5 of 6" only about two times in three. Sharing phase A should help a little. More seeds would help more, but the number must be fixed before running.

**Fresh evaluation.**
- Before any run, generate and seal new test sets from never-used generator seeds: grids5, sums4 and maze7 at up to 1,000 each, and grids4, grids6 and sums6 at 400 each. Use as many distinct 7×7 mazes as exist and record the count, because past panels repeated mazes heavily.
- Use one set for all seeds and arms. Block the test items from every training and candidate stream. Commit the hashes.
- Score the sealed sets once, after all runs finish. The old development sets are used for monitoring only.
- Pool size, step size, depth and every threshold are fixed now, by reasoning. Nothing is tuned on development scores.

**Record:**
- Scores after A, B and C: own-stop, any-round and 16-round, plus stop rounds.
- For every replay step: size, pool statistics, the chosen puzzles' blank counts, current loss, damage and currently-solved fraction, grid base IDs, the learning rate, and the size of the virtual step.
- Grid inputs' context weights.
- Pass counts and training time per arm.
- Code hash and random-stream seeds.

**Total runs.**
- If Stage 1 fails: 2 Phase-A runs + 2 R runs.
- If it passes: 6 Phase-A runs + 18 B→C continuations, i.e. 18 full trajectories sharing 6 Phase-A runs.

**The four comparisons are not the same thing:**
- **Model size:** equal. The temporary copies are scratch space, not weights.
- **Training steps:** equal (6,500), with equal replay counts (400) and kind mix.
- **Data exposure:** trained-on examples are equal. L and M *inspect* 4× more old puzzles without learning from them. R draws from the same pools, so the generated data are identical.
- **Compute:** not equal.

**Compute estimate.** This assumes a backward pass costs about 2× a forward pass and ignores size differences. Count in "puzzle-rounds": one puzzle through one forward round.
- **Ordinary training step:** 64 × (8.5 forward + 2 × 3.0 backward) ≈ 930.
- **L, per replay step:** 256 × 16 = 4,096, about 4.4 training steps.
- **M, per replay step:** 2 × 4,096 + about 930 for the virtual step ≈ 9,100, about 9.8 training steps.
- **Over 400 replay steps:**
  - L adds about 1,760 step-equivalents (+27% of a run). That is 102,400 candidate rollouts.
  - M adds about 3,900 (+60%, roughly doubling phases B+C). That is 204,800 candidate rollouts plus 400 virtual forward/backward steps.
- **Stage-1 logging:** about +15% per R run.
- **Temporary memory:** copies of the weights (6.6 MB) and AdamW's two moment buffers (13.2 MB), about 20 MB.
- I give no wall-clock figure. Past trajectories logged about 9.5 minutes of training on the Mac GPU, but CPU speed is unknown.

**Do the old targets protect every old ability? No.**
- "sums4 after B ≥ 195" was met with 200 in every past run, so it guards nothing. Final sums4 is the real test of addition, and it is now a guardrail.
- grids4 was never measured, and it is now a guardrail.
- The dip after B, and the generalization sets grids6 and sums6, aren't graded. grids6 and sums6 weren't even scored in the front-end runs. They are reported here.
- The original bars are kept unchanged.

---

## E. Verdict: **needs a specific redesign first**

As written, the provisional recipe leaves open the choices that decide what its score measures (B5, B3, B1, B4). It has no current-loss control, so a win over ordinary replay would be uninterpretable. The redesign is small and specified above:

- Pin the six essential choices.
- Add L.
- Share phase A.
- Pass the cheap forecasting gate before any training arm runs.

After that, it is worth the small test. My prior, which is opinion: M most likely ties L, because the measured forgetting is mostly difficulty. If so, keep the cheaper L, and test it properly on its own.

**What would change my verdict:**
- **Upgrade to "run Stage 2 now":** Stage 1 shows damage is stable (≥ 0.5) and forecasts forgetting clearly better than current loss.
- **Downgrade to "not worth the budget":**
  - damage and current loss rank nearly identically (Spearman > 0.9);
  - damage is unstable across batches (< 0.3);
  - or grid forgetting turns out to be mainly a whole-kind shift, such as the front end's context drifting or stop-head damage. Per-puzzle ranking can't fix that.
- **Better use of the same insight:** the timing result, plus MIR's own best results, point to choosing *which kind* to replay and *when*, based on measured old-kind loss. That changes the allocation, so it is a separate experiment with its own controls, not a bolt-on here.

## What I still don't know, and how it affects this review

- **CPU speed, and whether CPU runs are bit-for-bit repeatable.** This affects run time, and whether Stage-1 R runs can be reused.
- **Whether grid forgetting on training-distribution puzzles matches the test-puzzle pattern.** I only measured test puzzles.
- **How much forgetting comes from front-end drift.**
- **When in C grids are lost.** Only phase-end scores were saved.

None of these change the design. They change how much room within-kind selection has.

## Plain-language summary for Ben

The idea is to pause before each practice round on old puzzles and "peek": imagine the next lesson on the new puzzle, see which old puzzles that lesson would hurt most, and practise those. The published version worked in picture-classification tests. There, though, it could pick *which old kinds* to practise, and it practised them in the same step as the new lesson. Your version can only pick among old puzzles of the same kind and size. Your saved results show the grids you forget are mostly the hard ones with many blanks, so the "peek" will probably just find hard grids, which a much cheaper rule ("practise the ones you currently get most wrong") also finds. Your one big win so far came from *when* you practised (more grid practice during the maze stage), not *which* grids. That points to scheduling, not example-picking. Before training anything new, run a cheap check: does the peek predict which grids actually get worse, better than "currently most wrong" does? Only if it passes, run the three-way test (random, most-wrong, peek) on six seeds with fresh test sets.

## Sources

- MIR paper: Aljundi et al., "Online Continual Learning with Maximally Interfered Retrieval", NeurIPS 2019, <https://arxiv.org/abs/1908.04742>. Checked: Algorithm 1, section 3.1, Tables 1–4 and 8–9, Appendix B.
- MIR official code: <https://github.com/optimass/Maximally_Interfered_Retrieval>. Checked: `mir.py` for the virtual SGD step, the scores and the single combined step; `Scripts/ER_experiments.sh` for C = 50, the learning rates and the MNIST best-loss variant.
- Prabhu et al., "Computationally Budgeted Continual Learning: What Does Matter?", CVPR 2023, <https://arxiv.org/abs/2303.11165>.
- Toneva et al., "An Empirical Study of Example Forgetting during Deep Neural Network Learning", ICLR 2019, <https://arxiv.org/abs/1812.05159>.
- Repo:
  - `artifacts/codex-autoroute-20260927/`: `RESULTS.md`, `run_experiment.py`, `auto_model.py`, `run/*/{A,B,C}.jsonl`, `result.json`.
  - `artifacts/codex-autoroute-20260927/hard_replay/`: `RESULTS.md`, `run/`.
  - `scripts/claude_rsn358a_envs.py`: the grid generator.
  - `scripts/claude_mirreview_grid_forgetting.py`: this review's read-only analysis.
