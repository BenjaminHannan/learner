# Probe-4 results: PASS

Prereg `PREREG.md` (sealed ccfa95ec4f) + Addendum 1. 96 new tasks (38 traps) written by Claude Sonnet and frozen
before any try (84bbe0dbe2, sha256 b6c23113...27ab). Ben's M3, MLX, K2-Horizon-3.7B bf16, 16:51-21:41Z Oct 27,
peak 16.8 GB. Replay gate 100%. Raw: `results/m3/`. Re-analysed in the cloud from the pushed files: identical.

| picker | all (%) | traps (%) | non-traps (%) | generated tokens / task |
|---|---|---|---|---|
| FIRST (one guess, today's assistant) | 50.0 | 21.1 | 69.0 | 199 |
| RAND (a random one of 12) | 53.3 | 30.0 | 68.5 | 2,461 |
| VOTE | 47.9 | 21.1 | 65.5 | 2,461 |
| SELF (K2 judges itself) | 59.4 | 18.4 | 86.2 | 2,473 |
| TEST-B (untuned K2 tests) | 59.4 | 15.8 | 87.9 | 2,776 |
| **TEST-T (K2 + Probe-3 LoRA tests)** | **66.7** | **31.6** | **89.7** | 2,758 |
| ORACLE (any of 12) | 78.1 | 60.5 | 89.7 | 2,461 |

E1 (>= FIRST + 10 = 60.0) ok; E2 (>= SELF + 5 = 64.4) ok; E3 (>= TEST-B + 5 = 64.4) ok. PASS.
Paired bootstrap 95% CIs: TEST-T - FIRST [8.3, 25.0]; - SELF [2.1, 13.5]; - TEST-B [3.1, 12.5].

## What it means
- shown: on jobs from a different generator, 12 tries + K2's own trained tests solve 66.7% vs 50.0% for one try.
  On normal jobs the trained tests reach the 12-try ceiling (89.7% = oracle).
- shown: the trained tests transfer: 84.8% hold on the reference plan (untuned 66.4%), 0 empty samples.
- shown: traps are the weak spot: 31.6% picked vs 60.5% possible. Self-judging and untuned tests are WORSE than a
  random try on traps (18.4 / 15.8 vs 30.0): judges reward "did the literal thing".
- caveat: E2's interval reaches +2.1 (below the 5-point mark); 96 tasks; costs ~14x the tokens of one try.
