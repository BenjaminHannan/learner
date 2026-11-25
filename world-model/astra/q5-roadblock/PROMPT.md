# Roadblock: a small learned world model for Crafter is stuck just short of its marks. What single change next?

You cannot see our code, so everything you need is in the briefing below. Please label every claim **shown** (follows from the numbers below), **suggested** (your inference) or **untested**. Keep the board-model history and the conv world model separate. Propose **one change at a time**. For each one, give pass marks fixed in advance, the result that would prove it wrong, and honest odds. End with a 5-line plain-language summary for a high-school senior.

# Problem 7 briefing: grounding a small learned world model on real Crafter steps (stuck)

Written for an outside expert who cannot see the code. Claim labels: **shown** = measured or read in code; **suggested** = an inference that has not been proved; **untested** = not run. Numbers are copied from the project's result files. Where the files disagree or leave something unstated, this says "unclear". The project's own reviewers are called the lead (the coordinating agent), Neon (the main diagnosis agent), and Astra and Fable (earlier outside advisors). "Rank N" is the number of an idea in Neon's ranked list of next steps: Rank 1 was a no-training X-ray, Rank 2 was the scorer fixes that became Ruler B, Rank 3 and Rank 6 are below, and Ranks 4 and 5 were never run. "Rank 7" is the next try after Rank 6, the one change recommended by Neon's Rank 6 diagnosis (not the list's original Rank 7, which was sharper 64x64 frames). "Step N" / "S N" are the earlier board-model tries.

## 1. Goal and rules

**Goal.** Teach a small, fully learned world model to predict the next game frames of Crafter (an open 2D Minecraft-like survival game) from real recorded steps and the action taken. It must beat strong simple baselines 1, 3 and 5 steps ahead on unseen worlds and clearly use the action, so it can become the grounded "imagination" a later policy practises in.

**Rules that constrain it**
- **Real pairs only.** World-model gradient comes only from k=1 real pairs (frame t, action, frame t+1). Rollouts at k=3 and k=5 are open-loop and only scored, never trained. No real intermediate frame may enter a rollout.
- **No hand rules.** Nothing game-specific is written into the model: no hand rules, lookup tables, pixel masks or action-ID special cases. The model sees pixels and its own actions only. The game's internal state may be used only by the scorer.
- **Pinned tests.** One change per try. Marks are pinned in writing before any run. An idea is dropped after 3 clean misses.
- **Data discipline.** Dev worlds score the tries. A sealed set of 16 worlds, never opened, may be opened once, only after a two-seed dev PASS. Pilots may not touch dev or sealed data.
- **Compute.** A Mac (CPU for short probes, its built-in GPU for training) and one 16 GB consumer GPU on a PC. Each test wave stays under about 30 minutes. No paid compute.
- **Design history.** The first design kept one shared "thinking" trunk as the world model. After that failed (Rank 3 below), the lead moved to a separate small conv world model. Per the lead, a conv-model pass would mean "a separate world-model part works", **not** that Problem 7 is solved.

## 2. The models, data and marks

### 2a. Board model (shared trunk; steps 1-6 and Rank 3)
- **The board.** 64 rows (24 slow, 40 fast) of width 256, updated over several ticks by 2 attention plus mixture-of-experts blocks (16 experts, top-2).
- **Size: unclear.** The files give 2.47M-2.61M active and 6.1M-10.6M total parameters. Trunk width is 256 in one file and 192 in another.
- **Inputs.** A 16x16 frame enters as 16 patch tokens read as context (2 ticks per read). The action enters as one extra row; Rank 3 added FiLM to broadcast it to all rows.
- **Prediction.** One imagine pass gives the next board rows. The decoder reads only those imagined rows, never the context or the action row. It was first an MLP head predicting frame change, then a closed-form ridge readout, then (Rank 3) a per-row LayerNorm decoder.

### 2b. Conv world model (Rank 6 and Rank 7)
- **Architecture (2,688,963 parameters).** Encoder: one frame, 16x16x3 to 16x16x64 (two 3x3 convs plus coordinate channels). Dynamics: an action-FiLM conv U-Net (16 to 8 to 4 to 8 to 16) with 4x4 self-attention at the bottleneck and update z' = z + 3·tanh(raw/3). Decoder: two 3x3 convs.
- **Loss.** 1.0·reconstruction + 1.0·imagined residual + 0.25·imagined absolute + 0.05·latent match to encode(x_{t+1}).
- **Rollout.** Encode x_0 once, step the latents, output P_k = x_0 + (decode(z_k) − decode(z_0)).
- **Rank 7 changes.** The dynamics input becomes [z_t, z_t − z_{t-1}, coord] (+4,096 parameters). The verdict of record uses a "re-encode" rollout, which projects each imagined latent back through encode(clamp(x_0 + decode(z) − decode(z_0))). The "plain" rollout skips this and is scored only as a check.

### 2c. Data and training
- **Frames and policy.** 64x64 RGB area-pooled to 16x16 in [0,1]; 17 actions. Scripted exploration: 50% moves held 1-4 steps, 25% "do", 25% other.
- **Data sets.** Old train: 20,000 transitions, 160 worlds, day only. Dev: 5,008 transitions, 16 worlds, day and night. New train: 28,000 transitions, 80 worlds, 350-step day+night episodes. Sealed: 5,600 transitions, 16 worlds, never opened.
- **Pilot split.** From the new train source only: train on 72 worlds (25,200 windows), evaluate on 8 others (2,800).
- **Training.** Board: Adam, 1,500-3,000 steps, batch 64. Conv: AdamW (lr 3e-4, weight decay 1e-4), batch 64, 5,000 steps. Pilots: 3,000 steps.

### 2d. Marks
- **E_k, B_k.** E_k is the model's squared error summed over all held-out windows at horizon k. In every ruler, B_k is the better of "copy frame t" and the best fixed blend with the mean frame.
  - Legacy bars: E/B ≤ 0.80, 0.90, 0.95 at k = 1, 3, 5.
  - From Rank 3 on, the model must also beat two baselines fit on train. The bar on dev is **E/B < 0.2853, 0.4068, 0.4977**:

| Baseline (dev) | k1 E/B | k3 E/B | k5 E/B |
|---|---|---|---|
| Copy | 1.057 | 1.146 | 1.213 |
| Linear per-action map M_a·[x_t, 1] | 0.4738 | 0.5578 | 0.6103 |
| Shift-or-stay: linear player-centred 6x6-crop shift model plus a learned gate | 0.2853 | 0.4068 | 0.4977 |

- **Shuffle test.** Actions are permuted within each world (seed 43). On moved windows, shuffled error must be ≥1.25x true error at k1 and ≥1.10x at k5, in ≥12 of 16 worlds. The pooled k1 ratio must be ≥1.25.
  - "Proves wrong": E1/B1 ≤ 0.80 with pooled k1 shuffle < 1.05.
- **Ceiling.** Real-frame or real-board decode E/B must be ≤ 0.70. A ceiling above 0.95 is an automatic FAIL.
- **std ratio (anti-collapse).** Predicted-change std / real-change std per first action must be in [0.25, 2]. Final ruler: an action is gated only if it is active (n ≥ 20 windows and real-change std ≥ 0.02). Active actions with n ≥ 200 or Kish n_eff ≥ 10 are gated individually; n_eff = (Σe_i)²/Σe_i², where e_i is each window's mean squared real change. The remaining active actions are pooled, and the pool is gated only when its real std ≥ 0.02. A pooled action below 0.25 that carries ≥ 25% of the pool's real change energy fails the gate. The frequency-weighted mean ratio must also be in [0.25, 2].
- **pcs90.** Principal components covering 90% of predicted-change variance must be at least half the real count (111 on dev).
- **Wall (block/open).** The scorer labels valid move windows as open or blocked using a sprite-masked displacement classifier, about 99% accurate against true position. The same classifier is applied to the model's predicted frame. Dev has 3,034 valid move windows (2,222 open, 812 blocked).
  - FB = share of open moves predicted blocked; FO = share of blocked moves predicted open; mean_err = ½(FB + FO).
  - Pass: mean_err ≤ 0.75 × shift-or-stay's 0.0879 (**≤ 0.0659**), and neither rate worse than shift-or-stay's own (FB ≤ 0.0207, FO ≤ 0.1552).
- **PARTIAL and WRONG/FAIL by ruler (rulers defined in section 3).** Ruler A PARTIAL = the k1 mark, the k1 shuffle mark and the std/pcs marks pass, but k3 or k5 fails. Ruler B PARTIAL = additionally beats the baselines and wall at k1 with ceiling ≤ 0.70, while k3 or k5 misses. Ruler C narrowed PARTIAL to a k5-only miss. WRONG/FAIL = anything else.
- **Asleep R².** A diagnostic R² on asleep windows only, never a gate.
- **Strikes (Ruler C).** PARTIAL (k5-only miss) is not a strike. **VARIANT** = every non-std gate, every individual std gate and the frequency-weighted std gate pass, and the only failure is the pooled rare bucket or its energy-dominance guard; it does not count against the conv line. **LINE** = any other failure, including the frequency-weighted std gate or an incomplete or non-finite run; it counts against the conv line.
- **Pilot marks (unscored, on the 8 pilot evaluation worlds; any miss means no scored Rank 8).** **P1:** "do" (action 5) std ratio ≥ 0.30 on both seeds. **P2:** wake gap (mean predicted terrain-brightness change on the wake-up windows whose post-wake HUD (the status/inventory rows at the bottom of the frame) looks like a normal awake HUD, a proxy for waking at full energy, minus stay-asleep windows; hurt wake-ups are excluded. There are only 9 such wake-up windows on the pilot evaluation worlds, against 369 stay-asleep windows) ≥ 3x the uniform arm's. **P3:** versus the same seed's uniform arm, k1 E/B ≤ +0.005, k3 ≤ +0.008, wall mean_err ≤ +0.005.

## 3. Every scored try and pilot

The ruler changed twice:
- **Ruler A** is the original plan.
- **Ruler B** fixed whole-frame decoding, added the active-action std gate, the baselines and the wall mark, and moved to the day+night train set.
- **Ruler C** added the n_eff std gate (active-only pooling plus the energy-dominance guard), the LINE/VARIANT classes, and narrowed PARTIAL to k5-only misses. It was adopted before any Rank 7 training.

| # | Try (one change) | Ruler | k1 / k3 / k5 E/B | Shuffle | Other | Verdict |
|---|---|---|---|---|---|---|
| 0 | Free check, no training | – | – | – | Move-vs-noop pixel gate 19/24 prefixes (mark ≥8). Blend beats copy by 4/11/17%. Noop replays differ (unseeded game randomness). | PASS |
| 1 | Board, tiny (66K active), decode change | A | 1.055 / 1.140 / 1.204 | 1.000 | Row-loss target drifted (0.017 → 3,291) | WRONG |
| 2 | Row target = fresh read of t+1 | A | 1.056 / 1.143 / 1.210 | 1.000 | Head outputs about zero change | WRONG |
| 3 | Standardise head input (batch norm) | A | 1.014 / 1.152 / 1.710 | 1.052 (k1) | Ceiling 1.057. Worlds 0/16 (k1), 7/16 (k5). | WRONG; tiny-size idea closed |
| 3b | Same settings at planned size (about 2.5M active) | A | 1.004 / 1.608 / 4.527 | 1.082 / 1.025 | Ceiling 1.066 | WRONG; closed |
| S2 | Memory only: redraw current frame (mark ≤0.10 vs mean frame) | – | – | – | Trained decoder 0.145, then 0.140 with fixed patch scale (both FAIL). Closed-form ridge on the same board 0.062 (PASS; blank-input control 169x worse). | PASS via ridge |
| S3 | Forecast through the frozen ridge readout | A | 31.3 / 120.2 / 247.2 | 0.999 | Ceiling 0.226 | FAIL |
| S4 | Train imagination through the readout | A | 321 / 1,266 / 2,625 | 1.003 | Ceiling 3.63 (0.92 with a refit readout); reading degraded | FAIL |
| S5 | Damped, gated imagine step | A | 4.58 / 2.41 / 2.04 (refit 1.33 / 1.14 / 1.17) | 1.000 | Learned imagine scale fell 0.02 → 0.0000 | FAIL |
| S6 | Freeze trunk, separate small imagine head | A | 1.191 / 1.089 / 1.117 | 1.038 | Worlds 7/16 at k5. Ruler B re-score: 1.0257 / 1.0944 / 1.1457. | FAIL |
| R3 | Board "un-choke" bundle: signal path, action FiLM, residual loss | B | 0.953 / 0.945 / 0.958 | 1.152 | Wall FB 1.00, FO 0.00, mean 0.50. pcs 13/111. Board "burial" (fixed-offset RMS / frame-dependent spread RMS; exact definition for the 3.49 value unclear) 3,054:1 → 3.49:1. | PROVED WRONG by its stop rule (see section 5) |
| R6 s42 | Separate 2.69M conv world model (plain rollout = record) | B | 0.247 / 0.390 / 0.520 | 5.55 / 2.52 | Wall 0.025. 16/16 worlds. std fails: "do" 0.161, place 0.083 / 0.088. | FAIL (conv 1/3) |
| R6 s43 | (same) | B | 0.249 / 0.384 / 0.503 | 5.73 / 2.65 | Wall 0.026. std fails: "do" 0.176, place 0.118 / 0.106. | FAIL |
| R6 re-encode re-score | (eval only) | C | 0.2470 / 0.3740 / 0.4881 and 0.2488 / 0.3737 / 0.4827 | – | Still LINE on std | (historical verdict kept) |
| R7 s42 | 2-frame input, re-encode rollout | C | 0.2546 / 0.3821 / **0.4953** | 5.2 | Wall 0.0375. "do" std 0.126. Pool [8,9] (place table, place furnace) 0.078. | FAIL LINE |
| R7 s43 | (same) | C | 0.2564 / 0.3879 / 0.5016 | 5.6 | Wall 0.0478. "do" 0.194. Pool 0.102. Plain k5: 0.5116 / 0.5208. | FAIL LINE (conv 2/3) |
| P1 | Pilot: Rel-PER 50/50 vs uniform, seeds 7 / 8 | C | k1 0.268 / 0.263 vs 0.297 / 0.291; k3 0.398 / 0.399 vs 0.409 / 0.399 | – | P1 0.753 / 0.651 (uniform 0.175 / 0.196). P2 0.074 / 0.073 (uniform 0.0011 / 0.0008). **Wall 0.0687 / 0.0613 vs 0.0604 / 0.0495 (+0.008 / +0.012).** Asleep R² 0.06 → 0.49 / 0.53. | MISS on wall (Rel-PER 1/3) |
| P2 | Pilot: Rel-PER 75/25, seeds 7 / 8 | C | k1 0.271 / 0.272 vs 0.287 / 0.299; k3 0.397 / 0.403 vs 0.401 / 0.408 | – | P1 0.515 / 0.829. P2 0.047 / 0.071. **Wall seed 7: 0.0638 vs 0.0504 (+0.013, miss). Seed 8: 0.0572 vs 0.0708 (ok).** | MISS (Rel-PER 2/3) |

**The sampler being piloted (Rel-PER).** Each transition's priority is r_j = min(e_j / (v_action + 1e-4), 20). Here e_j is an EMA of that transition's own residual error, and v_action is the mean copy error for its action. The sampling probability is p_j = u/N + (1−u)·r_j^0.7 / Σ r^0.7, with u = 0.5 in pilot 1 and 0.75 in pilot 2. The loss itself is unweighted.

**Noise facts (shown; the same-seed comparison and the two gate readings were noticed while compiling this briefing, not logged by the project)**
- **Seed spread.** The uniform arm's wall error alone ranges 0.050-0.071 across seeds and runs, more than the +0.005 allowance.
- **Same-seed reruns.** Same seed, data and settings, on a later trainer build whose uniform path tested identical in a 20-step synthetic self-test. Wall: seed 7 0.0604 → 0.0504, seed 8 0.0495 → 0.0708. k1: 0.297 → 0.287 and 0.291 → 0.299. "Do" std: 0.175 → 0.179 and 0.196 → 0.166. An earlier board-model run on the same Mac GPU reproduced exactly, so this rerun mismatch is unexplained; it is not established noise.
- **Absolute bar.** Both pilot-2 Rel-PER wall values (0.064 / 0.057) are under the absolute 0.0659 bar; seed 7's pilot-1 value (0.0687) is not (the 0.0659 bar is calibrated on the 16 dev worlds, where shift-or-stay was scored; the pilot uses 8 different worlds, so this comparison is indicative only).
- **Pilot-2 wall gate, two readings.** The plan printed limits from pilot 1's uniform arms (seed 7 ≤ 0.0654, seed 8 ≤ 0.0545); the driver used pilot 2's own uniform arms. Seed 8 misses under the first reading, seed 7 under the second: a miss either way.
- **Pre-filed PASS odds.** Rank 6 50%, Rank 7 65%, pilot 2 30%.

## 4. Diagnoses so far

**Earlier outside advice (Astra, Fable; before any run; suggested)**
- A latent-only target is unsafe as the sole loss, because copying scores near zero.
- Anchor the model to a real next frame.
- Run a free no-training check first.

**Board model, steps 1-6**
- The board is about 99% a fixed offset; it holds the frame linearly, but only as about a 1% signal. The decode head died within about 25 steps (shown).
- The trained decoder underfit: 0.140 versus 0.062 for ridge on the same board (shown).
- Imagined boards go wrong in the low-variance directions the readout relies on, and the imagine delta is ungated and large against the real spread (suggested).
- In step 5 the model switched imagination off (shown).

**Rank 3 (Neon RUNG1-DIAG)**
- Seeing and action delivery were fixed: ridge on the real board gets 99.6% block/open; the action-by-screen interaction was 2,000x stronger than in step 6 (shown).
- The board stores pixels as a "global soup" with no 2D shift path: localisation 1.14 (max/mean patch weight per row; 1.0 = soup, 16 = specialist), attention entropy 93.5% of maximum (Neon: shown; lead: suggested).
- Early in training the imagine loss was outweighed about 65x (shown).

**Rank 6 (Neon RANK6-DIAG)**
- At 16x16 the HUD energy digits 6 and 9 are pixel-identical, so one frame cannot separate "keep sleeping" from "wake now". Wake-ups carry most of the "do" and place variance (shown; numbers in section 5).
- Chop and place are under-learned even on train, R² ≤ 0 (shown).
- The k5 miss is latent drift; re-encoding fixed it in a probe chosen after seeing dev (shown).

**Rank 7 (Neon RANK7-DIAG)**
- **"Do" collapses in two halves (shown).** (a) Wake-ups, 55% of the real "do" change energy on dev: only 0.41% of train windows, so 77% of batches have none, with about 62x less gradient into the history channels than moves. Layer probes suggest training erased a wake-up signal that the encoder and a random-init U-Net still carry (AUROC 0.937 → 0.685). (b) Awake chop, collect and place: a flat output of about 0.002 RMS, with 38-306x less gradient than moves.
- **The information is in the pixels (shown).** Kernel ridge on 16x16 pixels reaches R² 0.38 (centre crop) and 0.24 (HUD) for awake "do".
- **Wall regression versus Rank 6 (gap shown, cause suggested).** Rank 7's train-to-dev wall gap is about +0.015, against 0 for Rank 6; Neon blames overfitting of the move-difference channels.
- **Labels.** Neon called starvation "proven/shown". The lead called it suggested, then "shown in training" after pilot 1 learned "do" and wake-ups once they were sampled.

**Pilot 1 reading**
- The lead's reading was that prioritised sampling took practice from walks and bumps (suggested).
- The pilot-2 design contradicts this (shown). Move share rose, 60.6% → 63.2% (seed 7) and 60.7% → 63.3% (seed 8). Evaluation wall samples were identical (1,142 open, 500 blocked). Both FB and FO rose, and the held-out-minus-train wall gap grew (0.031 → 0.037; 0.020 → 0.034), even though seed 8's train wall improved.
- The mechanism is not proved (suggested).

**Honesty check (pilot-2 design; shown).** The P1 gain is largely wake-driven. For non-wake "do", the std ratio rose (0.212 → 0.723; 0.238 → 0.427) but R² got worse (−0.031 → −0.493; −0.035 → −0.165).

## 5. What is stuck now

**Strike ledger (kept separate)**
- **Board-model forecasting idea:** closed at tiny size and at planned size. The forecasting line on the board had 5 consecutive FAILs, steps 3-6 plus Rank 3.
- **Rank 3 (shared-board un-choke):** 1/3, proved wrong. Rank 3 had a pinned stop rule: it is proved wrong after one run if k1 E/B ≥ 0.4738 (cannot beat the per-action linear map) or pooled k1 shuffle < 1.25 or k1 shuffle passes in fewer than 12 worlds (plus cheat or wall triggers). The run hit the first two, so the other three planned variants were skipped. Not pursued.
- **Conv world-model line:** **2/3** (Rank 6 and Rank 7). The last scored strike is unspent. Any LINE failure on the next scored run closes the line.
- **Rel-PER sampler variant:** **2/3** on unscored pilots, parked. Both pilots passed P1, P2, k1 and k3 on both seeds and failed only the relative wall allowance: pilot 1 on both seeds, pilot 2 on seed 7 only.

**Exact blockage**
- The conv model passes k1, k3, wall, shuffle, ceiling and pcs with margin on dev. It fails because it predicts almost no change after "do" (std 0.13-0.19, needs ≥0.25) and after placing (pool 0.08-0.10), and on one seed is just over at k5 (0.5016 vs 0.4977).
- Pool [8,9] = place-table (8) and place-furnace (9). On dev, the "do" gate is dominated by 6 wake-up windows out of 733 (55% of real change energy). Action 9 has no real furnace placements, and a single wake-up window carries 86.5% of its energy (60.3% for action 8). Action 9 holds 49.8% of the pool's energy, so missing that one window trips the pool's energy guard by itself (shown).
- Rebalancing training toward rare events fixes "do" and wake-ups in pilots but worsens the wall mark by more than +0.005 (pilot 1 on both seeds, pilot 2 on seed 7). The wall's seed and rerun noise (0.050-0.071) exceeds that allowance.
- The pinned rules say any pilot miss means no scored Rank 8, so the last conv strike stays unspent. The lead's note on wall noise is recorded as "info only and not a re-grade".

**Alternative already proposed (untested; attributed)**
- If the conv line closes, Neon proposed a discrete-token patch world model: FSQ/VQ tokens, spatio-temporal attention, cross-entropy loss.
- That proposal has not been pinned or run.

## Questions
1. **Is the blockage real or a measurement problem?**
   - Two things are suspect:
     - the "do" and place std gates are dominated by a handful of wake-up windows (6 of 733; one window carries 86.5% of action 9's energy);
     - the wall allowance (+0.005) is smaller than the seed and rerun spread (0.050–0.071).
   - Which parts of the current failure reflect a real modelling gap, and which reflect the marks?
   - Answer for **future** pinned marks only: past verdicts stand and may not be re-graded.
2. **The unexplained same-seed rerun mismatch.**
   - Same seed and data gave a wall of 0.0604 → 0.0504 and 0.0495 → 0.0708.
   - What is the cheapest check (no training, or under 5 minutes) to find out whether the trainer or the evaluation is nondeterministic?
   - Should that check come before any further try?
3. **Mark design for the next try.**
   - Propose noise-aware marks for wall and rare-action std that keep the spirit of the originals:
     - "uses the action", "doesn't collapse rare events", "doesn't get worse at walls";
     - for example, paired seeds, confidence intervals, or a minimum window count before a gate applies.
   - Give exact numbers.
4. **The single next change.**
   - The conv line has one scored strike left and Rel-PER is parked at 2/3. Choose one and give exact settings:
     - (a) one more conv change;
     - (b) a sampler or loss change that protects walls while fixing "do";
     - (c) a frame or history change that fixes the HUD 6-vs-9 ambiguity (e.g. a short frame history or higher HUD resolution, still with nothing game-specific);
     - (d) switch to the discrete-token patch model;
     - (e) something else.
   - Pass marks, falsifier and odds, all within a 30-minute wave on one 16 GB consumer GPU or a Mac.
5. **Big picture.** Is a per-pixel conv model at 16x16 the right substrate for the later goal ("an imagination a policy can practise in"), or should we change direction now? Say what result would settle it.
