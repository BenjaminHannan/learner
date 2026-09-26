COMMON RULES (the "Creative answers in chat" thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: no (Mac CPU only). GLM 5.3 Flash through Ben's opencode route (scripts/claude_glm_opencode.py): $0 in money, no key is read or handled by anything here. At most 4 calls at once (the route is shared with lis-320). NO RENTALS.
TIME CAP: 3 hours in total. The answer step stops itself at 140 minutes; report "partial" with the counts if it does.
DUPLICATE GUARD, before anything else: stop with DUPLICATE if artifacts/claude-k1h-20260926/glm exists on origin/builder-outbox or origin/main.

YOUR TASK: k1h-glm. GLM writes more practice chats and one answer to every practice chat. These answers are what the thread will train its creative writer on (k1h; no training here). The thread wrote the code: run it, never edit it. If something breaks, copy back what exists and report the exact error and traceback.
Never open, print or quote the chats or answers in your report (counts only). They are GLM's words, and the thread checks them blind.

1. Put these origin/main files in a new temp dir with `git archive origin/main scripts/claude_k1h_glm.py scripts/claude_k1e_teacher.py scripts/claude_glm_opencode.py scripts/claude_cre333d_agent.py scripts/claude_chat338_agent.py scripts/claude_cre333_agent.py scripts/claude_cre333b_agent.py artifacts/claude-k1e-20260926/train/items.jsonl | tar -x -C <tmp>` and run everything from there with `uv run --offline --no-project --python 3.12 python -B` (standard library only; install nothing).
2. python -B scripts/claude_k1h_glm.py selftest   -> must print "k1h glm selftest 3/3 ok", else stop.
3. python -B scripts/claude_k1h_glm.py chats --existing artifacts/claude-k1e-20260926/train/items.jsonl --out O --calls 36 --workers 4 > chats-log.txt 2>&1
   -> its last line is one JSON line with "chats" (expected about 600 to 700). If "chats" is below 300, stop and report it with the log.
4. python -B scripts/claude_k1h_glm.py answer --items artifacts/claude-k1e-20260926/train/items.jsonl --items O/chats.jsonl --out O --workers 4 --max-minutes 140 > answer-log.txt 2>&1
   -> its last line is one JSON line (items, answered, failed, not_started, minutes, stopped_early).
5. Count "\r\n" in O/chats.jsonl and O/answers.jsonl (a byte count only; expected 0), and `wc -l` both.
6. Copy O (chats.jsonl, answers.jsonl) into the worktree as artifacts/claude-k1h-20260926/glm/, and chats-log.txt and answer-log.txt as artifacts/claude-k1h-20260926/glm/logs/ (force-add; artifacts/ is git-ignored). Check that the sha256 of each copy matches the temp dir's.
7. REPORT.md in artifacts/claude-k1h-20260926/glm/: counts only. Include the selftest line, both JSON lines, the wc and "\r\n" counts, the start and end times (UTC, from `date -u`), and every deviation. Quote no chat and no answer.
PUSH: artifacts/claude-k1h-20260926/glm
