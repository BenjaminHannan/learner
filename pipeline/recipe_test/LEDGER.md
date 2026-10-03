# Vast ledger (thread u9uvmq). Credit $13.08 at 19:46 UTC; $9.89 at 21:20 UTC (that drop includes other threads' boxes). Cap $6 total, reserve $1.
| contract | GPU | $/h | UTC | job | destroyed | est. cost |
|---|---|---|---|---|---|---|
| 54055987 | RTX 3090 | 0.161 | 19:47-20:23 | attempt 1, BASE (log cut result lines at ~500 chars, rows unrecoverable) | 20:23 | ~$0.10 |
| 54055992 | RTX 3090 Ti | 0.229 | 19:47-20:23 | attempt 1, RECIPE | 20:23 | ~$0.14 |
| 54055995 | RTX 4080S | 0.229 | 19:47-20:23 | attempt 1, copy-old | 20:23 | ~$0.14 |
| 54055997 | RTX 3090 | 0.296 | 19:47-20:23 | attempt 1, pool-mix | 20:23 | ~$0.18 |
| 54059817 | RTX 3090 | 0.164 | 20:25-21:20 | BASE pool-old seeds 0-5 | 21:20, after sha-verified copy-back | ~$0.15 |
| 54059818 | RTX 3090 Ti | 0.242 | 20:25-21:20 | RECIPE copy-mix seeds 0-5 | 21:20 | ~$0.22 |
| 54059819 | RTX 4080S | 0.222 | 20:25-21:20 | copy-old seeds 0-5 | 21:20 | ~$0.20 |
| 54059820 | RTX 3090 | 0.242 | 20:25-21:20 | pool-mix seeds 0-5 | 21:20 | ~$0.22 |
Total about $1.35 (estimate from hourly rates, not the invoice). Copy-back: result tarballs came through the box log in 380-char lines, each sha256-checked and every extracted json checked against the box's MANIFEST lines (0 mismatches, 24 runs).

## Round 2 (contextual reader), credit $8.43 at 22:10 UTC
| contract | GPU | $/h | UTC | job | destroyed | est. cost |
|---|---|---|---|---|---|---|
| 54066196, 54066198, 54066199, 54066201 | 3090 / 3090 Ti / 3090 Ti / Q RTX 8000 | 0.20-0.26 | 21:28-21:32 | aborted at once: my launch list lacked templates_eval_r2.json | 21:32 | ~$0.03 |
| 54066631 | RTX 3090 | 0.201 | 21:32-22:09 | RECIPE seeds 0-2 | 22:09 after sha-checked copy-back | ~$0.12 |
| 54066632 | RTX 3090 Ti | 0.242 | 21:32-22:09 | RECIPE seeds 3-5 | 22:09 | ~$0.15 |
| 54066644 | RTX 3090 Ti | 0.222 | 21:32-22:09 | CTX seeds 0-2 | 22:09 | ~$0.14 |
| 54066645 | Q RTX 8000 | 0.255 | 21:32-22:09 | CTX seeds 3-5 (slow, no TF32) | 22:09 | ~$0.16 |
Round 2 about $0.6. Whole thread about $2.0 (estimate from hourly rates).
