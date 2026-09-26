Starting your smoke run — fetching branches and checking gates.
Kit and panel docs reviewed. Now the credit and duplicate gates.
Cheapest qualifying offer is a 4090 at ~$0.40/hr. Renting it now.
Instance running. Setting up SSH and streaming the tree.
SSH auth still failing — verifying the key match.
Host isn't syncing SSH keys. Destroying and re-renting.
Running. Testing SSH.
SSH works. Streaming the code tree.
Models cached. Running seal checks (panel hash + selftest).
Seal checks pass. Launching all four lanes.
Launch command hung — checking box state.
All four lanes are running. Polling progress.
Approaching the $0.27 money-stop. Executing stop sequence now.
Copying results back to the Mac.
Hashes match. Destroying the instance.
Files are gitignored; force-staging just my PUSH paths.
Status: BUDGET-STOP (money-rule stop; final ~$0.261 of $0.30, killed at ~$0.257 before the $0.27 mark — continuing would have breached it).

CREDIT GATE: credit 6.303551406269861. PASS (rented).
DUPLICATE GATE: no origin/builder-outbox artifacts/claude-bmriv-smoke-20260926/run or RESULTS-rent.md; no live claude-benchmarks-bmrivsmoke instance. PASS.

Seals: panel sha256 da7202db858cee9537acbb4d40d2316921673e00cf27a19a60ef09c1973012e7 (match). Selftest ended `BMRIV-SELFTEST PASS 12/12`.
Env: torch 2.8.0+cu129, transformers 5.17.0, python 3.11.13. GPU RTX 4090. Peak mem 16926/24564 MiB.
Models: BASE .../models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc; Q2DIR .../models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc; L12DIR .../models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b.

Run JSON lines verbatim (counts only):
`{"name": "plain1b", "rows": 30, "think": "off", "max_new": 512, "shard": "0/1", "seconds": 318, "hit_max": 25, "think_closed": 0, "empty_replies": 0, "median_new_tokens": 512.0, "median_ms": 11191.7, "sha256": "dd5b756c2b73f8b64ce1607b587864a4d961f30015109fdead43113880a1ec77"}` — exit 0, start 2026-09-26T15:19:17Z, end 2026-09-26T15:24:37Z.
`{"name": "qwen2b", "rows": 30, "think": "off", "max_new": 512, "shard": "0/1", "seconds": 640, "hit_max": 30, "think_closed": 0, "empty_replies": 0, "median_new_tokens": 512.0, "median_ms": 21090.65, "sha256": "96213ade82a727aa442bbc98c8a9f5017961f191fd61bfab1bc1719e44d91ba6"}` — exit 0, start 2026-09-26T15:24:37Z, end 2026-09-26T15:35:18Z.
No JSON lines for lfm12b / qwen2b_think_s0,s1,s2 (killed by exact PID 15:36:48Z, exit 143, partial rows kept: 10/6/6/6). Merge skipped per task (shards never exited 0).

OUT files (88 rows total), sizes + sha256 match box: rival_plain1b.jsonl 30 rows 40339 B dd5b75…; rival_qwen2b.jsonl 30 rows 41690 B 96213a…; rival_lfm12b.jsonl 10 rows 14200 B 82ebbf…; rival_qwen2b_think_s0.jsonl 6 rows 1205 B e04012…; rival_qwen2b_think_s1.jsonl 6 rows 2212 B aec1e6…; rival_qwen2b_think_s2.jsonl 6 rows 798 B 968d15….

Instances: 52766147 (offer 52652212, 4090, dph 0.43437, created 15:01:12Z, destroyed ~15:10:10Z, ~0.15h, ~$0.065, SSH-FAIL: container refused all account keys incl. fresh attached key); 52767389 (offer 39064492, 4090, dph 0.42222, created 15:10:22Z, running 15:16:32Z, destroyed 15:38:15Z, ~0.46h, ~$0.196). Running total ~$0.261. 2 rentals of max 4. Post-destroy: 0 live. Ledger line appended; RESULTS-rent.md + run/ staged for the watcher (PUSH paths). No traceback (code never broke).

Deviations: (1) rental 1 was the cheapest passing offer but unusable (SSH key-sync fail) — destroyed by exact id, replaced with next-cheapest; (2) `git fetch origin main builder-outbox` hit a stale-lock on builder-outbox ref — read builder-outbox state via its known hash daecec3d instead; (3) first lane-launch ssh client timed out locally but all 4 processes launched correctly on the box (verified via ps); (4) stopped ~$0.013 before the $0.27 mark so copy+destroy would land under it (final $0.261); (5) PUSH files force-staged (`git add -f`) since artifacts/ is gitignored in this worktree. Code never edited, names fictional/none, no secrets printed, nothing written to repo-root notebook/. No replies quoted anywhere.
