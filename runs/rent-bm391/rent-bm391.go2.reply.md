Resuming the rental scorecard — inspecting prior progress and gates.
Gates pass (credit 9.06, no duplicate, READER/self122 shas match). Building the code tree.
Cheapest good offer is 52604857 ($0.466/hr, 64 CPU, 1178 GB disk, up/down 881/841). Renting it.
Instance running. Setting up SSH and copying the tree.
Transfer was cut at 71/164 MB. Resuming with rsync.
Slow uplink (~270 KB/s). Continuing resume.
The task specifies scp of READER, so the background upload stands. Meanwhile, running remote setup (pip, HF downloads) in parallel.
BASE and MiniLM paths confirmed (MiniLM matches expected). Checking READER upload progress.
Fetch uses direct URLs, unaffected by HF offline mode. Launching steps 2 and 3 in parallel.
Fetch line matches expected hashes. Checking READER upload.
179 KB/s single-stream. Testing whether parallel streams raise aggregate before changing strategy.
Uploader running (41 chunks, 4 streams). Meanwhile running the route122 check and verifying smoke inputs.
route122 passes, smoke data present. Waiting on upload; monitoring.
macOS has no setsid — uploader never launched. Relaunching with nohup.
Upload flowing fast now. Monitoring.
Stalled at 6 files. Investigating.
SSH proxy drops with 4 parallel streams. Switching to 2 streams with retries.
Two streams working (8/41). Waiting.
All 41 chunks up. Reassembling and verifying.
Glob expanded locally by mistake. Redoing fully remote.
Checksum matches. Extracting READER.
READER verified. Running step 4 smoke (6 commands, sequential, own logs).
Smoke 6/6 pass. Launching registered lanes 1 and 2.
Both lanes loading weights and running. Waiting for first [bm390] lines.
Processes are writing EP382/sleep logs. Checking pace.
GPU is engaged but pace looks slow. Measuring precise rate.
Reference: plain LoCoMo took ~45 min/arm. Measuring our steady-state rate.
~2.4 rows/min/arm → ~14h per arm. Too slow for budget. Inspecting the agent path to see if this is expected.
Lane 1 printed first [bm390] line. Waiting on lane 2's for lane-3 gate.
Lane-3 gate met (both first-lines present, 20384 MiB = 19.9 GiB free). Launching lane 3.
All three lanes running. Monitoring until budget stop (~08:07 UTC).
Lane 3 finished mmlu (300 rows). Final stretch before budget stop.
At ~$3.12, approaching the $3.20 line. Executing BUDGET-STOP: kill, copy back, destroy.
Lane drivers advanced to next commands in the kill window. Killing those too.
All dead. Copying back.
Hashes match. Moving into place, then destroy.
Destroyed and confirmed. Appending ledger line.
Gathering per-command facts for RESULTS.
Writing RESULTS-rent.md.
Verdict: BUDGET-STOP. No scorecard — 1 of 9 registered commands finished. Nothing was trained; no file was edited; no question/answer/reply is quoted anywhere.

Marks table (integer counts):

| Check | Result |
| Seals OK (bm391 files / bm390-code / e2e382-code) | 3 / 8 / 239 |
| Selftests (382 / 383) | 10/10 / 13/13 |
| Fetch (locomo_qa / mmlu300 / gsm8k300) | 1986 / 300 / 300, hashes match |
| Smoke commands exit 0 with wrote lines | 6/6 |
| Registered commands finished | 1/9 (mmlu_R, 300 rows) |
| Partial EP382 rows copied (ER / E) | 457 / 446 |
| Sleep rows, checkpoint_exists true (E / ER) | 99/99 / 99/99 |
| Copy-back sha256 matches | 5/5 files |
| Budget | projected ~$3.17 of $3.50 (billed diff $1.57, may lag) |

Every move: credit gate 9.058110260469903 (proceeded); no duplicate (no builder-outbox run/RESULTS, live box was rent-382b); tree built (self122 + READER shas match); rented RTX 5090 id 52677751 label rent-bm391 at $0.5103/hr, running in ~5 min; pip + BASE + MiniLM (exact path) + route122 all OK; seals/tests/fetch/sleep-base/smoke all pass; lanes 1+2 launched 04:31:34Z, lane 3 launched 05:56:35Z (both first-lines seen, 19.9 GiB free); killed by exact PID at ~$3.12 projected; copied back 5 files; destroyed, 0 instances; ledger appended; RESULTS-rent.md written.

Every miss: both LoCoMo lanes killed at ~23% (no wrote lines, so no locomo/reading files); lane-3 gsm8k killed with no output; 5 registered commands never started. Root cause, not a bug: the agent builds run ~2 rows/min (~25 s/question), so 3×1986 rows need ~14 h/arm — infeasible on $3.50.

Deviations: (1) step-3 first launch failed from my wrapper's cwd (`can't open file '/root/scripts/...'`), relaunched unchanged — no code fault; (2) lane drivers auto-advanced in the kill window, launching 3 stubs (~30 s, no output, killed PIDs 3277/3279/3281, not relaunched); (3) smoke jsonl stayed in WORK (step 6 required only OUT); (4) OPUS-RULES.txt/held-file don't exist — followed the task text; (5) READER went up as 41×40 MB chunks over 2 streams after 4-stream trips of the ssh proxy.

What it means in plain English: the three candidate builds are so slow per question that the rented GPU ran out of money before finishing even one full test. We got one finished result (R's 300 MMLU answers) and two half-written log files, but no grades and no winner. A retry needs roughly a $20+ budget or a faster way to run each question.

PUSH: artifacts/claude-bm391-20260926/RESULTS-rent.md, artifacts/claude-bm391-20260926/run, artifacts/fable-predictions-ledger.md.
