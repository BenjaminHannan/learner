# Think-1 final design: Gated Silent Think Slots (G-STS)

This synthesises the six-design panel (2026-10-24). Labels: **[shown]** = measured, or read in code or data today; **[suggested]** = inference or arithmetic; **[untested]** = nobody has run it here. Kept apart: the Qwen3.5-0.8B village pilot; v1 (premonition's 2M from-scratch village model, a prior only); and LFM2.5/tau2. Card experiments are not used.

## 1. Decision

**Build D6 (Silent Think Slots) with five grafts:**
1. D1's zero-init gated read.
2. No refiner access to the context.
3. Two-stage training on a frozen arm-A adapter.
4. D2/D5's control trained at one lap.
5. A smaller refiner whose output layer is not zero-initialised.

**Why D6.** All three judges ranked it first (Borda 18; D5 14, D1 11, D2 11, D4 6, D3 3) [shown]. The weighted score put it third (6.40 vs D5 6.73, D2 6.45) [shown], but that 0.33 gap is almost all speed (7.0 vs 9.0), i.e. the per-turn burst. The burst is under 3% of a 42 s tau2 turn: today's fit on 553 thinking-ON turns gives 10.8 s + 22.4 ms per output token + 3.43 ms per prompt token [shown]. D6 has the best gain score (5.67) and the strongest frozen-backbone evidence. LRT's recurrent refiner scored 56.7 against 47.5 for an equal-budget non-recurrent one, and INTACT's progressive re-encoding scored 84.4 vs 82.0 [shown, R4]. Attackers gave it P(pass) 0.07/0.10; of its three fatal points, the bar is shared by all designs and the grafts fix the other two. My estimate is **P(PASS) ≈ 0.10** [suggested]: the bar (≥70.12) is above Qwen3.5-2B + LoRA, which scored 69.81 [shown].

**D5 (Decision-Point Board; 6.73, Borda 14, attacker P 0.05/0.12).** Each lap feeds one frozen pre-norm layer (11 / 18) its own output. The damped step has no fixed point and no norm clamp, so the board drifts or goes flat [suggested, attack]. A lap is one attention read of one layer's KV, which is less compute than B's 8 extra layer passes that bought only +0.40 [shown]. At LFM the lap includes a frozen 64-expert router that the dense pilot never exercises [shown, config], so a pilot pass would not carry over. It alone adds per-token decode cost (+0.85-1.15 ms) [suggested]. Kept: halting rule, decision points, laps 9-12 in training, Mac timing/Jaccard check.

**D2 (Slot Laps; 6.45, Borda 11, attacker P 0.07/0.15).** It re-runs layers 8-11 (LFM 16-23, all MoE) on the slots' own output. That is the operation behind Loop-1L B's start loss of 2.56 vs 0.72 and its fall to 29.6 at 12 passes [shown]. With no gate, step 0 is not arm A. A CPU probe (frozen untrained Qwen3.5-0.8B, n=40, 2-shot): 16 pause slots cost +0.355 ± 0.090 nats of answer CE. D2's untrained laps then recover −0.04 / −0.15 / −0.28 / −0.31 nats at R = 1/4/8/12, mostly on shallow rows [shown, backbone/think/panel/probe/d2_probe_2shot.json, aggregated today]. So its "rises" mark can be met with no training. Kept: the C1 control, the swap and mean-board lesions, and the per-lap change trace.

**D1 (Forked Soft Board; 6.12, Borda 11).** Its only lap-to-lap path is a rank-64 linear map. That is the weakest feedback class: in HybridAgent, identity feedback scored 71.4 vs 88.2 for MLP+residual [shown, R4]. Kept as the core of the read path: a per-head zero-init tanh(α) gate on a parallel attention branch over slot K/V, which gives an exact arm-A start. Also its fork recipe, smoke tests and fallback.

**D4 (Draft-Check-Revise; 5.13).**
- Its Jacobi drafts converge to the model's own greedy answer, so the draft curve rises by construction [suggested].
- It needs three losses and reads ~11.9 GB per LFM lap [suggested].
- *Kept:* per-lap frozen-head readouts and flip counts.

**D3 (Lap-Routed; 4.88).**
- Routing adds a second source of decoration, and the evidence runs against it: untied routers moved loss by <0.01 nats, and loops re-pick the same experts [shown, R3].
- *Kept:* the expert-overlap check.

## 2. Pilot spec (Qwen3.5-0.8B, village)

**Task and frozen parts.**
- **Task.** Village QA in the stage-1 harness (`backbone/train.py`, max-len 2048, prompt + " [answer]", greedy decoding up to 24 tokens, exact match) [shown].
  - Validation has 8,675 rows with a `depth` field, and depth is A's weakest axis (Pdepth 74.47 vs P0 82.42) [shown].
  - The chats are near floor at 0.8B [suggested].
  - Training data stops at depth 3, while 1,558 validation rows (18%) are depth 4-6 [shown].
- **Frozen.** Qwen3.5-0.8B (24 layers, d=1024; attention at 3/7/11/15/19/23 with 8 q / 2 kv heads × 256; Gated DeltaNet elsewhere), plus arm A's LoRA r16 for the same seed, unmerged [shown].

**Board.** K=16 slots × 1024 in input-embedding space. Learned e₀ starts as 16 distinct neutral-token embeddings. The board is clamped to RMS ≤ ρ, where ρ is the median row RMS of the embedding table.

**Laps.** Laps run once per question, after the prefill of prompt[:-1] (everything except the final token of " [answer]"). A *pass* runs the K slots through all 24 layers on a fork of that cache. The slots read the prompt natively (the attention KV and the DeltaNet conv/recurrent state) and see each other causally. They all sit at the RoPE position T−1 of the held-back token, and a pass never writes into the prompt cache. Pass 0 reads e₀. After pass t the refiner updates the board, and pass t+1 reads the new board. **L laps = L refinements = L+1 passes**, and L=0 means learned pause slots.

**Refiner (2,644,016 params [shown, arithmetic]).**
1. u = W_in·[rms(h₁₁); rms(h₁₇); h_final] at the slot positions (3072→256).
2. Two pre-norm blocks, each with 4-head self-attention over the slots and a GELU MLP (256→1024→256).
3. Δ = tanh(W_out·norm(u)), with W_out (256→1024) at its default init, not zero.
4. e ← clamp_ρ(e + ρ·η⊙Δ), with a per-channel η initialised to 0.1.

There is no lap embedding, so every lap applies the same operator and lap 16 is defined. **There is no cross-attention to the context.** Any new fact has to arrive through another backbone pass, so recurrence is the only route to a second hop.

**How the backbone reads the board.** Only the answer path reads it, at the 6 attention layers. The answer pass continues from the un-forked prompt[:-1] cache with [last prompt token, answer tokens]. At layer ℓ, head h: o_h = SDPA(q, prompt+answer KV, causal) + tanh(α_ℓh)·SDPA(q, slot K_ℓ, slot V_ℓ). The result then passes through the layer's own sigmoid gate and o_proj. Slot K/V are the post-norm, post-RoPE keys from the final pass.

α (6×8) starts at 0, so at step 0 every logit equals arm A's whatever the board holds. The untrained lap curve is therefore flat, which removes D2's free rise and the +0.355-nat pause penalty. |tanh α| is the logged board-use meter Newt lacked [shown, R1]. The answer's DeltaNet layers never see the board. Cost: Flamingo every-4th-layer reads 68.8 vs every layer 70.7 [shown, other setting].

```python
def gsts(prompt, ans, L_max):
    with no_grad(): C, mask = prefill(prompt[:, :-1])      # frozen base + frozen A-LoRA (= arm A)
    p = last_pos(mask)                                      # RoPE position of the held-back token
    e, ces, pen = e0.expand(B, K, d), [], 0.0
    for t in range(L_max + 1):
        h, kv = backbone(inputs_embeds=e, pos=p.expand(K), cache=ForkCache(C),
                         taps=(11, 17, "final"), record_kv=ATTN_LAYERS)
        ces.append(answer_ce(C, prompt[:, -1:], ans, board_kv=kv, gate=tanh(alpha)))
        if t == L_max: break
        u = W_in(cat(rms(h[11]), rms(h[17]), h["final"]))
        for blk in refiner: u = blk(u)                      # slot self-attention + MLP only
        de = rho * eta * tanh(W_out(norm(u)))
        e = clamp_rms(e + de, rho); pen = pen + (de / rho).pow(2).mean()
    return mean(ces) + 0.01 * pen / max(L_max, 1)
```

**Training (two stages).**
- **Stage A** is arm A as already trained: LoRA r16 on all layers, answer-only CE, 418 steps, batch 16 [shown]. Seed s's adapter is loaded and frozen; if it is missing, it is retrained the same way.
- **Stage T** trains only e₀, α, η and the refiner. The prefill runs under no_grad, so gradients flow only through the slot and answer passes.
  - This means the LoRA cannot absorb the loss first (D6 attack F2).
  - Only one factor in the chain (α) starts at zero, so every refiner weight gets gradient as soon as α moves.
- **Optimisation:** 1,254 steps (3×418), batch 16 (micro 4), reshuffled with seed s; cosine schedule with 60 warmup steps; AdamW, weight decay 0, clip 1.0.
- **Learning rates:** α 1e-2 in its own logged group; e₀, η and the refiner 1e-3.
- **Laps per step:** L_max = 8 (probability 0.8) or 12 (0.2), with full backpropagation through time.
- **Loss:** answer CE averaged uniformly over laps t = 0..L_max (Ouro's uniform prior, R1 rule 6), plus 0.01·mean‖Δ/ρ‖² (LRT).
  - Every lap is then a valid exit, so a weak lap 1 cannot fake a rise.
  - TaH found per-lap loss scored −4.3 against final-lap-only [shown, R3], so final-lap-only at L~U{1..12} runs as an ablation.
- **Cost:** about 2-3 s per step on the 5070 Ti (~1 h per seed), with a 4-6 GB peak [suggested].

**Arms.** Three seeds unless noted. Seed s uses A's seed-s adapter. Names follow `backbone/think/run_box.sh`.

| Arm | What | Why |
|---|---|---|
| A, B | stage-1 adapters re-scored in the new harness | a rerun of the same arm and seed gave 67.78 vs 65.94 [shown] |
| A+ | A's LoRA + 1,254 steps on T's rows (seed 0; 3 seeds if A+ − A ≥ 1.0) | more training without a board; 537 steps gave −0.32 [shown] |
| t (T) | G-STS | the block |
| t1 (T1) | same module and steps, L_max = 1 | same parameters, one refinement (LRT's 47.5 control) |
| ablations (seed 0) | lastloss; K=8; 418 / 2,508 steps; detached hinge | design choices, budget |

**Evaluation.**
- **Lap sweep.** Full validation (8,675 rows) at L ∈ {0, 1, 2, 4, 8, 12}, with 16 and 24 as diagnostics. One prefill and one 24-lap run per row record the board K/V at every L; each L decodes from a cache clone. Cost ≈ 1.5-2× A's eval [suggested].
- **Other sets.** Dev at every L. Pdepth (4,367 rows, templates seen) at L = 1 and 8.
- **Lesions at L=8:**
  - *swap:* use the board from a different story;
  - *mean board:* average the slot K/V over the batch;
  - *repeat-Δ1:* reuse lap 1's update for laps 2-8, with no new passes;
  - *gates off:* must equal A exactly. This is a correctness check, not a result.
- **T1** is scored at L = 0 and 1 (and at 8 as a diagnostic).
- **Logged every 50 steps (512 dev rows):** |tanh α|, slot attention mass, ‖e_t − e_{t−1}‖/ρ, slot cosine, per-lap CE / accuracy / flips, and each slot's frozen-head top token.

## 3. Implementation notes (transformers 5.20.2) and CPU tests

**Read in the code today [shown]:**
- **In-place cache writes.** `LinearAttentionLayer.update_conv_state` and `update_recurrent_state` write in place with `copy_` (cache_utils.py, lines 1112 and 1133). Unforked laps would corrupt the prompt state.
- **Multi-token DeltaNet chunks.** With a cache, `Qwen3_5GatedDeltaNet` concatenates the cached conv state and calls `torch_chunk_gated_delta_rule(initial_state=…)`. In-place updates happen only in single-token decode (modeling_qwen3_5.py 560-640).
- **Gated attention.** `Qwen3_5Attention` computes attn·sigmoid(gate) before o_proj (lines 773-806), so the board term must be added before the gate.
- **Left padding.** Left-padded DeltaNet inputs are zeroed by `apply_mask_to_padding_states`.

**ForkCache (~40 lines)** wraps the prompt cache C:
- *Attention:* `update(k, v, i)` returns cat(C[i], k/v), stores nothing in C, and records (k, v) as the slot K/V.
- *Linear layers:* they read C's states and assign new ones into the fork's own dict, never into C.
- *Eval decode:* this uses a real clone instead (copy the GDN states, a few MB per row; crop the attention).

**Positions and masks.**
- `position_ids`: all slots sit at T_b − 1 for each row, expanded to the 3 mrope axes as `Runner.hidden` does [shown].
- Mask: cat(prompt_mask[:, :-1], ones(B, K)). HF builds the causal mask from the cache index, so slot j should see slots ≤ j [untested, T3].
- The board branch is an unmasked SDPA, with repeat_kv mapping 2 KV heads to 8.
- Logits are computed only at answer positions.

**Read patch.** Subclass the 6 `self_attn` modules. The subclass adds `tanh(alpha)[h]·sdpa(q, ks, vs)` when a board is set and is otherwise identical to the original.

**Memory.** Expect no checkpointing at micro-batch 4 [suggested]. If memory goes above 14 GB, checkpoint each slot pass (`use_reentrant=False`); that is safe because C is never mutated.

**CPU tests before any GPU run** (tiny `--smoke` config, plus the real 0.8B in fp32 on 5 rows):
- **T1** With α=0, answer logits equal stock A's within 1e-5 at L = 0/1/4/8.
- **T2** C is bit-identical after the laps (`torch.equal`).
- **T3** A fork pass equals a no-cache forward of [embed(prompt[:-1]); e] within 1e-4.
- **T4** Cached greedy decoding with the board equals a no-cache re-forward at L = 1/4/8.
- **T5** With α=0.5, gradients reach e₀, α, η and every refiner tensor, and none reach the backbone or the LoRA. Float64 `gradcheck` passes through one fork plus one lap.
- **T6** Logits for a single row equal its logits in a left-padded batch, within 1e-4.
- **T7** The swap lesion is a no-op at α=0 and changes the logits at α≠0.
- **T8** The same seed gives identical losses over 10 steps.

## 4. Preregistered marks (pilot)

**Notation.**
- S_s(L) = seed s's validation accuracy at L laps. S̄ = the 3-seed mean.
- A_ref = max(66.72, re-scored A mean, A+ mean).
- B_ref = max(67.12, re-scored B mean).

**PASS = G and R.**
- **G (gain):** S̄(8) ≥ max(A_ref, B_ref) + 3.0, which is ≥ 70.12.
- **R (rises)** requires all four:
  - **R1 (slope):** S̄(8) − S̄(1) ≥ 1.5, and S_s(8) − S_s(1) ≥ 0.5 in every seed (paired, same rows).
  - **R2 (monotone):** S̄(2) ≥ S̄(1) − 0.3, S̄(4) ≥ S̄(2) − 0.3 and S̄(8) ≥ S̄(4) − 0.3. The 0.3 is about 2 SE of a 3-seed paired lap difference, assuming ~6% of rows flip between lap counts [suggested].
  - **R3 (no collapse):** S̄(12) ≥ S̄(8) − 1.0, and S_s(12) ≥ S_s(8) − 2.0 in every seed.
  - **R4 (not just parameters or step size):** S̄(8) − T̄1(1) ≥ 2.0, and S̄(8) − S̄_repeatΔ1(8) ≥ 1.0.

**Wrong if** any one of these holds:
- S̄(8) − T̄1(1) < 1.0;
- S̄(8) − S̄(2) < 0.5;
- the swap lesion costs < 1.0 point;
- S̄(8) < A_ref + 1.0.

Anything between is partial: no scale-up.

**Mechanical gate (150 steps, seed 0, ~10 min):** debug first if mean |tanh α| < 0.02, cross-question slot cosine > 0.95, the clamp binds on >90% of slots at lap 12, or a loss is NaN.

**Futility stop after seed 0** (T, T1 and A+ seed 0, ~5 PC-hours). Stop the remaining seeds if any holds:
- S₀(8) < 68.7. A true mean at the bar would land this low only ~6% of the time, given a seed SD of ~0.9 [suggested].
- S₀(8) − T1₀(1) < 1.0.
- S₀(8) − S₀(2) < 0.5.
- The swap lesion costs < 1.0.

If only the first condition fails, the laps are real but too small. In that case the PASS track stops and Think-1b gets its own prereg.

**Secondary readouts (no weight in PASS).**
- **M1:** on where_before + plan_get (2,019 validation rows; A scores 33.5% / 37.8% [shown]), S̄(8) − T̄1 ≥ 3.
- **M2:** on Pdepth, S̄(8) − T̄1 ≥ 2.
- **Report by depth and bank.** 36.8% of validation is depth ≤1 [shown]. Q7/Q8 fail on new templates (validation 6.0/43.5 vs Pdepth 79.1/98.1) [shown], and laps cannot fix that [suggested].
- **If M1 passes and G fails,** Think-1b retrains all arms on difficulty-switched data with depth 4-6 chains. That is one change, under its own prereg.

## 5. Scale-up: LFM2.5-24B-A2B and tau2 retail (after a pilot PASS)

**Measure first (Mac, no training).**
- **(a) Paired table.** Thinking ON vs OFF win/loss on tasks 0-39 (minutes): how many of ON's 7 net gains were OFF's too_many_errors aborts?
- **(b) Guard run.** Thinking OFF plus a guard that refuses an identical repeat of a failed call (~3.4 Mac-hours, <$1 of Haiku, Ben's approval). If it scores ≥28/40, tau2 leaves ≤2 tasks for any board, so the board is judged offline only and v2 ships with the guard.
- **(c) Speed.**
  - Base decode with 2 agents at 6.4k and 9.4k tokens of context.
  - Nine 8- and 16-token `input_embeddings` passes after a 6k-token cached prompt. mlx-lm 0.32.2 lfm2_moe accepts `input_embeddings`; its conv cache is reassigned rather than mutated; `KVCache.trim` exists [shown, read today].
  - Expert Jaccard between laps.
  - Expected [suggested]: ~139 ms per pass at K=16 and ~90 ms at K=8, assuming ~64 GB/s.
- **(d) Thinking length,** already measured [shown]: mean 284 tokens per turn, median 122, p90 712; 74% of turns are ≤300 tokens; 48% of thinking tokens sit in turns over 700 tokens.

**Attach points.**
- K=8 slots (K=16 ablation) at every assistant generation, forked from prompt[:-1] of the thinking-OFF format; taps at layers 18 and 30 plus the final norm; refiner d_r=512 (10.53M); gated read at all 10 attention layers (320 gates, α=0); default L=4.
- No board carries across turns: the template strips old thinking and mlx re-prefills every turn [shown, attack]. The server needs only a post-prefill burst hook and the read patch in `Attention.__call__`.

**Distillation (stage 1).**
- **Setup.** A100-80GB, bf16, on dequantised mlx 4-bit weights, so the trained function is the deployed one. HF experts are 3-D parameters, so bitsandbytes cannot load them in 4-bit [shown, attack].
- **Data.**
  - Thinking-ON rollouts on retail tasks 40-113 only, ×4 at T=0.7: ~300 episodes, ~25 Mac-hours, ~$4 of Haiku [suggested].
  - DAgger states where thinking-OFF arm A repeats a failing call, relabelled with the teacher's action.
  - The 1,792 chats as warm-start.
- **Offline metric (M_tool-retail).** ~20 held-out tasks: exact tool-call match per turn plus the no-repeat rate, ~1,000 turns, SE ≈1.5 [suggested].
- **Loss.** CE on the teacher's post-think tokens (tool calls weight 1, text 0.5) plus top-32 KL, uniform over laps. No hidden-state term: on a model's own traces, CODI kept ~1/4 of CoT's accuracy [shown, R2].
- **Arms** (equal data and steps): A-dist (thinking-OFF LoRA, no board), T1, and T, both on top of A-dist.

**RL (stage 2): JOLT+ with a Sonnet 5.5 reward, run only if stage 1 passes.**
- **Port first:** rlaif is LoRA RL on Qwen3-1.7B in a files/email sandbox [shown, SPEC.md] and must be ported to tau2 tasks 40-113.
- **Reward:** 0.6·DB check + 0.4·Sonnet grade, using between_tools thinking and the ledger's hard stop [shown, grader.py].
- **Teacher and losses:** the teacher is the same weights given the reference actions as hints. Train with GRPO, plus reverse-KL to that teacher, plus a KL anchor (β 0.1) to the stage-1 policy. INTACT without its anchor fell from 78.8 to 42.9 [shown].
- **Exploration:** L fixed at 4; Gaussian noise on Δ (σ = 0.1ρ).
- **Cost:** ~$0.01-0.025 per grade (9-10k-token transcripts at $2/$10 per M [shown]), so ~$1-1.6 per step at G=4 × 16 tasks [suggested]. Cap $15 unless Ben raises it.
- **Infrastructure:** rollouts in mlx on the Mac, updates on the rental with ratio clipping [untested].

**LFM pass marks (fixed now).**
- **Offline:** T@4 ≥ A-dist + 3, T@4 − T1 ≥ 1.5, and the swap lesion costs ≥3.
- **tau2** (tasks 0-39 × 4 trials, paired by task): ≥27/40 and ≥ A-dist + 2 tasks. Wrong if T ≤ A-dist.
- **Speed:**
  - time-averaged decode ≥30 tok/s per agent (2 agents, 6.4k context) and ≥97% of base; if base itself is under 30, report that to Ben;
  - added TTFT ≤0.7 s per generation;
  - ≤ +15 s per episode, against ~87 s of thinking tokens for thinking-ON [suggested].

## 6. Open risks and claims to verify against code

1. **The bar.** 70.12 is above the 2B LoRA's 69.81 [shown], and the in-range chain errors may be worth only +1.5 to +2 [suggested]. Expect G to fail even if the laps work. M1, M2 and R4 are what make the run informative.
2. **Depth range.** Training stops at depth 3. Retrofits extrapolate only ~1.5× their supervised depth [shown, Shapiro].
3. **Frozen slot queries may retrieve poorly**, giving a flat curve. Fallback: expected-embedding feedback, softmax(lm_head(h)/τ)·W_emb [untested].
4. **Per-lap loss vs TaH's −4.3** [shown]. The lastloss ablation decides.
5. **Read capacity.** The board is read at only 6 of 24 layers and never by DeltaNet [untested cost].
6. **Verify in code:**
   - the causal mask when slots share one position (T3);
   - fla's backward pass with an initial state that has no grad, on 16-token chunks;
   - that the A/B adapters for seeds 0-2 exist;
   - the Pdepth path;
   - that the peft LoRA is active inside forks;
   - the RMS of `embed_tokens`;
   - the step-time and memory estimates.
7. **LFM:**
   - router behaviour on soft slots;
   - 4-bit vs bf16 parity on 20 transcripts (board cosine ≥0.98, next-token KL ≤0.05);
   - one renderer for training and serving: the OFF arm appends `<think>\n</think>\n`, Loop-1L writes `<think></think>` [shown, attack];
   - whether the tau2 gap is a repetition bug;
   - RL rollout cost;
   - re-measuring the 64 GB/s fit, the ~31 tok/s at 6.4k context, and the 42 s turn fit [inputs shown, readings suggested].
