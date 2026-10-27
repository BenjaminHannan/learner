# Loop net: learning a new kind (mazes) from few examples after practice — reading notes

Date 2026-09-27. Evidence labels: **shown** = measured in that paper's own setting; **suggested** = argued or indirect;
**untested** = nobody has measured it for our case. No paper below tests a looped/recurrent net transferring from one
task kind to a new one. Every card in part 2 is therefore **untested** for our question.

Plain summary (for Ben): the looping-net papers all train one puzzle type from scratch; the transfer papers are about
ordinary nets. The strongest leads are (1) make sure the loop is graded after enough rounds when it learns mazes,
(2) let it squeeze more learning out of each maze by working on the same batch several times while it keeps its
"scratch paper", and (3) carry over only the parts of the practised net that transfer (attention), or align the
output first before changing the whole net.

## 0. Facts checked in the repo (read only, nothing edited)

- Current benchmark `scripts/claude_xfer1_bench.py` (LOCKED): mazes arrive in batches of 32 fresh mazes via
  `model.learn(items)`; checks at 512 … 32768 examples on a 200-maze 7x7 dev panel; bar = 75% right;
  `examples_to_bar` (log-interpolated), `maze_auc`, `transfer = maze_auc − fresh_auc`; eval `predict(..., MAX_ROUNDS=48)`;
  also a 9x9 report. No kind labels (matches the brief). Practice length `PRACTICE_STEPS` is fixed by the harness.
- **The metric counts mazes handed over, not optimizer steps.** How many updates the learner makes per handed batch
  (reuse, augmentation, deep supervision) is the learner's choice. This makes cards 2 and 6 cheap levers, and it means
  a fair comparison must give the plain net and the fresh loop the same option.
- The learner modules `claude_xfer1_net.py` / `claude_xfer1_adapt.py` were **not present** in `scripts/` when I looked,
  so the loop details below come from the older `claude_rsn358m_run.py` / `claude_rsn358a_run.py`: TRAIN_ROUNDS 16,
  GRAD_ROUNDS 6, TEST_ROUNDS 48; maze phase: total ~ U{1..16}, k ~ U{1..min(total,6)}, loss = mean cell CE over the
  last k rounds + 0.5 × BCE(stop logit, exact); AdamW lr 3e-4, wd 0.1, betas (0.9, 0.95), 200-step warm-up, clip 1.0.
  Maze tokens reuse existing tokens (`/ + *`) and the answer reuses digit tokens 0/1, so nothing in the head is new.
  Check these against the xfer-1 learner once it exists.
- From-scratch trial (brief): loop loss ~0.5 at 2,000 steps × 64 = 128k mazes, i.e. 4× the harness's largest count.

## 1. Papers

### 2106.04537 — Schwarzschild et al. 2021, "Can you learn an algorithm?" (Deep Thinking). Read in full.
- Mechanism: a residual block (4 conv layers, skip every 2) shared across iterations; more iterations at test = "think
  longer". No recall of the input, no halting head; at test they take the iteration with highest mean confidence.
- Maze recipe: 50,000 9x9 mazes (DFS-carved, padded to 32x32 pixels), test 10,000 13x13. Width 128 (conv 3x3), head
  3 convs (32, 8, 2), no batch norm, no biases. Loss: mean per-pixel CE at the final iteration only, fixed m iterations,
  full backprop through all iterations (no detaching). SGD momentum 0.9, wd 2e-4, lr 0.001 after 5-epoch warm-up,
  ×0.1 at epoch 175, 200 epochs, batch 50. No EMA. ~7 GPU-hours per maze model.
- Maze results (shown): 13x13 accuracy, recurrent vs feed-forward at equal effective depth: depth 20: 12.66 ± 0.44 vs
  7.94 ± 0.36; depth 44: 29.72 ± 1.22 vs 22.53 ± 1.14. Dilated filters, depth 36: 50.50 ± 7.97 vs 26.54 ± 2.13. Trained
  with 20 iterations: about half of 13x13 solved; +5 test iterations: >70%. In-distribution (9x9) >97% for both.
- Slow/unstable training: prefix-sum training "unstable" — they keep only models reaching 100% train accuracy, use
  gradient clipping 1.0 and warm-up. Transfer across tasks: not studied.

### 2202.05826 — Bansal et al. 2022, recall + progressive loss. Read in full.
- Mechanism: (1) recall = concatenate the raw input to the features before every block application (+1 conv to map
  back to width); (2) progressive loss: start from a random partially-run state, detached, and train to finish from it,
  so the block cannot count iterations.
- Exact recipe (Algorithm 1): n ~ U{0, m−1}, k ~ U{1, m−n}; run n iterations with no gradient (detach φ_n); run k more
  with gradient → ŷ_prog; separately run a full m-iteration pass with full backprop → ŷ_m;
  L = (1−α)·CE(ŷ_m) + α·CE(ŷ_prog). Loss at one output only (not every round). m = 30.
  Mazes: width 128, α = 0.01 (grid {0, 0.01, 0.1, 0.5, 1}), Adam lr 1e-3, wd 2e-4, 10-epoch warm-up, 50 epochs,
  no clipping, no decay listed. Prefix sums: width 400, α = 1, Adam 1e-3 decayed ×0.01 at epochs 60/100, clip 1.0,
  150 epochs. Chess: α = 0.5, SGD 0.01. 20% of train held out; best-validation checkpoint kept. No norm layers, no EMA,
  no halting (models converge to a fixed point, so a large fixed iteration count is safe).
- Maze results (shown; train 9x9, m = 30): 13x13: DT-Recall 99.94 / 99.88 (α 0 / 0.01), DT 85.6–86.1, FF 38.2.
  59x59: DT-Recall α = 0.01 97.30 ± 0.68 (peak at iteration 984), α = 0 82.72 ± 15.14, DT and FF 0.00. 201x201: 74%
  (most failures are 1–7 wrong pixels out of 166,464). A loss weighted to penalise run time: 0% on 59x59 despite >99%
  train accuracy.
- Slow training / failure: 1 in 5 recall maze models and ~half of chess models failed to reach 99% train accuracy and
  were dropped from averages (so seed failure is common). Without recall, models "overthink" (accuracy collapses with
  more iterations; features blow up). Random n beats n = 0 (prefix sums 512-bit: 97.12 ± 1.88 vs 90.27 ± 5.95).
  **Mazes wanted the full-budget term to dominate (α = 0.01), unlike prefix sums (α = 1).**

### 2506.21734 — Wang et al. 2025, Hierarchical Reasoning Model (HRM). Read in full (no appendix beyond references).
- Mechanism: two transformer modules; L updates T times per H update, N cycles; only the last L and last H step carry
  gradient ("1-step gradient", justified by a fixed-point argument); deep supervision: M segments per sample, state
  detached between segments, **one optimizer step per segment**; halting by a Q-head on z_H trained by Q-learning
  (halt target = answer exactly right; continue target = max of next-step Q), with M_min = 1 or, with prob ε,
  U{2..M_max}.
- Recipe: encoder-only blocks with RoPE, GLU, RMSNorm, no biases, **post-norm**, truncated LeCun-normal init;
  Adam-atan2; **constant lr with linear warm-up** (value not given in the paper); stablemax instead of softmax "for
  small-sample experiments"; initial states z0 drawn once (trunc. normal, std 1) and fixed; inputs merged by addition.
  N = T = 2 (per TRM). 27M params. No augmentation for mazes.
- Maze results (shown): Maze-Hard 30x30 (shortest path >110), 1,000 train / 1,000 test: HRM 74.5%; "Direct pred"
  (8-layer transformer, same size, same recipe) 0.0%; a 175M transformer on 1M mazes <20% pass@64 (cited).
- Slow training claim (suggested): plain RNNs converge too early (updates shrink, later steps inert); BPTT costs memory.
  TRM (below) disputes the fixed-point justification.

### 2510.04871 — Jolicoeur-Martineau 2025, Tiny Recursive Model (TRM). Read in full.
- Mechanism: one 2-layer net; latent z ← net(x, y, z) n times, then answer y ← net(y, z); T−1 such recursions with no
  gradient, then 1 with **full backprop through all n+1 calls**; deep supervision up to N_sup = 16 with (y, z)
  detached and carried; halting = BCE of a q-head on "answer exactly right" (no continue loss, no extra pass); during
  training a sample stops when q > 0; at test all 16 steps run.
- Recipe: AdamW β = (0.9, 0.95), lr 1e-4, **wd 1.0** (Sudoku, Maze), 2K-iteration warm-up, batch 768, hidden 512,
  stablemax CE, **EMA 0.999**, T = 3, n = 6 (42 effective layers per step), 60k epochs. Mazes: attention version;
  **8 dihedral augmentations** per maze; a puzzle-embedding of shape [0,1,D] added to input. 4 L40S < 24 h.
- Maze results (shown): Maze-Hard 1,000 examples: TRM-attention 85.3% (7M), HRM 74.5% (27M), direct 0.0%;
  MLP-mixer TRM 0.0% on mazes (it wins only on 9x9 Sudoku).
- Sudoku-Extreme ablation (1K train; shown): TRM 87.4; with continue-loss ACT 86.1; separate nets 82.4; **no EMA 79.9**;
  4 layers n = 3 79.5; self-attention 74.7; T = 2, n = 2 73.7; **1-step gradient 56.5**; HRM 55.0.
- Why slow/overfits (shown/suggested): on small data HRM "overfits quickly and then diverges" → EMA; more layers
  overfit → 2 layers best; backprop through only the last k = 4 of 7 calls did not help; removing ACT (staying on a
  sample until solved) hurt ("too much time on the same samples"); tying input embedding to output head, MoE, and
  true fixed-point solving (TorchDEQ) all hurt. Cited ARC Prize analysis (not read): deep supervision alone doubled
  ARC accuracy 19% → 39%; the inner recursion added only 35.7 → 39.0.

### 2609.05988 — Tran Bao et al. 2026, DART. Read in full.
- Mechanism: replace the one-hot target by a soft target (one-hot + Gaussian noise, noise clipped to (−0.5, 0.5), then
  softmax); a WGAN critic scores [input, answer-distribution]; L = CE + λ·(−critic(ŷ)). Critic = same backbone
  (recurrent, T = 5), weight clipping 0.01, one critic update per batch. λ not stated in the text I read.
- Recipe (DTS maze): recall DT, width 128, block = 2 conv layers, T = 30 training iterations, train 9x9, AdamW lr 1e-3,
  critic lr 5e-5, 10-epoch warm-up, 50 epochs, σ = 0.3 (0.1 similar), 20% validation hold-out. Critic roughly doubles
  trainable params; chess epoch time 1.77× CE (progressive CE 1.42×). TRM Sudoku: hidden 128, H 3, L 6, trained on
  1,000 grids with 20% masked, tested at 30/40/50%.
- Maze results (shown; seeds apparently 2): 13x13 all ≈ 99.9–100. 31x31 peak: CE 73.92 ± 26.01 (one seed ≈ solves, one
  stuck ≈ 47.9), progressive CE 75.01 ± 16.69, **label smoothing ε = 0.3 98.22 ± 0.64**, Gaussian soft target without
  critic 59.58 ± 38.86, DART 99.91 ± 0.13. Trajectories: CE solves 51.6% of 31x31 at least once, ends 43.8%; DART 100%.
- Relevance: an easy-to-hard (bigger maze) fix, not a sample-efficiency one. CE failure is seed-bimodal.

### 2609.26487 — Krishna et al. 2026, "When recursive models finish computing". Read in full (analysis paper).
- No training recipe of its own: analyses released TRM checkpoints (hidden 512, H cycles 3, L cycles 6, 2 layers,
  nominal 16 outer steps, bfloat16, StableMax CE; maze checkpoint H 3, L 4).
- Findings (shown): running 16 → 512 steps: hard Sudoku 59.2% → 87.5% (attention), 74.4% → 91.9% (MLP); ~2/3 of
  step-16 failures were unfinished. Latent motion (relative update ‖Δz‖/‖z‖) separates finished from unfinished:
  step-16 median δL 0.025 solved vs 0.761 failed (~30×). Solved states almost never revert (859/875; MLP 919/919).
  Maze-Hard: 800/1000 match at step 3; 806 ever; 788 at step 16 (18 lost); of 212 non-matches 191 are valid paths
  (not an issue for our perfect mazes, where the path is unique).
- Relevance: a free "am I done?" signal for the stop head; nominal-budget failures can be unfinished computation.

### 2202.10054 — Kumar et al. 2022, LP-FT. Main text and Appendix B read in full; Appendix A proofs skimmed only.
- Mechanism (theory in 2-layer linear nets, shown empirically): fine-tuning with a badly aligned head (random or zero)
  moves the feature extractor a lot on the fine-tuning data and not elsewhere ("feature distortion"); fixing the head
  first by linear probing (LP), then fine-tuning everything (FT), moves features 10–100× less.
- Recipe: LP = ℓ2-regularised logistic regression on frozen features (or, on ImageNet, 5 epochs at lr ∈ {0.01, 0.03,
  0.1}); then FT at a **lower lr** (ImageNet FT-only sweep {1e-4, 3e-4, 1e-3}; LP-FT's FT stage {1e-5, 3e-5, 1e-4});
  cosine schedule, batch 64 (128 ImageNet), early stop on ID validation; equal total compute to FT.
- Results (shown): mean over 10 shifts ID 85.1 (FT) / 82.9 (LP) / 85.7 (LP-FT); OOD 59.3 / 66.2 / 68.9. Living-17:
  features move ~20× less with LP-FT; 10× head lr gets 80.4 OOD and L2-to-init 80.0 vs FT 77.7, LP-FT 82.6.
  FT beats LP OOD when features are weak (MoCo-v1) or shift is small (CIFAR-10.1). Scratch is far worse than all.
- Relevance: about OOD robustness with good features, not sample efficiency; no recurrent nets.

### 2505.22308 — Shinnick et al. 2025, procedural pretraining (found via search). Read in full (short paper).
- Setup: 2-layer, 4-head, width-16 GPT-2 nets pretrained on procedural data (k-Dyck, Dyck-shuffle, stack, identity,
  set, cellular automaton rule 110); fine-tuned (AdamW 1e-3, wd 1e-3, 10^4 steps, batch 1000, fresh data, 10 seeds).
- Findings (shown): different procedural data help different skills; **attention-only transfer (fresh MLPs and
  embeddings) often beats full transfer** — Haystack from identity: full 18.8 vs attention-only 99.0 (random init
  11.3); from set: 18.9 vs 88.9. **Full transfer can be worse than random init**: reversed addition from stack 34.9,
  from set 44.6 vs random 76.4. MLP-only helps sometimes (reversed addition). Shuffling pretrained weights removes most
  of the gain for Haystack/Addition (structure, not scale). Set-attention + automaton-MLPs combined is good on all 4.
- Relevance: the closest evidence on "which practised parts help a new kind"; transformers, not loops.

### 2502.19249 — Hu et al. 2025, pre-pretraining on formal languages (found via search). Main text + Appendix B read;
proofs skipped.
- Setup: Pythia-160M on C4 for 10,000 steps (≈665M tokens), after t0 steps of formal-language pre-pretraining; AdamW
  5e-4, cosine, warm-up 1,000 steps (re-warmed in the second stage), wd 0.1, clip 1.0, batch 32 × 2048 tokens.
- Findings (shown): k-Shuffle-Dyck best; **there is an optimal pre-pretraining length (500 steps for Shuffle-Dyck,
  1,000 for k-Dyck); more is worse**; random binary/integer strings are harmful (higher loss than none); copy language
  ww unhelpful; n-gram look-alikes of Shuffle-Dyck worse (structure matters). Marginal rate of substitution 7.15
  (160M) and 17.3 (1B: same final loss with 33% fewer tokens). Attention heads found in pre-pretraining stay important
  after natural-language training (ablating them hurts more than random heads).
- Relevance: practice length and practice content matter; too much practice can reduce transfer.

## 2. Hypothesis cards (ranked)

Common test for every card (fix before running): harness `claude_xfer1_bench.py`, dev split, ≥3 seeds, arms
practised-loop, fresh-loop, practised-plain; primary = practised-loop `examples_to_bar`; secondary = `transfer`
(maze_auc − fresh_auc) and `practice_acc` guard. Default pass mark: median `examples_to_bar` of the practised loop at
most half the unchanged baseline (one log2 check step), `practice_acc` down by no more than 0.05; tighten once the
baseline's seed spread is measured. Generic changes (cards 3, 4, 6, 7, 8) are applied to all three arms; loop-only
changes (1, 2) get the plain analogue named in the card. Holdout only after a dev pass.

### Card 1 — Grade the loop after enough rounds while it learns mazes. MAZE PHASE ONLY, loop only.
- Change: add Bansal's full-budget term. L = 0.99 · CE(after 16 rounds, gradient through all 16) + 0.01 · (current
  random-round loss). Nothing else.
- Mechanism: with total ~ U{1..16}, a quarter of batches stop at ≤4 rounds, where a 2-layer block may not be able to
  trace a path. Those batches reward guessing path-like cells, not a round-by-round procedure — a possible cause of the
  ~0.5 plateau. Bansal found mazes wanted α = 0.01 (full budget dominant); prefix sums wanted α = 1.
- Source recipe: 2202.05826 Alg. 1: n ~ U{0,m−1}, k ~ U{1,m−n}, L = (1−α)L_max + αL_prog, α = 0.01, m = 30,
  Adam 1e-3. Evidence: shown for conv DT mazes (59x59: 97.3 vs 82.7 at α = 0); untested for looped transformers or
  transfer.
- Free check first (no training change): log the current maze-phase loss by total-round bucket (1–4, 5–8, 9–12,
  13–16). If the 13–16 bucket also sits near 0.5, this card's mechanism is wrong; skip it.
- Expected: practised loop and fresh loop both drop below the plateau sooner; practised loop reaches the bar ≥2×
  sooner.
- CPU cost: ~2–3× per step (an extra 16-round pass with full backprop; memory ~16/6 of today's grad path).
- Proven wrong if: the loss by bucket is flat (above), or with the term added the practised loop's
  `examples_to_bar` does not improve by ≥2× on ≥2 of 3 seeds.

### Card 2 — Deep supervision with carried state: several updates per handed batch. MAZE PHASE ONLY, loop only.
- Change: in `learn(items)`, run up to N_sup supervision steps on the same 32 mazes; each step starts from the
  previous step's detached state, runs (T−1) no-grad segments + 1 grad segment, takes one optimizer step on
  CE + BCE(stop, exact); drop mazes whose stop logit > 0.
- Mechanism: each maze gives many updates, and later updates start from a half-solved state, so the loop practises
  "continue from where I am" at effective depths well beyond 16 rounds. Because the metric counts mazes, not steps,
  this targets the metric directly.
- Source recipe: TRM Fig. 3 (N_sup = 16, T = 3, n = 6, halt when q > 0, full backprop through the last recursion,
  AdamW 1e-4, wd 1.0, EMA 0.999); HRM Fig. 4 (detach between segments, optimizer step per segment). Evidence: shown
  that HRM/TRM reach 74.5–85.3% on 30x30 mazes from 1,000 examples (×8 augmentation); single-step supervision halves
  ARC accuracy (secondary source). Untested for transfer.
- Required control: same number of optimizer steps per batch but state reset each step (plain reuse), for the loop
  and for the plain net. Card passes only if carried state beats plain reuse.
- Expected: large drop in `examples_to_bar` for both loops; the practised loop gains more if practice taught a
  reusable refine step.
- CPU cost: up to N_sup× optimizer steps per batch (training-time ACT kept HRM under 2 steps per sample on Sudoku).
- Proven wrong if: carried-state loop ≤ plain-reuse loop at matched steps, or practised loop gains no more than the
  fresh loop (transfer unchanged).

### Card 3 — Carry over only the practised attention. MAZE PHASE ONLY (initialisation), both arms.
- Change: start the maze phase from practised attention weights (incl. the row/column offset-bias table); MLPs and
  token embeddings fresh (Shinnick's T_attn). Then fine-tune everything as now.
- Mechanism: attention carries general routing ("look along rows/columns, find matching cells"); MLPs store
  practice-specific rules (carry digits, Latin symbols) that may fight the maze rule (negative transfer).
- Source recipe: 2505.22308 §4.1: T_attn = (E_rand, A_pre, F_rand), full fine-tune, AdamW 1e-3, wd 1e-3.
  Evidence: shown in 2-layer GPT-2 on sequence tasks (e.g. 99.0 vs 18.8 full transfer); untested for loops.
- Expected: practised-loop `examples_to_bar` below both full transfer and fresh loop; if full transfer is currently
  worse than fresh (negative transfer), this should remove the gap.
- CPU cost: none.
- Proven wrong if: attention-only ≥ full transfer's `examples_to_bar` on ≥2 of 3 seeds AND ≥ fresh loop's. (A diagnostic
  either way: run MLP-only too if budget allows, as a second card.)

### Card 4 — Align the output first, then fine-tune (LP-FT). MAZE PHASE ONLY, all arms.
- Change: stage A — freeze the body (all blocks, norms, offset bias); train only token embedding, output head and stop
  head at 10× the current lr for the first ~10% of maze steps; stage B — unfreeze all at 1/10 the current lr.
- Mechanism: the practised head maps states to digits for sums/grids, so it is badly aligned for "on path / off path".
  Large head errors pull the whole body hard (feature distortion), wiping practised structure. Aligning the head first
  keeps the body's changes small.
- Source recipe: 2202.10054: LP 5 epochs at lr {0.01–0.1}, then FT at lr {1e-5–1e-4} (10× below FT-only), cosine, equal
  total compute. Evidence: shown for OOD accuracy with good pretrained features; untested for sample efficiency and
  for loops. Our head is practised, not random, so the premise holds only as "misaligned head".
- Expected: smaller change in hidden states on the practice panel (paper: 10–100× less), better `practice_acc`
  guard, modest (not large) gain in `examples_to_bar`.
- CPU cost: stage A cheaper than full steps; none overall.
- Proven wrong if: stage A reaches ~0% on the maze panel (practised features not maze-ready, premise fails), or hidden
  states move as much as with plain fine-tuning, or `examples_to_bar` is no better.

### Card 5 — Practise less. PRACTICE PHASE.
- Change: stop updating in `Practice.step` after a fraction f of PRACTICE_STEPS (f ∈ {0.25, 0.5}; 1.0 = today).
  (The harness fixes the number of batches offered, not how many the learner uses; confirm with the harness owner.)
- Mechanism: past an optimal length, practice specialises weights to sums/grids and lowers plasticity for a new kind.
- Source recipe: 2502.19249 §4: sweep pre-pretraining length (500–4,000 steps); optimum 500 (Shuffle-Dyck) or 1,000
  (k-Dyck); longer was worse. Evidence: shown for 160M LMs on formal → natural language; untested for loops/mazes.
- Expected: a U-shape in `examples_to_bar` over f, with the best f < 1.
- CPU cost: saves practice time (practice checkpoints are cached per net code, so each f is a new cache key).
- Proven wrong if: `examples_to_bar` is flat or improves monotonically with f (longer practice never hurts).

### Card 6 — Eight views of each maze (dihedral augmentation). MAZE PHASE ONLY, all arms.
- Change: in `learn(items)`, also train on the 8 rotations/reflections of each handed maze (start/goal and path move
  with it).
- Mechanism: the maze rule is symmetric; the offset-bias table and the net must otherwise learn each direction from
  separate examples.
- Source recipe: TRM §5: "Maze-Hard uses 8 dihedral transformations per data example" (HRM used none). Evidence:
  suggested (no ablation of augmentation alone). Rules check needed: augmented mazes are derived from handed mazes;
  confirm the harness counts them as allowed.
- Expected: `examples_to_bar` down by up to ~8× for all arms; little effect on `transfer`.
- CPU cost: 8× steps (or 8× batch) per handed batch.
- Proven wrong if: `examples_to_bar` improves by less than 2× for all arms.

### Card 7 — Evaluate an averaged copy of the weights (EMA). MAZE PHASE ONLY, all arms.
- Change: keep an EMA of the weights during the maze phase and score the EMA copy.
- Mechanism: smooths noisy small-batch updates; TRM found it prevented collapse on small data.
- Source recipe: TRM EMA 0.999 (Sudoku ablation: 87.4 with, 79.9 without). Deviation needed: the harness's first check
  comes after 16 steps of batch 32 and the last after ~1,024, so 0.999 would score nearly the unadapted net early.
  Use a bias-corrected EMA with decay min(0.99, (1+t)/(10+t)). Evidence: shown for 60k-epoch small-data training;
  untested for short streaming adaptation.
- Expected: small gain and lower seed spread, mainly at 4k–32k examples.
- CPU cost: negligible.
- Proven wrong if: EMA copy is not better than raw weights at ≥4 of 7 checks on ≥2 of 3 seeds.

### Card 8 — Soften the path target (label smoothing 0.3). MAZE PHASE ONLY, all arms.
- Change: cell CE with label smoothing ε = 0.3 (stop-head target unchanged).
- Mechanism: one-hot targets are brittle as mazes grow; smoothing reduced seed-bimodal failure when scaling up.
- Source recipe: DART Table 5 baseline, ε = 0.3 (the full DART critic is ~1.8× cost and a larger change; try only if
  this helps). Evidence: shown for conv DT trained 9x9 → tested 31x31 (98.2 ± 0.6 vs 73.9 ± 26.0, ~2 seeds); at 13x13
  it made no difference. Our main metric is in-distribution 7x7, so expect effect mainly on the 9x9 report.
- Expected: little change in `examples_to_bar`; better `maze9`, lower seed spread.
- CPU cost: none.
- Proven wrong if: `maze9` does not improve and seed spread does not shrink.

Considered, not carded: practising on a grid reachability kind (Shinnick/Hu show specific practice data builds
specific skills), but it shrinks the gap between practice and "new kind" and changes Ben's question; running more
test rounds / a motion-based stop (Krishna) — the harness already evaluates with up to 48 rounds, so only the
stop rule is open; stablemax loss (HRM/TRM) — no ablation reported.
