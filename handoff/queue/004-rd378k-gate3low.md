COMMON RULES (the "Trustworthy notes" thread, Claude, wrote this task on 2026-09-27 00:24 UTC). It replaces rd378k-gate3oc, which is stopped (see PASSMARKS-I.md). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts.
GPU: no. Mac CPU only; about 120 GLM 5.3 Flash calls at opencode reasoning effort "low" (about 5-15 s each), at most ~350 with retries, through Ben's opencode subscription, $0 per run. ONE process, no parallel parts; no OpenRouter, no rental. It may run at the same time as 005-rd378g-writelow.

YOUR TASK: rd378k-gate3low. Read origin/main:artifacts/claude-rd378k-20260926/PASSMARKS-F.md, then PASSMARKS-H.md, then PASSMARKS-I.md. This is the label gate again on the same 38 dialogs, with every GLM call at reasoning effort low. No training, no GPU. Code: scripts/claude_glm_low_run.py, scripts/claude_glm_opencode_low.py, scripts/claude_lis320_glm_oclow.py, scripts/claude_rd378k_teacher3oc.py, scripts/claude_rd378k_teacher3.py, scripts/claude_rd378k_teacher.py and scripts/claude_glm_opencode_v11.py (read their docstrings). Run them, never edit them; if something breaks, stop and report the exact error.
OPENCODE RULES: never read, print, copy or commit any opencode config, auth file or key. Report `/usr/local/bin/opencode session list -n 1000 --format json` counts (numbers only), run from your worktree root, before and after; delete no session yourself.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rd378k-20260926/gate3low/labels.jsonl.
ORDER GATE: `git fetch` every 60 s, for up to 30 min, until origin/builder-outbox has artifacts/claude-peek-rd378oc2-20260927/REPORT.md; if it never appears, stop with NO-PEEK. Then `ps -axo pid,command | grep claude_rd378k_teacher3oc.py | grep claude_glm_v11_run.py | grep -v grep`: if anything matches, the old gate is still running; stop with OLD-RUNNING. Never kill it yourself.

1. COMMIT=$(git log -1 --format=%H origin/main -- artifacts/claude-rd378k-20260926/SEAL-ADD-I.sha256.txt). `git archive $COMMIT scripts artifacts/claude-rd378k-20260926 artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl | tar -x -C <tmp>`, then `git show origin/builder-outbox:scripts/claude_glm_opencode.py > <tmp>/scripts/claude_glm_opencode.py` and `git show origin/builder-outbox:scripts/claude_glm_opencode_v11.py > <tmp>/scripts/claude_glm_opencode_v11.py`, and run from <tmp> (python via `uv run --offline --no-project --python 3.12 python -B`; standard library only). Report COMMIT.
2. SEAL: `shasum -a 256 -c` on these files in artifacts/claude-rd378k-20260926/:
   - SEAL-ADD-I.sha256.txt (7 OK)
   - SEAL-ADD-H.sha256.txt (1 OK)
   - SEAL-ADD-G.sha256.txt (3 OK)
   - SEAL-ADD-F.sha256.txt (3 OK)
   - SEAL-ADD-E.sha256.txt (2 OK)
   - SEAL-ADD-D.sha256.txt (2 OK)
   - SEAL-ADD-C.sha256.txt (2 OK)
   - SEAL.sha256.txt (15 OK; the ONLY allowed FAILED line is scripts/claude_lis300_train.py, which PASSMARKS-D.md replaces)
   Anything else: stop with SEAL-MISMATCH and every line.
3. python -B scripts/claude_glm_low_run.py --check -> "glm low bound ok"; python -B scripts/claude_glm_low_run.py scripts/claude_rd378k_teacher3oc.py selftest -> ends "rd378k teacher3oc selftest 1/1 ok"; else stop.
3b. LEAK CHECK (one opencode call, before step 4): first `git show origin/main:scripts/claude_glm_leakcheck.py > <tmp>/scripts/claude_glm_leakcheck.py`, then from <tmp>, `python -B scripts/claude_glm_leakcheck.py --worktree <your worktree root, absolute path>` (its sha256 must be 9e3de25929b8c25e7f3547ca6084656494578e4131942a944488d954a87adbb2). Report its JSON line. Exit code 2: stop with ROUTE-FAIL. Exit code 3 (left_after_cleanup above 0): stop with LEAK; do not start step 4.
4. Under nohup with its own log (one process; poll the log; never start a second copy): python -B scripts/claude_glm_low_run.py scripts/claude_rd378k_teacher3oc.py label --judge-in artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl --only-hash 3 --hash-rem 1 --out artifacts/claude-rd378k-20260926/gate3low
5. python -B scripts/claude_rd378k_teacher.py agree --labels artifacts/claude-rd378k-20260926/gate3low/labels.jsonl --verdicts artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl
6. python -B scripts/claude_rd378k_teacher.py agree --labels artifacts/claude-rd378k-20260926/gate3low/labels_passA.jsonl --verdicts artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl   (report only)
7. Copy into the worktree: artifacts/claude-rd378k-20260926/gate3low/labels.jsonl, labels_passA.jsonl, failures.jsonl, and the console output of steps 3-6 as gate3low/teacher-log.txt. Report every printed JSON line verbatim, wall time per step, and the number of "call failed" lines in the log.
PUSH: artifacts/claude-rd378k-20260926/gate3low
