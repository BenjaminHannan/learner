# D5 (halting-first): "Decision-Point Board": fixed laps at a few chosen positions, no learned halt

## 1. Summary
Every-token laps cannot fit the Mac rule: even ONE re-run LFM layer × 8 laps per token gives 1000/(28.2 + 8·28.2/40) = 29.5 tok/s with 2 agents, a fail (arithmetic, untested). So thinking runs only at **decision points**: the end of each assistant header (after every user message and tool result) and, if text came first, right after `<|tool_call_start|>`. There a K=16-slot board is refined for a **fixed** L laps (default 8) by the backbone's own mid-depth attention layer (own LoRA), reading that layer's existing KV cache. Later tokens read the board through zero-init low-rank cross-attention at 3 (Qwen) / 5 (LFM) depths. **No learned halt**: a lap costs ~6 ms once per turn, so a halt saves ≤1% of turn time, and the literature and our v1 say halts buy compute, not accuracy. The budget goes instead into a tied, damped operator trained with random lap counts and a "more laps must not be worse" hinge.

## 2. Mechanism
- **Block = backbone attention layer ℓ, reused** (Qwen ℓ=11, full attention; LFM ℓ=18, attention). Pilot: deep-copy peft-wrapped layer 11 (gated attention, q/k norms, MLP) so the block has its own LoRA r16 on frozen weights. Mac: share layer 18's weights and frozen MoE; block LoRA as separate low-rank matmuls.
- **Reads:** layer-ℓ context K,V up to the decision token = `cache.layers[ℓ].keys/values` (post-norm, post-RoPE; checked in transformers 5.20.2 `cache_utils.py`, `Qwen3_5Attention.forward`). In training they are recomputed from the stored layer-ℓ input with the layer's own k_proj/k_norm/RoPE. Slots take the decision token's RoPE position and attend to context plus each other. No DeltaNet/conv layer is re-run, so no recurrent state is touched (no Loop-1L unrolled cache).
- **Board:** K=16 × d (1024 / 2048), init `z = z0 + h_ℓ[dec]` (instance-dependent, against collapse); optional cross-turn carry `+ c·z_prev`, c=0 at init (LFM only).
- **Lap update:** tied, damped, no lap embedding (lap 16 = same operator): `z ← z + γ⊙(Block(z) − z)`, γ = sigmoid(a) per channel, init 0.5. Context re-enters every lap via attention (input injection by construction).
- **How the backbone reads it:** after layers {11,15,19} (Qwen) or {18,22,26,30,34} (LFM), `x += 1[t ≥ dec] · Wo·Attn(Wq·rms(x), Wk·rms(z), Wv·rms(z))`. 4 heads × 64, rank 256, **Wo zero-init** (step 0 = exactly arm A). Board K/V computed once per burst.
- **Halting:** none; L fixed on dev. Zero-parameter ‖Δz‖/‖z‖ and between-lap answer KL are logged.
- **Parameters (new, on top of arm A's LoRA):** Qwen: block LoRA 401,408 (q 16·5120, k,v 16·1536 each, o 16·3072, MLP 3·16·4608) + sites 3·4·1024·256 = 3,145,728 + z0 16,384 + γ 1,024 = **3.56M** (plus an 18.4M frozen copy). LFM: block LoRA on attention 212,992 + sites 5·4·2048·256 = 10,485,760 + z0 32,768 + γ 2,048 = **10.7M**, with no copy.

```python
def forward(ids, pos, dec, L):                    # dec: decision index per row; L: laps
    x, pe = embed(ids), rope(pos)
    for i in range(n_layers):
        if i == ELL: x_in = x
        x = layer[i](x, pe, masks)
        if i == ELL:                               # build the board once, from layer-l KV
            Kc, Vc = kv_of(layer[ELL], x_in, pe)  # == cache.layers[ELL].keys/values at inference
            ctx_ok = arange(T)[None] <= dec[:, None]
            z = z0[None] + x[arange(B), dec][:, None]          # (B,K,d)
            for t in range(L):
                ctx = no_grad() if t < L - 8 else nullcontext()  # truncated BPTT past 8 laps
                with ctx:
                    u = block(z, Kc, Vc, ctx_ok, pe_at(dec))     # attn(slots -> ctx+slots) + MLP, residual
                    z = z + sigmoid(a) * (u - z)
            zn = rms(z)
            BK = {s: (Wk[s](zn), Wv[s](zn)) for s in SITES}
        if i in SITES:
            r = Wo[i](mha(Wq[i](rms(x)), *BK[i]))  # 4 heads x 64 over 16 slots
            x = x + (arange(T)[None] >= dec[:, None])[..., None] * r
    return lm_head(final_norm(x))
```
Chats with D decision points: batch (B·D) boards with per-point context masks; each token reads the latest board at or before it (block mask over D·K slots).

## 3. Training
**Pilot (village, Qwen3.5-0.8B).** Village fits: one decision point (end of prompt), 8,675 held-out rows (SE ≈ 0.5 pt), a `depth` field (3,426 rows at depth ≥3, counted, shown), and depth is our weakest axis (−8). Chat M_tool at 0.8B is near floor (card tau2 11.6; suggested). Recipe:
- Same as arm A (LoRA r16 on all layers, answer-only CE, 418 steps, bsz 16), plus the block and sites.
- Learning rates: 1e-3 for the new parameters, in their own parameter group.
- Laps: L ~ U{1..8} with probability 0.9, U{9..12} with probability 0.1 (the first L−8 laps run without grad).
- Hinge: on 25% of rows, also run L2 = min(L+4, 12) and add 0.5·relu(CE(L2) − sg(CE(L))). Only the upper half is recomputed (+~12%).
- Cost ≈ +15% step time vs A (B: +33%); fits 16 GB since B does.
- Arms: A, B, D, plus a **D1 control** (same parameters, trained/tested at L=1) to separate laps from parameters (Newt).

**LFM2.5.**
- Stage 1: the teacher is the same backbone with thinking ON, kept only on turns matching the gold call; the student is thinking OFF + board. Loss: CE plus KL on the teacher's action tokens, plus preservation KL (β=0.1) to thinking-OFF on general chat (INTACT collapsed without it). Same lap sampling.
- Stage 2, JOLT+: GRPO + reverse-KL to the hinted teacher at fixed L=8; only block, sites and LoRA train.

## 4. Speed (M1 Pro, 4-bit LFM, 2 agents)
- **Budget:** base 1000/35.4 = 28.2 ms/token; the 30 tok/s floor is 33.3 ms, so there is 5.1 ms of headroom.
- **Per-token reads:** 5 sites × (Wq + Wo) = 5.24M fp16 params = 10.5 MB, against ~1.2 GB for the base, which is about 0.16 ms. Add ~40 small kernels at ~10 µs each, about 0.4 ms. Scaling by the 2-agent contention factor (28.2/18.35 = 1.54) gives **+0.85 ms**.
- **Per lap:** attention weights ~6 MB, plus ~40.6 unique experts for 16 slots × top-4 (64·(1−(63/64)^64)) × 9.44M params × 0.56 B ≈ 215 MB, plus 12k-token KV at 2 KB/token ≈ 24 MB. That is ≈ 245 MB per lap. At the observed decode efficiency (~67 GB/s) it takes 3.7 ms, or **5.6 ms with 2 agents**.
- **Bursts:** 8 laps = **+45 ms TTFT per turn** (prefilling a 200-token tool result already takes ~480 ms).
- **Mid-turn re-think** after text: ~0.5 per turn × (4 laps + one upper-half re-forward ≈ 38 ms), over ~60 tokens ≈ +0.3 ms/token.
- **Total:** 28.2 + 0.85 + 0.3 = 29.35 ms → **≈ 34 tok/s per agent** (untested).
- **Uncertain-token triggers: off.** TaH lost 30% throughput at 6% of tokens; a jointly trained trigger collapsed (−30.4) (shown, R3). As an ablation the budget allows ≤ ~8% of tokens.

## 5. Why laps should matter
A depth-d village question needs chained lookups (the balloon → who set it down → where they were before). Each lap is ONE attention read over the context, and the lap-t query depends on what lap t−1 retrieved, so hop t needs about t laps (suggested).
- **Prediction:** validation score at 8 laps minus 1 lap = **+3.0** overall, ≥ +5 at depth ≥3, ≈ 0 at depth 0-1. The score at 12 laps is within 1 point of 8 laps, and 16 does not collapse, because the operator is tied and damped and laps 9-12 are in training.
- **Analogue:** forcing 8 loops in v1 gave +1.7 on validation (shown, a different model).

## 6. Top 3 failure modes and cheapest tests
1. **Lap 1 does everything (flat curve, Newt-style).** Test: 1 seed, 150 steps of D and D1 on the PC (≈1 GPU-hour, free); score depth ≥3 rows at L = 1/2/4/8. Wrong if D(8) − D(1) < 1.5 or D(8) ≤ D1 + 1.
2. **Backbone ignores the board** (arm A's LoRA suffices). Log ‖site out‖/‖x‖ every 50 steps; at step 150 test a board swap and a zero board. Fail if the swap costs < 3 points. Fallback: warm-start from a trained A adapter and train block and sites only (plus a continued-A control).
3. **Layer-ℓ KV too shallow for chains, or the frozen MoE routes slots badly.** Pilot: per-lap slot attention mass on lines containing the answer string; retry ℓ=15 if < 2× chance. LFM: time 8 laps of layer 18 over 16 slots at a 12k context on the Mac (no training) and log lap-to-lap expert overlap. Pass if ≤ 8 ms per lap with 2 agents.

**Halting decision rule (fixed now):** compute held-out oracle headroom = per-row best L minus best fixed L. If it is under 2 points, never add a halt. If it is ≥ 2, try only a post-hoc KL exit with its threshold fit on dev, never a jointly trained gate.

## 7. Claims and labels
- **Shown:** the brief's A/B/v1/Loop-1L numbers; learned halts within ~0.5-2.4 points of fixed or zero-parameter exits (Ouro, 2607.20519, HRM; R3); a frozen-retrofit halt head right 9% of the time, PonderNet collapsed (Shapiro; R1); zero-init gates beat random init (Flamingo 70.7 vs 66.5; R4); the cache layout and layer types in §2 (code).
- **Suggested:** the speed arithmetic in §4; that decision points capture most of what thinking-ON does (the think-tool post and the tau-bench failure analysis); village fits the pilot better than chats.
- **Untested:** any gain; a KV-read board on a hybrid conv/MoE; frozen-router behaviour on slots; cross-turn carry; §5's predictions; the pilot forecast of +2.0 over B (≈69.1), with ~30% odds of clearing the +3 PASS bar.

## 8. Self-scores
- **Gain 5.** The mechanism targets depth, our weakest axis, but frozen-backbone latent modules historically give +1 to +5.
- **Speed 9.** About 34 tok/s with 2 agents and +45 ms per turn. Every-token designs fail by arithmetic.
- **Trainability 7.** Exact arm A at init, a clean gradient path, +15% step cost and 3.6M new parameters. Risk: the board stays unused.
- **Decoration risk 7.** The tied, damped laps, the hinge, the D1 control, the depth-sliced curves, and swap/zero-board lesions make decoration measurable. Proven wrong if the slope is under +1.5.
