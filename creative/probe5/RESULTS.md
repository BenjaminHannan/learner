# Probe-5 results: PASS (narrowly on E2)

Prereg `PREREG.md` (sealed a91269cea9). Same 96 frozen Probe-4 tasks (38 traps). Ben's M3, LFM3-1.7B BF16 GGUF on
llama.cpp (`--jinja`, thinking off, 4 parallel slots), test-writer LoRA trained with torch + peft on MPS (vendored
model file), 00:20-03:32Z Oct 28. Raw: `results/m3/`. Re-analysed in the cloud from the pushed files: every success
rate identical (only TEST-B's token count differs, because the cloud rerun lacked the generation log).

| picker | all (%) | traps (%) | non-traps (%) | K2 all (Probe-4) |
|---|---|---|---|---|
| FIRST (one guess) | 38.5 | 18.4 | 51.7 | 50.0 |
| RAND | 40.7 | 22.6 | 52.6 | 53.3 |
| VOTE | 43.8 | 23.7 | 56.9 | 47.9 |
| SELF (LFM3 judges itself) | 52.1 | 13.2 | 77.6 | 59.4 |
| TEST-B (untuned tests) | 50.0 | 13.2 | 74.1 | 59.4 |
| **TEST-T (LFM3 + LoRA tests)** | **57.3** | **21.1** | **81.0** | 66.7 |
| ORACLE (any of 12) | 72.9 | 57.9 | 82.8 | 78.1 |

E1 (>= 48.5) ok; E2 (>= 57.1) ok by 0.2 points; E3 (>= 55.0) ok. PASS.
Paired bootstrap 95% CIs: TEST-T - FIRST [9.4, 28.1]; - SELF [0.0, 10.4]; - TEST-B [2.1, 13.5].
Gates: replay 100%; tool calls parsed natively (3,120 native, 0 text fallback); val loss 0.992 -> 0.298; TEST-T empty 0/384.

## What it means
- shown: the recipe transfers to LFM3. 12 tries + LFM3's own trained tests: 57.3% vs 38.5% for one try (+18.8).
  On normal jobs the trained tests nearly reach the 12-try ceiling (81.0 vs 82.8).
- shown: the trained test writer is what works. Tuned tests: 0/384 unparsable, 78.3% hold on the reference plan.
  Untuned LFM3 tests: 311/384 unparsable (it reasons in prose and hits the 768-token cap), so TEST-B is mostly SELF.
- suggested: E2 (beat self-judging by 5) is the weak part: met by 0.2 points, interval reaches 0.
- shown: LFM3 is weaker than K2 one try at a time (38.5 vs 50.0) and after picking (57.3 vs 66.7). Descriptive
  only (different backbones, no pass mark).
- shown: trick jobs stay the weak spot: 21.1% picked of 57.9% possible; self-judging (13.2%) is worse than a
  random try (22.6%). This is Probe-6's target (`PROBE6-PLAN.md`).

## Cost
Free. Training 58 steps x ~80 s (peak 7.0 GB). Tries + SELF + tests 63 min at 4 slots (~21 tries/min, ~4x K2 on
MLX). Server peak 14.8 GB RSS (mostly the mapped model + 64k context). Two disk pauses from another thread's files.
