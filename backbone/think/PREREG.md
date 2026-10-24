# Think-1: a trained thinking block for premonition v2, pilot on Qwen3.5-0.8B (pre-registration, 2026-10-24)

Written before any Think-1 training run. Labels: **shown** = measured or read in code/data; **suggested** = inference;
**untested** = nobody has run it. Village model only (`learnlab/village`). The small card experiments are not part of this.
The village `test` split is sealed: it is never built, read or scored by anything here.
Design and why it won: `DESIGN.md`. Research: `RESEARCH.md`. Scale-up to LFM2.5: `SCALEUP.md`.

## Question
Can a small trained block make a frozen borrowed model think silently, by looping in latent space over a few
"thinking slots" before it answers, and beat both plain training and re-running the model's own middle layers?
Stage 1 showed re-running layers 8-11 ties plain LoRA on validation (+0.40 over 3 seeds) [shown]. Loop-1L showed re-running
LFM2.5's layers 16-23 makes tool use worse (40.1 vs 47.7) and a per-position board without a gate diverged [shown,
RESULTS-loop1L.md].

## The block (G-STS, "gated silent think slots"; details in DESIGN.md)
- Backbone: Qwen/Qwen3.5-0.8B, frozen, plus arm A's trained LoRA for the same seed, also frozen.
- Board: K=16 slots x 1024, in input-embedding space. rho = median row RMS of the embedding table (0.0195 [shown]).
  Learned start e0 = rho * e0_hat, with e0_hat initialised from the embeddings of 16 distinct tokens divided by rho and
  clamped like every board, so its learning rate acts on unit-scale numbers.
- When it thinks: once per question, after the prompt minus its last token is prefilled. All slots sit at the RoPE
  position of that held-back token. Prompt tokens never see the slots.
- One lap: the 16 slots run through all 24 frozen layers on a copy of the prompt cache (they read the prompt natively),
  then a 2.64M-parameter refiner (2 blocks of slot self-attention + MLP, d=256; NO access to the context) reads the slot
  states at layers 11, 17 and the final norm and writes a bounded update: e <- clamp_rms(e + rho * eta * tanh(W_out u), rho).
  New facts can only enter through another pass of the backbone, so a second hop needs a second lap.
- How the answer reads it: at each of the 6 full-attention layers, answer tokens add tanh(alpha_{layer,head}) x
  attention over the 16 slot keys/values. alpha starts at 0, so at step 0 every logit equals arm A's exactly.
- L laps = L refinements = L+1 slot passes. L=0 means learned pause slots.

## Data (same as stage 1)
`backbone/build_data.py` (v1 generator, seed 0, digests checked against v1): train shards 0-39 (86,238 questions,
depth <= 3), dev = 4,000 questions from shards 380-399, validation = all 8,675 questions (new names, templates,
styles and rule families; 1,558 rows at depth 4-6, which training never contains) [shown]. Prompt = context + question
+ " [answer]", target = " answer" + EOS, max length 2048, greedy decode of up to 24 tokens, exact match after
normalisation [shown, train.py].

## Arms (one harness: `backbone/think/think1.py`; same data order, padding, loss code and GPU type for every arm)
| arm | what | steps |
|---|---|---|
| a | LoRA r16 on all layers (stage-1 arm A recipe) | 418 |
| b | a + layers 8-11 run 3 times at every position, shared weights and LoRA (stage-1 arm B) | 418 |
| aplus | a's adapter, LoRA trained 1,254 more steps on the stage-2 rows (more training, no board) | 418 + 1,254 |
| t | a's adapter frozen; only the board parts train (e0, alpha, eta, refiner) | 418 + 1,254 |
| t1 | as t, but trained with L_max = 1 always (same parameters and steps; one refinement) | 418 + 1,254 |
| bplus | b's adapter, LoRA trained 1,254 more steps (seed 0; all seeds only if bplus - b >= 1.0) | 418 + 1,254 |
| tw | as t1 but K=144 slots: one refinement with the same slot-token compute as t at L=8 (seed 0, diagnostic, PC run only) | 418 + 1,254 |

Seeds 0, 1, 2 for a, b, aplus, t, t1. Every arm of one seed runs on the same GPU type and number format (bf16 on
RTX 3090 / 5070 Ti; fp16 with a gradient scaler and fp32 trainable weights on Kaggle T4s, which have no bf16), so every
comparison inside a seed is like for like; seeds may differ in hardware, and each seed's hardware is recorded. The stage-1 adapters were not kept, so a and b are retrained here; the stage-1
3-seed means (A 66.72, B 67.12) are used only as floors in the marks below. Stage 1's own same-seed rerun spread was
1.84 points (67.78 vs 65.94) [shown], which is why the arms are not mixed across harnesses.

Fixed settings: batch 16 (micro-batch 4), LoRA lr 2e-4 cosine with warmup min(100, steps/10) (stage 1); stage-2 runs
(aplus, bplus, t, t1, tw): cosine with 60 warmup steps over 1,254 steps (aplus/bplus re-warm their LoRA to 2e-4), AdamW,
weight decay 0, grad clip 1.0 per parameter group (the gates are clipped apart from the refiner), rows drawn from a
second shuffle (seed s + 1000; about 92% of its rows are new to stage 1), in the same order for every stage-2 arm.
Board learning rates (gentle, after Loop-1L's divergence at 1e-3): alpha 3e-3 (own group, logged), e0_hat and eta 5e-4,
refiner 5e-4. Every slot pass and every teacher-forced answer pass runs on its own copy of the
prompt cache, so no pass can see another pass's tokens (in particular, no lap can see the gold answer).
Laps in training: L_max = 8 with probability 0.8, 12 with probability 0.2; loss = answer cross-entropy averaged uniformly over every lap t = 0..L_max, plus 0.01 x mean ||delta/rho||^2.
Cross-entropy: every arm uses the fixed cross-entropy of Barron et al. 2026 (arXiv 2610.31642, `backbone/think/xent.py`),
computed in fp32. In PyTorch 2.14 the standard version zeroes the target gradient once a token's margin passes ~17 in
fp32 while the other gradients stay non-zero [shown, measured today]. The fix changes nothing else.

## Evaluation
- Every arm: dev (4,000) and validation (8,675), plus per-row hits so that all differences are paired.
- b also at 1 pass (lesion).
- t: validation at L = 0, 1, 2, 4, 8, 12 (all 8,675 rows) and 16, 24 (first 2,000 rows, diagnostic); dev at L = 0, 1, 8.
  Each row is prefilled once; the board's keys/values are recorded at every L from one run, and each L is decoded from
  its own copy of the cache.
- t1: validation at L = 0, 1 and 8 (diagnostic); dev at L = 1. tw: validation at L = 1.
- Eval noise: arm a's seed-0 checkpoint is scored twice (different batch order); the observed difference sets the
  R2 tolerance below.
- Lesions on t at L=8, full validation: swap (board from a question in another story), mean board (slot keys/values
  averaged over the batch), repeat-delta1 (lap 1's update reused for laps 2-8 with no new backbone passes), gates off
  (must equal arm a; a correctness check, not a result).
- Logged every 10 steps: |tanh alpha| per layer/head, ||e_t - e_(t-1)||/rho per lap, slot cosine within a board and
  across questions, clamp fraction, loss. Every 250 steps on the first 256 dev rows: answer CE and accuracy at L = 1 and 8,
  the swap lesion at 8, refiner gradient norm.

## Marks (fixed now)
Notation: S_s(L) = arm t, seed s, validation accuracy at L laps; S(L) = mean over seeds 0-2; T1 = arm t1 at L=1 (mean);
A_ref = max(66.72, mean of a, mean of aplus); B_ref = max(67.12, mean of b, mean of bplus if run).

**PASS = G and R.**
- **G (gain):** S(8) >= max(A_ref, B_ref) + 3.0 (so at least 70.12).
- **R (score rises with laps):** all of
  - R1 slope: S(8) - S(1) >= 1.5, and S_s(8) - S_s(1) >= 0.5 in every seed (paired, same rows);
  - R2 monotone: S(2) >= S(1) - tol, S(4) >= S(2) - tol, S(8) >= S(4) - tol, with tol = max(0.3, 2 x the observed
    eval-noise difference);
  - R3 no collapse: S(12) >= S(8) - 1.0, and S_s(12) >= S_s(8) - 2.0 in every seed;
  - R4 laps, not parameters: S(8) - T1 >= 2.0, and S(8) - S_repeat-delta1(8) >= 1.0.

**Wrong if** any of: S(8) - T1 < 1.0 (laps add nothing over one refinement); S(8) - S(2) < 0.5 (work done by lap 2);
the swap lesion costs < 1.0 point at L=8 (the board's content is not used); S(8) < A_ref + 1.0.
Anything else is **partial**: reported, no scale-up.

**Mechanics gate (every t / t1 / tw run, automatic):** abort and report if, at step 150, mean |tanh alpha| < 0.02 (the
gates never opened); or, at any step after 20, a NaN loss or gradient, or a 20-step mean training loss above 2x the
first-20-step mean (divergence guard, Loop-1L arm C). Logged but not aborts: cross-question cosine of the boards and of
their updates (e_L - e_0), the share of slots at the rms clamp, the swap lesion on the 256 logging rows, and the
refiner's gradient norm. (Amended before any run, 2026-10-24: on the real model every board starts from the same e0 at
the clamp, so board cosine is ~0.99 and ~94% of slots sit at the clamp at step 0 [shown, CPU check]; those two
conditions would have aborted healthy runs. The swap lesion in the futility stop tests board content instead.)

**Futility check on seed 0** (a, b, aplus, t, t1 at seed 0). Amended before any run (2026-10-24, Ben): free hardware
(Kaggle, Ben's PC) lets seeds 1 and 2 run at the same time as seed 0, so this is no longer a stop that saves money; it is
computed and reported, and a stop is used only for seeds that have not started yet. Any seed that completes counts.
The rule fires if any of
S_0(8) < 68.0; S_0(8) - T1_0(1) < 1.0; S_0(8) - S_0(2) < 0.5; swap lesion < 1.0. (Same-seed reruns differed by 1.84
points in stage 1, so run sd may be ~1.3; a true mean of 70.12 then lands below 68.0 about 5% of the time [suggested].)
If only the first condition fails, the laps are real but small: the PASS track stops and Think-1b (below) gets its own prereg.

**Secondary readouts (no weight in PASS):** M1 chain banks (where_before + plan_get, 2,019 validation rows; arm A
33.5% / 37.8% in stage 1 [shown]): S(8) - T1 >= 3. M2 depth 4-6 (1,558 rows): S(8) - T1 >= 2. Also by depth (0-3 vs 4-6),
by bank and by question type, with paired bootstrap 95% intervals.

## What counts
Only the numbers named in the marks count, computed by `backbone/think/summarize.py` from the result files. Validation
is our only held-out set, so nothing is tuned on it: every setting above is fixed now, the futility stop and lesions are
fixed rules, and no loss variant or lap count is switched after seed 0. The sealed test is never generated (build_data.py
has no code path for it).

## Expectations written now (so a fail is not a surprise)
Every panel designer predicted about +2 over B; every attacker put the chance of PASS at 5-15%; the synthesis estimate
is about 10% [suggested]. G sits above Qwen3.5-2B + LoRA (69.81, one seed) [shown]. The run is informative mainly through
R4, M1 and M2: a real lap effect with G failing would send us to Think-1b, not to the scale-up.

## Think-1b (not run here; one change, needs its own prereg)
Retrain every arm on `generalize.probes.write_training_data(("difficulty",), ...)` data, which adds depth 4-6 chains to
training without putting validation items in it [shown, code], so the laps get a job inside the training range.

## Budget and hardware
All seeds in parallel: seed 0 on Vast (RTX 3090 boxes labelled with the branch, `claude-think1-compassionate-davinci-...`,
cap $2.50 of this week's credit), seed 1 on Kaggle (free 2x T4, fp16), seed 2 on Ben's PC (RTX 5070 Ti, one command in
`backbone/think/README.md`) or, if the PC is busy, a second free Kaggle session. Estimated per seed on a 3090: a 1.3 h, b 1.6 h, aplus 1.5 h, t 2.5 h,
t1 1.5 h [suggested].
