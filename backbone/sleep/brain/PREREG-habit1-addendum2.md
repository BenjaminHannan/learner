# Habit-1 addendum 2: a 3-bit-base arm in stage 2 (written 2026-10-27 ~06:20Z, before any stage-2 run)

Labels: shown / suggested / untested. Stage 2 only.

## Why
Ben (2026-10-27 06:11Z) asked whether the 3-bit Qwen3.6 can still sleep and train. Ben's M1 assistant now runs NexVeridian/Qwen3.6-35B-A3B-3bit.
Its config was checked on the Hub on 2026-10-27: affine, 3 bits, group 64, with 8 bits on the 80 router `mlp.gate` and `mlp.shared_expert_gate`
modules. This is the mlx-community 4-bit recipe with 3 bits in place of 4.

## Arms (both: ab_ob_b4_nb, Week-2, seed 1, work scale 4, `--habit spot`, parser as addendum 1)
- **q36_hab:** `--q4-base --q4-mlx-moe` (4 bits; the deployed-until-now recipe).
- **q36_hab3:** the same plus `--q4-bits 3` (the NexVeridian recipe: `q4_apply` puts the routed experts and every Linear at 3 bits, and the gates at 8 bits).
Runner: the speed thread's packed base with checkpointing (speed/qwen36_mem/run_sleepb_packed.py), 32 GB 5090, if it supports 3 bits;
otherwise the plain loader on a larger card.

## Pass marks (fixed now)
- **H1 (4-bit, as PREREG-habit1):** routine >= 75 and exact McNemar p < 0.05 against addendum 12's q36_q4 (routine 30).
- **Q3 (3-bit sleeps about as well):** q36_hab3 recall C2+C4 >= 75 AND >= q36_hab's recall - 5; no-harm marks as addendum 12
  (ARC-Easy >= its own pre-sleep - 5, diary >= its own base_diary - 5).
  **Wrong if** q36_hab3 recall < q36_hab - 10 (paired McNemar p < 0.05). Then 3 bits costs memory, and the deployed assistant should
  sleep on a 4-bit (or bf16-master) copy.
- Reported: routine, two-hop, reverse and changed-new for both; pre-sleep ARC-Easy for 3-bit against 4-bit (the cost of 3 bits before any sleep).
- If money allows only one arm, q36_hab3 runs first. It answers Ben's question, and its routine score also tests H1 at 3 bits (reported, not marked).

## Not covered
The MLX path on the Mac (true 3-bit kernels, not our PyTorch quantize-dequantize copy) is not tested here. A short Mac MLX run (a few nights,
small LoRA) can be added as a first look, but it is not this addendum's test.
