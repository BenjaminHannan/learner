STATUS: HELD. Waiting on the Thread manager's word (critic option on Ben's creative card). The "Creative answers in chat" thread moves this file to handoff/queue/ only then. Do not run it from here.

COMMON RULES (the "Creative answers in chat" thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts.
GPU: no (Mac CPU only; about 40 network calls to OpenRouter, well under $0.20).

YOUR TASK: k1e-teacher-c: one change to how GLM labels the 1B's creative drafts, chosen on half of DEV and checked once on the other half (phase 1 failed the label rule: 121 of 157, needs 85%). No training here. Code: scripts/claude_k1e_teacher_c.py (read its docstring). Run it, never edit it; if it breaks, stop and report the exact error.
KEY RULES: the key lives ONLY in ~/.config/openrouter/key. The script reads it itself. Never print, echo, log, copy or commit it; never put it on a command line. If any output you are about to write contains "sk-or", stop and write KEY-LEAK-RISK instead.
1. Put these origin/main files in a temp dir with `git archive origin/main scripts/claude_k1e_teacher.py scripts/claude_k1e_teacher_c.py artifacts/claude-k1e-20260926/dev | tar -x -C <tmp>`, and run from there (python via uv run --offline --no-project --python 3.12 python -B; standard library only). D = artifacts/claude-k1e-20260926/dev, O = artifacts/claude-k1e-20260926/teacher-c:
   python -B scripts/claude_k1e_teacher_c.py selftest     -> "k1e teacher-c selftest 3/3 ok", else stop
   python -B scripts/claude_k1e_teacher_c.py split --packet D/packet_dev.jsonl --key D/key_dev.json --out O     -> must print {"chats": 40, "chats_A": 20, "lines_A": 78, "lines_B": 79}, else stop
   python -B scripts/claude_k1e_teacher_c.py label --packet O/packet_A.jsonl --how high --out O/A_high
   python -B scripts/claude_k1e_teacher_c.py label --packet O/packet_A.jsonl --how vote3 --out O/A_vote3
   python -B scripts/claude_k1e_teacher_c.py choose --dir O --key D/key_dev.json --verdicts D/verdicts_dev.json
   Then, with C = the "chosen" value it printed (high or vote3), and only for that one:
   python -B scripts/claude_k1e_teacher_c.py label --packet O/packet_B.jsonl --how C --out O/B_C
   python -B scripts/claude_k1e_teacher_c.py check --dir O --key D/key_dev.json --verdicts D/verdicts_dev.json
2. Copy O (everything in it) into the worktree as artifacts/claude-k1e-20260926/teacher-c, and the console log as artifacts/claude-k1e-20260926/teacher-c-log.txt. Report every printed JSON line.
PUSH: artifacts/claude-k1e-20260926/teacher-c artifacts/claude-k1e-20260926/teacher-c-log.txt
