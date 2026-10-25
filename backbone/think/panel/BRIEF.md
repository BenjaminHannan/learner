# Design panel brief: a trained "thinking block" for premonition v2 (2026-10-24)

You are one of several independent designers. Each designer gets a different ANGLE (given in your prompt).
Read this brief, read the research notes listed at the end, then propose ONE block design from your angle.
Do not edit any repo files, run training, or use a GPU. You may read files and search the web.

## The goal
premonition v2 = a FROZEN borrowed backbone with its written chain of thought switched OFF. It should think
silently by LOOPING a small trained block in latent space and updating a "thinking board" (latent scratch slots),
never by writing words. Target task: tau2-bench retail (multi-turn customer-service agent with tools: look up user,
order, product; follow store policy; modify/cancel/return orders; ask to confirm). Real-jobs score on 40 tasks:
- LFM2.5-24B-A2B thinking OFF: 23/40 (9 tasks aborted with too_many_errors: it repeated a failing call such as
  "User not found" 10 times).
- LFM2.5-24B-A2B thinking ON (writes <think>...</think> at the start of each assistant turn): 30/40.
- Claude Haiku 5.5: 29/40.
Goal: close the 23 -> 30 gap with silent latent thinking.

## The two models
Target backbone: LiquidAI/LFM2.5-24B-A2B (shown, HF config): 40 layers, hidden 2048, vocab 128k, tied embeddings.
Layers 2,6,10,...,38 (10 layers) are full GQA attention (32 q heads, 8 kv heads); the other 30 are short gated
convolutions (cache length 3, i.e. local mixing only). FFN: layers 0-1 dense, layers 2-39 MoE with 64 experts,
top-4, expert width 1536 (~600M params per MoE layer, ~38M active per token). ~2B active params per token.
Pilot backbone: Qwen/Qwen3.5-0.8B (shown): 24 layers, hidden 1024, 3 Gated-DeltaNet linear-attention layers per
full-attention layer (full attention at 3,7,11,15,19,23; 8 q heads, 2 kv heads, head_dim 256), dense MLP 3584,
vocab 248k, tied embeddings.

## Hardware and the speed rule
Ben's Mac M1 Pro 32 GB, mlx-lm 4-bit LFM2.5 (shown): 1 agent 54.5 tok/s; 2 agents 35.4 tok/s each; 4 agents 21.1
each. Prefill ~420 tok/s. Peak 13.7 GB. Decode is memory-bandwidth bound (~18 ms per token, mostly reading the
~2B active weights). RULE: v2 must keep >= 30 tok/s per agent with 2 agents running. That leaves only ~15%
per-token decode overhead. A block that re-runs 8 of 40 layers 4 times at EVERY token (+24 layers) would cut
decode to ~0.6x and fail the rule. Thinking that happens once per assistant turn (a burst of laps before the
first token) costs latency, not per-token speed: one lap of a single copied LFM2.5 layer over a few dozen latent
slots is roughly a few ms on the Mac (suggested estimate).
Training hardware: Ben's PC (RTX 5070 Ti 16 GB, free) and Vast rentals (~$0.3-1/h; this week's remaining credit
is only a few dollars). Pilot runs must fit 16 GB with Qwen3.5-0.8B + LoRA.

## What this project has already measured (all shown unless marked)
1. Stage 1, Qwen3.5-0.8B on the "village" task (multi-hop QA over a long text log of village visits; held-out
   validation split of 8,675 questions with new names/templates/styles/rule families; ~2k-token prompts; short
   answers; 418 training steps, LoRA r16 on all layers, answer-only loss). Three seeds:
   - A (LoRA, no loop): validation 67.78 / 66.06 / 66.32, mean 66.72. Dev mean 80.68.
   - B (A + the borrowed middle block, layers 8-11 of 24, re-run 3 times with shared weights and the same
     LoRA, at every position): validation 67.57 / 66.33 / 67.45, mean 67.12 (+0.40 vs A, inside seed spread
     ~1.2). Dev +1.57 (all seeds positive).
   - B scored with 1 pass (lesion): validation 59.43 (-7.7): the trained model relies on the loop, but the loop
     buys no generalisation.
   - Probes (arm A): new wording costs 6 points; new names ~1; new rules ~2; DEEPER stories (more hops) ~8.
     Depth is the weakest axis.
2. v1 (premonition's own from-scratch village model, ~2M params) has a 2-layer "Think" block looped up to 8
   times over a 76-row x 128 state with 4 registers; register 0 drives ASK (notebook lookup) and HALT.
   - It used ~2.3 of 8 loops (learned halt). Forcing 8 loops at test time raised dev in 23/23 runs (+8.2) and
     validation in 17/23 (+1.7).
   - A learned halt made it think longer without gains on held-out questions.
   - State change per loop falls fast (registers ~6.7x their size in loop 1, 1.8 in loop 2, 0.14 by loop 8):
     the loop converges to a fixed point within ~3 loops.
   - The decoder ignored 4 registers (zeroing them: no change). With 16 registers, zeroing cost 5.4 (one run).
   - "lastloss" (answer loss only at the final loop, no per-loop deep supervision): validation gain from 2 to 8
     loops +13.0 vs +7.9 for base; endpoint not significantly better (47.5 vs 44.7, p~0.16).
   - Input injection (re-adding the original rows each loop): no effect.
   - Seed/GPU noise is large on that small model (same seed on two GPUs: 46.0 vs 51.4).
3. Loop-1L (running now, LFM2.5-24B-A2B, 1,792 Claude-written tool-use chats, metric M_tool = exact tool-call
   match per assistant turn on 100 held-out chats): arms A LoRA no loop / B layers 16-23 re-run, random 1-8
   passes in training (weighted to more) / C = B + a per-position d=256 latent board (h += W_in z at block
   input, z += sigmoid gate * tanh(W_up h) after each pass). Tested at 1/4/8/12 passes. First number: A seed 0
   M_tool 48.8%. Seed 0 so far (shown, box log 13:25Z; 56 optimizer steps only): A 48.8% (322 turns);
   B at 8 passes 40.1% (322 turns), B at 1 pass 41.4% and at 4 passes 43.8% (162-turn subset). B's training
   loss STARTED at 2.56 vs 0.72 for A: re-running 8 MoE layers knocks the frozen model far off its pretrained
   function, and 56 steps did not recover it. Decode on the A100: A 74 tok/s, B at 8 passes 27.8 tok/s,
   B at 4 passes 41 tok/s. Update 13:55Z: B at 12 passes (beyond the 1-8 training range) 29.6% (162-turn
   subset; B at 8 on the same subset 40.7): the re-run loop COLLAPSES past its trained range. B's pass curve on the
   subset: 1 -> 41.4, 4 -> 43.8, 8 -> 40.7, 12 -> 29.6. C (board) still running.
4. A separate "tricks" review ranked "naive looping, latent reasoning" and "retrofitted recurrence (0-1.5 pts
   and slower decode)" as do-not-build for this hardware (suggested, literature). Your design must beat that
   prior, not ignore it.
5. RL infrastructure exists: rlaif/ (GRPO vs JOLT+, Sonnet 5.5 grades transcripts 0-10, sandboxed tools,
   reward 0.6*checks + 0.4*grade). JOLT+ = one set of weights as student and as a teacher that sees privileged
   hints (reference solution + critique); student gets reverse-KL distillation toward the teacher plus GRPO.

## The starting recipe (beat it if you can)
A copy of a middle backbone block + cross-attention read/write to the board, a zero-init output gate, random lap
counts, a halt signal, backbone frozen; distill from the backbone's own thinking-ON answers; then RL with a
Sonnet 5.5 reward via JOLT+.

## The test your design must pass (fixed by Ben)
Pilot on Qwen3.5-0.8B first, 3+ seeds per arm. Arms: no loop (A) / re-run middle (B) / your block. PASS = your
block beats BOTH A and B by >= 3 points on the held-out metric AND the score rises with lap count (e.g. at
1/2/4/8 laps, and does not collapse at 12). Then a scale-up to LFM2.5-24B-A2B and tau2 retail on the Mac.
Note: on the pilot there is no "thinking-ON teacher" worth distilling from (0.8B), so the pilot's training signal
is the gold answer (village) or the Claude-written gold tool calls (assistant chats). Say which pilot task your
design suits and why.

## Scoring axes (the judge will score every design on these)
1. Expected gain (pilot and tau2), with evidence.
2. Mac speed cost: decode tok/s with 2 agents (must stay >= 30) and added time-to-first-token per turn.
3. Trainability from a frozen backbone (gradient path, init, stability, data needed, fits 16 GB at 0.8B).
4. Risk that the loops are decoration (the block does all its work in lap 1, or the backbone ignores the board),
   and how your design makes that measurable and unlikely.

## What to deliver (write to the file named in your prompt, 900-1,600 words)
1. Name and one-paragraph summary.
2. Exact mechanism: where the block attaches (layer indices for both models), what it reads, what it writes,
   board shape (K slots x d), how the backbone reads the board, when laps run (every token? once per turn?
   at which positions?), init (copied weights? zero-init gates?), lap sampling in training, halting (if any).
   Parameter count at 0.8B and at LFM2.5 scale. Pseudocode for one forward pass (< 40 lines).
3. Training recipe for the pilot (losses, steps, what is frozen) and for LFM2.5 (distillation target, RL).
4. Speed estimate on the Mac with 2 agents (show the arithmetic) and per-turn latency.
5. Why the laps should matter: the specific computation that needs more than one lap, and the prediction
   "score at 8 laps minus 1 lap" you expect.
6. The 3 strongest reasons it could fail, and the cheapest experiment that would show each.
7. Claims labelled shown / suggested / untested.
8. Self-score 1-10 on each of the 4 axes with one line of justification each.

Research notes (read the ones relevant to your angle; they are literature sweeps done today):
backbone/think/research/R1-recurrent-depth.md
backbone/think/research/R2-latent-cot.md
backbone/think/research/R3-halting-moe.md
backbone/think/research/R4-frozen-workspace.md
Code for reference (read-only): Loop-1L block code, `git -C /home/user/learner show origin/claude/project-thread-j59yy5:backbone/loop/loop1l.py`;
stage-1 Qwen3.5 runner, backbone/train.py
