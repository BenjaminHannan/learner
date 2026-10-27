COMMON RULES (the "Trustworthy notes" thread, Claude, wrote this task on 2026-09-26 16:50 UTC). Get every file with `git fetch -q origin main` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts.
GPU: no (Mac CPU only; about 60-70 network calls to OpenRouter, well under $1; no rental). Ben chose "Use GLM" at 16:39:45 UTC 09-26 (Thread manager card; goals page 5f38f110e): nothing a model trains on is written or judged by Claude, so GLM 5.3 Flash writes the practice dialogs and grades the note writer's notes; the model is the script default z-ai/glm-5.3-flash.

YOUR TASK: rd378k-teacher, phase 1 of rd-378k (read origin/main:artifacts/claude-rd378k-20260926/PASSMARKS.md): (a) label gate: does the teacher grade the note writer's notes like the blind judges did, and (b) the teacher writes 160 practice dialogs. No training, no GPU. Code: scripts/claude_rd378k_teacher.py (read its docstring). Run it, never edit it; if it breaks, stop and report the exact error.
KEY RULES: the key lives ONLY in ~/.config/openrouter/key. The script reads it itself. Never print, echo, log, copy or commit it; never put it on a command line. If any output you are about to write contains "sk-or", stop and write KEY-LEAK-RISK instead.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rd378k-20260926/glm/dialogs.jsonl.

1. COMMIT=$(git log -1 --format=%H origin/main -- artifacts/claude-rd378k-20260926/SEAL.sha256.txt). Put the files in a temp dir with `git archive $COMMIT scripts artifacts/claude-rd378k-20260926 artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl | tar -x -C <tmp>` and run from there (python via `uv run --offline --no-project --python 3.12 python -B`; standard library only). Report COMMIT.
2. SEAL: `shasum -a 256 -c artifacts/claude-rd378k-20260926/SEAL.sha256.txt` must print OK for all 16 lines, else stop with SEAL-MISMATCH and every line.
3. Run, in this order, each printing one JSON line at the end:
   python -B scripts/claude_rd378k_teacher.py selftest        -> "rd378k teacher selftest 3/3 ok", else stop
   python -B scripts/claude_rd378k_teacher.py label --judge-in artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl --only-hash 3 --out artifacts/claude-rd378k-20260926/gate
   python -B scripts/claude_rd378k_teacher.py agree --labels artifacts/claude-rd378k-20260926/gate/labels.jsonl --verdicts artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl
   python -B scripts/claude_rd378k_teacher.py write --out artifacts/claude-rd378k-20260926/glm
   (run write even if agree prints "passes_label_rule": false). Keep the whole console output of all four as the log.
4. Copy into the worktree: artifacts/claude-rd378k-20260926/gate/labels.jsonl, artifacts/claude-rd378k-20260926/glm/dialogs.jsonl, and the console log as artifacts/claude-rd378k-20260926/teacher-log.txt (check it for "sk-or" first). Report every printed JSON line verbatim, the wall time of each command, and the total cost_usd.
PUSH: artifacts/claude-rd378k-20260926/gate artifacts/claude-rd378k-20260926/glm artifacts/claude-rd378k-20260926/teacher-log.txt
