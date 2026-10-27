COMMON RULES (the "Creative answers in chat" thread, Claude, wrote this task on 2026-09-26 20:13 UTC). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Never read or print opencode config, auth or key files. Report in your final reply: verdict first, integer counts, every deviation.
GPU: no (Mac CPU only). GLM 5.3 Flash through Ben's opencode route with GLM helper v1.1: $0 in money. At most 2 GLM calls at once (k1h's share of the opencode budget; the wrapper enforces it). NO RENTALS.
TIME CAP: 8 hours in total. Push what exists if anything stops early.
DUPLICATE GUARD, before anything else: stop with DUPLICATE if artifacts/claude-k1h-20260926/glm exists on origin/builder-outbox or origin/main, or if any process whose command contains claude_k1h_glm is running.

YOUR TASK: k1h-glm2. GLM answers the 240 k1e practice chats, writes about 650 more practice chats, and answers those. These answers are what the thread will train its creative writer on (k1h; no training here). The first try (k1h-glm) was stopped on purpose and made nothing. Read artifacts/claude-k1h-20260926/ADDENDUM-2-route.md first. The thread wrote the code: run it, never edit it. If something breaks, copy back what exists and report the exact error and traceback.
Never open, print or quote a chat or an answer in your report (counts only).

1. Put these origin/main paths in a new temp dir with `git archive origin/main scripts artifacts/claude-k1e-20260926/train/items.jsonl artifacts/claude-k1h-20260926 artifacts/claude-k1f-20260926 artifacts/claude-k1fpanel-20260926/SEAL.sha256.txt | tar -x -C <tmp>` and run everything from there with `uv run --offline --no-project --python 3.12 python -B` (standard library only; install nothing). O = <tmp>/O.
2. Checks, from <tmp>: `shasum -a 256 -c artifacts/claude-k1h-20260926/SEAL-k1h.sha256.txt` (25 OK), `shasum -a 256 -c artifacts/claude-k1h-20260926/SEAL-addendum1.sha256.txt` (2 OK), `shasum -a 256 -c artifacts/claude-k1h-20260926/SEAL-addendum2.sha256.txt` (4 OK). Any other result: stop with SEAL-MISMATCH. Then `python -B scripts/claude_k1h_glm_v11.py selftest` must print "k1h glm selftest 3/3 ok", else stop.
3. `opencode session list -n 1000 | wc -l` (the count only; "sessions before").
4. python -B scripts/claude_k1h_glm_v11.py answer --items artifacts/claude-k1e-20260926/train/items.jsonl --out O --max-minutes 100 > answer1-log.txt 2>&1
5. python -B scripts/claude_k1h_glm_v11.py chats --existing artifacts/claude-k1e-20260926/train/items.jsonl --out O --calls 36 > chats-log.txt 2>&1
   (its last line is one JSON line with "chats"; if it fails or "chats" is 0, report it and still do step 6 with only the first --items)
6. python -B scripts/claude_k1h_glm_v11.py answer --items artifacts/claude-k1e-20260926/train/items.jsonl --items O/chats.jsonl --out O --max-minutes M > answer2-log.txt 2>&1
   with M = 480 minus the minutes used since step 1 began, minus 25 (so the job ends inside its cap).
7. `opencode session list -n 1000 | wc -l` ("sessions after"). Count "\r\n" in O/*.jsonl (byte count only; expected 0) and `wc -l` them.
8. Copy O (chats.jsonl, answers.jsonl) into the worktree as artifacts/claude-k1h-20260926/glm/, and answer1-log.txt, chats-log.txt, answer2-log.txt as artifacts/claude-k1h-20260926/glm/logs/ (force-add; artifacts/ is git-ignored). Check that the sha256 of each copy matches the temp dir's.
9. REPORT.md in artifacts/claude-k1h-20260926/glm/: counts only. Include the seal and selftest lines, every JSON line the three steps printed, the session counts before and after, the wc and "\r\n" counts, start and end times (UTC, `date -u`) of each step, and every deviation. Quote no chat and no answer.
PUSH: artifacts/claude-k1h-20260926/glm
