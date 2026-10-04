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

## Round 3 (two-step), credit $6.66 at 23:29 UTC
| contract | GPU | $/h | UTC | job | destroyed | est. cost |
|---|---|---|---|---|---|---|
| 54072716, 54072717, 54072718, 54072721 | 4080S / 3090 Ti / A10 / 3090 | 0.22-0.30 | 22:31-22:48 | first launch: 8 of 12 runs crashed on the real core's 49-token cap | 22:48 | ~$0.27 |
| 54074342 | RTX 3090 | 0.151 | 22:49-23:29 | TWO seeds 0-2 | 23:29 after sha-checked copy-back | ~$0.10 |
| 54074346 | RTX 3090 | 0.202 | 22:49-23:29 | TWO seeds 3-5 | 23:29 | ~$0.13 |
| 54074348 | RTX 4080S | 0.216 | 22:49-23:29 | TWO-O seeds 0-2 | 23:29 | ~$0.14 |
| 54074349 | RTX 3090 | 0.296 | 22:49-23:29 | TWO-O seeds 3-5 | 23:29 | ~$0.20 |
Round 3 about $0.85; thread total about $2.9 (estimates from hourly rates).

## Round 4 (2026-10-04)
- 12:49Z 54149669 (3090 $0.139/h, seeds 0,1), 54149670 (3090 $0.151/h, seeds 2,3), 54149671 (3090 $0.156/h, seeds 4,5): two-ctx-comp, commit 67cba7ab. Credit before: $2.56.
- 12:55Z 54149671 destroyed (pip failed: huggingface_hub missing; no run started, ~$0.01). Relaunched seeds 4,5 on RTX 5090 offer 53547156 ($0.446/h, torch 2.8 cu128 image), per Ben.
- 12:58Z 54149669 destroyed (pip failed, no run; ~$0.02). Seeds 0,1 relaunched on 5090 offer 45669057 ($0.47/h). Seeds 2,3 still on 54149670 (3090), 4,5 on 54150085 (5090).
- 13:15Z results copied back sha-checked (3 waves); 54150696, 54150085, 54149670 destroyed. Round 4 cost ~$0.46 (incl. two failed pip boxes ~$0.03). Credit \$2.10 at 13:20Z 10-04.

## Round 5 (2026-10-04)
- Credit \$22.05 at 14:37Z (Ben's top-up landed). 14:42Z six RTX 5090 boxes (torch 2.8 cu128 image), commit e666bc01: 54161541 (comp seeds 0,1; \$0.47/h), 54161544 (comp 2,3), 54161562 (comp 4,5), 54161563 (tabv 0,1), 54161565 (tabv 2,3; \$0.476/h), 54161567 (tabv 4,5; \$0.498/h). Expected ~\$0.15 each for ~20 min.
- ~14:45Z aborted first launch (6 boxes destroyed within ~2 min; frame bug caught by smoke test; ~$0.05). Relaunch below.
- 14:44Z relaunch, commit 344aa27f, six 5090 boxes: 54161732 (comp 0,1), 54161733 (comp 2,3), 54161734 (comp 4,5), 54161735 (tabv 0,1), 54161736 (tabv 2,3), 54161737 (tabv 4,5).
- 15:14Z results copied back sha-checked (12 runs); all six round-5 boxes destroyed. Credit $18.66.
