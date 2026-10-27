# D6 (contrarian, evidence-maximal): Silent Think Slots

Labels: [shown] means measured (paper, repo log or code I read). [suggested] means inferred. [untested] means nobody has run it here.

## 1. Name and summary

**Silent Think Slots (STS): K latent tokens inside the empty think block, refined by a small recurrent refiner, with the WHOLE frozen backbone re-reading them on every lap.**

No re-run layers, no per-position board. Once per assistant generation, the backbone prefills the history up to `<think>`. Then 16 soft "slot" embeddings are appended. For each lap: (a) the frozen backbone runs a 16-token forward pass over the slots over the cached context; (b) a ~12M refiner reads slot hidden states at three depths plus the context's final states and writes a bounded residual update to the slots. After L laps the slots are committed to the cache, `</think>` is appended, and the reply decodes at normal speed. No layer ever receives its own output; the backbone only sees token-like inputs. Evidence: LRT (recurrent refiner emitting soft tokens on frozen Qwen3-8B; more cycles help) [shown]; INTACT (progressive re-encoding by the frozen LM beats joint construction, 84.4 vs 82.0) [shown]; DCA (latents as embeddings beat pause tokens; deep/KV reads beat last-layer reads) [shown]; ALAR (K=4 latents per tool-call turn, distilled from own successful thinking rollouts, matched thinking mode on BFCL) [shown].

**Why not the starting recipe.** Re-running layers is what failed on a frozen MoE: Loop-1L B started at loss 2.56 vs 0.72 and fell to 29.6 at 12 passes [shown]; Newt's looped retrofits tied a one-pass control [shown, unreviewed]; LOOM reports expert collapse when MoE layers loop [shown]. One middle cross-attention read is weak (Flamingo 59.8 vs 70.7 reading at every layer) [shown]. Slots in the sequence are read natively by every attention layer (6 in Qwen, 10 in LFM) and the conv/DeltaNet mixers, at no decode cost.

## 2. Mechanism

- **Placement.** Village: `context ⏎ question [16 slots] [answer]`. Chats: `<|im_start|>assistant\n<think>[16 slots]</think>reply`, at every assistant generation (after a user turn or tool result), where thinking-ON thinks. Earlier slots stay cached, so the board carries across turns (Nemotron-Cascade 2: keeping latest thoughts +3-5 on tau2 [suggested]).
- **Board.** K=16 slots × d_model (1024 for Qwen, 2048 for LFM), living in input-embedding space. Slot RMS is clamped to the embedding RMS ρ (raw hidden-state feedback: nonsense rollouts in HRPO, 71.4 vs 88.2 in HybridAgent [shown]).
- **Taps.** Qwen: outputs of layers 11 and 17, plus the final norm. LFM: outputs of layers 18 and 30, plus the final norm. Context memory C = final-norm context hidden states (computed in prefill anyway).
- **Refiner.** A 3-tap input projection to d_r, plus a lap embedding, then 2 pre-norm blocks (slot self-attention, cross-attention to C, MLP 4×), then a zero-initialised output projection to d_model and a per-lap step size η_t (init 0.5, own parameter group with 10× LR, logged). Lap 0: e₀ = learned slots initialised from a 16-token neutral string's embeddings, so at init the model is exactly "A + 16 pause tokens".
- **Parameters.** Pilot (d_r=512): taps 3·1024·512 = 1.57M; per block self-attn 1.05M + cross-attn 1.57M + MLP 2.10M = 4.72M, ×2 = 9.44M; out 0.52M; slots/lap emb 0.02M → **11.6M**, plus arm-A LoRA r16 (467.5k × 18 DeltaNet + 401.5k × 6 attention = 10.8M) → **22.4M trainable**. LFM (d_r=768): taps 4.72M + 2 × (2.36+4.33+4.72) = 22.8M + out 1.57M → **29.1M**, no LoRA.
- **Laps.** Fixed L, no halt (learned halts buy compute, not accuracy; v1's halt "thought longer without gains" [shown]). Train L∈1..8 (weight 1) and 9..12 (weight 0.5), backprop through the last 6 laps. Evaluate 1/2/4/8/12/16.
- **HF 5.20.2 (checked in code).** `Qwen3_5GatedDeltaNet` continues multi-token chunks from cached `recurrent_states`/`conv_states`; `DynamicLayer.update` appends via `torch.cat`; but linear-attention states update **in place** (`copy_`), which would corrupt the context state on a lap and break autograd [shown]. Fix: inference snapshots/restores DeltaNet states (~5M values/sample) and `crop(16)`s attention; training uses a ~20-line cache shim (`record_past=True` so conv states are assigned, plus an assigning `update_recurrent_state`) [untested]. LFM2 ShortConv keeps only conv_states (kernel 3) [shown], so the shim ports. mlx needs a small patch for conv-state snapshot and inputs_embeds in `lfm2_moe` [untested].

```python
def think_and_answer(ids, L):
    cache, H_ctx = backbone.prefill(ids)              # context once (with grad if LoRA trains)
    C = H_ctx.final                                   # [T, d] context memory for the refiner
    e = slot_init.clone()                             # [K, d]  lap 0 = learned pause slots
    pos = T + arange(K)
    for t in range(1, L + 1):
        fork = shim(cache)                            # reads cached state, writes nowhere permanent
        taps = backbone.forward_embeds(e, pos, fork, return_layers=TAPS)   # full 24/40 layers
        u = W_in(cat(rms(taps))) + lap_emb[t]
        for blk in refiner: u = blk(u, C)             # self-attn over slots, x-attn to C, MLP
        e = e + eta[t] * W_out(u)                     # bounded residual, W_out zero-init
        e = e * clamp(rho / rms(e), max=1.0)          # stay on the embedding manifold
        if t <= L - 6: e = e.detach()                 # truncated BPTT
    backbone.forward_embeds(e, pos, cache)            # commit slots to the cache
    return backbone.decode(cache, prefix="</think>")  # ordinary decoding, zero per-token cost
```

## 3. Training

**Pilot (Qwen3.5-0.8B, village, 16 GB).** Same data, 418 steps, schedule and seeds as A and B; LoRA and refiner train jointly; loss = answer CE at the sampled L + 0.01·‖Δ‖² (LRT). Overhead: (L+1) 16-token passes on a 2k context, ~7% of MLP FLOPs at L=8; memory is dominated by the arm-A context pass, which already fits. Required controls, all at the same steps: **P** = 16 slots, 0 laps (prompt tuning, the pause control); **A32** = LoRA r32 (parameter-matched); **S** = STS with slots swapped from another question at evaluation; **F** = STS with no LoRA (frozen backbone, diagnostic only).

**LFM2.5 (A100 rental, frozen 4-bit or bf16 base).**
- Stage 1 (ALAR + INTACT): thinking-ON rollouts on retail-style tasks disjoint from the 40 eval tasks, plus the 1,792 chats re-answered by the teacher; keep successes only. Student sees `<think>[slots]</think>`. Losses: per-token KL, teacher reply distribution (given its thought) to student; CODI L1 on hidden states at the first reply position at the tap layers, teacher stop-grad, last thought sentence cut (CODI: −19 without the term, −12 with leakage [shown]); CE on gold tool-call tokens.
- Stage 2: JOLT+ GRPO on reply tokens; exploration from text sampling plus Gaussian noise on Δ (Latent-GRPO); reverse-KL anchor to the stage-1 policy (INTACT collapsed without one, 42.9 vs 78.8 [shown]).

## 4. Speed (Mac M1 Pro, 4-bit LFM2.5)

- **Decode.** Per-token path unchanged; 16 cached positions per generation (320 after 20 turns vs ~10k context, <1% of attention reads). Steady decode with 2 agents **≈35 tok/s per agent** [suggested].
- **One lap** = a 16-token pass. Uniform routing touches 1 − (60/64)^16 = 0.64 of experts: 41 × 9.44M × 38 layers = 14.8B params ≈ 8.3 GB at ~4.5 bits, +0.6 GB dense; at ~170 GB/s ≈ 52 ms. Measured prefill gives 16/420 = 38 ms. Take **~50 ms/lap** (correlated routing is cheaper). Refiner ~60 MB ≈ 0.4 ms.
- **TTFT.** L=8 = 9 passes ≈ 0.45 s (1 agent), ~0.7 s (2 agents) per generation; thinking-ON writes 200-500 tokens ≈ 6-14 s.
- **Time-averaged decode.** A ~0.7 s burst every ~3-4 s halves the other agent's speed meanwhile: ≈32-33 tok/s average, above 30 [suggested]. K=8 cuts the burst to ~60% (0.40 of experts).

## 5. Why laps should matter

One pass caps sequential retrieval rounds over the context at depth (6 attention layers in Qwen). A k-hop village question needs k dependent lookups (person → visit → item → rule). Each STS lap is a full backbone pass whose slot queries attend over the whole log, conditioned on the previous lap's writes, so retrieval depth grows with L; arm B instead re-applies 4 layers to their own output. This targets the measured weak axis (deeper stories −8 in stage-1 probes [shown]). tau2 analogue: user → order → item → policy check before the call.

**Prediction [untested].** Validation lap 8 − lap 1 ≈ **+2.5** (+5 on 3+-hop, ~0 on 1-hop); STS@8 ≈ **+3.0** over B (67.1), P(PASS) ≈ 0.4; flat 8→16, no collapse (bounded update, 12 inside training range, no self-fed layers). tau2: 23 → ~26/40.

## 6. Top 3 failure modes and the cheapest test for each

1. **Backbone ignores slots, or slots collapse to a constant** (SoftCoT/EBM-CoT collapse; frozen bases capped at 22-24 vs 38.5 in Coda-Forno [shown]). Pre-training test (~10 min, PC): answer-logit KL under 16 random/perturbed slot embeddings. At 100 steps: answer→slot attention mass, swap control S, slot cosine. Kill if S is within 1 point of STS.
2. **Laps saturate by lap 2** (v1 fixed point in ~3 loops [shown, from-scratch model]; ≤0.01 nats past lap 4 in Closing the Loop [shown]). Test: 1 seed, 150 steps, 2k deep-question rows; kill if lap4 − lap1 < 1 point on 3+-hop or ‖Δ₃‖/‖Δ₁‖ < 0.1.
3. **Budget too small** (Newt: "budget, not architecture"; LRT used 30 epochs/task [shown]). Test: 1 seed at 418 vs 1,254 steps, A also at 1,254; if STS − A grows, budget is the bottleneck.

LFM risk: own-trace distillation fails on verbose traces (Tale of Two Regimes [shown]). Free test: thinking-ON tokens/turn in the 30/40 transcripts; median >400 → ALAR action-CE only.

## 7. Claims by label

Shown: Loop-1L, stage-1 and v1 numbers (v1 = separate from-scratch village model, used only as a prior); HF code facts; cited paper numbers. Suggested: lap cost, Mac speed, TTFT, expert coverage, hop-depth argument, cross-turn carry. Untested: STS, the shim, the mlx patch, all section-5 predictions.

## 8. Self-score (higher = better)

- Gain 6: best frozen-backbone evidence (LRT, INTACT, DCA, ALAR), none on multi-turn tools.
- Speed 9: zero per-token cost; ~0.5-0.7 s per turn.
- Trainability 6: native-attention gradient, zero-init = pause baseline; but BPTT through 6 full passes, small budget.
- Decoration risk 7: laps act via the backbone's own retrieval; swap/pause/hop/Δ-norm tests expose decoration in 150 steps.
