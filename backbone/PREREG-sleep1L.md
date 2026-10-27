# Sleep-1L: Sleep-1 on the real backbone, LFM2.5-24B-A2B, on Ben's Mac (pre-registration, 2026-10-24 ~03:50Z)

Not the village model, not the card experiments. Sleep-1 (`RESULTS-sleep1.md`, Qwen3.5-2B) passed M1, M2 and M4 and failed M3
(two-hop 0%). This repeats it on the model Ben chose for the assistant, `LiquidAI/LFM2.5-24B-A2B-MLX-4bit` (4-bit, QLoRA in mlx-lm),
and adds one extra arm for the two-hop failure.

Data, tests, prompts, LoRA rank 16, 300 steps, lr 2e-4 and the KL guard are the same as Sleep-1 (facts.py seed, 120 facts,
forward 120 / reverse 120 / two-hop 60, ARC-Easy 500). Thinking is switched off in every prompt (Ben's plan uses the model without it).

Arms: S0 base, IC facts in context, S1 plain LoRA on the 120 sentences, S2 dreams + verify + KL guard, and
S2T = S2 plus dreamed two-hop questions (one change: the dream step also writes "where does X's mentor live?"-style questions
whose answers are checked by chaining two facts from the notes; two-hop test questions are still excluded by the leak filter).

## Marks (fixed now)
- M1 S2 forward >= 70 and >= S1 + 15. M2 S2 reverse >= 40. M4 S2 ARC >= S0 - 2. (Same as Sleep-1.)
- M5 S2T two-hop >= S2 two-hop + 15, with S2T forward >= S2 forward - 5.
**Wrong if** S2 <= S1 on both forward and reverse, ARC drops more than 5, or S2T two-hop <= S2 two-hop + 5.
Compute: Ben's Mac, free. If the Mac is too slow for all arms overnight, run S0, S2 and S2T first; IC and S1 come after.
