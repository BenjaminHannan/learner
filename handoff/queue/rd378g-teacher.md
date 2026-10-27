COMMON RULES (the "Trustworthy notes" thread, Claude, wrote this task on 2026-09-26 16:58 UTC). Get every file with `git fetch -q origin main` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts.
GPU: no (Mac CPU only; about 40 writing calls and about 240 grading calls to OpenRouter GLM 5.3 Flash; no rental). Ben chose "Use GLM" at 16:39:45 UTC 09-26; Thread manager ruling 16:53: the note writer is retrained with no Claude-written or Claude-judged row. The model is the script default z-ai/glm-5.3-flash.

YOUR TASK: rd378g-teacher (read origin/main:artifacts/claude-rd378g-20260926/PASSMARKS.md): GLM writes 240 practice dialogs with memory notes, then GLM grades every note. No training, no GPU. Code: scripts/claude_rd378g_teacher.py and scripts/claude_rd378k_teacher.py (read their docstrings). Run them, never edit them; if something breaks, stop and report the exact error.
KEY RULES: the key lives ONLY in ~/.config/openrouter/key. The scripts read it themselves. Never print, echo, log, copy or commit it; never put it on a command line. If any output you are about to write contains "sk-or", stop and write KEY-LEAK-RISK instead.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl.
ORDER: this job may run at the same time as rd378k-teacher (both only call OpenRouter).

1. COMMIT=$(git log -1 --format=%H origin/main -- artifacts/claude-rd378g-20260926/SEAL.sha256.txt). `git archive $COMMIT scripts artifacts/claude-rd378g-20260926 | tar -x -C <tmp>` and run from there (python via `uv run --offline --no-project --python 3.12 python -B`; standard library only). Report COMMIT.
2. SEAL: `shasum -a 256 -c artifacts/claude-rd378g-20260926/SEAL.sha256.txt` must print OK for all 14 lines, else stop with SEAL-MISMATCH and every line.
3. python -B scripts/claude_rd378g_teacher.py selftest   -> "rd378g teacher selftest 1/1 ok"; python -B scripts/claude_rd378k_teacher.py selftest -> "rd378k teacher selftest 3/3 ok"; else stop.
4. WRITE: `python -B scripts/claude_rd378g_teacher.py writenotes --out artifacts/claude-rd378g-20260926/glm` (prints one JSON line at the end).
5. GRADE in 4 parallel parts (each part is its own process under nohup with its own log):
   python -B scripts/claude_rd378g_teacher.py split --file artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl --parts 4
   for i in 0 1 2 3: python -B scripts/claude_rd378k_teacher.py label --judge-in artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl.$i --out artifacts/claude-rd378g-20260926/glm/lab$i
   Wait for all four, then `cat artifacts/claude-rd378g-20260926/glm/lab{0,1,2,3}/labels.jsonl > artifacts/claude-rd378g-20260926/glm/judge_w1.jsonl`, and report `wc -l` of it and the number of non-assistant turns in notes_w1.jsonl (turns that have a "notes" key).
6. Copy into the worktree: artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl, artifacts/claude-rd378g-20260926/glm/judge_w1.jsonl, and the console output of steps 3-5 (all logs) as artifacts/claude-rd378g-20260926/teacher-log.txt (check it for "sk-or" first). Do NOT copy the .0-.3 part files or the lab* folders. Report every printed JSON line verbatim, wall time per step, and the total cost_usd.
PUSH: artifacts/claude-rd378g-20260926/glm artifacts/claude-rd378g-20260926/teacher-log.txt
