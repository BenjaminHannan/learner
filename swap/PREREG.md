# Swap-1: replace LFM2.5 as the v2 backbone (pre-registration, 2026-10-25 ~12:40Z)

Labels in the results: shown / suggested / untested. This is the assistant backbone, not the village model or the card experiments.

## Why
Artificial Analysis (index v4.3.2, fetched 2026-10-25) puts LFM2.5-8B-A1B at 7. Candidates that score higher:
K2-Horizon-7B 21 and K2-Horizon-3.7B 16 (reasoning-only models, AA marks the scores as estimates),
Qwen3.5-9B 13 / Qwen3.5-4B 11 with thinking off, K2-Horizon MoVA 36B-A4B 25, Qwen3.8-27B / Qwen3.6-27B 20 with thinking off,
and Qwen3.6-35B-A3B 15 with thinking off. Ben wants two tiers: K2-Horizon-7B (bigger computers) and K2-Horizon-3.7B (smaller ones).

## Ruler
The scoreboard1 store test is tau2-bench retail, tasks 0-39, run at **2 trials** (80 sims per arm). The customer and judge are
claude-haiku-5-5 with the same patched tau2 (cc1df47) the Mac runs use, plus retries on 429s. The success metric is DB match.
The agent is served with vLLM bf16 on one rented RTX 5090, using each model's default sampling (generation_config).
Thinking off means the template ends with an empty think block, the same trick as the LFM Mac runs.
Thinking arms (K2 `reasoning_effort` low/medium) are judged equally, since v2 loops the model anyway (Ben, 12:35Z).
Agent tokens and seconds are recorded per sim.

Control: LFM2.5-8B-A1B no-think, on the same box and stack. Mac runs of it scored 14, 19 and 23 out of 40 across bf16, q4 and q8.

## Pass marks (fixed now)
- **P1 (K2-7B replaces LFM):** K2-7B at its best setting has DB match >= LFM control + 8/80 (10 points).
- **P2 (K2-3.7B replaces LFM on small machines):** K2-3.7B no-think or low >= LFM control, at about half the q4 size.
- **P3 (AA ranking transfers to our job):** the order K2-7B > Qwen3.5-9B and K2-3.7B > Qwen3.5-4B holds in the no-think arms.
- **Harness check:** tool-call parse failures (sims ending in too_many_errors) < 10% for any arm we call a winner.

**What would prove it wrong:** K2 no-think scores at or below the LFM control. That would mean AA's thinking-on scores don't carry over
to raw use. We would then judge K2 only at low thinking, and weigh its token cost.

## After this
The Mac q4 runs come next, when the Mac is free: speed (1/2/4 agents, prefill), q4 vs q8 quality for the picked tiers,
and MoVA 36B-A4B / Qwen3.6-35B-A3B / Qwen3.8-27B at q4 for the big tier.
Cost cap: Vast $3.50 (coordinator-approved). Haiku comes out of the API credit.
