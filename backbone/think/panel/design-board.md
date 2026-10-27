# D2 (board-centric): "Slot Laps": a thinking board that lives in the sequence

Labels: **[S]** shown (measured here or in a cited paper), **[Sg]** suggested, **[U]** untested.

## 1. Summary
The board is K=16 extra positions placed where thinking would go: after the question (village) or between `<think>` and `</think>` (LFM2.5). Once per assistant turn, before the first answer token, only these 16 positions are re-run R times through a middle band of the real backbone layers. On each lap they read the clean prompt cache and each other, using a "think" LoRA that is active only on slot positions. Each update is damped and held at a fixed norm. The final board then goes up the upper stack like ordinary tokens and stays in the KV cache. Every later token and every later turn reads it through the frozen model's own attention.

Text never enters the loop, so decode cost is about zero, and the Loop-1L failure (re-running MoE layers on all positions took start loss from 0.72 to 2.56 [S]) cannot hit text.

## 2. Mechanism
- **Band [a,b).** Qwen3.5-0.8B uses layers 8–11 (DeltaNet 8–10, full attention 11). Same band as stage-1 arm B, so the only difference from B is looping the slots instead of every position. LFM2.5 uses layers 16–23 (attention at 18 and 22, six conv layers, all MoE), the same band as Loop-1L B.
- **Init (instance-dependent).** The slot embeddings start as the embeddings of 16 ordinary tokens. They pass once through layers [0,a), reading the prompt and any earlier boards, which gives Z0. Across turns, Z0 also gets a zero-init per-channel carry: Z0 += tanh(g)⊙Z_R(previous turn).
- **Lap.**
  - Restore the band's prompt snapshot: KV cropped to the prompt, plus cloned DeltaNet/conv states (HF updates these in place with `copy_`; checked in `cache_utils.py`, 5.20.2).
  - Run Z through the band with the think adapter. Full-attention layers get a hand-built 4-D mask (slots see the prompt and all slots); SDPA uses it as given. DeltaNet/conv run causally over the slots.
  - Update Z ← Z + α⊙(Y−Z) and rescale each slot to rms(Z0). α is per channel, starts at 0.5, has its own learning rate (R1). The prompt cache is the re-injection.
- **Readout.** The final Z passes through [b,L) and is cached. Answer tokens read it through three routes:
  - the upper attention layers (Qwen 15/19/23; LFM 26/30/34/38),
  - the band's final-lap KV,
  - the DeltaNet recurrent state.

  The board comes out of real layers via a zero-init LoRA, so it stays near normal hidden states [Sg].
- **Persistence.** Old boards stay in the cache. A new board reads them during init, during every lap's attention, and through the carry. After "User not found", the next board sees the error and its old plan.
- **Laps.** Laps run once per assistant turn, at the 16 slots only. In training, R is sampled from {1,2,3,4,6,8} with probabilities {.10,.10,.15,.20,.20,.25}. Evaluation uses 1/2/4/8/12. There is no learned halt: R is fixed with a cap of 12 (R1, R3; v1's halt gave no held-out gain [S]).
- **Parameters** (r16, computed):
  - Qwen think-LoRA on all band projections and MLPs: 3×467,456 + 401,408 = **1.80M**; slots and α add 0.02M. All arms share arm A's task LoRA (10.82M).
  - LFM think-LoRA on attention q/k/v/out (2 layers) and conv in/out (6 layers): 2×212,992 + 6×196,608 = 1.61M. Slots, α, carry and a per-lap router bias (8×64) add 0.04M, for **≈1.65M** in total. Experts and the router stay frozen.

```python
def turn(cache, new_ids, R, prev_z=None, ans=None):          # cache holds earlier text AND earlier boards
    run(embed(new_ids), layers[0:L], cache)                    # ordinary pass; text never sees "think"
    pos = arange(cache.len(), cache.len() + K)
    z = run(slot_emb, layers[0:a], cache, pos)                 # instance-dependent init, cached in [0,a)
    if prev_z is not None: z = z + tanh(g) * prev_z            # zero-init cross-turn carry
    s = rms(z); snap = cache.snapshot(layers[a:b])             # band prompt state (KV len, conv/delta states)
    if ans is not None: ha = run(embed(ans), layers[0:a], fork(cache))   # teacher-forced, lap-independent
    ce = []
    for r in range(R):
        cache.restore(snap, layers[a:b])
        y = run(z, layers[a:b], cache, pos, adapter="think", mask=SLOTS_SEE_PROMPT_AND_SLOTS)
        z = z + alpha * (y - z); z = z * s / rms(z)            # damped, norm-held
        if ans is not None:                                    # cheap: (K+|ans|) tokens x (L-a) layers
            c = fork(cache); run(z, layers[b:L], c, pos)
            ce.append(CE(run(ha, layers[a:L], c), ans))
    run(z, layers[b:L], cache, pos)                            # board enters upper stack, stays cached
    return ce, z                                               # z becomes prev_z next turn

loss = ce[-1] + 0.1 * sum(relu(ce[r+1] - ce[r].detach()) for r in range(R - 1))
```
Training needs a small `BoardCache` (about 60 lines) whose state updates assign new tensors instead of calling `copy_`; otherwise autograd breaks [Sg, from reading the code]. The detached hinge only pushes later laps to improve; it cannot reward a weak lap 1 (a faked rising curve).

## 3. Training
**Pilot (Qwen3.5-0.8B, village).** The base is frozen. The trained parts are the task LoRA (as in arm A), the think-LoRA, the slots and α. The run uses the stage-1 data order, 418 steps and batch 16, with a learning rate of 2e-4 for LoRA and 1e-3 for the board. Prompts are left-padded so the slots follow each prompt directly. The loss is the CE at the final lap plus the hinge.

There are four arms with 3 seeds each: A, B, Slot Laps, and **C1 = Slot Laps trained at R=1 only**. C1 has the same parameters and positions but no recurrence, so it controls for "pause tokens". Expect about 1.1–1.2× arm A's step cost and similar memory, within 16 GB [Sg].

**LFM2.5.**
1. Warm-start on the 1,792 Claude chats, with the slots inside `<think></think>`.
2. Distil from LFM2.5's own thinking-ON rollouts, collected on the Mac with mlx: about 4M tokens in about 13 h at 4×21 tok/s, at no cost. Keep only successful turns (ALAR). The loss is CE on the reply and tool-call tokens, plus reverse-KL to the teacher's reply distribution, plus L1 matching the student's hidden state at `</think>` to the teacher's on layers 24–39 (CODI/KaVa).
3. RL with JOLT+ (reward 0.6·checks + 0.4·grade). The board gets gradient only through the log-probs of sampled tokens. R stays fixed, so the lap count cannot be gamed, and a KL anchor to the distilled student guards against drift (INTACT).

## 4. Mac speed (4-bit, 2 agents)
- **Decode.** Text runs the unchanged model with the task LoRA merged in. The only extra cost is attention over the board positions:
  - KV per board position: 10 layers × 8 heads × 64 × 2 × 2 B = 20 KB.
  - A 20-turn chat holds 320 board positions, about 6.4 MB per token, against about 1.3 GB of weights read per token: **about 0.5%**.
  - Predicted **35.2 tok/s per agent**, against the measured 35.4 [S] [Sg].
- **Burst per turn.** With uniform routing, 16 tokens touch about 64·(1−(60/64)^16) ≈ 41 of 64 experts per layer:
  - One 40-layer pass then reads about 9 GB, about 60 ms at about 150 GB/s.
  - Each extra 8-layer lap adds about 12 ms.
  - **R=8: about 145 ms. R=4: about 96 ms.** With 2 agents sharing bandwidth, expect about 220 and 150 ms of added time to first token [Sg]. Thinking-ON's 100–500 tokens per turn cost 3–14 s.
- **Amortised throughput.** 145 ms is about 8 tokens' worth of decode, so over a 60-token turn the rate is about 31.3 tok/s (R=8) or 32.5 (R=4). Both stay at or above 30 [Sg].

## 5. Why laps matter
Village questions chain dependent lookups. For example, "Where was the ball before Sali went to the mill?" needs four steps in order:
1. Find when Sali went to the mill.
2. Find the ball's last move before that.
3. Notice that the ball was in the box.
4. Find where the box was.

Each query depends on the previous answer, and the context was encoded before the question arrived, so every hop must fit in the layers after the question. Depth is arm A's worst probe axis (−8 [S]), and 39.5% of validation questions have depth ≥3 (computed from `validation.jsonl`).

Each lap adds one question-directed full-attention read (layer 11) plus 3 DeltaNet layers, so roughly one hop per lap [Sg]. B cannot do this: its laps rewrite the whole context instead of following a chain. In tau2 the analogue is plan-then-check and cross-turn state.

**Predictions [U]:**
- Score at 8 laps minus 1 lap: **+3.0** overall, about +6 at depth ≥3, about 0 at depth ≤1.
- Against the best of A and B: **+1.8** (about 68.9).
- Chance of clearing the +3 bar at 418 steps: about 25%.

## 6. Three failure modes, and the cheapest test of each
1. **The model treats the slots as pause tokens.** Test: at eval, swap in the board from another question, and separately use a mean board. A drop of under 2 points means the board's content is ignored (INTACT's swap cost 8 [S]).
2. **The board reaches a fixed point by lap 2–3**, as in v1 [S]. Test: a free lap sweep plus the per-lap change ‖Z_r−Z_{r−1}‖/‖Z0‖. If that ratio falls below 0.05 by lap 3, the later laps are decoration.
3. **The training signal is too weak.** The pilot has about 7M tokens with answer-only loss, and Coconut trained that way stayed at the no-CoT level [S]. Test: one seed each of A and Slot Laps at 2× steps. If the gap widens, the method is starved for data rather than wrong.
4. **(LFM)** The 7-task tau2 gap (p≈0.10 [S]) may be grounding, not depth. Test: score by failure type on all retail tasks.

## 7. Pass marks (fixed in advance; pilot, 3 seeds, validation)
- **PASS** requires all of:
  - Slot Laps at R=8 scores ≥ 70.12 (B + 3).
  - R8−R1 ≥ 2, with R2 ≥ R1, R4 ≥ R2 and R12 ≥ R8−1.
  - Slot Laps beats C1 by ≥ 2.
  - The swap control costs ≥ 5 points.
- **Wrong** if any of these: Slot Laps scores < 69, R8−R1 < 1, or the swap costs < 2.
- Logged: slot attention mass at layers 15/19/23; results by depth.
- v1 (premonition's own village model) motivated the risks only; none of its numbers enters a pilot prediction.

## 8. Self-scores
- **Gain 5:** it targets the measured depth weakness, but frozen-backbone evidence is +1 to +5 (INTACT), and B gave +0.4.
- **Speed 9:** decode is untouched (about 0.5%), and the burst is about 0.1–0.3 s per turn.
- **Trainability 7:** zero-init LoRA on real layers, text never enters the loop, and the norm is held. Risks: custom cache, weak answer-only gradient.
- **Decoration risk 7 (higher = safer):** the C1 arm, the swap test, the per-lap Δ and the detached hinge all make decoration measurable. A fixed point is still plausible.
