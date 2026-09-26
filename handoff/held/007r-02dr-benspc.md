COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti 16 GB; one job at a time). Queue ONLY after 007b-382b-benspc has finished (the Director releases it). $0, no rental.
DISK: 1
TIME CAP: 2 hours wall. If reached: stop by exact PID, copy back what exists, report "partial".

YOUR TASK: 02dr-benspc, THE REGISTERED RUN 0.2d-r (marks: artifacts/claude-e2e02dr-20260926/PASSMARKS-02dr.md). One arm (X') on bank D, rerun with the right reader weights. TEST-ONLY, never open, print or quote: artifacts/claude-e2e331-bankD-20260925 (only the runner and scorer read it). Run ONCE.
DUPLICATE: if artifacts/claude-e2e02dr-20260926/run exists on origin/builder-outbox, stop with DUPLICATE.

SETUP (same machine facts as origin/main:handoff/queue/006k-02c-benspc.md SETUP: Python, env vars, BASE, git-bash sha256sum, nohup+disown, native Windows paths):
- W0 = C:/Users/benja/lis301/work/e2e02c (0.2c's tree; READ-ONLY, other jobs use it). W = C:/Users/benja/lis301/work/e2e02dr (NEW folder).
- On BensPC, copy W0/tree to W/tree (a local copy on BensPC; nothing staged on the Mac). Then add from origin/main, streamed straight to BensPC (`git show origin/main:<path>` piped over ssh, nothing written on the Mac): scripts/claude_readersha_wrap.py and artifacts/claude-e2e02dr-20260926/ (PASSMARKS-02dr.md, SEAL-02dr.sha256.txt).
- Check, from W/tree, `sha256sum -c artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt` and `sha256sum -c artifacts/claude-e2e02dr-20260926/SEAL-02dr.sha256.txt` all OK and `python -B scripts/claude_readersha_wrap.py --selftest` prints 9/9. Any failure: stop.
- READER301 = C:/Users/benja/lis301/work/run/merged. READER319 = C:/Users/benja/lis319/work/run/merged. SHA319 = e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76.
- ADAPTER = W/tree/artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.pt: check sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5 (and adapter02c.json next to it). Mismatch or missing: stop.
- Before step 2, check free VRAM: nothing else of ours may be on the GPU.

STEPS (from W/tree; OUT = artifacts/claude-e2e02dr-20260926/run; BD = artifacts/claude-e2e331-bankD-20260925):
1. R0 guard (seconds, loads nothing): `READER_SHA=SHA319 python -B scripts/claude_readersha_wrap.py scripts/claude_e2e336_run.py --model READER301` must exit with READER-SHA-MISMATCH. Record its one output line. If it does NOT refuse: stop and report R0 FAIL (step 2 is not run).
2. X', launched ONCE: READER_SHA=SHA319 SLEEP02C_ADAPTER=ADAPTER SLEEPCHECK_STOP=1 SLEEPCHECK_LOG=OUT/sleep_X.jsonl EP382_LOG=OUT/ep382_X.jsonl GRAM360_LOG=OUT/gram360_parts_X.jsonl python -B scripts/claude_readersha_wrap.py scripts/claude_sleepcheck_wrap.py scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --bank BD --out OUT --arm claude_e2e02c:build_02c --name X --model READER319 --gen-model BASE
   Its first output line must be "readersha: reader weights sha256 e688e1b2... match READER_SHA".
3. Score: `git show origin/builder-outbox:artifacts/claude-e2e02c-20260926/run/arm_G.jsonl > W/arm_G_02c.jsonl` and the same for arm_T.jsonl (unread), then `python -B scripts/claude_e2e336_score.py --bank BD --runs OUT/arm_X.jsonl W/arm_G_02c.jsonl W/arm_T_02c.jsonl --out artifacts/claude-e2e02dr-20260926/score`.
4. Copy back to the Mac (small files only, no weights), check sizes and sha256.
5. RESULTS-benspc.md in artifacts/claude-e2e02dr-20260926/: R0 line, step 2's first two lines, rows and lives written, the scorer's mechanical counts per arm and per ask type (counts only, as 006k's RESULTS did), ms median/p90, wall time per step. Never open judge_* files, the bank, or quote any reply.
PUSH to builder-outbox: artifacts/claude-e2e02dr-20260926/RESULTS-benspc.md artifacts/claude-e2e02dr-20260926/run artifacts/claude-e2e02dr-20260926/score
