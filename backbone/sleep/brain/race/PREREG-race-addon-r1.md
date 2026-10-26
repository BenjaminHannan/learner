# PREREG sleep race, add-on side, round 1: LoRA+ (faster B matrices)

Thread "Make add-on sleep beat whole-model" (Ben 2026-10-25 21:37Z). Rules: /mnt/project-files/sleep-race/LEADERBOARD.md (frozen 21:45Z, rule 2 reworded 21:58Z).
Sealed before any run below. The CPU card test (SmolLM2-135M) and the chat-week board are separate; the card only picked the change.

## Why this change (evidence, all one seed, tiny model: suggested only)
CPU card test, SmolLM2-135M-Instruct, MLX-affine 4-bit base, 120 invented facts, 1,440 training texts, 1,200 steps, no KL guard
(scratchpad card/log_v2.txt; copied to /mnt/project-files/sleep-race/addon/card/):
- forward recall at step 400: LoRA r16 0.142, DoRA r16 0.125, LoRA r64 0.717, LoRA+ (B lr x16) 0.983; PEQA scales/offsets lr 1e-3 0.000 (diverged).
- general-text CE rise at step 400 (lower is better): LoRA +2.38, DoRA +2.41, r64 +2.01, LoRA+ +1.98.
- reverse recall at step 1200: LoRA 0.017, DoRA 0.017, LoRA+ 0.142.
Literature: LoRA+ (Hayou, Ghosh, Yu, ICML 2024) sets the B learning rate ~16x A; faster feature learning at equal steps.

## The one change
`--lora-plus 16`: every lora_B matrix trains at lr x 16 (3.2e-3), lora_A at 2e-4, same cosine per night (Trainer.step keeps the ratio).
Everything else is the a11 q4 champion: `--arm ab_ob_b4_nb --model IFM/K2-Horizon-3.7B --revision 9d280ff742235796925c9fe3cf243dc1beea5c08
--week backbone/sleep/brain/data/week2.json --tok-budget 1024 --arc-base --q4-base`, bsz 16, lr 2e-4, r16, alpha 32, KL guard, SHY, morning gate. No --schedule.
`--lora-plus 1` (default) is the old path bit for bit.

## Runs (Ben's 4090s via the GPU queue, one card each, same commit for all three)
- C2: control (no --lora-plus), seed 2. Seed-1 control = results_a11/result_k2s_q4.json (86.0).
- P1: --lora-plus 16, seed 1.
- P2: --lora-plus 16, seed 2.
Served copy = what is scored (q4 base + LoRA). The GPU type differs from a11 (5090); treat that as seed noise.

## Marks (fixed now)
Primary = recall C2+C4, weights only (200 items per seed), pooled over seeds 1+2 (400 paired items, paired.py, exact McNemar).
- R1 PASS (add-on improved): pooled LoRA+ recall >= pooled control + 4 AND p < 0.05 AND each seed's LoRA+ >= its control.
- Harm (fails the round if either seed misses): ARC-Easy 500 after >= that run's ARC base - 5; diary pooled >= 79.5 (the bf16 run's 84.5 - 5).
- WRONG (LoRA+ does not help on K2): pooled LoRA+ recall <= pooled control + 1.
- Also recorded, no mark: gate reverts per night (a reverted night with LoRA+ is reported as a likely lr-too-high sign), reverse, two-step, C1, changed new/stale, routine, wall time, peak memory.
## Race comparison
Against the whole-model round-1 champion (PEQA, branch claude/project-thread-qcuhwj), same seeds: the add-on claims the lead if pooled recall is higher with p < 0.05 and no harm fail on either side; otherwise no lead change.
