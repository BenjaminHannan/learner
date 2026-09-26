# RESULTS-rent: bm-riv smoke (Benchmarks thread, 2026-09-26, label claude-benchmarks-bmrivsmoke)

Smoke run, not a registered experiment. Four rival arms answer Sleep research's 30-item SMOKE panel
(seed 36000, NOT a test panel). Counts only; no replies quoted. Origin/main code run unmodified, never edited.

## Gates

- CREDIT GATE (first): credit 6.303551406269861 (balance 0). >= $0.30: PASS, rented.
- DUPLICATE GATE: origin/builder-outbox has no artifacts/claude-bmriv-smoke-20260926/run and no
  artifacts/claude-bmriv-smoke-20260926/RESULTS-rent.md (ls-tree empty); `vastai show instances --raw`
  showed no live instance labelled claude-benchmarks-bmrivsmoke. PASS, rented.

## Seal checks (step 1)

- `sha256sum artifacts/claude-panel-rsn358b3-smoke-20260926/panel.jsonl` =
  da7202db858cee9537acbb4d40d2316921673e00cf27a19a60ef09c1973012e7 (required value). PASS.
- `python -B scripts/claude_bmriv_rivals.py selftest --tok BASE` ended `BMRIV-SELFTEST PASS 12/12`. PASS.

## Environment

- torch 2.8.0+cu129 (CUDA True), transformers 5.17.0, python 3.11.13.
- GPU: NVIDIA GeForce RTX 4090. Peak GPU memory seen: 16926 MiB of 24564 MiB.
- BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
- Q2DIR = /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc
- L12DIR = /root/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b
- Setup: streamed only scripts/claude_bm390.py, scripts/claude_bmriv_rivals.py,
  artifacts/claude-panel-rsn358b3-smoke-20260926/panel.jsonl, artifacts/claude-bmriv-smoke-20260926
  (git archive origin/main | ssh | tar). Kit pip line only. HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1
  MKL_NUM_THREADS=1 PYTHONUTF8=1 for all runs. PANEL = panel.jsonl above,
  OUT = artifacts/claude-bmriv-smoke-20260926/run (new folder).
- This job did not need READER, self122_head.pt, MiniLM, or the route122 check (per task).

## Runs (step 2; R = `python -B scripts/claude_bmriv_rivals.py run --panel PANEL --out OUT`)

All four lanes started together 2026-09-26T15:19:17Z, each a fresh process with its own log
(lane1.log lane2.log lane3.log lane4.log), from ~/tree under setsid/nohup.

- Lane 1, plain1b: `R --model BASE --name plain1b`. exit 0. start 2026-09-26T15:19:17Z, end 2026-09-26T15:24:37Z.
  {"name": "plain1b", "rows": 30, "think": "off", "max_new": 512, "shard": "0/1", "seconds": 318, "hit_max": 25, "think_closed": 0, "empty_replies": 0, "median_new_tokens": 512.0, "median_ms": 11191.7, "sha256": "dd5b756c2b73f8b64ce1607b587864a4d961f30015109fdead43113880a1ec77"}
- Lane 1, qwen2b: `R --model Q2DIR --name qwen2b`. exit 0. start 2026-09-26T15:24:37Z, end 2026-09-26T15:35:18Z.
  {"name": "qwen2b", "rows": 30, "think": "off", "max_new": 512, "shard": "0/1", "seconds": 640, "hit_max": 30, "think_closed": 0, "empty_replies": 0, "median_new_tokens": 512.0, "median_ms": 21090.65, "sha256": "96213ade82a727aa442bbc98c8a9f5017961f191fd61bfab1bc1719e44d91ba6"}
- Lane 1, lfm12b: `R --model L12DIR --name lfm12b`. start 2026-09-26T15:35:18Z. Killed by exact PID at
  2026-09-26T15:36:48Z (BUDGET-STOP, exit 143, SIGTERM). No final JSON line (run did not finish).
  Partial rows kept: 10.
- Lane 2, qwen2b_think_s0: `R --model Q2DIR --name qwen2b_think_s0 --think on --max-new 4096 --shard 0/3`.
  start 2026-09-26T15:19:17Z. Killed by exact PID at 2026-09-26T15:36:48Z (BUDGET-STOP, exit 143).
  No final JSON line. Partial rows kept: 6.
- Lane 3, qwen2b_think_s1: same with `_s1 ... --shard 1/3`. start 2026-09-26T15:19:17Z.
  Killed by exact PID at 2026-09-26T15:36:48Z (BUDGET-STOP, exit 143). Partial rows kept: 6.
- Lane 4, qwen2b_think_s2: same with `_s2 ... --shard 2/3`. start 2026-09-26T15:19:17Z.
  Killed by exact PID at 2026-09-26T15:36:48Z (BUDGET-STOP, exit 143). Partial rows kept: 6.

## Merge (step 3)

Skipped: the time cap did not stop a lane, but lanes 2-4 did not exit 0 (killed for BUDGET-STOP),
so per the task the merge is skipped. The shard files keep what finished (6 rows each).

## OUT files copied back (step 4)

Copied back before destroy; sizes and sha256 match the box. 88 rows total.

- rival_plain1b.jsonl: 30 rows, 40339 bytes,
  sha256 dd5b756c2b73f8b64ce1607b587864a4d961f30015109fdead43113880a1ec77
- rival_qwen2b.jsonl: 30 rows, 41690 bytes,
  sha256 96213ade82a727aa442bbc98c8a9f5017961f191fd61bfab1bc1719e44d91ba6
- rival_lfm12b.jsonl: 10 rows (partial, killed), 14200 bytes,
  sha256 82ebbf2a2da785f0dd0b90b46bacf1f2adccb28588ac086d215eaf7ac95dabc7
- rival_qwen2b_think_s0.jsonl: 6 rows (partial, killed), 1205 bytes,
  sha256 e04012937776503f7a32337e03e188ea243ccb8d5d56df3feec131a36448c0a7
- rival_qwen2b_think_s1.jsonl: 6 rows (partial, killed), 2212 bytes,
  sha256 aec1e6b43f549572e551a260209b26221ebeb70b206a705cd6723d4e93280770
- rival_qwen2b_think_s2.jsonl: 6 rows (partial, killed), 798 bytes,
  sha256 968d150a70269e29db87eb6fc485a02f679fcd51361b119abd2b0bccfeca80c1

## Instances, hours, money

- Rental 1: instance 52766147 (offer 52652212, RTX 4090, cheapest 5090/4090 passing the kit filter at
  $0.3996/hr search dph; actual dph 0.43437037). Created 2026-09-26T15:01:12Z, running ~15:04:41Z
  (within the 6-min rule). Outcome: SSH-FAIL — the container never accepted the account SSH key
  (account key verified matching; a freshly created + attached key also refused), so no work ran.
  Destroyed by exact id ~15:10:10Z. ~0.15 h x $0.43437037 = ~$0.065. 10-min watchdog never triggered
  (no job started). Rental 1 of max 4.
- Rental 2: instance 52767389 (offer 39064492, RTX 4090, next-cheapest passing filter).
  dph 0.42222222, image pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime, disk 80.
  Created 2026-09-26T15:10:22Z, running 2026-09-26T15:16:32Z, lanes launched 15:19:17Z,
  all run processes killed by exact PID 15:36:48Z, destroyed 2026-09-26T15:38:15Z,
  confirmed gone with `vastai show instances` (0 claude-benchmarks-bmrivsmoke live).
  27.88 min = 0.4647 h x $0.42222222 = ~$0.196. Rental 2 of max 4.
- Running total ~$0.261 of the $0.30 task budget (Benchmarks thread's $2; $1.50 already on rent-bm398r).
  Stopped by the MONEY RULE before the $0.27 mark (kill at ~$0.257, destroy completed at ~$0.261);
  continuing the think shards + lfm12b would have breached $0.27. Status: BUDGET-STOP.
  Time cap (40 min on the rental) not hit. No re-rents beyond the 2 above.

## Errors / tracebacks

None from the Benchmarks thread's code: nothing broke, no traceback. The only failure was
infrastructure (rental 1 SSH key-sync). Commands finished: panel sha256 check, selftest,
plain1b run, qwen2b run. Commands killed unfinished (exit 143, partial rows kept): lfm12b run,
qwen2b_think_s0/s1/s2 runs. Merge not attempted (skipped per task).
