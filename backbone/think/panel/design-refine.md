# D4: Draft-Check-Revise board (DCR)

Labels: [S] shown (measured, or read in code), [Sg] suggested, [U] untested. Village pilot and LFM2.5/tau2 are kept separate throughout.

## 1. Summary
Once per answer (village) or per assistant turn (tau2), the frozen backbone runs N laps over K board positions placed after the prompt. Each lap, the frozen LM head decodes the draft slots into a draft answer (or the first 24 tokens of the next reply or tool call). Three checks grade it: (a) zero-parameter checks (confidence, entropy, margin, change since the last lap); (b) an agreement check that comes free from a Jacobi shift (draft slot j is fed lap k-1's draft token j-1, so lap k scores how strongly the backbone endorses the old draft, token by token); (c) a learned verifier trained with BCE on whether each draft token, and the whole draft, is correct. A small refiner reads the board states plus these checks and writes the next board; the verifier sets the step size, so a draft judged right stops moving. The answer is then decoded normally, attending to the final board; no laps run during decoding.

## 2. Mechanism
- **Board.** Pilot: K = 8 scratch + 16 draft slots (village answers are p50 3, p90 13, p99 25 tokens, measured on all 8,675 validation rows [S]); input x is 24x1024 and refiner latent b is 24x512. LFM: 8 scratch + 24 draft slots, x 32x2048, b 32x1024.
- **Where.** The board enters as `inputs_embeds` at positions T..T+K-1 and passes through all layers. Read taps (parameter-free RMSNorm of the residual stream at board positions): Qwen3.5 layers 7, 15, 23 (the ends of full-attention groups); LFM2.5 layers 14, 26, 39.
- **State reset.** Every lap restarts from the post-prompt cache (laps replace, not chain). HF 5.20.2 maps `conv` and `linear_attention` layers to `LinearAttentionLayer`, whose state updates use in-place `copy_` [S, read in cache_utils.py], which would break autograd across laps. Fix: a 20-line subclass that assigns instead, plus a shallow clone of the cache per lap (full-attention K/V already grow by `torch.cat`). Multi-token lap chunks take the `torch_chunk_gated_delta_rule(initial_state=cached)` path (GatedDeltaNet) and the cat-then-conv path (LFM ShortConv) [S, read]; the in-place single-token kernels run only in no-grad decoding. `Runner.hidden`/`LoopLM.hidden` need an `embeds=` argument. Smoke test: lap-cache output matches a no-cache forward to 1e-4.
- **Init.** `W_o` is zero-init, so at step 0 a lap is pure Jacobi drafting over learned slot embeddings. The step scale alpha starts at 0.1 per channel, in its own group at 3x LR, logged every 50 steps.
- **Laps in training.** P(N=1) = 0.1, otherwise N is uniform on 2..10. Backprop runs through every lap; with K = 24, lap compute is about 20% of the prompt pass.
- **Halting.** Fixed N at test, swept over 1/2/4/8/12. The verifier gate damps the steps but does not stop the loop.
- **Parameters** (computed): the pilot block is 8.73M (refiner 6.30M, taps 1.57M, W_o 0.52M), plus the same r16 LoRA as arm A (10.82M), for 19.5M trainable. The LFM block is 34.8M (2-layer refiner at d = 1024: 25.2M; taps 6.3M), plus arm A's LoRA.

```
def dcr(prompt, N, gold=None):
  C0 = backbone.prefill(prompt, cache=FunctionalCache())     # frozen + LoRA, once
  b, prev, loss = b0, None, 0.0
  for k in range(1, N + 1):
    x = slot_emb + W_o(b)                                     # W_o zero-init
    x[:, Ks] += start_emb
    if prev is not None:                                      # Jacobi shift
      x[:, Ks+1:] += soft_embed(prev[:, :-1])                 # top-4 renormed tied-embedding mix, norm-matched
    C = C0.shallow_clone()                                    # every lap restarts from the prompt state
    H = backbone.forward_embeds(x, pos=T + arange(K), cache=C, taps=TAPS)
    logit = lm_head(final_norm(H[-1][:, Ks:]))                # draft read by the frozen head
    p = logit.softmax(-1)
    chk = cat([p.max(-1), entropy(p), margin(logit),
               logp_of(p, argmax(prev)) if prev is not None else 0,  # does lap k endorse lap k-1?
               kl(p, prev) if prev is not None else 0], -1)
    r = Refiner(b + P_r(rms(H[TAPS])) + P_c(pad(chk)))        # 2-layer self-attn over K slots
    v_tok, v_seq = sigmoid(V_t(r[:, Ks:])), sigmoid(V_s(r.mean(1)))
    if gold is not None:
      ok = argmax(logit) == gold
      loss += 0.3*(k/N)*CE(logit, gold) + 0.1*(BCE(v_tok, ok) + BCE(v_seq, ok.all(-1)))
    if k < N:
      b = b + alpha * (1 - v_seq.detach()) * tanh(W_r(r))    # the check sets the step
    prev = p
  return C   # answer: CE on gold (training) or greedy AR decode from C at positions T+K...
```

**Draft corruption (the "check curriculum").** In 30% of examples, lap 1's `prev` is a corrupted gold answer: one or two tokens swapped for a name, place or object from the same log (tau2: a wrong order or item ID from the context). This balances the verifier's labels and trains repair of the commonest errors: wrong entity (village), wrong ID or argument (tau2, about half of tau-bench failures [Sg, R4]).

## 3. Training
- **Pilot task: village.** Short gold answers give exact per-token draft labels for the verifier; rows carry depth labels; and n = 8,675 gives an SE of ~0.5 points. Assistant chats (M_tool on 322 turns, SE ~2.7) would put a 3-point bar at about 1 SE, and the 0.8B is near the floor there.
- **Pilot (village; backbone frozen, LoRA + block train).** Loss = answer CE after lap N + draft CE per lap (weight 0.3·k/N; v1's last-lap loss gave the larger lap gain [S]) + verifier BCE + 0.01·||Δb||². Stage 1's 418 steps × batch 16, left-padded prompts (DeltaNet state stays zero over left pads [Sg]). LR: LoRA 2e-4, block 1e-3, gates 3e-3. Fits 16 GB: the 248k-vocab draft logits (16 slots × 10 laps) are about 2 GB at micro-batch 4 with head checkpointing [Sg]. Add a compute-matched arm A at 1.3× steps.
- **LFM2.5.** Teacher = the same frozen LFM2.5, thinking ON, on the 1,792 chats with gold history; keep turns whose teacher tool call matches gold (ALAR-style [S, BFCL]). Loss = top-32 KL to the teacher's reply tokens (think text never shown) + gold CE + draft CE on the teacher's first 24 reply tokens + verifier BCE. Then JOLT+ GRPO at N = 8, with a per-rollout refiner dropout mask for variance (Dropout-GRPO [S]), a KL anchor to the distilled policy (INTACT collapsed without one [S]), and verifier BCE on rollout success. Boards never enter the history: at turn end, roll back to the pre-board cache (KV trim + conv-state copy) and re-prefill the reply with the next message, so training and inference match.

## 4. Mac speed (LFM2.5 4-bit, ~0.5625 bytes/param)
- **Decode:** 2.53B params (1.43 GB) read per token in 18 ms, so ~79 GB/s effective [Sg]. No laps in decode; 32 extra KV positions in 10 layers, for the current turn only (<0.5%). Two agents: ~35 tok/s each in decode windows, ~32 time-averaged because one agent's laps steal bandwidth from the other [Sg]. Both clear 30.
- **One lap** (32 tokens): uniform routing touches 64·(1-(60/64)^32) = 55.9 experts/layer, i.e. 38 × 55.9 × 9.44M + 1.1B = 21.1B params = 11.9 GB, which is 100-150 ms at 80-120 GB/s. Compute: 157 GFLOP, ~40 ms, overlapped.
- **TTFT** at N = 8: +0.8-1.2 s per turn (up to ~1.8 s with two agents contending), +0.1 s reply re-prefill. Thinking ON spends seconds of tokens per turn. Knobs: K = 16 (8.9 GB/lap, -25%), N = 4 (-50%). All [Sg]; measure on the Mac.

## 5. Why laps should matter
Deeper stories cost about 8 points, the worst probe axis [S]: one pass must compose every hop inside 24 layers. DCR makes the intermediate guess explicit, as tokens the 6 full-attention layers can use as queries next lap; the checks flag a wrong entity and the corruption curriculum trains its repair. Jacobi iteration has a fixed point, so laps past convergence leave the draft unchanged instead of drifting, which should prevent collapse at 12 [Sg] (arm B: 40.7 → 29.6 [S]). Predictions on validation: lap 1 ≈ 66.0 (a blank board), lap 8 ≈ 69.5, so **lap 8 - lap 1 ≈ +3.5**. Lap 12 should land within 0.5 of lap 8. The gain should concentrate at depth ≥ 3 (39% of rows). Against the best baseline (B, 67.1) I predict **+2.5**, so a ≥ 3 pass is about 35% likely. Village SE is about 0.5 points at n = 8,675. On tau2: 23 → 26-27 out of 40 [U], inside the noise for n = 40.

## 6. Failure modes and the cheapest test of each
1. **The draft settles at lap 1-2; later laps are decoration.** After 100 steps, count per-lap wrong→right and right→wrong flips on 1,000 dev rows. Fail if wrong→right at laps 3-8 is under 1% of rows, or if draft exact-match at lap 8 minus lap 1 is under 1 point.
2. **The check adds nothing** (the verifier just reproduces p_max; the refiner ignores the checks). At test time, set `chk` to its training mean and the gate to 1. Fail if 8-lap accuracy drops by under 1.0 point, or if verifier AUROC is within 0.02 of the p_max product.
3. **The extra positions or soft inputs knock the frozen model off its function** (arm B's loss started at 2.56 vs 0.72 [S]; LFM router drift [U]). At step 0, with no training, compare answer CE with an untrained board vs no board on 200 village rows (PC) and on 50 LFM chats (one A100 hour). Fail if the board adds more than 0.10 nats, or is not at arm A's loss by step 100.
Plus a swap test (final board taken from another question): a drop under 5 points means the backbone is not reading the board.

## 7. Claims ledger
[S]: the layer, cache and kernel facts in section 2 (from reading HF 5.20.2 code); the answer-length and depth counts; all quoted project numbers. [Sg]: the speed arithmetic, the memory fit, and the lap mechanism. [U]: all pilot and tau2 predictions, router behaviour on soft inputs, and transfer from village to tool calls.

## 8. Self-scores (10 = best on the axis)
- **Gain 5:** it targets the measured depth weakness, but frozen-backbone latent methods usually give +1 to +5 [S, R2/R4].
- **Speed 8:** per-token decode is untouched; the cost is ~1 s of TTFT per turn.
- **Trainability 7:** the init is exact Jacobi, every lap is supervised, BPTT is cheap, and it fits 16 GB; the cache needs a subclass.
- **Decoration risk 7:** per-lap draft accuracy, flips, the check ablation and the swap test measure it directly, and the corruption curriculum forces later laps to repair.
