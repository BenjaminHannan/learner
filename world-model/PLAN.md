# PROBLEM-7 PLAN: ground the world model on real game steps (marks pinned 2026-11-23 ~23:00 ET, BEFORE any run)

Sources: astra/REPLY.md, fable/REPLY.md, advisor/q1/REPLY.md (Fable high), code check in STATUS.md. All below = suggested
unless labelled. Toy shape only (~3M active, main-build v2 code). No claim about the 466M trunk.

## Rule reading (strict): WM gradient only from k=1 real pairs. Rollouts k=3,5 are SCORED only, never trained.

## Step 0: free check (no training, CPU, minutes)
Needs Crafter installed (pip; awaiting Ben's OK). Record 24 prefixes x throwaway seeds; 5,000 random-policy steps on 20 seeds.
- Pixel gate: 16x16 RGB area-pooled in [0,1]; move-vs-noop next-frame MSE > noop-vs-noop MSE + 1e-4 on >= 8/24 prefixes.
  Fail -> stop: capture path shows no action effect.
- Target choice (one precedence rule): 16x16 pixels by default. Frozen image-encoder rows only if encoder sensitivity
  (median moved-step feature change / median random same-episode distance) >= 0.1.
- Also print: share of moved steps; copy and best-blend baselines at k=1,3,5 (blend coefficient fit on train seeds).
- Forward-only through today's checkpoint: does z move when the frame moves? (report only)

## Step 1: the single change (DeepSeek codes it in ds-copies/problem-7/, one scoped diff review)
In the real-transition harness: a zero-init decode head reads ONLY the imagined board next_rows (never the context,
never the action row) and predicts the CHANGE from frame t to frame t+1 (16x16 pixels). Plus one rule-safe k=1 row
loss: next_rows vs the detached board after the model really reads frame t+1 (so a fed-back board stays board-like).
The head is also trained on real boards (gives a "ceiling": can the board hold the frame at all?).
Context frozen at frame t for every imagined step. Old latent loss weight 0. Nothing game-specific written in.
Data: 20,000 train transitions (seeds 0-159), 5,000 held-out (seeds 1000-1015, 16 worlds), split by world.
Exploration script outside model: 50% moves held 1-4 steps, 25% "do", 25% other; episodes cut at 250.
Fit: batch 64, ~1,500 Adam steps lr 3e-4, init seed 42; time 20 steps first, cap training 15 min (cut steps, not data).
Score final checkpoint only.

## Pass marks (held-out worlds; fixed now)
E_k = model squared error at step k summed over all windows; B_k = better of copy-frame-t and best fixed blend.
- Pre-gate: real-board decode ceiling E/B <= 0.70. If > 0.95 -> board doesn't hold the frame; imagine result moot.
- (a) E_1/B_1 <= 0.80, E_3/B_3 <= 0.90, E_5/B_5 <= 0.95. Moved windows reported separately.
- (b) Shuffle actions within world (keep action frequencies, seed 43): on moved windows shuffled error >= 1.25x at k=1
  and >= 1.10x at k=5, in >= 12/16 worlds.
- (c) Predicted-change std per first-action group = 0.25-2x real; PCs for 90% variance of predicted change >= half the
  real-change count.
PASS = all. PARTIAL = k=1 marks + k=1 shuffle + (c) pass, k=3 or 5 fails. WRONG = anything else.
Odds (advisor, uncalibrated): PASS 20 / PARTIAL 45 / WRONG 35.
PROVES PLAN WRONG: k=1 mark met but shuffled error < 1.05x on moved windows (beats copy without using the action).

## Next
- PASS: same test at production shape in gpu_slot tickets; then first dream test: freeze WM, actor practises 5-step
  imagined rollouts from recorded REAL states; judge only on REAL play, 40 held-out seeds vs same actor without dreams
  and vs random: >= +1.0 reward/episode, imagined-minus-real 5-step return within +/-0.1, ties < 20% of decisions.
- PARTIAL (with row loss already in): ask Ben whether "trains only on real transitions" allows unrolled training where
  inputs are imagined but every target is a real frame. Do not do it without his yes.
- WRONG: inspect saved forecasts first; one change per retry (encoder target / action into every row / 4x worlds).
  Three locked misses close the idea.

## Machine
Recording + free check: CPU (M1 or M3). Fit: M3 MPS under /tmp/premonition_m3_mps.lock, or the-pc gpu_slot ticket
(ask <= 4,000 MiB, <= 12 min) if M3 is too slow at the 20-step timing.

## AMENDMENT 2026-11-24 ~08:20 ET: STEP 6 pinned BEFORE any scored run (PROBLEM-7 = world model / dreaming)
Ordered by the lead: freeze the shared brain, give imagination its own small trainable layers, P7 experimental copy only.
Canonical core untouched. Code (M3 scratch ~/learner-ops/seven-problems-m3/PROBLEM-7/wm-harness/, copies in forecast4/):
forecast4.py (= step-5 forecast3.py with: trunk/reader/everything frozen via requires_grad False; trainable = imagine_out +
action_emb + action_in + action_pos; one Adam group lr 1e-3, 100-step warmup, clip 1) + imagine_head6.py (step-5 damped copy
with imagine_alpha removed; delta = imagine_out(hn) x imagine_scale, imagine_out = Linear(d,d)-GELU-Linear(d,D), last layer
zero-init; imagine_scale = per-coordinate spread of REAL train boards). Init = step-2 exact-readout model, P7toy, seed 42,
3,000 steps, 40-min cap, M3 MPS under /tmp/premonition_m3_mps.lock. Loss, data, readout, noise, controls = step 4 re-pin.
What is learned: only the imagination layers and the action embedding. Nothing game-specific written in.
Marks: UNCHANGED = step-4 re-pin (E_k/B_k <= 0.80/0.90/0.95; >= 12/16 worlds pass BOTH shuffle marks (k1 >= 1.25x,
k5 >= 1.10x); std ratio per first action 0.25-2; pcs90 pred >= 0.5 x real; ceiling <= 0.70 for PASS/PARTIAL; ceiling > 0.95
= FAIL). PARTIAL = k1 + k1 shuffle + std + pcs + ceiling. Primary readout = training readout (as step 4/5).
Sanity (reported, not a mark): with the trunk frozen the real-board ceiling must stay near step 3's 0.23; if it moves > 0.1
the freeze leaked -> infrastructure stop, not a strike.
PROVES STEP 6 WRONG: k1 E/B >= 1.0 or shuffle pooled < 1.05 on moved windows -> separate layers on the frozen trunk's
features do not carry the action's effect; the fault is upstream (trunk features), not the shared-weight conflict.
Strike count: the forecasting line (steps 3, 4, 5) has 3 FAILs, each a different change, each separately ordered; this
step-6 variant is 0 misses before the run. Pre-filed guess (unlocked 600-step probe of the linear draft stayed img/copy
~1.0): FAIL 80 / PARTIAL 12 / PASS 8. Advisor tool was rate-limited at pin time (not advisor-checked).
