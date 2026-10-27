# Creative-2: same loop, checker bans lookup tables (pre-registration, 2026-10-24 ~01:55Z)

Not the village model, not the card experiments. Follows Creative-1 (`RESULTS-creative1.md`), which failed because
Qwen learned to "fit" the examples with lookup tables such as `lambda x: 900 if x == 29 else 49 if x == 22 else 900`.
Those pass the check but can't answer a new input. Sleep then trained on them and made the habit worse.

**One change:** the checker rejects any program containing if/else, a comparison, or and/or (`--no-branch`). The rule
applies everywhere programs are judged: F0, C16, and choosing sleep data. All 300 HARD gold programs and all five C2
kinds can be written without branches; this was checked in code (300/300 HARD gold programs pass).
Everything else is identical to Creative-1: Qwen3.5-0.8B, same HARD set (seed 0), C2 dev, pool, dreams, 16 samples,
LoRA r16, 300 steps, KL guard.

## Marks (fixed now, before any run)
- K1' checking: C16 >= F0 + 10 points on HARD, and precision among answered on HARD >= 80%.
- K2 sleep: F1 (post-sleep first try) >= F0 + 10 points on HARD.
- K3 C2 dev: report F0, C16 and F1 against v1's 34.8% first try and Creative-1's F1 of 35.5% (no mark).
**Wrong if** C16 precision on HARD < 60% (banning branches doesn't stop false fits), or F1 <= F0 on HARD.
Budget: one Vast A100 run, cap $2.
