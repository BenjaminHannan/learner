Starting your bm-390 third attempt — checking guards and seals before touching the GPU.
Duplicate check passed — pulling the run specs and prior attempt logs.
I've got the full runbook — now checking the connection to BensPC.
Connection is solid and GPU is idle — building the fresh tree for this attempt.
Tree package is ready (161MB) — shipping it to BensPC.
Tree is live on BensPC and all models check out — running seal verification.
Hit Windows quoting issues — switching to script files for reliable execution.
Seals and wrapper checks passed — running the sleep checkpoint.
Data fetch verified and Qwen rival loads — checking the second rival.
Smoke P passed in 39 seconds — running the plain-model smoke.
Both smokes passed — verifying row counts and line endings.
Smoke stage is fully green — launching the registered benchmark arms.
Primary arm P is running (PID 22324) — watching for first progress to decide lane strategy.
Direct launch gets killed on disconnect — switching to persistent background execution.
P is reading sessions (sleep log growing) — preparing lane 2 for parallel start.
First conv line is in and GPU shows 8GB free threshold not met — running lane 2 sequentially after lane 1.
P is a quarter through (3 convs, 497 questions) — continuing to monitor.
Network blip lost the monitor but P survived on BensPC — resuming polling.
P at 47% of sleep sessions — steady progress, no errors.
P past halfway on sleep sessions — holding course toward the time cap.
P at 71% — about 3.5 hours left in the cap.
P at 89% — entering the final stretch.
P finished — verifying output before starting the general tests.
P complete with full 1986 rows — running MMLU general test.
MMLU agent test still running — monitoring toward completion.
MMLU agent test finished — checking output and starting GSM8K.
GSM8K agent test running — about an hour left in the cap.
GSM8K taking longer than MMLU — 46 minutes to cap.
Lane 1 complete, T started but GPU memory looks tight — checking status.
Rb succeeded with full rows — C is running but nearing the time cap.
Time cap reached — stopping remaining work and collecting results.
Files copied back — verifying integrity before writing the results.
All counts verified — assembling the final results file.
Results file is ready — confirming it's staged for the watcher.
Verdict: TIME-CAP partial. Winnl2 PASS, smoke PASS, seals ALL-OK, lane 1 complete (P/Pm/Pg), lane 2 partial (Rb OK, T OOM, C killed no-output, Q2 stopped at cap, rest never launched). Validity VOID (not FAIL): T traceback + missing arms. No file edited; 1 new RESULTS file + 7 run files for PUSH.

Marks table (integer counts, PASSMARKS bm-390):
- M1 (P vs every yes-arm, cat 1-4 F1 +3.0 and bootstrap>0): 0 computed, 0 pass, 0 fail — INCOMPLETE (need scorer; T missing, Q2/L12 missing).
- M3 (P fewer confident-wrong than every yes-arm): 0 computed — INCOMPLETE.
- M4 (P >= T-3.0 on MMLU-300 and GSM8K-300): 0 computed — INCOMPLETE (P generals done, T generals missing).
- Validity: seals 240 OK / 0 FAIL (8+3+229); data 1986/300/300 OK; rows: P 1986, Rb 1986, others 0; sleep 272 rows, 272 checkpoint_true, 0 attempted; traceback 1 (T OOM) → VOID.

Every move (UTC):
- DUPLICATE guard PASS (no run/RESULTS-rent/RESULTS-benspc3 on builder-outbox).
- Tree3 built (builder-outbox+main+self122 5ca02173…), 161 MB tgz to BensPC, extract OK.
- Setup verified: python 3.10.9, READER/BASE present, Q2/L12 present, MiniLM D8 0.9732, pyarrow 25.0.1. Installed 0.
- Step1 seals: 8 OK, 3 OK, 229 OK, 0 FAIL.
- W CHECK: (a) ok true crlf 3; (b) winnl2 line + ok true crlf 0. Not WINNL-FAIL.
- Step2: JSON seconds 13.4, .pt 4655b761… 2969 bytes, exit 0.
- Step3 fetch verbatim OK (1986/300/300, hashes 1a44e304…/073acc01…), exit 0. Load Q2 Qwen3_5ForCausalLM 1881825088 exit 0; L12 Lfm2ForCausalLM 1170340608 exit 0.
- Smoke P exit 0 39 s wrote 5 bare 5; T exit 0 8 s wrote 5; sleep 2 rows 2 true 0 attempted; 5 files all crlf 0. PASS.
- P start 09:48:09Z end 14:08:47Z exit 0 wrote 1986/1986. Pm 14:09:09–14:52:33 exit 0 wrote 300. Pg 14:52:38–15:59:17 exit 0 wrote 300.
- Lane decision AFTER (first conv 10:19Z, free 8089 MiB <8192).
- T 15:59:31–<16:00:14 OOM, 0 files, traceback full in RESULTS. Rb 16:00:14–16:08:13 exit 0 wrote 1986. C 16:08:20–killed, 0 files, 9 convs partial. Q2 16:26:57–stopped 16:37:15 PIDs 10028/14012, 0 files. L12/Tm/Tg/Q2m/Q2g/L12m/L12g 0 launches.
- Copy-back 7 files sizes/sha256 match (listed in RESULTS). Models left on BensPC.
- PUSH: artifacts/claude-bm390-20260925/RESULTS-benspc3.md artifacts/claude-bm390-20260925/run

Misses/deviations:
- Time cap 09:35:50–16:35:50Z reached; Q2 stopped by exact PID, rest not run.
- P Mac ssh timeout ~11:00Z, server survived, no relaunch (no duplicate).
- C Mac tool 10-min timeout killed client, BensPC exited no-output, not relaunched.
- T OOM whole-chat (4.62 GiB alloc, 0 free, 40.92 GiB PyTorch) — lane-2 fail does not stop others.
- Exit codes P/Pm/Pg/Rb 0 inferred from wrote+no-traceback+clean exit (P Mac monitor dropped, noted).

What it means / doesn’t mean (high-school plain):
- The Windows line-ending fix works: smoke and all finished files have 0 \r\n, seals pass, sleep log perfect 272/272.
- The main agent (P) finished all its real work: 1986 answers + bare 1986 + 300 MMLU + 300 GSM8K. That part is solid.
- We did NOT finish the comparison: plain whole-chat (T) crashes the GPU (too much memory), closed (C) got killed, rivals Q2/L12 never finished. So we can’t say if P beats anyone yet.
- BM25 short-context (Rb) finished 1986 fine — long context is the OOM cause, not the model size.
- Nothing was trained, no test questions quoted, only counts. Need a next run for missing arms (or shorter-context/plain-general arms) to get a PASS/FAIL.
