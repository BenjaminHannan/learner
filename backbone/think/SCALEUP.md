# Think-1 scale-up plan: G-STS on LFM2.5-24B-A2B, tau2 retail, Ben's Mac (draft, 2026-10-24)

Runs only after the Qwen pilot PASSES (PREREG.md). A PARTIAL pilot goes to Think-1b, not here. Labels: **shown** /
**suggested** / **untested**. The village pilot and LFM2.5/tau2 are separate: nothing here is evidence about the other.
Sources: panel synthesis section 5, the scale-up attacks and the critic (`panel/`), `backbone/RESULTS-mac-lfm25.md`,
`backbone/RESULTS-loop1L.md`.

## Step 0: free measurements on the Mac (no training, before any spend)
1. **Is the gap thinking at all?** Build the paired win/loss table of thinking ON (30/40) vs OFF (23/40) on tasks 0-39 from
   the two results.json files (minutes). Count how many of ON's net wins are among OFF's 9 too_many_errors aborts.
2. **Repetition guard.** Re-run thinking OFF on tasks 0-39 with a guard that refuses an identical repeat of a failed call and
   returns a hint (about 3.4 Mac-hours, under $1 of Haiku user simulation; needs Ben's OK). If OFF + guard >= 28/40, tau2 has
   at most ~2 tasks of headroom for any board: then the board is judged on the offline metric only, and v2 ships with the guard.
3. **Speed at real context** (the 35.4 tok/s rule baseline used a short prompt; tau2 prompts are mean 6.8k, p90 9.4k, max 12.5k
   tokens [shown, thinking-ON transcripts]): 2-agent decode at 6.4k, 9.4k and 12k context. If the base is already below 30
   there, report that before blaming any board.
4. **Burst cost.** In mlx-lm, time 9 sequential 8- and 16-token `input_embeddings` passes after a 6k cached prompt, and the
   per-token cost of the gated read at 10 attention layers (expect 0.5-2%). Log expert-set overlap (Jaccard) between laps.
5. **Untrained board probe.** Gates closed must reproduce thinking OFF token for token; with gates at 0.1, nothing explodes.
6. **4-bit vs bf16 parity** on 20 transcripts: board cosine >= 0.98, next-token KL <= 0.05 (marks fixed now). If it fails,
   fake-quantise the backbone (affine 4-bit, group 64) inside the laps for the last 20% of training.
7. Already measured [shown, today]: 13.8 generations per episode (p90 18); thinking per generation mean ~284 tokens
   (estimated from characters / 3.68), median ~122, 74% of generations <= 300 tokens; the 10% over 700 tokens hold 48% of
   all thinking. Long traces are where latent distillation is weakest (R2: 12-15% vs 53% on own MATH traces).

## Block at LFM scale
- K = 8 slots (16 as an ablation) per assistant generation, forked from prompt[:-1] in the thinking-OFF format.
- Laps: L = 4 by default; 8 only if the speed marks allow. Each lap = one 8-token pass of the whole model (~90 ms at the
  ~64 GB/s fitted from Ben's bench [suggested]), so ~0.45 s per generation at L = 4.
- Refiner d_r = 512 (~10.5M); taps at layers 18 and 30 (attention layers) and the final norm; no context access.
- Read: gated attention over the slot K/V at all 10 attention layers (2, 6, ..., 38), 320 gates starting at 0.
  Alternative if step 0.4 shows the side branch costs > 2% per token: append the slot K/V to the attention cache with a
  learned per-layer logit bias starting at -10 (no extra kernel; near-exact thinking OFF at init).
- Short-conv layers (cache 3) and the frozen MoE router see the slots only during laps; the router's expert overlap is
  logged. Per-lap router biases are not used (LFM's expert_bias only affects selection and gets no gradient [shown, code]).
- Board lifetime: v2.0 builds a fresh board per generation and keeps none. Note: LFM's template keeps thinking for
  assistant messages after the last user message, and 41% of user turns have more than one generation [shown], so the
  teacher sees its earlier thoughts within a user turn while the student does not. Ablation: carry the board within a user turn.
- One renderer for training and the Mac (the OFF arm appends `<think>\n</think>\n`; Loop-1L rendered `<think></think>` [shown]).

## Stage 1: distillation (rented A100-80GB, bf16)
- Weights: the Mac's mlx 4-bit weights dequantised to bf16, so the trained function is the deployed one. HF stores LFM's
  experts as 3-D parameters, so bitsandbytes 4-bit loading does not apply [shown, code].
- Port first to `LiquidAI/LFM2.5-8B-A1B` (exists on the hub [shown]; check it uses the same `Lfm2Moe` class) for a cheap end-to-end smoke on Vast.
- Data: thinking-ON rollouts on retail tasks 40-113 only (never 0-39), 4 per task at temperature 0.7 (~300 episodes,
  ~25 Mac-hours, ~$4 of Haiku [suggested]); keep episodes with tau2 DB reward 1. DAgger states: where thinking-OFF repeats a
  failing call, relabelled with the teacher's action. The 1,792 Claude chats as a format warm-start.
- Loss: CE on the teacher's post-think tokens (tool-call tokens weight 1, text 0.5) + top-32 KL to the teacher, averaged over
  laps; plus a preservation KL (beta 0.1) to thinking-OFF on general chat. **Both KLs use `xent.fixed_kl`**: at step 0 the
  student equals the frozen model, which is exactly the Softmax Cancellation case of Barron et al. 2026 (standard KL then
  gives non-zero gradients: ~3e-8 in fp32, ~8e-4 in bf16, measured today [shown]); never compute these KLs in bf16 with the
  standard formula.
- Arms (equal data and steps): A-dist (LoRA, no board), T1 (one refinement), T (G-STS).
- Offline metric M_tool-retail: ~20 held-out tasks from 40-113, exact tool-call match per turn on successful teacher turns,
  plus the no-repeat rate on DAgger states (~1,000 turns, SE ~1.5 points [suggested]).

## Stage 2: RL (only if stage 1 passes; needs Ben's budget approval)
- First choice: rejection-sampling fine-tuning (sample T on the Mac on tasks 40-113, keep DB-reward-1 episodes, SFT on the
  rental with the preservation KL). Cheaper and steadier than GRPO on latents.
- JOLT+ (rlaif/) after that: port from Qwen3-1.7B / sandbox to LFM2.5 / tau2; reward 0.6 x DB check + 0.4 x Sonnet 5.5 grade;
  teacher = the same weights with the reference actions as hints; KL anchor (beta 0.1) to the stage-1 policy with
  `xent.fixed_kl`; laps fixed at L = 4; exploration from token sampling plus Gaussian noise on the refiner update (0.1 rho).
- Cost [suggested]: one GRPO step (4 x 16 = 64 episodes) is ~5.3 Mac-hours and $0.64-1.6 of grading, so a $15 cap buys
  ~10-23 steps over several days. That is Ben's call.

## LFM pass marks (fixed now)
- Offline: T at L=4 >= A-dist + 3 on M_tool-retail; T@4 - T1 >= 1.5; swap lesion costs >= 3.
- tau2 retail tasks 0-39 x 4 trials, paired by task: mean >= 27/40 and >= A-dist + 2 tasks. Wrong if T <= A-dist.
- Speed (2 agents, 6.4k context): decode time-averaged over a full tau2 episode (generated tokens / wall time of the
  generation phase, counting the other agent's bursts and prefills) >= 30 tok/s per agent and >= 97% of base at the same
  context; added time to first token <= 0.7 s per generation; added time <= 15 s per episode.
- Measurement scripts for all three are written and committed before the run.

## Budget (this week's Vast credit is a few dollars)
Step 0 is free (Mac) apart from <$1-2 of Haiku. Stage 1 needs ~$4 Haiku + an A100-80GB for several hours (~$3-8) and is
outside this week's credit unless Ben approves. RL is a separate approval.
