# D1 (minimal adapter): Forked Soft Board (FSB)

Labels: **[shown]** = measured, or read in code/config today; **[suggested]** = inference or literature from another setting; **[untested]** = nobody has run it here. The stage-1 Qwen village runs and v1 (the 2M from-scratch village model) are kept apart: v1 numbers are cited only as v1.

## 1. Summary

No new layers. The "thinking block" is the frozen backbone itself (with the same LoRA as arm A), run over **K = 8 soft tokens** (the board) on a **forked copy of the prompt cache**, once per answer/turn, before the first output token. Between laps, a rank-64 feedback adapter (zero-init) adds a bounded residual to the board, computed from the slots' own final hidden states. Answer tokens read the last lap's slot K/V at the full-attention layers through a parallel attention branch. That branch reuses the frozen q/k/v projections, and a per-head `tanh(α)` gate starts at 0. New parameters: **0.14M** (Qwen3.5-0.8B) and **0.28M** (LFM2.5). At init the model is exactly the base model (exactly arm A's start). Decode cost is about one 8-key softmax per attention layer. Laps are meaningful because each lap is a full-depth re-read of the context, with queries conditioned on what the previous lap found. That is pointer-chasing, one hop per lap.

## 2. Mechanism

- **Where.** Laps run all layers (0-23 Qwen, 0-39 LFM2.5) over the K slots only. The read happens at every full-attention layer: Qwen 3, 7, 11, 15, 19, 23 [shown, config]; LFM2.5 2, 6, …, 38 (10 layers) [shown, brief].
- **What a lap reads.** The whole prompt, natively. Slot tokens continue from the cache of `prompt[:-1]`, so the GDN/short-conv layers start from the prompt's recurrent and conv state and the attention layers see the prompt KV. In transformers 5.20.2, `Qwen3_5GatedDeltaNet.forward` and `Lfm2MoeShortConv.forward` with `seq_len > 1` and an existing cache prepend the cached conv state and pass `initial_state = recurrent_state` to the chunked rule [shown, code read].
- **What a lap writes.** `E ← rms_to(E + U·V·RMSNorm(h_final), emb_rms)`. Here `h_final` is the slots' final-normed hidden state, which with tied embeddings lives in token-embedding space. U is zero-init, and the residual is bounded and rescaled to the embedding RMS.
- **Board.** K = 8 slots × d_model (1024 / 2048). E0 is initialised from the embeddings of a fixed 8-token phrase ("Let me trace this step by step:"), so lap 1 starts in-distribution.
- **How the backbone reads it.** At read layer l, for answer positions: `o = attn(q, prompt+answer KV) + tanh(α_l)[head] · softmax(q·K_slotᵀ/√d)·V_slot`, then the layer's own output gate (Qwen `sigmoid(gate)`) and `o_proj` / `out_proj`. Because o_proj is linear, the sum is formed before it, so there is no extra matmul. Prompt positions never read the board.
- **When.** Once per turn: after prefilling `prompt[:-1]` and before feeding the final prompt token. Village: the last token of " [answer]". LFM2.5 chat: the board sits conceptually inside `<think>…</think>`; the cut is before `</think>`. Then decoding continues from the un-forked cache.
- **Training lap sampling.** N ~ Uniform{1..8} per step, answer loss at the final lap only. v1 "lastloss" gave the larger 2→8 gain [shown, v1 only]. Full BPTT through the laps is cheap: 8 tokens per lap.
- **Halting.** None. The lap count is fixed at test time and swept over 0 (gates off), 1, 2, 4, 8, 12. Learned halts did not help v1 [shown, v1] or the literature [suggested, R3].

**Parameter count.**
- Qwen: E0 8×1024 = 8,192; V+U 2×1024×64 = 131,072; α 6×8 = 48. Total **139,312**. Arm A's LoRA is 10,822,656 [shown, result_a.json; it matches my per-layer count], so FSB trains 10.96M in all.
- LFM2.5: 16,384 + 262,144 + 10×32 = **278,848** added.

```python
# trained: E0[K,d], V[d,64], U[64,d] (U=0), alpha[R,H] (=0), plus arm-A LoRA (shared)
def fsb_forward(prompt, answer, N):            # prompt LEFT-padded, answer right-padded
    x, last = prompt[:, :-1], prompt[:, -1:]
    C = OutOfPlaceCache(cfg)                   # subclass: assigns states, never copy_()
    run_layers(embed(x), C, pos=arange(T-1))   # ordinary prefill (= arm A)
    E = E0.expand(B, K, d)
    for t in range(N):
        Ct = C.fork()                          # new cache object, same tensors (no copy)
        set_read_mode("record")                # read layers store slot (k, v) after RoPE
        hs = run_layers(E, Ct, pos=T-1+arange(K))  # frozen backbone + LoRA over slots
        if t < N - 1:
            E = rms_to(E + U(V(rmsnorm(hs))), emb_rms)
    set_read_mode("read")                      # use the lap-N slot (k, v)
    h = run_layers(embed(cat(last, answer[:, :-1])), C, pos=T-1+arange(len(answer)))
    return cross_entropy(lm_head(h), answer)

class ReadAttn(Qwen3_5Attention):              # same pattern for Lfm2MoeAttention
    def forward(self, h, pe, mask, past_key_values=None, **kw):
        q, gate = split(self.q_proj(h)); q = rope(self.q_norm(q)); k = rope(self.k_norm(self.k_proj(h)))
        v = self.v_proj(h); k, v = past_key_values.update(k, v, self.layer_idx)
        o = sdpa(q, k, v, mask)                # unchanged base path
        if self.mode == "record": self.slot_kv = (k[..., -K:, :], v[..., -K:, :])
        if self.mode == "read":
            ks, vs = repeat_kv(self.slot_kv)   # all K slots visible, no mask
            o = o + tanh(self.alpha)[None, :, None, None] * sdpa(q, ks, vs, None)
        return self.o_proj(flat(o) * sigmoid(gate))
```

**Implementability [shown by code reading; numerics untested].** HF linear-attention cache layers update with in-place `copy_()` (`LinearAttentionLayer.update_recurrent_state`, and `update_conv_state` unless `record_past`). Forking the cache under autograd would therefore hit version-counter errors, or one lap would corrupt the prompt state for the next. The fix is a ~30-line cache subclass that assigns new tensors instead. At inference, fork by cloning the GDN states (about 9 MB per sequence at 0.8B) and `crop` the attention layers. Smoke test first (Loop-1L template): α = 0 logits equal stock HF; cached generation equals full re-forward at N = 1/4/8.

## 3. Training recipe

**Pilot** (village, 3 seeds): identical to arm A (LoRA r16 on all layers, 418 steps, batch 16, lr 2e-4, answer-only CE, backbone frozen). The block params get their own group: α lr 1e-2 (Shapiro: gates need their own group or they fail silently [suggested]); U, V, E0 lr 1e-3. Compute is A plus N·K/T, about 64/1000 = +6% at N = 8 (+4% on average), so it fits wherever A fits (A ran on the 16 GB PC [shown]).

**LFM2.5**:
1. Distil from the same model's thinking-ON runs on the 1,792 chats and tau2-style rollouts. Keep only successful episodes. Loss: CE on the post-`</think>` action tokens, plus top-32 KL to the thinking-ON teacher's action-token distribution (the teacher conditioned on its own think text; logits stored offline). Add a preservation KL on the student's own lap-0 rollouts (INTACT's no-preservation run collapsed, 42.9 vs 78.8 [suggested]).
2. JOLT+/GRPO with the existing rlaif reward, plus a ~0.01 penalty per lap if a lap-count head is ever added (Switch reward-hacked laps [suggested]).

## 4. Mac speed (LFM2.5, 4-bit, 2 agents)

- **Per decoded token.** The extra cost is 10 layers × a softmax over 8 keys, plus reading slot KV: 8 × 8 kv-heads × 64 × 2 (K,V) × 2 B × 10 = 164 KB, against about 1.24 GB of weights per token, i.e. 0.01%. Decode stays **≈35.3 tok/s per agent** (rule: ≥30) [suggested arithmetic].
- **Per lap.** One forward of 8 tokens through 40 layers. Weight reads:
  - Non-expert: ~0.75B params.
  - Experts: union of 8 tokens × top-4 of 64, at most 64·(1−(60/64)^8) = 25.8 experts per layer, say 16-26, × 9.44M × 38 layers = 5.7-9.3B params.
  - At 4.5 bits that is 3.7-5.6 GB.
  - Decode moves 1.24 GB in 18 ms (≈69 GB/s effective); big batched reads should run nearer 100-150 GB/s.
  - Result: **≈25-55 ms per lap**.
- **Per turn.** 8 laps ≈ 0.2-0.45 s with 1 agent, ~0.3-0.7 s with 2 agents. That is time-to-first-token (TTFT) only. With K = 4 the expert union, and so the lap cost, is roughly halved [untested].

## 5. Why laps should matter

Village answers need chains of the form "balloon → in box → box at bakery → …". The training data has depth 0-3 only. Validation has 1,558 rows at depth 4-6 [shown, counted today], and depth is A's weakest probe axis (−8) [shown]. One lap is one full-depth query from the slot positions into the log. Feeding the slot's final state back lets lap t+1's attention queries carry the entity found at lap t, so reach grows by about one hop per lap. Re-running layers 8-11 at every position (arm B) adds depth but not a query that changes between rounds [suggested].

**Predictions** (validation, N = 8, 3-seed mean): **+2.0 over B (≈69.1)**, 80% interval −0.5 to +4.5. My chance of clearing the +3 bar is about 30%. **lap8 − lap1 = +2.5**, concentrated at depth ≥ 3 (depth 4-6: +6). Lap 12 within 1 point of lap 8.

**Pass marks, fixed now:** the PASS rule in the brief, plus the swap control (each question gets another question's board) dropping ≥ 2 points at N = 8.

**Wrong if:** lap8 − lap1 ≤ 0.5 on depth 4-6 rows, or the swap drop is < 0.5. Either means the board is ignored or decorative, whatever the headline.

## 6. Three strongest failure reasons and the cheapest test of each

1. **The board is ignored** (α stays near 0, or the LoRA absorbs all the learning). Test: 1 seed, 100 steps; log tanh(α) per layer and the swap drop on 1k validation rows. About 15 GPU-minutes on the PC.
2. **Fixed point by lap 2** (v1 converged in about 3 loops [shown, v1]), so the curve is flat. Test: same checkpoint; lap sweep 1/2/4/8/12 by depth, plus ‖ΔE‖/‖E‖ per lap. No training needed.
3. **Fed-back hidden states are off-manifold**, so laps 2+ hurt (HRPO/HybridAgent saw this [suggested]). Test: at 50 steps, compare validation loss at lap 2 and lap 1. If it is worse, swap the feedback for the parameter-free expected embedding `softmax(lm_head(h)/τ)·W_emb` and rerun the same 50 steps.

## 7. Claims

- [shown] Layer types and indices for both models. The GDN/short-conv cache continuation path. In-place cache writes. The LoRA count of 10.82M. Village depth counts. The stage-1 A/B/lesion numbers. v1 lap facts (v1 only).
- [suggested] The per-lap and per-token Mac costs (arithmetic, not measured). The hop-per-lap mechanism. That gates need their own learning rate. That preservation KL is needed at LFM scale.
- [untested] Everything about FSB's accuracy. Soft-token routing through LFM2.5's MoE. Forking the cache in mlx-lm. Distillation and RL on tau2.

## 8. Self-scores

- **Gain 5.** A real mechanism aimed at the measured weak axis, but frozen-base soft-token methods give modest gains [R2/R4], and my central estimate (+2) is below the bar.
- **Speed 9.** Decode is essentially unchanged; it costs about +0.3-0.7 s of TTFT per turn.
- **Trainability 8.** Exact base at init, +4-6% compute, fits 16 GB, 0.14M new params. A cache subclass and gate learning-rate care are required.
- **Decoration risk 6.** The fixed-point risk is real. The lap-1 control, swap control and by-depth curve make it measurable at no extra training cost.
