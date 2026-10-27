# D3: Lap-Routed Thought Layers (MoE-of-thought angle)

Labels: [S] shown (measured here or in a cited paper), [Sg] suggested, [U] untested.

## 1. Name and summary
**Lap-Routed Thought Layers (LRTL).** The backbone stays frozen. Once per turn, a board of K=16 slots thinks before the first answer token. On each lap a router sends every slot to ONE of M=4 "layer experts": the backbone's own full-attention layers, each reading the cached context at its own depth through its own pretrained attention and FFN. At LFM2.5 scale that FFN is the native 64-expert MoE, whose router gets a lap bias. Decoding reads the board through 4 zero-init gated cross-attention sites.

What this buys over a dense block:
- Each lap can be a *different* pretrained function, a direct attack on the fixed point (v1's state change fell to 0.14 by loop 8 [S]; Loop-1L B collapsed at 12 passes [S]).
- Each lap picks *which depth* of context to query (Liu et al.: multi-layer KV read 26.8 vs last-layer 23.2 GSM8K [S]).
- The routing log is a built-in decoration meter.

**Honest prior: this angle is weak.** No paper shows lap-specialised experts helping a frozen backbone [S, R3 §8]; untying routers moved loss by under 0.01 nats [S, Tying the Loop]; loop-trained routers re-pick the same experts [S, SMELT, LOOM]. Below is the strongest version, plus a dense control that decides whether routing earns its place.

## 2. Mechanism
- **Pool layers (layer experts).** Qwen3.5-0.8B: full-attention layers {3, 7, 11, 15} (verified from config.json). LFM2.5: attention layers {10, 14, 18, 22}, each with its 64-expert MoE.
- **Read sites.** Gated cross-attention at the inputs of layers {16, 18, 20, 22} (Qwen) and {24, 28, 32, 36} (LFM). These sit above every pool layer, so training is a single pass.
- **Board.** 16×1024 (Qwen) or 16×2048 (LFM). Initialisation is `z = h[T-2] + S`: the last prefilled token's hidden state after layer LOW_END−1, plus learned slot offsets S (instance-dependent and in distribution).
- **Lap update.** Each slot is routed top-1 (Switch-style) with straight-through scaling `p/p.detach()`. Router input is `rms(z) + E_lap[k]`.
- **Inside a layer expert.** The layer's own attention module, with a thought-LoRA r16 on q/k/v/o used only on the slot path (separate from arm A's LoRA). Context enters through a `PeekCache` whose `update(k,v,idx)` returns `cat(cached[idx], k)` without storing. Both `Qwen3_5Attention` and `Lfm2MoeAttention` call `past_key_values.update(k, v, self.layer_idx)` [S, transformers 5.20.2]. An explicit additive mask (slots see context before T-1 and all slots) turns off SDPA's `is_causal` [S, sdpa_attention.py]. Slots use RoPE position T-1.
- **FFN in a layer expert.** The layer's frozen FFN plus a new "thought expert" (SwiGLU, width 256 Qwen / 512 LFM, zero-init down-projection). For LFM, router logits get `+RB[j][k]` (64 floats). `Lfm2MoeTopKRouter` uses sigmoid(logits) for both selection and weights, and `expert_bias` affects selection only [S, code], so the bias changes which experts are picked and gets gradient through the weights.
- **Damped update.** `z += beta_k * dz`, with beta_k initialised at 0.5 [Sg, R1 §5.3].
- **Initialisation.** Read gates use tanh(α) with α=0, so at step 0 the model is exactly arm A. This avoids Loop-1L B's start loss of 2.56 vs 0.72 [S]. All LoRA B matrices and thought-expert down-projections start at 0.
- **Laps.** Training draws n ~ U{1..12}, which is cheap (one layer over 16 slots per lap) and covers 12 to prevent collapse there.
- **Halting.** None. The lap count is fixed on dev (default 8). A zero-parameter exit (‖Δz‖/‖z‖ < ε) is reported only as a speed option [Sg, R3 lesson 1].

**Parameters (added on top of arm A's LoRA):**

| Item | Qwen3.5-0.8B | LFM2.5 |
|---|---|---|
| Slot offsets, lap embeddings, router, betas | 32.8K | S 32.8K + E 24.6K + Wr 8.2K + RB (4×12×64 = 3.1K) = 68.6K |
| Thought-LoRA per pool layer | q 16·(1024+4096) + k 16·1536 + v 16·1536 + o 16·(2048+1024) = 180,224 | 16·(4096+2560+2560+4096) = 212,992 |
| Thought expert per pool layer | 3·1024·256 = 786,432 | 3·2048·512 = 3,145,728 |
| Pool layers (×4) | 3.87M | 13.43M |
| Read sites (×4, rank 256: q, k, v, o) | 4·1024·256 = 1.05M each, 4.20M total | 4·2048·256 = 2.10M each, 8.40M total |
| **Total** | **8.10M** | **21.9M** |

```python
def forward(ids, T, n_laps, train=True):      # reads start at position T-1
    rec = Recorder(POOL)                      # stores K,V of pool layers only; None for GDN/conv layers
    h = embed(ids)
    for i in range(LOW_END):                  # 16 (Qwen) / 24 (LFM); frozen layers + arm-A LoRA
        h = layer[i](h, past_key_values=rec if i in POOL else None)
    z = h[:, T-2:T-1] + S                     # (B,K,d), last prefilled token
    mask = slot_mask(keys_before=T-1)         # explicit additive mask, so not causal
    boards, aux = [], 0
    for k in range(n_laps):
        u = rms(z) + E_lap[min(k, 11)]
        p = softmax(Wr(u) / tau)              # (B,K,M)
        m = argmax(p + gumbel() * train)
        dz = zeros_like(z)
        for j, L in enumerate(POOL_LAYERS):
            s = (m == j)
            x = z[s] + E_lap[min(k, 11)]
            x = x + L.attn(L.norm1(x), PeekCache(rec, L.idx), mask[s], lora=TL[j], pos=T-1)
            y = L.norm2(x)
            x = x + L.ffn(y, router_bias=RB[j][k]) + TE[j](y)  # frozen FFN/MoE + thought expert
            dz[s] = (x - z[s]) * (p[s, j] / p[s, j].detach())
        z = z + beta[k] * dz
        boards.append(z); aux += load_balance(p, m)
    def upper(zb):
        kv = {i: SITE[i].kv(rms(zb)) for i in SITES}  # once per board
        g = h
        for i in range(LOW_END, N):
            if i in SITES:
                g = g + tanh(alpha[i]) * pos_ge(T-1) * SITE[i].xattn(rms(g), kv[i])
            g = layer[i](g)
        return lm_head(final_norm(g))
    r = randrange(len(boards))
    return CE(upper(boards[-1])) + 0.3 * CE(upper(boards[r])) + 0.01 * aux
```

At inference: prefill `ids[:T-1]` with the normal cache (no reads), run the burst through a PeekCache over the cached pool-layer K,V, project the site K,V once, then decode from token T-1 with the read sites on. This is the same manual layer loop as `Runner.hidden` (stage 1) and `LoopLM.hidden` (Loop-1L) [S, read].

## 3. Training
**Pilot (village).** Arm D = arm A's LoRA r16 + LRTL, answer-only CE as above, 418 steps as in stage 1, 3 seeds, backbone frozen. Learning rates: LoRA 2e-4, block 5e-4, router 1e-3, α gates 5e-3 in their own logged group [Sg, R1 §5.2]. Gumbel τ anneals 1 → 0.3; for the first 100 steps 10% of slot-laps are routed at random so every pool layer's LoRA trains. Fits 16 GB [Sg]: about +35% compute (second upper pass) plus a few MB of slot activations.

**LFM2.5.**
- Stage 1 (distillation): teacher = the same frozen LFM2.5 with thinking ON, on the 1,792 chats plus tau2-style rollouts, keeping turns whose calls match gold. Loss = CE + token KL on the visible post-`</think>` action tokens; student = thinking-OFF + board. Add a preservation KL to frozen thinking-OFF on the student's own rollouts (INTACT collapsed without one, 42.9 vs 78.8 [S]).
- Stage 2 (RL): JOLT+ (reward 0.6·checks + 0.4·Sonnet grade, reverse KL to the hinted teacher). Only block parameters train. Laps are fixed at 8 and the load-balance term stays on.
- Optional: carry the board across turns, `z_init += γ·z_prev` with γ zero-initialised [U].

## 4. Mac speed (2 agents)
- **Base.** 35.4 tok/s = 28.2 ms/token/agent; effective bandwidth ≈ 1.37 GB/token ÷ 18 ms ≈ 76 GB/s [Sg].
- **Per token.** 4 sites × (q 2048×256 + o 256×2048) = 4.2M fp16 params = 8.4 MB ≈ 0.11 ms, plus ≈0.36 ms dispatch (4 sites × 6 kernels × 15 µs) [Sg]: 28.2 → 28.7 ms, **≈34.8 tok/s per agent** (rule ≥30).
- **Per lap (burst).**

| Item | Size |
|---|---|
| Attention weights, 4-bit | 5.9 MB |
| KV read at 8k context (2 KB/token) | 16 MB |
| MoE: 16 slots × top-4 → expected 64·(1−(60/64)^16) = 41 distinct experts × 5.3 MB | 218 MB |
| Thought expert | 6.3 MB |
| **Total** | **≈ 246 MB ≈ 3.2 ms** |

- **TTFT.** 8 laps ≈ +26 ms per turn (12 laps 39 ms; ≈40 ms under 2-agent contention), vs ≈0.7 s to prefill a 300-token tool result: ≈+4% [Sg].
- **Cheaper fallback.** One routing decision per board instead of per slot cuts the MoE read to 4 experts (about 21 MB per lap).

## 5. Why laps should matter
- **Pointer-chasing.** One lap = one attention read per slot: find the visit mentioning X, copy Y into the slot; the next lap queries Y.
- **Why route.** Name-matching suits a shallow layer's KV, "where did the object end up" a deeper one; routing lets each hop pick its depth [Sg].
- **Where to look.** Validation has depths 4–6 (1,558 questions) that never appear in training, whose maximum depth is 3 [S, counted]. Depth is also arm A's weakest axis (−8) [S]. Gains should concentrate there.
- **Predictions (overall validation):**
  - 8 laps minus 1 lap ≈ **+2.5**; on depth ≥4, ≈ +6.
  - 12 laps within 1 point of 8 laps.

## 6. The three strongest failure modes, and the cheapest test of each
All three are read from ONE seed, 418 steps on the PC.
1. **The backbone ignores the board** (or the gain is just extra LoRA capacity). Kill if a shuffled board (another question's) costs <3 dev points, or |tanh α| < 0.05.
2. **The router collapses** (one layer takes everything, or the same route every lap), so routing adds nothing over a dense block. Log a (lap × layer) histogram every 50 steps; kill if one layer takes >80% of slot-laps or same-route-as-previous-lap exceeds 90% after warmup. Run D-fixed (M=1, pool {11}, all else identical): routing must beat it by ≥1 point or is dropped. LFM pre-check on the Mac, no training: Jaccard overlap of selected experts across laps with the untrained block; >0.8 makes the RB lap bias mandatory.
3. **The fixed point arrives by lap 2** (or one layer per lap is too weak for a hop). Dev lap sweep 1/2/4/8/12 plus ‖Δz‖ per lap; kill if 8-minus-1 < 1 point or ‖Δz_8‖/‖Δz_1‖ < 0.05.

**Pass mark (Ben's, fixed in advance):** D beats A (66.72) and B (67.12) by ≥3 validation points (3-seed mean), the 1/2/4/8 lap curve is non-decreasing, and 12 does not collapse. **Proven wrong if** D-fixed is within 1 point of D: routing is then decoration, even if the board helps.

## 7. Claims
- **Shown:** the baselines; the code facts (PeekCache hook, mask/causality, router selection, layer indices, depth counts); the cited literature numbers.
- **Suggested:** the speed arithmetic, depth-selective reading, fitting in 16 GB.
- **Untested:** routing frozen layers over a board, a lap bias on a frozen MoE router, carrying the board across turns, any tau2 gain.

## 8. Self-scores (higher = better)
- **Gain: 4.** The +3 bar is far above +0.4 for B. Routing has no prior evidence. The depth-OOD slice is the real chance.
- **Speed: 9.** About 1.7% decode cost and about 26 ms TTFT; no per-token laps.
- **Trainability: 6.** Exact arm-A start, a small block and a single pass, but Switch routing over 4 frozen layers with Gumbel adds fragility.
- **Decoration risk: 6.** Route histograms, the lap sweep, the shuffled board and D-fixed make decoration measurable. A fixed point remains likely.
