# PREREG lfm3q4: does sleep on LFM3's official 4-bit file remember as well as sleep on full precision?

Sealed 2026-10-27 before any run of arm G (sha256 in PREREG-lfm3q4.md.sha256). Thread "Fit sleep on an 8 GB M2". Sleep-B chat-week world only; no card or village experiments.

## Why
Ben (2026-10-27 19:45Z): the small tier is now LiquidAI/LFM3-1.7B. On a Mac it runs the official QAD-Q4_0 GGUF (quantization-aware trained,
LFM3-1.7B-QAD-Q4_0.gguf, sha256 43a7d09a0e9cba91b63eb7052488b9564569bddfd65754d2e426465e572a7452). Sleep there has to train its add-on on top of that
frozen 4-bit base. Earlier 4-bit sleep lost memory: K2-3.7B -10.5 recall (MLX-style 4-bit, p = 0.0002), Qwen3.5-2B -16.2 (Week-1, p = 0.035).
Those used plain rounding; LFM3's file was trained to survive 4-bit, so the gap may be smaller. This test measures it on the exact weights the Mac runs.

## Setup
The recipe is addendum 19's arm l3_g570_w (sleep thread, PREREG-sleepB-addendum19.md, sealed 09e4139256): `--arm ab_ob_b4_nb --model LiquidAI/LFM3-1.7B
--revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --rem-chain-mode q_think
--rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval --rem-writer base --rem-pairs distinct --rem-parse first_q
--rem-verify-tokens 96 --reword backbone/sleep/brain/data/week2_reworded.json --gen-bs 24` (16 on OOM).
Code commit: edfa43e154 (branch claude/project-thread-iu5z4i = the LFM3 port f35dd7e840 merged with --q4-gguf; the port's Qwen / K2 / LFM3 smoke
results are unchanged by the merge apart from timing, shown on CPU).
- Arm F: full-precision base = addendum 19's own run of l3_g570_w on Ben's PC (RTX 5070 Ti, bf16). Not rerun here.
- Arm G: the same command + `--q4-gguf LFM3-1.7B-QAD-Q4_0.gguf` (repo LiquidAI/LFM3-1.7B-GGUF, sha256 above), on the Radeon PC (RX 7700 XT 12 GB, ROCm,
  bf16). q4gguf.apply_gguf replaces every base weight by its dequantized GGUF tensor; mapping checked on CPU: 153 Q4_0 tensors rel. error
  0.086-0.118, token_embd Q6_K 0.024, 132 F32 0.00003-0.0125, no permutation or transpose; rope_freqs ignored.
- The two arms run on different GPUs. Treat that like a different seed (as addendum 11 did). If G lands in the inconclusive band below, arm F is
  rerun on the Radeon PC before any other follow-up, and the marks are then read F(Radeon) vs G.

## Primary measure
Recall C2+C4 forward, weights only (200 questions), as in addendum 19, paired exact McNemar G vs F on per-question rows (`paired.py`).

## Pass marks (fixed now)
- G PASS (4-bit sleep is fine on LFM3): recall G >= recall F - 3 AND ARC-Easy after >= that arm's own ARC base - 3 AND diary G >= diary F - 5.
- G WRONG (4-bit hurts sleep on LFM3, like K2): recall G <= recall F - 6 AND McNemar p < 0.05.
- Anything else: inconclusive. The only follow-up then is arm G8 = G with `--budget-scale 8`, sealed as an addendum first.
- Two-hop (addendum 19's main goal) is reported for both with a paired exact McNemar, not marked.
- If F itself recalls under 60, the test says nothing about 4-bit (sleep is not working on LFM3 yet): stop and hand back to the sleep thread.

## Also recorded
Base recall before any night (F vs G: how much the 4-bit file alone forgets), reverse, two-hop, changed-new, routine, diary, ARC base/after, gate reverts,
night wall time per phase and peak GPU memory (to scale to an 8 GB Mac), fp16 overflow steps if fp16.
