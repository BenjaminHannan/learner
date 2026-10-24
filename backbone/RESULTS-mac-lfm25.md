# LFM2.5-24B-A2B on Ben's Mac (M1 Pro 32 GB, mlx-lm 4-bit), 2026-10-24

## Real-jobs scoreboard (tau2-bench retail, tasks 0-39, Haiku 5.5 as user simulator and judge, 1 trial; prereg gaps/scoreboard1/PREREG.md)
| agent | DB match /40 | Pass^1 |
|---|---|---|
| Claude Haiku 5.5 (cloud; Stage A) | 29 | 0.725 |
| LFM2.5 thinking on | 30 | 0.725 |
| LFM2.5 thinking off (chat template ends with `<think>\n</think>\n`) | 23 | 0.525 |
Thinking off: 9 tasks aborted with too_many_errors (the agent repeated a failing call, e.g. "User not found", 10 times).
mlx_lm.server needs --max-tokens 8192 (default 512 cuts the thinking). Files on the Mac:
~/learner-ops/scoreboard1/tau2-bench/data/simulations/{lfm25,lfm25_nothink}/results.json (sha256 77e0c258..., 568af86e...).

## Speed (bench.py, short prompt, 300 new tokens)
| agents | each tok/s | total tok/s | peak GB |
|---|---|---|---|
| 1 | 54.5 | 54.5 | 13.6 |
| 2 | 35.4 | 70.8 | 13.7 |
| 4 | 21.1 | 84.6 | 13.7 |
| 8 | 11.5 | 91.9 | 13.8 |
Prefill: ~420 tok/s (1k tokens 2.4 s, 4k 8.7 s, 16k 36.5 s to the first token). Same-day comparison: Qwen3.6-35B-A3B 42/27/15/9 each,
Qwen3.5-4B 44/30/16/7 each.

## PopQA lookup (tricks thread's test; their scoring with unicode normalisation)
With the same Wikipedia evidence, the LFM2.5 boss ties Qwen3.5-4B (39.25 vs 40.0). LFM writes U+202F/U+2011, so normalise before matching.
