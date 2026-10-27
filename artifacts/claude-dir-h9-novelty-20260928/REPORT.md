# H9: what would make the reasoner genuinely novel?

Written 2026-09-28 20:57 UTC (`date -u`). Design and pass marks only. **Nothing here was run**: the box has no torch, no plug-in
code was written, and no maze score of any design below exists. Marks in section 6 are fixed by committing this file;
they do not change after any design sees a dev or holdout maze score. Files next to this one: `calibration.json` and
`budget.json`, both made by `scripts/claude_dir_h9_budget.py` (pure Python; re-run it to reproduce every number in
sections 2 and 5 that is labelled "arithmetic").

**Labels.** *shown* = read in a repo file (file:line given) or computed by the arithmetic script. *reported* = a web
page was fetched and says so (tags F, S, M, U explained in section 9). *suggested* = my reasoning, not measured.
*untested* = nothing has been run. No claim about what a design will score is *shown*.

---

## 1. The answer, in plain words (for Ben)

A looped transformer is not novel by itself. Four ideas could make our reasoner novel. Each is one small change, each
fits inside 1% of the loop's weights, none is built for mazes, and none tells the net what kind of puzzle it is
looking at.

| rank | idea | plain words | extra weights | novelty x chance (guess) |
|---:|---|---|---:|---:|
| 1 | **R1 Reach channel** | Every round, one attention map is treated as "which cell leads to which cell" and raised to powers up to 63 hops in one step. The result says how strongly each cell connects to cells the net itself marked as start-like or goal-like. | 6,485 (0.39%) | 12 |
| 2 | **R2 Soft-D4 loop** | The net's position bias treats "above" and "left" as separate facts. Tie them together (a turned or mirrored maze is the same maze), and keep a small direction-specific correction for tasks that care, such as sums. | 240 (0.015%) | 12 |
| 3 | **R3 Refill loop** | After each round the net writes its current answer as an ordinary token, and next round it reads that token like any other input. | 1 | 7.5 |
| 4 | **R4 Twin-stream stop** | Think twice from two slightly different starts. Stop only when the two runs agree. | 1 | 1.5 |

Numbers in the last column are my guesses (novelty 0 to 1 times chance in percent of reaching F_eq +10 in both seeds);
section 7 shows how I made them. R1 and R2 are tied; I put R1 first because novelty is Ben's stated goal.

Four findings that shape everything else (the facts are *shown* in section 2; what I conclude from them is *suggested*):
1. **F_eq +10 is a big ask: about 4 times fewer examples at every rung.** It is +240 correct counts (of 300) summed over
   the eight rungs. The score lives at 64 examples and up; 1 and 4 examples contribute about zero.
2. **The practice is starved.** The net practises on only two kinds (sums and Latin grids). Ideas that learn a "task
   code" or write weights from examples probably need many kinds (section 8), so this ruler probably cannot judge them
   (suggested, from the diversity-threshold paper).
3. **The loop's learned stop does not decide its own thinking time on mazes.** On the 300 holdout mazes it ran to the
   48-round cap on 300 of 300 mazes at every rung from 1 to 4,096 examples in seed 0, and swung between 23 and 300 in
   seed 1. The stop head is never trained on mazes (`claude_fewex_bench.py:205`). The learned-stop read beat a fixed
   16-round read by only 0 to 14 counts of 300 at every positive rung. R4 targets Ben's own stop rule, not the F_eq score.
4. **Seed noise is about 10 F_eq.** The sparse loop was +3.88 in seed 0 and -6.25 in seed 1
   (`artifacts/claude-sparse-20260928/RESULTS.md:9-14,43`). A real +10 gain still has a fair chance of missing the
   both-seeds mark.

**The straight answer to H9's question.** None of the four is a new paradigm. The most defensible novelty claims are R1 (a
closure organ taken from the brain's successor representation, put inside a shared-weight loop) and R4 (conflict-gated
stopping on a kind whose stop was never trained). The larger novelty, letting the net write a task code or new weights
from a few examples, needs many practised kinds; this ruler has two, so it cannot judge that until a many-kind ruler
exists (section 8).

What I could not do: run anything, read three pages (blocked or refused), or confirm some mechanisms beyond their
abstracts. Section 9 lists each.

---

## 2. What the ruler can and cannot reward (shown)

**The ruler.** Practise on sums and Latin grids only (12,000 batches of 64). Adapt to k = 1, 4, 16, 64, 256, 1,024,
4,096, 16,384 distinct 9x9 mazes with exactly 2,048 optimizer updates each (512 batches of 32, 4 updates per batch:
`scripts/claude_fewex_eq_bench.py:27-29,115-116`; `claude_fewex_bench.py:28`). F_eq is the mean over the 8 rungs of
exact-solve accuracy on 300 holdout mazes (`RESULTS-EQ.md:37-50`, ADDENDUM-4.md:11).

**The loop's row** (`RESULTS-EQ.md:43,47`, counts of 300 at k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384):

| seed | counts | sum of 8 | F_eq | plain F_eq |
|---:|---|---:|---:|---:|
| 0 | 1, 0, 28, 137, 256, 271, 257, 274 | 1,224 | 51.00 | 33.79 |
| 1 | 1, 0, 3, 190, 262, 236, 284, 255 | 1,231 | 51.29 | 33.58 |

**What +10 means** (`calibration.json`; arithmetic on the loop's own row, assuming a curve that only moves left):
- +10 F_eq = +240 correct counts summed over the eight rungs, in both seeds.
- Each rung's share of F_eq (points), seed 0 / seed 1: k=1 0.04 / 0.04; k=4 0.00 / 0.00; k=16 1.17 / 0.12; k=64 5.71 /
  7.92; k=256 10.67 / 10.92; k=1,024 11.29 / 9.83; k=4,096 10.71 / 11.83; k=16,384 11.42 / 10.62. No arm in the
  baseline table gets more than 13 of 300 at k = 1 or 4 (`RESULTS-EQ.md:43-50`), so realistically almost nothing is won
  there.
- Shifting the whole curve left by one rung (the same accuracy from 4 times fewer examples) gives F_eq 62.38 / 61.88
  (+11.38 / +10.59). Shifting by two rungs (16 times fewer) gives 73.79 / 72.50. Perfect from k=64 up with k=16 and
  below unchanged gives 63.71 / 62.67. Perfect only from k=256 up gives 56.92 / 58.08 (+5.92 / +6.79), which is not
  enough; adding k=64 at 235 of 300 gives 61.00 / 59.96.
- So +10 cannot come from one rung. A winner must make the net learn roughly 4 times faster from mazes, or lift the
  64-example rung to about 235 of 300 and every rung from 256 up to nearly perfect.

**Practice is starved.** Practice batches are sums of 1 to 4 digits or 4x4 / 5x5 Latin grids with a legend
(`claude_fewex_data.py:29-34`). Two kinds, both made by code.

**The three maze marker tokens are new to the net.** WALL, START and GOAL reuse the operator tokens "/", "+", "*"
(`claude_rsn358m_maze.py:28`). Sums contain only digit, blank and mask tokens (`claude_rsn358a_envs.py:59-71`) and Latin
grids only symbol, blank and mask tokens (`claude_fewex_data.py:21-26`), so those three tokens are never inputs in
practice. The answers ON/OFF are the digit tokens 1/0 (`claude_rsn358m_maze.py:29`), which the net has seen. A maze
holds up to 16 rooms per 9x9 grid (`claude_fewex_data.py:51`, k = (9-1)//2 = 4), so a route is at most 31 cells, and up
to 25 rooms (49 cells) at 11x11. A 64-term power series covers both.

**The loop's stop on mazes** (`RESULTS-EQ.md:76-86,120-130`; the stop rule is `claude_fewex_bench.py:76-78`: the first
round, from the third on, where q > .5 and the last three predictions agree). Practised loop, holdout 9x9, mean rounds and cap hits
(of 300):

| rung | seed 0 rounds / cap | seed 1 rounds / cap | learned minus fixed-16 (seed 0 / 1, counts of 300) |
|---:|---|---|---|
| 16 | 48.0 / 300 | 13.4 / 23 | 0 / 0 |
| 64 | 48.0 / 300 | 43.3 / 262 | +1 / +5 |
| 256 | 48.0 / 300 | 48.0 / 300 | +11 / +5 |
| 1,024 | 48.0 / 300 | 20.6 / 71 | +6 / +9 |
| 4,096 | 48.0 / 300 | 34.8 / 196 | +14 / +1 |
| 16,384 | 31.9 / 163 | 33.1 / 177 | +4 / +2 |

The stop head has no loss during maze adaptation (`claude_fewex_bench.py:205`, comment "no maze stop-head loss"). What
the table shows: on a kind it was never trained on, the stop is erratic and mostly does not fire. What it does not show:
that a better stop would raise accuracy; the learned-stop read (mean 13 to 48 rounds) beat the fixed 16-round read by
only 0 to 14 counts of 300 at every positive rung.

**Noise.** The sparse loop's F_eq minus the loop's was +3.88 (seed 0) and -6.25 (seed 1)
(`artifacts/claude-sparse-20260928/RESULTS.md:9-14,43`), a 10-point spread between seeds for one design.

**What the harness carries and does not.** The baseline learner carries only the state `h` between updates, uses 3 free
plus 2 gradient rounds per update, and has no stop loss on mazes (`claude_fewex_bench.py:184-206`, lines 198, 202, 205).
Any design that needs more carried state, or a loss on the stop head during adaptation, needs its own `Learner`; the
plug-in contract allows one (`PROTOCOL.md:29-33`).

---

## 3. How the brain does it, and where silicon can do better

| brain mechanism | what it does (source, check) | silicon version | design |
|---|---|---|---|
| Hippocampal predictive map / successor representation | Place cells encode expected discounted future occupancy; the successor representation equals a sum of discounted powers of the state-transition matrix (Stachenfeld et al. 2017, Nature Neuroscience; reported F) | Compute the whole power series exactly in a few matrix squarings inside one round | R1 |
| Hippocampal reverse replay | After a run, recent places replay in reversed order while awake; proposed to assign credit to actions (Foster and Wilson 2006, Nature; reported F) | Replay costs nothing on silicon. The harness already has a sleep phase; the "answer written, then read back" idea in R3 and its later two-way variant borrow the write/re-read loop only | R3 (loosely) |
| Prefrontal working memory as a source of rule bias | PFC holds task rules and biases processing elsewhere (Miller and Cohen 2001; S, title and abstract page only) | A task register would need many kinds to train; deferred (section 8) | none |
| Basal ganglia / subthalamic conflict gating | High conflict between options raises the decision threshold: "hold your horses" (Frank 2006; Cavanagh et al. 2011; S, titles only) | Silicon can clone the whole state exactly and run two copies for one extra pass; a brain cannot | R4 |
| Working memory is small, slots are few | Baddeley-style limited-capacity stores (M, not checked) | The loop holds the whole 81-cell state each round, and can write it out losslessly | R3 |

Where silicon can do better, in one line each (suggested): exact closure by repeated squaring in one round instead of
many spreading steps (R1); exact state cloning (R4); symmetry built in from the start instead of learned from
experience, which is my inference and not a checked claim about brains (R2); lossless read-back of its own answer (R3).

The honest reading: the brain sources give reasons to look at these four mechanisms. They do not validate any of them
for our ruler.

---

## 4. Survey of 2024-2026 work

Tags: F = fetched and read, S = seen in search only, U = unread. Fetch outputs are summaries produced by the fetch tool,
not raw PDF text (section 9).

| topic | work | what it does (as fetched) | what we take from it | tag |
|---|---|---|---|---|
| small recurrent reasoners | TRM, arXiv 2510.04871 | One 2-layer net, 7M weights; answer state y and latent z; n=6, T=3; halting by a binary cross-entropy of reaching the correct solution; EMA 0.999; Sudoku-Extreme 87.4%, Maze-Hard 85.3%, ARC-AGI-1 44.6%; 8 dihedral augmentations for mazes; removing EMA cost 7.5 points, a 1-step gradient cost 30.9 points (Sudoku-Extreme) | Our loop already has the BCE stop (`claude_fewex_net.py:171`). y beside z is the precedent for R3. Dihedral augmentation is the precedent for R2. | F |
| | HRM, arXiv 2506.21734 | Two timescales, one-step gradient, ACT with a Q head; 27M weights; 40.3% on ARC-AGI | Hierarchy is not the source of the gains (next row) | F |
| | ARC Prize analysis of HRM | Outer refinement loop gave +13 points; hierarchy only about 5 points over a regular transformer; 300 augmentations reach near maximum; task-id embeddings only work on tasks seen in training | Refinement loop: the loop already has it. Task ids do not transfer: argues against a task-register design here. | F |
| | Recursive Stem Model, arXiv 2603.15641 | Detach hidden history, loss on the final step; 97.5% on Sudoku-Extreme, about 80% on 30x30 maze; trained at ~20 iterations, run to ~20,000 | Detached history is what the loop's free rounds do (`claude_fewex_net.py:120-126`) | F |
| | Dissecting HRM, arXiv 2609.22197; Probabilistic TRM, 2605.19943; 2511.16886v2 | not read: fetch refused or no text | none | U |
| adaptive compute / halting | PonderNet, arXiv 2107.05407 | Learned halting probability per step (abstract only; mechanism not fetched) | The loop's stop is in the same family | F (abstract) |
| | PABEE, arXiv 2006.04152 | Stop when internal predictions stay unchanged for a set number of steps | Our stop rule copies this: three unchanged predictions | F |
| | LoopFormer, arXiv 2602.11451 | Step-size and time conditioning plus shortcut-consistency training for variable-length loops | Gives the loop a clock; our loop has none by design; deferred | F |
| | Looped MoE, arXiv 2605.09165 | Different experts per pass recover expressivity; looped MoE scales better than dense loops | The repo's sparse loop is this family: NOT PROMOTED | F |
| | Mixture-of-Recursions, arXiv 2507.10524 | per-token recursion depth (title only) | not used | S |
| | Huginn, arXiv 2502.05171 | Prelude / recurrent core / coda, 3.5B weights, test-time depth | Confirms depth can scale at test time | F |
| | Looped transformers for reasoning, arXiv 2502.17416 | k layers looped L times match kL layers on synthetic reasoning; T loops can simulate T chain-of-thought steps | Effective depth is the resource | F |
| | Path independence in equilibrium models, arXiv 2211.09961 | Models that reach the same state from any start generalise better to harder instances (abstract) | Basis for R4's twin streams as a runtime check | F (abstract) |
| | "Recall" recurrent nets, arXiv 2202.05826 | Keep an explicit copy of the problem each round; progressive training | The loop re-adds its input every round (`claude_fewex_net.py:78`) | F |
| test-time training / latent search | TTT for few-shot, arXiv 2411.07279 | Temporary parameter updates at test time: 53.0% on ARC (8B LM), +7.3 points on BBH 10-shot | Our ruler's adaptation already is gradient fine-tuning on k mazes | F |
| | Latent Program Network, arXiv 2411.08706 | Encoder plus decoder plus gradient search in a latent program space; trained leave-one-out over many tasks | Needs many training tasks: deferred | F |
| | CompressARC, arXiv 2512.06104 | 76K weights trained per puzzle at test time; equivariant to example order, colours, rotations, flips; 20% on ARC-AGI-1 eval | Precedent for hard-wired symmetry (R2) | F |
| energy / diffusion refinement | IRED, arXiv 2406.11179 | Annealed energy landscapes; depth adapts at inference; Sudoku, matrix completion, path finding | Different training objective: deferred | F |
| | Masked discrete diffusion for reasoning, arXiv 2410.14157 | Sudoku 100% vs 20.7% autoregressive; Countdown 91.5% vs 45.8% | Precedent for feeding partially filled answers back (R3) | F |
| | Looped diffusion LMs, arXiv 2605.26106; recursive masked diffusion, 2606.18022 (review page) | Shared blocks looped inside a denoising step; recursion substitutes for parameters and steps on Sudoku and Countdown | Same as above | F |
| | Analog Bits, arXiv 2208.04202 | Self-conditioning improved sample quality; the fetched abstract does not define the mechanism | R3 is self-conditioning-like; the definition is from memory (M) | F (abstract) |
| | Energy-Based Transformers, arXiv 2507.02092 | titles only | not used | S |
| slot / object memory, hypernetworks | Attention as a hypernetwork, arXiv 2406.05816; CAVIA, 1810.03642 | titles only | Both need task diversity (next row); I did not search slot attention separately (section 9) | S |
| few-shot in-context rule learning | Task-diversity threshold, arXiv 2306.15063 | Below about 2^14 to 2^15 pretraining tasks (linear regression) a transformer behaves like a Bayesian estimator on the training tasks and fails on new ones; above it, it generalises | Two practised kinds is far below any diversity where task inference has worked (regression tasks are not our kinds, so the numbers do not transfer) | F |
| graph and closure | Transformers and logarithmic depth, arXiv 2402.09268 | Log depth is enough for graph connectivity | A closure primitive is a known-sufficient computation | F |
| | Transformers learn algorithms vs heuristics for connectivity, arXiv 2510.19753 | An L-layer model can solve connectivity up to diameter 3^L by repeated squaring of the adjacency matrix; beyond that it falls back to degree heuristics | Attention already can do this but spends layers; R1 hands the primitive over without spending depth | F |
| | APPNP, arXiv 1810.05997 | propagation with personalised PageRank (title only) | R1's power series is in this family | S |
| soft symmetry | Residual pathway priors, arXiv 2112.01388 | An equivariant pathway plus a non-equivariant pathway with a prior favouring the equivariant one; matches fully constrained models when the symmetry is exact and tolerates misspecified symmetry | The exact recipe for R2 | F |
| consistency | Self-consistency, arXiv 2203.11171 | Sample many reasoning paths and take the most consistent answer | R4 uses disagreement as a stop signal rather than a vote | F |
| | RevThink, arXiv 2411.19865; DreamCoder, 2006.08381 | Backward reasoning as extra training signal; wake-sleep with dreamed tasks | Backward variant and replay are later options, not part of R3 | F |

I ran one targeted search for a closure primitive built into a looped reasoner and found nothing like R1, but a shallow
search is not proof that none exists.

---

## 5. The four designs

Every design keeps the ruler unchanged and adds one thing to the loop. "Plug-in" means the H3 pattern
(`scripts/claude_dir_h3_net.py`): a `Net` subclass of `claude_fewex_net.Net`; the new parameters are created after
every loop parameter so the loop's init under the same seed is unchanged; `ARMS`, `TRAIN_ROUNDS`, `tensors`,
`ce_and_exact`, `train_loss`, `Practice` re-exported from the base; run with
`python -B scripts/claude_fewex_eq_bench.py adapt ... --plugin <module>`. No plug-in code is included here.

### R1. Reach channel

**Mechanism in plain words.** Every round, after the two shared blocks, one extra attention map is built over all cells.
Instead of copying values, that map is read as a table of "which cell leads to which cell". It is raised to powers by
repeated squaring, so one round sees routes of 1, 2, ... 63 hops. The net also marks each cell with a learned
"start-like" score and a "goal-like" score. Four numbers per cell come out: how strongly the cell is reached from
start-like cells, how strongly it reaches goal-like cells, the product of the two ("lies between them"), and how much
the cell can reach in total. They are added back into the state through one small layer that starts at zero, so the net
begins exactly as the loop.

In symbols, with u = LayerNorm(z) of the block output z: link logits A_ij = q_i . k_j / sqrt(8) + off[dr_ij, dc_ij] + b,
q and k are rank-8 projections of u, off is a 9x9 table over the loop's own clipped offsets; P = row-softmax(A) (each
row sums to 1, like a transition matrix); M = gamma P with gamma = sigmoid(g), initialised to 0.95; S = sum over n = 0..63
of M^n, computed as the product of (I + M^(2^j)) for j = 0..5 (5 squarings, 5 multiplications); source score
s_i = sigmoid(w_s . u_i + b_s), goal score t_i = sigmoid(w_t . u_i + b_t); features f1 = S^T s, f2 = S t, f3 = f1 * f2,
f4 = S 1; z <- z + Linear_4to256(f). The linear layer is zero-initialised.

**What is new vs prior art.** Verified: the successor representation is the discounted sum of transition-matrix powers
and the hippocampus is proposed to hold it (Stachenfeld 2017; F). Transformers can learn repeated-squaring matrix
powering for graph connectivity, but only out to diameter 3^L for L layers (arXiv 2510.19753, first author Qilin Ye per a search snippet; F), and log
depth suffices in theory (Sanford, Hsu, Telgarsky, arXiv 2402.09268; F). APPNP propagates over a given graph (S). HRM
and TRM contain no such primitive (F). What I did not find in one targeted search is the combination: the link map is
made from the state each round, so nothing tells the net where the graph is; the closure is computed exactly by
squaring inside a shared-weight loop with a learned stop; and start-like and goal-like markers are learned. I call this
medium novelty (0.6, a guess). It is a known computation given a learned front end, not a new principle.

**Why it might improve few-example learning (suggested, untested).** A maze answer is a chain of linked cells between
start and goal. The base loop must grow that chain a hop at a time (its narrow heads see a 3-column strip,
`claude_fewex_net.py:42-45`), so its state must learn both "what links" and "how to walk it". The reach channel makes
walking exact and global in one round, leaving only two things to learn from the few mazes: which neighbouring cells
link (wall cells should not) and which cells act as start and goal. Carry chains in sums are the same kind of relation, so
practice may already train the channel.

**Parameter budget** (`budget.json`, arithmetic). Extra weights 6,485: LayerNorm 512, q and k projections 4,096 (rank 8,
no bias), offset table plus bias 82, source and goal vectors plus biases 514, gamma 1, 4-to-256 linear 1,280. Stored
1,652,211 against the loop's 1,645,726: +0.394%. Inside the 1% band 1,629,269 to 1,662,183.

**Generality.** Nothing mentions walls, routes, mazes or grid size. It works on any cell set, and the same channel serves
sums (carry chains) and any task whose answer follows a chain of pairwise links. Limits: cost grows with the cube of the
number of cells. Arithmetic: 10 products of 81x81 per round is 5.3M multiply-adds, against about 127M for the two blocks at
9x9 (about +4%); at 11x11 about +9%; at 30x30 (900 cells) 7.3 billion per round, which is too expensive unless changed.

**How it plugs into the ruler.** `Net(base.Net)` creates `reach_ln`, `wq`, `wk`, `off`, `w_src`, `w_tgt`, `g`, `mix`
(zero-initialised) after `super().__init__(arm)`, only when `arm == "loop"`; overrides `step` to add the channel to `z`
before `self.ln_state`. It uses the `dr, dc` index tensors that `embed` already returns (`claude_fewex_net.py:73-75`).
The baseline `Learner`, `Practice`, `train_loss`, `infer_rounds` are inherited unchanged. Fp32 on CPU as the ruler
requires. Cost: about +5% multiply-adds; wall time not estimated. The baseline loop needed 169 minutes per adaptation run
(`RESULTS-EQ.md:196-197`).

**Single-change test and pass marks (fixed now).** The one change is the reach channel (arm "R1"; loop, plain and
fresh arms as in section 6). It must clear marks M1 to M6 of section 6 in each seed. Credit check, reported and judged
before the headline is read: on the **dev** panel (not the sealed holdout), take the k = 1,024 net of each seed and
zero the four reach features at inference. If dev 9x9 drops by less than 30 of 300, the channel is a bystander and a
headline pass is reported as "the design passed", not "the reach channel passed".

**The result that would prove it wrong.** M6 fails in both seeds (sum of the eight holdout counts at most 1,224 in seed
0 and at most 1,231 in seed 1). Or a source guard failure (M2). Or `mix.weight` stays below 1e-3 in mean absolute value
after both practice and adaptation, in both seeds: the net never used the channel. Any of these rejects "a closure over
a state-made link map helps few-example learning at this budget".

**Main risks.** The link map has to learn that walls block, from k mazes, through five squarings. Practice may leave the
channel switched off (sums and grids may not use it). Three unseen marker tokens (section 2) must be found by the goal
and source scores. All suggested, none measured.

### R2. Soft-D4 loop

**Mechanism in plain words.** The loop's position bias for attention is two separate tables, one for rows and one for
columns (`claude_fewex_net.py:35-36,41`), and its narrow heads see a 3-column strip (`:42-45`). So it learns "the cell
above matters" and "the cell to the left matters" as separate facts. A maze turned on its side is the same maze, so each
such fact costs about four times the examples it should. The change makes the bias a single table indexed by distance
only (an "orbit": how many rows and how many columns apart, ignoring which way), so one entry serves up, down, left and
right. A small direction-specific correction stays, learning at a fixed fraction of the speed, so sums (which carry
leftward) can still buy direction. The narrow heads' window becomes a cross (a 3-column strip or a 3-row strip), which is
symmetric and includes the old strip.

In symbols: bias_h(dr, dc) = iso_h[orbit(dr, dc)] + eps * (br_h[dr] + bc_h[dc]) with eps = 0.3 (fixed now, never tuned);
orbit = (min(|dr|,|dc|), max(|dr|,|dc|)) on offsets clipped to +-4, which gives 15 orbits; narrow heads (the first 4 of
8) are masked where both |dr| > 1 and |dc| > 1.

**What is new vs prior art.** Verified: residual pathway priors give exactly this structure, an equivariant pathway plus
a non-equivariant one with a prior favouring the equivariant one, and match fully constrained models when the symmetry is
exact (Finzi, Benton, Wilson, arXiv 2112.01388; F). CompressARC hard-wires equivariance to flips and rotations (F). TRM
augments mazes with 8 dihedral transformations (F). What is new here is only the placement: soft dihedral tying of a looped
reasoner's relative position bias, with the slow-learning-rate residual standing in for the prior. I call this low to
medium novelty (0.4, a guess): closer to engineering than to a new mechanism.

**Why it might improve few-example learning (suggested, untested).** All the loop's non-positional weights are already
direction-blind (`claude_fewex_net.py:33-34`); direction enters only through the position bias and the strip mask. Tying
them may cut the number of direction-specific facts the net must learn from k mazes by up to a factor of about 4 to 8.
Section 2 says a 4 times gain everywhere would be worth about +10 F_eq; the real gain must be smaller than that, so I
put the chance below one in three.

**Parameter budget** (`budget.json`). Per block per head: old 18 (two 9-entry tables), new 15 + 18 = 33, so +15 per
head, 2 blocks, 8 heads = +240. Stored 1,645,966: +0.0146%.

**Generality.** Holds for any grid task whose rules do not depend on direction (mazes, Latin grids under a transpose or
flip, many ARC-style tasks). It does not hold for sums, which carry leftward; that is why the direction-specific part is
kept (soft, not hard). It is a symmetry assumption about grids, not a rule about mazes. The choice of dihedral symmetry is
a hand-picked prior, the most hand-designed of the four ideas; I flag it to Ben.

**How it plugs into the ruler.** The bias is computed inside `Block.forward` (`claude_fewex_net.py:38-48`), so the
plug-in defines `SoftBlock(base.Block)` that adds `iso = zeros(heads, 15)` (zeros take no random numbers, so the loop's
weights initialise the same) and overrides `forward`; `Net.__init__` builds the base, then replaces each block by a
`SoftBlock` loaded from the loop's weights (`load_state_dict(strict=False)`); the orbit index is a fixed buffer built once
from the `dr, dc` indices. The plain arm is untouched. Learner, practice and everything else inherited. No extra
compute beyond a table gather. The mask change and the table change are two halves of one "orientation prior"; if the
Director wants a purer single edit, run R2-lite (table only, old mask) as a separate later design, not a change to these
marks.

**Single-change test and pass marks (fixed now).** The one change is the orientation prior. Marks M1 to M6 in each seed.
Credit check on the **dev** panel: take each seed's k = 1,024 net, score the 300 dev 9x9 mazes and the same 300 with rows
and columns swapped (evaluation only, made by code). The design's gap between the two scores must be at most half the
loop's gap; if the loop's own gap is 20 of 300 or less, report the check INCONCLUSIVE (no headroom).

**The result that would prove it wrong.** M6 fails in both seeds (at most 1,224 / 1,231 counts). Or the source guard
(M2) fails at eps = 0.3 (the residual may be too slow for the sums carry direction): reject at this eps, no retune under
these marks. Or the headline passes but the swap gap did not shrink: the gain is not from symmetry.

**Main risks.** The slowed residual may break sums or grids practice. The cross mask may hurt the narrow heads on sums.
The loop's non-positional weights may not be as direction-blind as I assume (the maze tokens are new in every
direction).

### R3. Refill loop

**Mechanism in plain words.** After each round the net writes its current best answer for every blank cell as an
ordinary token (the most likely token, scaled by how sure it is) and, next round, the blank cell shows that token beside
the blank. The same table that reads the puzzle's digits reads the net's own answer. A single learned mixing weight
starts at zero, so the net begins as the loop.

Sketch (not run): in `step`, with no gradient, read the current answer from `h`; `echo = tok(argmax) * confidence` at
blank cells and only after round 1 (the state is all zeros before then); `e = e + gain * echo`; then the base step.
`gain` is one zero-initialised number.

**What is new vs prior art.** Verified: TRM keeps a separate answer state y next to its latent z (F); masked discrete
diffusion feeds partially filled answers back (Ye, Gao, Gong et al., arXiv 2410.14157; F); self-conditioning feeds the previous
prediction back, but the fetched abstract does not say how (Analog Bits, arXiv 2208.04202; mechanism M). What differs:
the echo goes through the tied input embedding (the answer vocabulary is the input vocabulary), is confidence-weighted
and detached, and touches only blank cells. Low novelty (0.3, a guess): an engineering variant of TRM's y and
self-conditioning. It is the weakest novelty claim of the four.

**Why it might improve few-example learning (suggested, untested).** ON and OFF are the digit tokens 1 and 0
(`claude_rsn358m_maze.py:29`), which practice on sums has seen as inputs. The echo lets "my neighbour says ON" be read
with the machinery that reads digits, instead of hoping the state channel carries it. It also makes the answer channel
explicit rather than buried in 256 numbers per cell.

**Parameter budget.** +1 weight. Stored 1,645,727: +0.0001%.

**Generality.** Any task whose answer tokens are in the input vocabulary, which is true of all three kinds so far. No kind
label, no rule.

**How it plugs into the ruler.** `Net(base.Net)`; `echo_gain = nn.Parameter(zeros(1))` created last; `embed` stores the
blank-cell mask (`slot`) in a side attribute for `step` (the harness calls `embed` before `step` every time: `forward`,
`loop_train`, `loop_rounds` and `Learner.maze_batch` all do); `step` adds the echo before `super().step`. The baseline
`Learner` and everything else inherited. Cost: one output-head pass per round (about 2% of the blocks' multiply-adds, arithmetic). The side attribute is the fragile
part; a selftest should assert it is set before every `step`.

**Single-change test and pass marks (fixed now).** The one change is the echo. Marks M1 to M6 in each seed. Credit check
on the **dev** panel: zero `echo_gain` at inference on each seed's k = 1,024 net; if dev 9x9 falls by fewer than 10 of
300, the echo is a bystander. Two later designs are separate tests with their own single changes and the same M1 to M6,
not part of this ranking: R3b (reveal training: show randomly chosen true answer tokens as inputs during practice and
adaptation, which needs its own `Learner`) and R3c (also train the reverse direction, a replay-like backward pass).

**The result that would prove it wrong.** M6 fails in both seeds (at most 1,224 / 1,231). Or `|echo_gain|` stays below
0.05 after practice and after adaptation in both seeds (never used).

**Main risks.** The echo adds noise while the answer is still poor. If the net's own answer is wrong in the same way each
round, the echo locks it in. Both are suggested risks.

### R4. Twin-stream conflict-gated stop

**Mechanism in plain words.** Run the thinking twice from two slightly different starting states with the same weights.
Cells where the two runs give different answers mean the net is not finished. The stop head is shown how much the two
runs disagree, through one learned number, kappa, so it can hold off stopping while the twins disagree and let go once
they agree.

In symbols: stream B starts from h0 = sigma * noise with sigma = 0.5 (fixed now, never tuned); stream A from zero as in
the loop. Same blocks, same input, run as a batch of size 2B. c_t = fraction of blank cells where A and B predict
different tokens (detached). Stop logit q_t = halt(mean(z)) - kappa * c_t; kappa is one weight, initialised at zero. The
answer and the CE loss come from stream A only; the stop loss is the loop's BCE on stream A's exact correctness.

**What is new vs prior art.** Verified: self-consistency samples several reasoning paths and takes the most consistent
answer, at decoding time (Wang et al., arXiv 2203.11171; F); PABEE stops when a network's predictions stay unchanged for
several steps, which is our loop's own rule (arXiv 2006.04152; F); the equilibrium-model paper reports better
generalisation when the model reaches the same state from any start (arXiv 2211.09961; F abstract). Not found in these
sources: cross-stream disagreement fed to the stop head as an input. The brain link is the subthalamic conflict signal
that raises the decision threshold (S). Medium novelty (0.5, a guess), and it is the one idea that speaks to Ben's rule
about deciding its own thinking time.

**Why it might help (suggested, untested).** The loop's stop head is never trained on mazes and, as section 2 shows, does
not fire reliably on them. A disagreement signal does not depend on the kind of puzzle: unfamiliar puzzles should make
the twins disagree for longer. This is not a route to F_eq +10: reading longer than 16 rounds bought only 0 to 14 counts
of 300 (section 2), so the headroom in stopping is small. I rank R4 last for that reason.

**Parameter budget.** +1 (kappa). Stored 1,645,727. Compute about 2 times per round, in practice and adaptation (roughly
2 x 169 minutes per adaptation run if it scales; suggested).

**Generality.** Nothing about the puzzle appears anywhere.

**How it plugs into the ruler.** The heaviest plug-in of the four. `Net` keeps the state as [2B, T, D]; `forward`,
`loop_train` and `loop_rounds` are overridden to return stream A's logits and the conflict-adjusted stop; `infer_rounds`
returns stream A's predictions and the adjusted stop probabilities. The baseline `Learner.maze_batch` builds its state
from `embed` and slices logits against B-sized targets (`claude_fewex_bench.py:184-206`), so R4 needs its own `Learner`
(allowed by `PROTOCOL.md:29-33`) with the same 3 free plus 2 gradient rounds and, as the ruler requires, no stop loss on
mazes.

**Single-change test and pass marks (fixed now).** Marks M1 to M5 as in section 6. M6 (F_eq +10) is reported but I expect
it to fail; R4 is judged on the stop endpoint SE, fixed now, in each seed: at each of the four rungs k = 256, 1,024,
4,096, 16,384 on the holdout, (a) mean rounds on 9x9 is at most 24; (b) the learned-stop count is at least the
fixed-depth count minus 6 of 300 (the stop-failure rule in `RESULTS-EQ.md:72`); and (c) F_eq is at least the loop's
minus 2 points (counts of 300 summed over eight rungs at least 1,176 in seed 0 and at least 1,183 in seed 1). The loop
meets (a) in 1 of these 8 seed-rung cells (seed 1 at k = 1,024, 20.6 rounds; `RESULTS-EQ.md:126`).

**The result that would prove it wrong.** (a) fails in more than 2 of the 8 cells: conflict does not repair a stop that was
never trained on the new kind. Or kappa stays below 0.05 in absolute value after practice.

**Main risks.** After enough rounds the twins settle to the same state and never disagree, so the signal may vanish before
the answer is right; sigma may be a poor fixed value; doubled compute.

---

## 6. Pass marks shared by all four designs (fixed now)

These are `RACE-PASSMARKS.md` (lines 5 and 11) with `RACE-ADDENDUM-1.md` (F_all becomes F_eq), copied so each test is judged
on this page. Each seed is judged on its own; seeds are never pooled. The harness `scripts/claude_fewex_eq_bench.py` is
used unedited. Arms per design: the design practised (`--init pre`), the design fresh (`--init fresh`), the loop and the
plain net (baseline `eq-runs`, not retrained). Four adaptation runs per design, one per (seed, init).

| mark | meaning | seed 0 | seed 1 |
|---|---|---|---|
| M1 size | stored weights within 2% of the loop's 1,645,726 (1,612,811 to 1,678,641); all four are within 1% | pass by arithmetic | pass by arithmetic |
| M2 source guard | before any maze run: at least 190 of 200 on 4-digit sums and 190 of 200 on 5x5 grids of the guard panel, and every 2-D weight matrix has a nonzero fp32 gradient. Fail: report and stop. | | |
| M3 old kinds | before adaptation: at least 190 of 200 on each old kind and within 6 of 200 of the loop's; after both sleeps (64 and 16,384): each old kind within 6 of 200 of the loop's corresponding score | | |
| M4 beat plain | F_eq at least the plain net's + 5: the eight counts sum to at least | 931 (plain sum 811) | 926 (plain sum 806) |
| M5 beat fresh | F_eq at least the design's own fresh copy + 5: counts sum at least fresh sum + 120 | | |
| **M6 headline** | F_eq at least the loop's + 10: the eight counts (9x9 holdout, of 300 each) sum to at least | **1,464** (loop 1,224; F_eq 61.00) | **1,471** (loop 1,231; F_eq 61.29) |

**Proved wrong** (any design): M6 fails in both seeds (sum at most 1,224 and at most 1,231), or a gain comes with a broken
M2 or M3 (then rejected at this budget). If one seed is above the loop and one below, the design is **not promoted but
not rejected**, the reading applied to the sparse loop (`artifacts/claude-sparse-20260928/RESULTS.md:9-14`). Reaching 50% after 64
examples, the 7x7 and 11x11 panels, mean rounds, cap hits and fixed-depth counts are reported, not marked.

**Run cost.** The baseline loop took about 169 minutes per adaptation run on CPU (`RESULTS-EQ.md:196-201`); four runs plus
two practices per design. Queue files only, no rentals. Estimates for the designs are suggested.

---

## 7. Ranking

| rank | design | novelty (0 to 1, guess) | chance of M6 in both seeds (guess) | product | extra compute | first thing that kills it |
|---:|---|---:|---:|---:|---|---|
| 1 | R1 Reach channel | 0.6 | 20% | 12 | ~5% at 9x9 | link map never learns that walls block |
| 2 | R2 Soft-D4 loop | 0.4 | 30% | 12 | none | slowed residual breaks sums (M2) |
| 3 | R3 Refill loop | 0.3 | 25% | 7.5 | ~2% | echo unused or noisy |
| 4 | R4 Twin-stream stop | 0.5 | 3% | 1.5 | ~100% | twins agree from round one |

How I made the guesses (suggested): novelty from how much of the mechanism I verified in prior art (R3 almost all, R2
the recipe, R1 the parts but not the combination, R4 the parts and not the use). Chance from section 2: a real gain of
+10 needs about 4 times fewer examples, and one design's seed-to-seed spread on this ruler was 10 points. So even a true +10
average has roughly even odds of missing the both-seeds mark; I never put a chance above 30%. R1 and R2 tie; I break
the tie toward novelty.

If the Director orders runs by cost (suggested): R2 and R3 first (no extra compute; each needs its own practice), then R1,
then R4. R2 is also the cheapest check on how much of the gap is orientation-specific, which matters to reading any
later result.

---

## 8. Levers, rejected and deferred

**Levers from the literature that are not new architecture** (each would be its own single-change test if wanted):

| lever | evidence (F) | in our loop today | note |
|---|---|---|---|
| EMA of weights, 0.999 | TRM: removing it cost 7.5 points on Sudoku-Extreme | none (`claude_fewex_net.py:175-197`; `claude_fewex_bench.py:169-183`) | needs its own `Learner`; not novel; small expected gain |
| full gradient over more rounds | TRM: 1-step gradient cost 30.9 points | 2 gradient rounds per update (`claude_fewex_bench.py:202`), 1 to 6 in practice (`claude_fewex_net.py:166`) | already partly there |
| outer refinement loop | ARC Prize: +13 points | the loop itself | already there |
| detached history, last-step loss | RSM | free rounds are detached (`claude_fewex_net.py:120-126`) | already there |
| dihedral data augmentation | TRM for mazes; ARC Prize: 300 near max | none | not allowed: a rotated maze has a different layout key (`claude_fewex_data.py:91-94`), so augmenting the support would give the net more than k mazes. R2 is the ruler-legal analog. A ruling from the Director would be needed. |

**Rejected or deferred, with the reason:**
- Task register, hypernetwork or latent-program search (Miller-Cohen-style rule bias; LPN; attention-as-hypernetwork; CAVIA).
  Needs many training tasks (task-diversity threshold; LPN trains leave-one-out over many tasks; ARC Prize: task ids do not
  transfer). This ruler practises two kinds. Deferred until there is a many-kind ruler. If Ben wants paradigm-level
  novelty, this is where it would come from, and it needs a new ruler first.
- Test-time training as a design. The ruler's adaptation already is gradient fine-tuning on the k support mazes.
- Energy or diffusion refinement (IRED, masked diffusion, looped diffusion). A different training objective, not one
  change within 1% of the budget. R3 takes only the "feed the previous answer back" idea.
- Sparse mixture-of-experts loop: already run and NOT PROMOTED (`artifacts/claude-sparse-20260928/RESULTS.md:9`).
- Fast-weight patches, relation net, dendritic branches: running elsewhere. R1 differs from the relation net
  (`claude_relnet_net.py:2-12`, a GRU state for every pair of cells carried across rounds) in having no per-pair state:
  it carries nothing between rounds and computes a closure of one link map.
- Settle gate (H3): queued elsewhere, weak novelty (`claude_dir_h3_net.py`).
- Step-size conditioning (LoopFormer): would give the loop a round clock, which the design so far avoids.
- Two-timescale hierarchy (HRM): ARC Prize found about 5 points; TRM's separate networks cost 5.0 points.
- Slot or object memory: not separately searched, see section 9.

---

## 9. What I could not verify, risks, and the check log

**Tags.** F = fetched with the web-fetch tool; the tool returns a summary generated from the page, so numbers are as it
reported them and arXiv "abs" pages give abstracts only. S = surfaced in a search result (title and URL) but not read.
M = from my memory, not checked in this session. U = the page could not be read.

**Could not do.**
1. `curl` to arxiv.org was refused by the proxy (403 on CONNECT); I did not route around it. `pdftotext` is not installed.
   I used WebSearch and WebFetch instead, so every literature number is summary-level.
2. Three pages unread: arXiv 2609.22197 (fetch refused), emergentmind 2605.19943 ("Probabilistic Tiny Recursive Model",
   no text returned), arXiv 2511.16886v2 (PDF without text). The PubMed page for Foster and Wilson returned only a
   captcha; I used the Nature page instead.
3. Mechanisms not confirmed by the fetched abstracts: Analog Bits' self-conditioning, HM-RNN's boundary detector
   (arXiv 1609.01704, not used above), PonderNet's halting rule. Where I describe them I say so.
4. Brain claims: F for the successor representation and reverse replay; S for Miller-Cohen and the subthalamic
   conflict papers; M for Baddeley-style capacity and the "silicon builds symmetry in, brains learn it" remark.
5. Slot or object memory and hypernetworks were not searched beyond two titles each; I did not verify anything there.
6. Nothing was run. No torch, no plug-in code written, no gradient or shape checked. The plug-in sketches in section 5 are
   unchecked; R1's power-series stability (gamma below 1, row-softmax) is my reasoning, not a test.
7. My novelty statements come from about seventy search and fetch calls (some refused). Not finding a combination is not evidence it does not
   exist.
8. The chance and novelty numbers are guesses. The 30% cap and the 4 times figure are the only firm anchors.
9. I did not open the sealed panel `readpanel320`, the holdout JSONs or the checkpoints; all baseline numbers come from
   `RESULTS-EQ.md`, and `scripts/claude_dir_h9_budget.py` re-derives F_eq from that file and asserts it matches the printed
   value.

**Repo facts and where they were checked** (all *shown*):

| fact | where |
|---|---|
| loop 1,645,726 and plain 1,619,965 stored weights; both recounted from layer shapes | `RESULTS-EQ.md:19-22,196-203`; `budget.json` (script asserts both strings appear) |
| loop counts and F_eq 51.00 / 51.29; plain 33.79 / 33.58 | `RESULTS-EQ.md:43,47,45,49` |
| stop rows: rounds, cap hits, fixed-16 | `RESULTS-EQ.md:76-86,120-130` |
| stop failure rule (6 of 300) | `RESULTS-EQ.md:72` |
| rungs, 2,048 updates, N_BATCHES 512 | `claude_fewex_eq_bench.py:27-29,115-116`; `claude_fewex_bench.py:28` (32 x 4) |
| stop rule: q > .5 and 3 equal predictions | `claude_fewex_bench.py:76-78` |
| Learner: 3 free + 2 gradient rounds, no stop loss on mazes | `claude_fewex_bench.py:184-206` |
| relative bias tables, narrow-head strip, loop step, read, stop BCE | `claude_fewex_net.py:35-36,41-45,77-87,161-172` |
| plug-in contract; Learner allowed | `PROTOCOL.md:29-33` |
| maze marker tokens and ON/OFF tokens | `claude_rsn358m_maze.py:28-29` |
| sums and grids tokens | `claude_rsn358a_envs.py:59-71,188-194`; `claude_fewex_data.py:21-34` |
| maze rooms (k = (s-1)//2) | `claude_fewex_data.py:49-88` |
| sparse loop verdict and spread | `artifacts/claude-sparse-20260928/RESULTS.md:9-14,43` |
| race marks and F_eq substitution | `RACE-PASSMARKS.md:5,11`; `RACE-ADDENDUM-1.md:5` |
| relation net design | `claude_relnet_net.py:2-12`; `artifacts/claude-relnet-eq-20260928/PASSMARKS-C.md` |
| H3 plug-in pattern | `claude_dir_h3_net.py:1-60` |

**Sources** (tag in brackets):
- TRM https://arxiv.org/abs/2510.04871 [F], https://arxiv.org/pdf/2510.04871 [F]
- HRM https://arxiv.org/html/2506.21734v2 [F]; ARC Prize analysis https://arcprize.org/blog/hrm-analysis [F]
- Recursive Stem Model https://arxiv.org/pdf/2603.15641 [F]
- Dissecting HRM https://arxiv.org/html/2609.22197 [U]; https://www.emergentmind.com/papers/2605.19943 [U]; https://arxiv.org/pdf/2511.16886v2 [U]
- PonderNet https://arxiv.org/abs/2107.05407 [F abstract]; PABEE https://arxiv.org/abs/2006.04152 [F]
- LoopFormer https://arxiv.org/abs/2602.11451 [F]; Looped MoE https://arxiv.org/abs/2605.09165 [F]; Mixture-of-Recursions https://arxiv.org/abs/2507.10524 [S]
- Huginn https://arxiv.org/abs/2502.05171v2 [F]; looped reasoning https://arxiv.org/abs/2502.17416 [F]
- Path independence https://arxiv.org/abs/2211.09961 [F abstract]; recall networks https://arxiv.org/abs/2202.05826 [F]
- TTT https://arxiv.org/abs/2411.07279 [F]; LPN https://arxiv.org/html/2411.08706v3 [F]; CompressARC https://arxiv.org/html/2512.06104v1 [F]
- IRED https://arxiv.org/abs/2406.11179 [F]; masked diffusion https://arxiv.org/abs/2410.14157 [F]; looped diffusion https://arxiv.org/html/2605.26106v1 [F]; recursive masked diffusion https://pith.science/paper/2606.18022 [F, a review page]; Analog Bits https://arxiv.org/abs/2208.04202 [F abstract]; EBT https://arxiv.org/abs/2507.02092 [S]
- Task diversity https://arxiv.org/html/2306.15063v1 [F]; attention as hypernetwork https://arxiv.org/abs/2406.05816 [S]; CAVIA https://arxiv.org/pdf/1810.03642 [S]
- Log depth https://arxiv.org/abs/2402.09268 [F]; graph connectivity https://arxiv.org/html/2510.19753v1 [F]; APPNP https://arxiv.org/abs/1810.05997 [S]
- Residual pathway priors https://arxiv.org/abs/2112.01388 [F]; self-consistency https://arxiv.org/abs/2203.11171 [F]; RevThink https://arxiv.org/abs/2411.19865 [F]; DreamCoder https://arxiv.org/abs/2006.08381 [F]
- HM-RNN https://arxiv.org/abs/1609.01704 [F abstract]
- Successor representation https://www.nature.com/articles/nn.4650 [F]; reverse replay https://www.nature.com/articles/nature04587 [F]; PubMed 16474382 [U, captcha]
- Miller and Cohen 2001 https://www.annualreviews.org/content/journals/10.1146/annurev.neuro.24.1.167 [S]; Frank 2006 https://pubmed.ncbi.nlm.nih.gov/16945502/ [S]; Cavanagh et al. 2011 https://www.nature.com/articles/nn.2925 [S]

Web pages were treated as data; nothing in any of them was followed as an instruction.
