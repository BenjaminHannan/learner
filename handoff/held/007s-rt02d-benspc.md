COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti 16 GB; one job at a time). Queue ONLY after 007r-02dr-benspc has finished (the Director releases it). $0, no rental.
DISK: 1
TIME CAP: 3 hours wall. If reached: stop by exact PID, copy back what exists, report "partial".

YOUR TASK: rt02d-benspc, THE REGISTERED RUN rt-02d (marks: artifacts/claude-rt02d-20260926/PASSMARKS-rt02d.md + ADDENDUM-rt02d.md). Chat route to the slept puzzle skill. TEST-ONLY, never open, print or quote: artifacts/claude-panel-rt02d-20260926 (only claude_rt02d.py run/score read it). Each registered process is launched ONCE.
DUPLICATE: if artifacts/claude-rt02d-20260926/run exists on origin/builder-outbox, stop with DUPLICATE.

SETUP (same machine facts as origin/main:handoff/queue/006k-02c-benspc.md SETUP: Python, env vars, BASE, git-bash sha256sum, nohup+disown, native Windows paths):
- W0 = C:/Users/benja/lis301/work/e2e02c (0.2c's tree; READ-ONLY). W = C:/Users/benja/lis301/work/rt02d (NEW folder).
- On BensPC copy W0/tree to W/tree (local copy; nothing staged on the Mac). Then stream from origin/main straight to BensPC (`git show origin/main:<path>` piped over ssh, nothing written on the Mac): scripts/claude_rt02d.py, scripts/claude_readersha_wrap.py, artifacts/claude-rt02d-20260926/ (PASSMARKS-rt02d.md, ADDENDUM-rt02d.md, SEAL-marks.sha256.txt, SEAL-code-rt02d.sha256.txt), artifacts/claude-panel-rt02d-20260926/ (all 5 files; copy only, never open).
- From W/tree: `sha256sum -c artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt`, `sha256sum -c artifacts/claude-rt02d-20260926/SEAL-code-rt02d.sha256.txt`, and inside artifacts/claude-panel-rt02d-20260926 `sha256sum -c SEAL-panel.sha256.txt`: all OK. `python -B scripts/claude_rt02d.py --selftest` prints 55/55 and `python -B scripts/claude_readersha_wrap.py --selftest` prints 9/9. Any failure: stop.
- READER319 = C:/Users/benja/lis319/work/run/merged; SHA319 = e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76.
- ADAPTER = W/tree/artifacts/claude-e2e02c-20260926/run/sleep/adapter02c.pt: sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5 and adapter02c.json next to it. Mismatch or missing: stop.
- Nothing else of ours on the GPU before step 1.

Every command below runs from W/tree with env READER_SHA=SHA319 SLEEP02C_ADAPTER=ADAPTER and the prefix
  PFX = python -B scripts/claude_readersha_wrap.py scripts/claude_twinb_wrap.py scripts/claude_rt02d.py run --model READER319 --gen-model BASE --out OUT
OUT = artifacts/claude-rt02d-20260926/run; PD = artifacts/claude-panel-rt02d-20260926. Arms: B0 = --arm claude_e2e02c:build_02c, B1 = --arm claude_rt02d:build_rt02d, B1off = --arm claude_rt02d:build_rt02d_off.

STEPS
1. DEV GATE (not registered): PFX --task dev --arm claude_e2e02c:build_02c --name B0a, then the same with --name B0b. Compare dev_B0a.jsonl and dev_B0b.jsonl replies with a one-line Python check (these are my dev cases, not a panel; you may read them). If any reply differs: stop with NONDETERMINISTIC, report how many differ, run nothing else.
2. Panel (registered, each ONCE): PFX --task puzzles --panel-dir PD for B0, B1, B1off (--name B0 / B1 / B1off with their arms).
3. Negatives (registered, ONCE): PFX --task negatives --panel-dir PD with B1.
4. No harm (registered, each ONCE): PFX --task general with B0 and B1; PFX --task chatdev --panel-dir artifacts/claude-panel382-dev-20260925/chat with B0 and B1.
5. Score: `python -B scripts/claude_rt02d.py score --out OUT --panel-dir PD --score artifacts/claude-rt02d-20260926/score`. Put its one printed line in RESULTS.
6. Copy back to the Mac (small files only; never the adapter or weights), check sizes and sha256.
7. RESULTS-benspc.md in artifacts/claude-rt02d-20260926/: setup checks, the dev gate result, rows/routed per run (the one JSON line each run prints), the score line, wall time per step, VRAM peak if logged. Never open or quote puzzles_*, negatives_* rows or the panel files.
PUSH to builder-outbox: artifacts/claude-rt02d-20260926/RESULTS-benspc.md artifacts/claude-rt02d-20260926/run artifacts/claude-rt02d-20260926/score
