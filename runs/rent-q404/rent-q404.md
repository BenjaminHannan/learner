COMMON RULES (the Month-end thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: rent
BUDGET: $1.20 for this whole task, re-rents included, from Month-end's $2 (Ben, 12:59 UTC 09-26). Label: claude-monthend-q404. Needs READER319 and the 0.2c ADAPTER. Re-run the offer search before every create.
DISK: 1
TIME CAP: 3 hours on the rental. If reached: stop by exact PID, copy back what exists, destroy, report "partial".
HELD until Month-end writes artifacts/claude-q404-20260926/ADDENDUM-q404-route.md (after 383's verdict) saying Q404_ROUTE=1 or 0, then moves this file to queue.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-q404-20260926/run, or a live instance is labelled claude-monthend-q404.

YOUR TASK: q-404, THE REGISTERED RUN (marks: artifacts/claude-q404-20260926/PASSMARKS-q404.md and ADDENDUM-q404-route.md; read them). TEST-ONLY, never open, print or quote: artifacts/claude-panel-q404-20260926 (only scripts/claude_q404.py run/score read it). Run the code; never edit it. Each registered process is launched ONCE.

SETUP: exactly S1-S5 of origin/main:handoff/queue/rent-rt02d.md (code tree streamed, kit C models, sleep base checkpoint, READER319 from the Director's depot with the Mac fallback and the sha e688e1b2... check, ADAPTER a33211dc... with its json), with this task's label and budget. If rent-rt02d or 007r's rental is live at the same time, ask the Director whether to share it (only after their runs exit, separate OUT).
S6. From ~/tree: `sha256sum -c artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt`, `sha256sum -c artifacts/claude-q404-20260926/SEAL-code-q404.sha256.txt`, inside artifacts/claude-panel-q404-20260926 `sha256sum -c SEAL-panel.sha256.txt`: all OK. `python -B scripts/claude_q404.py --selftest` prints 24/24 and `python -B scripts/claude_readersha_wrap.py --selftest` prints 9/9. Any failure: destroy and stop.

Every command runs from ~/tree under nohup/setsid with its own log, one at a time, with env READER_SHA=e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 SLEEP02C_ADAPTER=ADAPTER Q404_ROUTE=<value from ADDENDUM-q404-route.md> CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONUTF8=1 HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 and the prefix
  PFX = python -B scripts/claude_readersha_wrap.py scripts/claude_twinb_wrap.py scripts/claude_q404.py run --model ~/reader319 --gen-model BASE --out artifacts/claude-q404-20260926/run --panel-dir artifacts/claude-panel-q404-20260926
STEPS
1. DEV GATE (not registered; my dev cases, you may read them): PFX --task dev --arm claude_q404:build_b --name Ba, then --name Bb. If any reply in dev_Ba.jsonl differs from dev_Bb.jsonl: copy both back, destroy, stop with NONDETERMINISTIC.
2. Registered, each ONCE: PFX --task math --arm claude_q404:build_b --name B; PFX --task math --arm claude_q404:build_q --name Q; PFX --task self --arm claude_q404:build_q --name Q.
3. Score: `python -B scripts/claude_q404.py score --out artifacts/claude-q404-20260926/run --panel-dir artifacts/claude-panel-q404-20260926 --score artifacts/claude-q404-20260926/score`. Put its printed line in RESULTS.
4. Copy back to the Mac (small files only; never the adapter, reader or weights): run/, score/, step logs as logs/; check sizes and sha256 on both ends BEFORE destroying. Destroy and confirm it's gone.
5. RESULTS-rent.md in artifacts/claude-q404-20260926/: setup checks, reader source and time, dev gate, the JSON line each run prints, the score line, wall time per step, GPU, instance id, hours, cost. Counts only: never open or quote math_*/self_* rows or the panel.
PUSH to builder-outbox: artifacts/claude-q404-20260926/RESULTS-rent.md artifacts/claude-q404-20260926/run artifacts/claude-q404-20260926/score artifacts/claude-q404-20260926/logs
