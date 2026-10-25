# Swap-1 results (in progress, 2026-10-25)

Labels: shown = measured here; suggested = vendor or third-party claim.

## Store test, GPU (vLLM 0.32 bf16 on an RTX 5090, tau2 retail tasks 0-39 x 2 trials, Haiku 5.5 as customer and judge), shown
| arm | DB match /80 | reward pass /80 | agent tokens/sim | s/sim | ended by errors |
|---|---|---|---|---|---|
| K2-Horizon-3.7B, thinking off | 56 | 51 | 2025 | 41 | 0 |
| K2-Horizon-7B, thinking off | 55 | 49 | 1832 | 46 | 0 |
| K2-Horizon-7B, reasoning_effort low | 50 | 44 | 1881 | 55 | 0 |
| K2-Horizon-3.7B, reasoning_effort low | 46 | 40 | 2094 | 45 | 1 |
The LFM2.5-8B-A1B control didn't start on vLLM 0.32 ("Layer 0 (conv) does not dispatch through the Transformers attention interface"),
so the pre-registered same-stack control is missing. The Qwen3.5-4B/9B arms failed after it (GPU memory not freed; serve() fixed since).
Earlier Mac runs of LFM2.5-8B scored 14/40 (bf16), 19/40 (q4) and 23/40 (q8), each 1 trial, on mlx_lm.
P1 (K2 >= LFM + 10 points) holds against every LFM run, but only across stacks, so it is suggested, not shown, until the Mac q4 run of K2-3.7B.
Short thinking (low) did not help either K2 size.

## Speed on Ben's M1 Pro, MLX 4-bit, tok/s each at 1 / 2 / 4 agents, shown
| model | 1 | 2 | 4 | TTFT 1k / 4k | peak GB |
|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | 47.1 | 30.1 | 17.4 | 2.5 / 9.6 s | 21.5 |
| K2-Horizon-3.7B | 35.9 | 30.1 | 15.9 | 3.0 / 13.0 s | 5.5 |
| K2-Horizon-7B | 23.9 | 18.4 | 10.3 | 5.4 / 22.9 s | 8.5 |
| K2-Horizon MoVA 36B-A4B | 16.8 | 13.4 | 8.8 | 4.2 / 17.5 s | 28.1 |
| LFM2.5-8B-A1B (Oct 24) | 108 | 67 | 38 | ~5 s at 4k | 4.5 |
MoVA's store test was stopped at 0/80 (OOM at 2 agents, >10 h at 1).

## Decision (Ben, 13:40Z / 13:43Z)
Big tier: Qwen3.6-35B-A3B. Small tier: K2-Horizon-3.7B. Pivot if something better ships before release.
