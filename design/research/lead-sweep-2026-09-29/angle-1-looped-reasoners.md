# Angle 1: tiny recursive and looped reasoners (HRM, TRM, looped transformers)

Written 2026-09-29 01:56 UTC by a research agent. Research only: no repo file edited, nothing trained or run.
Labels: **shown** = measured result in the cited source or a repo file; **suggested** = my reasoning; **untested** = nobody has run it on our ruler.
"Authors only" = not reproduced by anyone independent that I found. Fetch tool output is a machine summary of each page, not raw text (some numbers may be wrong; check before acting).

## 1. Plain-language summary for Ben

- The small puzzle-solvers that beat huge models (TRM, HRM) all share one trick: they run the same small network many times and are graded on the answer after EACH batch of runs, then keep going from where they were (the "carry"). Fancy brain-style structure did not matter much; the repeated-answer-grading and heavy data variety did.
- Our loop already has most of that (repeat the block, re-inject the puzzle, grade several rounds, a stop signal trained on "right now").
- Two real differences: (a) we always restart from a blank state and never train on rounds past 16, yet we test up to 48; they train and test at the same depth and carry the state from one training step to the next. (b) They use huge amounts of free variety (flip/rotate/relabel the same puzzle 8 to 1000 times); our few-example ruler gives the net k mazes and nothing more.
- Three one-change tests below. Two are cheap add-ons at adaptation time only (no new practice run).

## 2. The strongest sources

| # | Source | Read how | Author-only? |
|---|---|---|---|
| 1 | TRM, Jolicoeur-Martineau, "Less is More: Recursive Reasoning with Tiny Networks" https://arxiv.org/abs/2510.04871 (read through fetch summary of the HTML) | main text | Numbers are the author's; the ARC part is partly checked by a later analysis (row 4), Sudoku and Maze are not independently reproduced as far as I found |
| 2 | ARC Prize analysis of HRM https://arcprize.org/blog/hrm-analysis | full blog via fetch | Independent of the HRM authors (the ARC Prize team reran HRM), but a blog, not peer reviewed |
| 3 | "Are Your Reasoning Models Reasoning or Guessing? A Mechanistic Analysis of Hierarchical Reasoning Models" https://arxiv.org/html/2601.10679 | fetch summary | Independent of the HRM authors; own interpretability work, single group |
| 4 | "Tiny Recursive Models on ARC-AGI-1: Inductive Biases, Identity Conditioning, and Test-Time Compute" https://arxiv.org/html/2512.11847v1 | fetch summary | Analyses one released checkpoint only; no new training |
| 5 | Bansal, Schwarzschild et al., "End-to-end Algorithm Synthesis with Recurrent Networks" (recall + progressive loss) https://arxiv.org/abs/2202.05826 | ABSTRACT ONLY | Authors' claims, abstract level; details below from memory are marked |

Also used (weaker): Geiping et al. https://arxiv.org/abs/2502.05171 (abstract only: random recurrence depth, truncated backprop on last 8 iterations, random start state, input injection each step); Fan et al. looped length generalisation https://arxiv.org/abs/2409.15647 (abstract only); HRM https://arxiv.org/abs/2506.21734 (abstract only; recipe details below are from memory of the paper and the ARC Prize post, marked); CTM https://pub.sakana.ai/ctm/ (search snippets only, not read); Symbol-Equivariant Recurrent Reasoning Models https://arxiv.org/abs/2603.02193 (abstract-level); Readout Feedback https://arxiv.org/abs/2608.24136 (abstract-level). Not read at all: Saunshi looped-latent-thoughts, Giannou, Universal Transformer, Sakana CTM paper body.

## 3. What actually made them work (recipe facts)

### 3.1 Deep supervision with a carried, detached state
- HRM (from memory, plus the ARC Prize post): the model is run in "segments" (max 16); after each segment the answer is graded, weights are updated, the latent state is DETACHED and carried into the next segment of the same puzzle. ARC Prize (shown, independent): the outer refinement loop was the largest single factor: one refinement pass gave about +13 points; going from 1 to 8 training-time refinement loops roughly doubled accuracy; refining only at inference was worth less than training with refinement.
- TRM (shown, author): T=3 supervision recursions per step, n=6 latent updates, N_sup=16 supervision steps, carry (y, z) detached between supervision steps. Same 16 at train and test: TRM does NOT run beyond its training depth.
- Sudoku-Extreme ablation (author, one dataset): 87.4 baseline; separate high/low nets 82.4; no EMA 79.9; 4 layers with n=3 79.5; self-attention instead of MLP 74.7 (attention loses on the small fixed 9x9 grid, wins on 30x30); T=2,n=2 73.7; adding an HRM-style second ACT pass 86.1 (no gain).
- ARC-AGI-1 checkpoint analysis (shown, one checkpoint): step 1 already gives about 94% of the final accuracy (38.25 vs 40.5 at step 4) and extra steps beyond training depth add nothing. So in practice the "deep" recursion is shallow on ARC; the gain is mostly from the trained-in refinement plus augmentation and voting.

### 3.2 One-step gradient versus back-propagating through the recursion
- HRM used a one-step approximation of the gradient (implicit-function argument). TRM (author) says removing it and back-propagating through one full n+1 recursion lifted Sudoku-Extreme from 56.5 to 87.4. Authors only, one task.
- Our loop: gradient through the last k rounds, k up to 6 (mean about 3). That is real BPTT over a short window, already on the good side of this. Not a gap. (suggested)

### 3.3 Two latents (y answer, z scratch) instead of two networks
- TRM: y = current answer, z = reasoning scratch; one 2-layer net does both roles. The two-net hierarchy was worse (82.4 vs 87.4, author) and ARC Prize found hierarchy worth only about 5 points over a plain transformer of the same size, and different H/L cycle counts made no difference (shown, independent).
- Our loop has a single state h. Explicit y-feedback is the queued "R3 refill loop" (H9 report), so I do not propose it.

### 3.4 EMA of weights
- TRM 0.999; no-EMA cost 7.5 points on Sudoku (author). Nothing like it in our recipe (AdamW only). Proposed as test T3.

### 3.5 Data augmentation (the quiet big factor)
- TRM: about 1000 shuffles (Sudoku), 8 dihedral (maze), 1000 colour/rotate/translate (ARC), plus test-time voting over augmented copies. ARC Prize (shown, independent): 300 augmentations reached near the maximum; augmentation of training tasks mattered more than a bigger voting pool; training only on the 400 evaluation tasks gave 31% vs 41%, i.e. much of it is per-task memorisation (puzzle-id embeddings only work for tasks seen in training; TRM checkpoint analysis: blanking the id gives 0%).
- Mechanistic HRM paper (independent, one group): mixing difficulty and relabelling symbols raised Sudoku-Extreme 55.0 to 59.9 (difficulty mix) and about +18 (token relabelling), reaching 96.9 with an ensemble of checkpoints.
- Symbol-equivariant recurrent models (abstract only): building the symmetry into the layers gave competitive ARC with less augmentation and 2M weights, and Sudoku 9x9 transfer to 4x4, 16x16, 25x25.
- Reading for us (suggested): the tiny-net results lean on large amounts of free variation; our fewex ruler gives the adapting net only k mazes, no free variation.

### 3.6 Halting
- HRM: Q-learning ACT (extra forward pass). ARC Prize: ACT gave only a marginal gain. TRM: plain BCE on "is the current answer correct", single pass, and (author) ACT-style variant no better. Our halt head is already the TRM form.
- Important (shown, author-independent mechanistic paper): HRM often has NO fixed point: it "corrupts its answer by making unnecessary updates to its latent state even after reaching the correct answer", and can fail on a puzzle with one blank cell. Loss plateaus then drops suddenly ("grokking"), and there are spurious attractors. The fix they report was data variety, not architecture.
- In HRM/TRM the halt signal is mostly a TRAINING-time device (finish easy puzzles early, save compute); TRM evaluates at the full 16 steps (author). Their setups never needed a reliable inference-time stop on a new kind. That is exactly our open problem, so there is no direct recipe to copy. (suggested)

### 3.7 Train depth versus test depth
- Bansal/Schwarzschild (abstract, plus memory): recall (re-inject the input each iteration) and a progressive loss (random n iterations with no gradient, then k with gradient) stop the net learning iteration-number-specific behaviour, allowing many more iterations at test. Our train_loss is essentially this progressive loss (untested comparison beyond that); the abstract does not say how far past training depth they went, so I cannot give a ratio.
- Geiping (abstract): random depth in training, gradient on last 8, test-time depth scaling helps. Recursive Stem Model (from H9 survey, author): trained at about 20 iterations, run to about 20,000 with detached history.
- Repo note (handoff-looped-flows.md, citing 2609.19107 App. B.4, suggested): tied loops get worse beyond the pass count they were trained on; random-count training only flattens it.
- Our recipe: rounds beyond 16 never appear in training but the stop cap and all F_eq answers are read at up to 48. Nothing supervises the "stay right once right" property (fixed point) for rounds 17..48, and the halt head has never seen state at those rounds. (shown from the code: TRAIN_ROUNDS=16 in scripts/claude_fewex_net.py line 24; adaptation reuses the same 1..16 draw per artifacts/claude-xfer1-20260927/notes.md line 24.)

## 4. Our recipe against theirs: the gaps, ranked

1. **Horizon mismatch (train up to 16, test up to 48).** They match train and test depth or use detached carry to make deep states trainable. Suggested most relevant to "stop never fires on new mazes: 300 of 300 hit the 48 cap": if the answer at round 30 to 48 is off-distribution for both readout and halt head, stop-prob will not fire even when the answer is right. Untested here.
2. **No free variety on the few examples.** TRM/HRM lean on 8 to 1000x augmentation. Our ruler adaptation uses the k mazes as is. Untested.
3. **No weight averaging.** EMA cost TRM 7.5 points when removed (author). Untested here.
4. **No carry of state across optimizer steps.** We restart from zero each step; TRM/HRM continue. Partly covered in effect by gap 1 (the carry is a way of reaching deep states cheaply). I do not propose the carry itself: it needs a persistent per-puzzle state buffer and changes the data pipeline, so it is not one cheap change.
5. Not gaps: BPTT window (ok), halt as BCE (same as TRM), input re-injection (same as Recall), hierarchy (not needed, ARC Prize), ACT Q-learning (not needed). Explicit y latent is queued as R3; D4 as a built-in loop symmetry is queued as R2 (see T2 for the difference).

## 5. Mapping to the open problems

- **F_eq few-example ruler:** T1 to T3 all act inside adaptation and reuse the existing 2,048-update ruler (shown ruler numbers: practised loop 51.00 / 51.29, plain 33.79 / 33.58, fresh 20.67 / 21.50).
- **Stop never fires on new mazes:** gap 1 above (state at rounds 17 to 48 is untrained); the HRM no-fixed-point finding says a net can leave a correct answer if never trained to hold it. A free diagnostic below checks this before any training. Does not duplicate H12, SL or Pond, which change the stop TARGET or the stop head, not the training depth of the loop.
- **Numbers search fails:** no evidence in these sources for search inside one recurrent trajectory. TRM/HRM tasks are solved by propagation; both checkpoint analyses show recursion mostly shallow. Nothing here helps numbers directly. (suggested)
- **Carry-over to new kinds:** puzzle-id conditioning does not transfer (independent, ARC Prize and checkpoint analysis: 0% with blanked ids): supports having no task-id register. Symbol-equivariant models transferring across board sizes is the closest carry-over evidence (abstract only).
- **Sleep:** nothing in these sources.
- **Improve with use / scale:** T2 and T3 are used at adaptation time and scale trivially. T1 leaves the practice recipe alone and could later move into practice if it works.

## 6. Free diagnostics (no training; do before any test)

Read the per-round predictions the ruler already produces (loop_rounds returns up to 48 rounds of answers and stop probabilities):
- D1: on the practised loop, held-out mazes, fraction exactly right at round 8, 16, 24, 32, 48. Also the fraction right at round r but wrong at round 48 (un-solving rate).
- D2: mean stop-probability by round.
- Prediction (suggested): if accuracy is flat from 16 to 48 and un-solving is about 0, gap 1 is not the problem and T1 should fail; run T2/T3 first. If accuracy decays after 16 or stop-prob collapses after 16, T1 is well motivated.

## 7. Proposed tests (one change each)

Common setup: fair ruler, 9x9 mazes, adaptation by full fine-tuning on k mazes, 2,048 updates, F_eq as defined in RESULTS-EQ.md. Compare with the existing practised-loop and plain-net rows (same seeds 0 and 1, same k rungs). Noise about 3.3 to 4.2 F_eq sd (NOISE.md); bar F_eq +8.0 over the same arm without the change; anything under +4.0 counts as noise. Costs are relative to one practice run of about 12,000 steps (call it 1 PR); an adaptation run is 2,048 steps.

### T1. Match the training depth to the test depth during adaptation

- **Change:** during adaptation only, the total rounds are drawn from 1..48 instead of 1..16 (grad window k unchanged: 1..min(total,6)). The practised net, plain net and everything else unchanged.
- **Why (suggested):** rounds 17 to 48 are otherwise never trained; the loop is read and stopped there.
- **Rungs:** k = 16, 256, 4,096; loop arm only, 2 seeds; the plain net has no rounds so its existing row is the control.
- **Cost:** per step about 1.9x (more no-gradient rounds: 24 instead of 8 on average; no-grad rounds are about a third the cost of graded ones). 6 adaptations x 2,048 x 1.9 / 12,000 = about 2 PR (about 2 to 3 GPU-hours if 1 PR is about an hour; unknown, adjust). CPU: too slow, use the GPU.
- **Pass (fixed now):** mean loop F_eq over the 3 rungs and both seeds at least +8.0 above the existing 1..16 row, and both seeds individually at least +4.0, and the loop-minus-plain gap not smaller than in RESULTS-EQ.md.
- **Proved wrong if:** mean gain below +4.0, or D1 shows no drift or un-solving beyond round 16 (then the mechanism is not there even if a noise win appears). Also report (not a pass condition) how many of 300 stop before 48; a rise from 0 would be a bonus, and a rise from 0 with no F_eq gain still would not count as passing.
- **Overlap check:** Pond/SL/H12 change the stop TARGET or HEAD; this changes how deep the LOOP is trained. Sleep and staged-unfreeze do not touch round counts.

### T2. Eight-way flip/rotate augmentation of the k adaptation mazes (data-level D4)

- **Change:** each adaptation batch item is randomly transformed by one of the 8 dihedral maps (applied identically to the maze and its solution) instead of used as is. Applied to ALL arms in the ruler (loop, plain, fresh) so it is a ruler variant "F_eq+D4", not a loop-only trick. No extra labels, no extra updates.
- **Why:** TRM (author) and the ARC Prize analysis (independent) both say augmentation is the main free lever; the ruler currently gives it none.
- **How it differs from queued R2 (soft-D4 loop):** R2 changes the architecture (equivariant pathway) and needs a new practice run; T2 changes only the data seen in adaptation, on the existing checkpoint. If R2 later lands, the two can be stacked and compared. It also differs from A (practice breadth).
- **Check first (fast):** confirm the net's position/offset encoding (dr, dc in claude_fewex_net.py) does not encode a fixed compass direction that a rotation would contradict. If it does, rotations are still legal maze data, so no fix is needed, but note it.
- **Rungs:** k = 1, 16, 256; 2 seeds; three arms. 18 adaptations x 2,048 / 12,000 = about 3 PR at 1x cost (per-step cost unchanged); loop and plain only: 2 PR.
- **Pass (fixed now):** loop F_eq at k=16 and k=256 each at least +8.0 over its own existing row (mean over seeds), and the loop keeps a gap over the plain-with-D4 row of at least +8.0 F_eq at k=256.
- **Proved wrong if:** loop gain under +4.0 at both k=16 and 256, OR plain net gains by as much as the loop (then augmentation only rescues the weaker net and says nothing about the loop). A gain only at k=1 also fails the pass mark (that rung is the noisiest).

### T3. Exponential moving average of weights during adaptation

- **Change:** keep an EMA copy of the weights during adaptation (decay 0.99, fixed now; half-life about 70 updates, sized for 2,048 updates, not TRM's 0.999) and evaluate the EMA copy. Nothing else changes.
- **Why:** TRM lost 7.5 points on Sudoku without EMA (author). Full fine-tuning on a handful of mazes with lr 1e-3 is a noisy path; averaging could remove some of the run-to-run noise that sets our 3.3 to 4.2 sd.
- **How it differs from WiSE-FT interpolation (standing/03):** WiSE-FT blends the start and end weights of one run; EMA averages along the trajectory and never uses the pre-adaptation weights.
- **Rungs:** k = 16, 256, 4,096; loop arm and plain arm; 2 seeds. Cost almost nil beyond one extra weight copy: 12 adaptations x 2,048 / 12,000 = about 2 PR; on the same checkpoints it can be evaluated alongside the plain run by tracking both weight sets in a single run (the adaptation is the same run), halving cost to about 1 PR.
- **Pass (fixed now):** mean loop F_eq gain at least +8.0 over the same run's non-EMA evaluation.
- **Proved wrong if:** gain under +4.0, or negative at k=4,096 (EMA lagging a slow fit). It would also be wrong if the plain arm gains as much (no loop-specific effect, but then it is still a usable ruler improvement; say so).

Suggested order: run D1/D2 (free), then T3 (cheapest), T2, T1. Each is independent; none needs a new practice run.

## 8. Things I did not do or could not verify

- I read HRM only at abstract level; the deep-supervision segment count (16), one-step gradient and ACT details are from memory plus the ARC Prize post and TRM's account of HRM.
- Bansal/Schwarzschild, Geiping, Fan, CTM, Saunshi, Giannou, Universal Transformer: abstract or search-snippet level only; no exact train/test depth ratios were extracted. CTM notes only: it trains on the loss at the two ticks that are lowest and most certain (author claim), and generalised 39x39 to 99x99 mazes (author claim); not read in depth and not compared.
- TRM numbers came through a summarising fetch tool (the PDF fetch failed; the HTML fetch worked) and I did not check the tables against the paper.
- All web sources are information only; nothing in them was treated as instructions.
- These are tiny-net image/grid puzzle results with 1,000 training puzzles. None of it involves our village model; I kept the two apart.
