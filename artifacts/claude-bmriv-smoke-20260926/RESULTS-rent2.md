# bm-riv smoke 2: three rival arms at 4,096 tokens on 8 SMOKE items (rental report, 2026-09-26)

Not a registered experiment. Smoke 1 (RESULTS-rent.md) showed a 512-token cap cuts every rival off
before its final answer. This run gives the three thinking-off arms 4,096 new tokens on 8 of the 30
SMOKE panel items (--shard 1/4; seed 36000; NOT a test panel) so Sleep research can check its scorer
on whole replies. Code: origin/main scripts/claude_bmriv_rivals.py, unmodified. Nothing trained.
Counts only; no replies quoted.

Outcome: BUDGET-STOP (money rule $0.18 crossed between polls; lane 3 killed, rows kept).

- Credit at gate: 8.83074058626977
- Panel sha256: da7202db858cee9537acbb4d40d2316921673e00cf27a19a60ef09c1973012e7 (match)
- Selftest: BMRIV-SELFTEST PASS 12/12
- torch 2.8.0+cu129, transformers 5.17.0, python 3.11.13 (Python 3.11.13)
- GPU: RTX 4090, 24564 MiB
- BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
- Q2DIR = /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc
- L12DIR = /root/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b

## Lanes (R = `python -B scripts/claude_bmriv_rivals.py run --panel PANEL --out OUT --max-new 4096 --shard 1/4`)

Lane 1 (PID 972, start 2026-09-26T16:39:05Z, end 2026-09-26T16:43:41Z, exit 0 inferred):
{"name": "plain1b_4k", "rows": 8, "think": "off", "max_new": 4096, "shard": "1/4", "seconds": 277, "hit_max": 2, "think_closed": 0, "empty_replies": 0, "median_new_tokens": 841.0, "median_ms": 20351.050000000003, "sha256": "596f1386a95b701cdad3fbbabbc6f4ec42880e3700138a510a29e31e2d8f65d7"}

Lane 2 (PID 1030, start 2026-09-26T16:40:22Z, killed 2026-09-26T16:56:55Z by SIGTERM, exit 143 inferred, no final JSON line; 7 rows kept):
(no JSON line; killed mid-row-8)

Lane 3 (PID 1068, start 2026-09-26T16:40:28Z, end 2026-09-26T16:44:46Z, exit 0 inferred):
{"name": "lfm12b_4k", "rows": 8, "think": "off", "max_new": 4096, "shard": "1/4", "seconds": 258, "hit_max": 0, "think_closed": 0, "empty_replies": 0, "median_new_tokens": 2175.0, "median_ms": 31916.3, "sha256": "2277023dc9a113a4a8d1772cf37ab4dcc4e5c78f32a39a9e6f7130b5731e2bde"}

Finished lanes: plain1b_4k (8 rows), lfm12b_4k (8 rows). Killed lane: qwen2b_4k (7 rows).

## OUT files (artifacts/claude-bmriv-smoke-20260926/run2/, copied back before destroy, sizes and sha256 match the box)

- rival_plain1b_4k.jsonl: 8 rows, 33197 bytes, sha256 596f1386a95b701cdad3fbbabbc6f4ec42880e3700138a510a29e31e2d8f65d7
- rival_qwen2b_4k.jsonl: 7 rows, 49956 bytes, sha256 cdfedadb760aa3ab09d746bac21de6765b3f0156e374de654e1971194cfe2a0b
- rival_lfm12b_4k.jsonl: 8 rows, 40403 bytes, sha256 2277023dc9a113a4a8d1772cf37ab4dcc4e5c78f32a39a9e6f7130b5731e2bde
- Total rows: 23

## Rental

- Peak GPU memory seen: 9665/24564 MiB (sparse polling; true peak may be higher)
- Instance 52778379 (offer 43681503, RTX 4090, Malaysia MY, image pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime, disk 80)
- Created 2026-09-26T16:27:10Z, running ~16:31:36Z, destroyed 2026-09-26T16:58:03Z: ~0.515 h x dph $0.38222222 = ~$0.197 of $0.20 budget (money rule $0.18)
- Rentals used: 1 of max 4. Post-destroy live with this label: 0.
- Traceback: none. No code error; no replies quoted.

## Deviations

1. Lanes 2-3 started 77-83 s after lane 1 (the combined 3-lane launch ssh call timed out client-side after lane 1 was up; lanes 2 and 3 were launched individually right after). All three overlapped 16:40:28-16:43:41Z.
2. Exit codes inferred, not captured numerically (lanes ran detached; completion evidenced by final JSON line plus full 8-row files; lane 2 by SIGTERM kill). Same inference as smoke 1.
3. Money-rule overshoot: spend was ~$0.172 at the 16:54:06Z poll and ~$0.189 at the 16:56:45Z poll; PID 1030 was killed immediately (~16:56:55Z). Final ~$0.197, inside the $0.20 task budget.
4. Peak GPU memory from sparse nvidia-smi polls only.
5. One ssh client-side timeout on the combined lane-launch command; no effect on the rental (lane 1 launched fine).
