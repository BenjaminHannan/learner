COMMON RULES (the "Trustworthy notes" thread, Claude, wrote this task on 2026-09-27 03:57 UTC). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts.
GPU: no. Mac CPU only; 1-3 pilot calls, then about 21-63 long calls to GPT-6 Luna through Ben's Codex plan via the Director's helper, $0 per run. ONE process; no opencode, no OpenRouter, no rental. It may run at the same time as 006-rd378k-gate3luna.
LOAD-LIGHT: yes (network-bound: each Luna call runs remotely through the Codex CLI; locally only python plus one codex process per call)

YOUR TASK: rd378g-writeluna. First read origin/main:artifacts/claude-rd378g-20260926/ADDENDUM-D.md, then ADDENDUM-F.md, then ADDENDUM-I.md. It runs a one-batch format pilot, and only if the pilot passes, writes with Luna the 21 practice batches that were lost to GLM route failures, then tags every dialog with its writer. No training, no GPU. Code: scripts/claude_luna_run.py, scripts/claude_luna_codex.py, scripts/claude_rd378g_writemore_oc.py, scripts/claude_rd378g_teacher.py and scripts/claude_rd378g_tagwriter.py (read their docstrings). Run them, never edit them; if something breaks, stop and report the exact error. The writing script writes its file only at the end and has no resume. Run it once under nohup with its own log and poll the log. Never start a second copy while one runs (check `ps`).
LUNA RULES: never read, print or copy anything under ~/.codex or any Codex / ChatGPT config, auth file or key; the helper handles the route.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rd378g-20260926/glm2N/notes_w1.jsonl or artifacts/claude-rd378g-20260926/pilot-luna/pilot-log.txt.

1. COMMIT=$(git log -1 --format=%H origin/main -- artifacts/claude-rd378g-20260926/SEAL-ADD-I.sha256.txt). Run `git archive $COMMIT scripts artifacts/claude-rd378g-20260926 | tar -x -C <tmp>`. Then, with mkdir -p first:
   - `git show origin/builder-outbox:scripts/claude_glm_opencode.py > <tmp>/scripts/claude_glm_opencode.py`;
   - `git show origin/builder-outbox:scripts/claude_glm_opencode_v11.py > <tmp>/scripts/claude_glm_opencode_v11.py`;
   - `git show origin/builder-outbox:artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl > <tmp>/artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl`.
   Run everything from <tmp> (python via `uv run --offline --no-project --python 3.12 python -B`; standard library only). Report COMMIT.
2. SEAL: `shasum -a 256 -c` on these files in artifacts/claude-rd378g-20260926/:
   - SEAL-ADD-I.sha256.txt (5 OK)
   - SEAL-ADD-F.sha256.txt (1 OK)
   - SEAL-ADD-E.sha256.txt (3 OK)
   - SEAL-ADD-D.sha256.txt (4 OK)
   Anything else: stop with SEAL-MISMATCH and every line.
3. python -B scripts/claude_luna_run.py --check -> "luna bound ok"; python -B scripts/claude_luna_run.py scripts/claude_rd378g_writemore_oc.py selftest -> ends "rd378g writemore selftest 1/1 ok"; python -B scripts/claude_rd378g_tagwriter.py selftest -> "rd378g tagwriter selftest 1/1 ok"; else stop.
4. PILOT: python -B scripts/claude_luna_run.py scripts/claude_rd378g_writemore_oc.py write --have artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl --batches 18 --out artifacts/claude-rd378g-20260926/pilot-luna
   Save its console output as artifacts/claude-rd378g-20260926/pilot-luna/pilot-log.txt and report its JSON line verbatim.
   - PILOT PASS: the log has a "batch 18 ok" line and 0 "call failed" lines. Go on to step 5.
   - Otherwise: stop with PILOT-FAIL, and do not run steps 5-6. Still do step 7 for pilot-log.txt only.
   Never copy the pilot's notes_w1.jsonl.
5. WRITE: python -B scripts/claude_luna_run.py scripts/claude_rd378g_writemore_oc.py write --have artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl --batches 18-20,22-39 --out artifacts/claude-rd378g-20260926/glm2N   (prints one JSON line at the end)
6. TAG: python -B scripts/claude_rd378g_tagwriter.py tag --have artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl --in artifacts/claude-rd378g-20260926/glm2N/notes_w1.jsonl --out artifacts/claude-rd378g-20260926/glm2N/notes_w1_tagged.jsonl   (prints one JSON line)
7. Copy into the worktree:
   - artifacts/claude-rd378g-20260926/pilot-luna/pilot-log.txt;
   - if step 5 ran: glm2N/notes_w1.jsonl and glm2N/notes_w1_tagged.jsonl, plus the console output of steps 3 and 5-6 as glm2N/teacher-log.txt.
   Report both JSON lines verbatim, wall time per step, and the number of "call failed" lines in each log.
PUSH: artifacts/claude-rd378g-20260926/glm2N artifacts/claude-rd378g-20260926/pilot-luna/pilot-log.txt
