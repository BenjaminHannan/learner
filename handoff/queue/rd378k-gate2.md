COMMON RULES (the "Trustworthy notes" thread, Claude, wrote this task on 2026-09-26 17:35 UTC). Get every file with `git fetch -q origin main` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts.
GPU: no (Mac CPU only; about 60-80 calls to OpenRouter GLM 5.3 Flash, well under $0.10; no rental). Ben chose "Use GLM" at 16:39:45 UTC 09-26.

YOUR TASK: rd378k-gate2 (read origin/main:artifacts/claude-rd378k-20260926/PASSMARKS-C.md): the label gate measured again with the fixed labeller (at most 7 graded turns per call). No training, no GPU. Code: scripts/claude_rd378k_teacher2.py and scripts/claude_rd378k_teacher.py (read their docstrings). Run them, never edit them; if something breaks, stop and report the exact error.
KEY RULES: the key lives ONLY in ~/.config/openrouter/key. The scripts read it themselves. Never print, echo, log, copy or commit it; never put it on a command line. If any output you are about to write contains "sk-or", stop and write KEY-LEAK-RISK instead.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rd378k-20260926/gate2/labels.jsonl.

1. COMMIT=$(git log -1 --format=%H origin/main -- artifacts/claude-rd378k-20260926/SEAL-ADD-C.sha256.txt). `git archive $COMMIT scripts artifacts/claude-rd378k-20260926 artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl | tar -x -C <tmp>` and run from there (python via `uv run --offline --no-project --python 3.12 python -B`; standard library only). Report COMMIT.
2. SEAL: `shasum -a 256 -c artifacts/claude-rd378k-20260926/SEAL-ADD-C.sha256.txt` (2 OK) and `shasum -a 256 -c artifacts/claude-rd378k-20260926/SEAL.sha256.txt` (16 OK), else stop with SEAL-MISMATCH and every line.
3. python -B scripts/claude_rd378k_teacher2.py selftest -> "rd378k teacher2 selftest 1/1 ok", else stop.
4. python -B scripts/claude_rd378k_teacher2.py label --judge-in artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl --only-hash 3 --out artifacts/claude-rd378k-20260926/gate2
5. python -B scripts/claude_rd378k_teacher.py agree --labels artifacts/claude-rd378k-20260926/gate2/labels.jsonl --verdicts artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl
6. Copy into the worktree: artifacts/claude-rd378k-20260926/gate2/labels.jsonl, artifacts/claude-rd378k-20260926/gate2/failures.jsonl, and the console output of steps 3-5 as artifacts/claude-rd378k-20260926/gate2/teacher-log.txt (check all three for "sk-or" first). Report every printed JSON line verbatim, wall time per step, and cost_usd.
PUSH: artifacts/claude-rd378k-20260926/gate2
