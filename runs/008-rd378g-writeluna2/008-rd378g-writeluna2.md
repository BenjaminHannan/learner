COMMON RULES (the "Trustworthy notes" thread, Claude, wrote this task on 2026-09-27 06:45 UTC). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts.
GPU: no. Mac CPU only; 2 timing calls in parallel, then about 21-63 long calls (one at a time) to GPT-6 Luna through Ben's Codex plan, $0 per run; no opencode, no OpenRouter, no rental. It may run at the same time as 006-rd378k-gate3luna.
LOAD-LIGHT: yes (network-bound: each Luna call runs remotely through the Codex CLI; locally only python plus one codex process per call)

YOUR TASK: rd378g-writeluna2. First read origin/main:artifacts/claude-rd378g-20260926/ADDENDUM-I.md, then ADDENDUM-J.md. A timing check picks the Codex setting by a fixed rule; then Luna writes the 21 practice batches that were lost to route failures, and every dialog is tagged with its writer. No training, no GPU. Code: scripts/claude_rd378g_lunadiag.py, scripts/claude_luna_run2.py, scripts/claude_luna_effort.py, scripts/claude_luna_codex.py, scripts/claude_rd378g_writemore_oc.py, scripts/claude_rd378g_teacher.py and scripts/claude_rd378g_tagwriter.py (read their docstrings). Run them, never edit them; if something breaks, stop and report the exact error. The writing script writes its file only at the end and has no resume. Run it once under nohup with its own log and poll the log. Never start a second copy while one runs (check `ps`).
LUNA RULES: never read, print or copy anything under ~/.codex or any Codex / ChatGPT config, auth file or key. Never print any reply text; the scripts print counts only.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rd378g-20260926/glm2N/notes_w1.jsonl or artifacts/claude-rd378g-20260926/glm2N/diag-log.txt.

1. COMMIT=$(git log -1 --format=%H origin/main -- artifacts/claude-rd378g-20260926/SEAL-ADD-J.sha256.txt). Run `git archive $COMMIT scripts artifacts/claude-rd378g-20260926 | tar -x -C <tmp>`. Then, with mkdir -p first:
   - `git show origin/builder-outbox:scripts/claude_glm_opencode.py > <tmp>/scripts/claude_glm_opencode.py`;
   - `git show origin/builder-outbox:scripts/claude_glm_opencode_v11.py > <tmp>/scripts/claude_glm_opencode_v11.py`;
   - `git show origin/builder-outbox:artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl > <tmp>/artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl`.
   Run everything from <tmp> (python via `uv run --offline --no-project --python 3.12 python -B`; standard library only). Report COMMIT.
2. SEAL: `shasum -a 256 -c` on these files in artifacts/claude-rd378g-20260926/:
   - SEAL-ADD-J.sha256.txt (7 OK)
   - SEAL-ADD-I.sha256.txt (5 OK)
   - SEAL-ADD-F.sha256.txt (1 OK)
   - SEAL-ADD-E.sha256.txt (3 OK)
   - SEAL-ADD-D.sha256.txt (4 OK)
   Anything else: stop with SEAL-MISMATCH and every line.
3. Each of these must end as shown; else stop:
   - python -B scripts/claude_luna_run2.py --check -> "luna2 bound ok";
   - python -B scripts/claude_luna_run2.py --effort low --timeout 600 scripts/claude_rd378g_writemore_oc.py selftest -> ends "rd378g writemore selftest 1/1 ok";
   - python -B scripts/claude_rd378g_tagwriter.py selftest -> "rd378g tagwriter selftest 1/1 ok";
   - python -B scripts/claude_rd378g_lunadiag.py selftest -> ends "rd378g lunadiag selftest 1/1 ok".
4. TIMING CHECK: python -B scripts/claude_rd378g_lunadiag.py run --have artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl --settings low:600,default:1200
   It prints 2 JSON lines. Save its console output as artifacts/claude-rd378g-20260926/glm2N/diag-log.txt and report both lines verbatim.
5. CHOOSE (ADDENDUM-J's rule):
   - the "low" line has "pass": true -> EFFORT=low, TIMEOUT=600;
   - else the "default" line has "pass": true -> EFFORT=default, TIMEOUT=1500;
   - else stop with DIAG-FAIL, and do not run steps 6-7. Still do step 8 for diag-log.txt only.
   Report the choice.
6. WRITE: python -B scripts/claude_luna_run2.py --effort $EFFORT --timeout $TIMEOUT scripts/claude_rd378g_writemore_oc.py write --have artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl --batches 18-20,22-39 --out artifacts/claude-rd378g-20260926/glm2N   (prints one JSON line at the end)
7. TAG: python -B scripts/claude_rd378g_tagwriter.py tag --have artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl --in artifacts/claude-rd378g-20260926/glm2N/notes_w1.jsonl --out artifacts/claude-rd378g-20260926/glm2N/notes_w1_tagged.jsonl   (prints one JSON line)
8. Copy into the worktree:
   - artifacts/claude-rd378g-20260926/glm2N/diag-log.txt;
   - if step 6 ran: glm2N/notes_w1.jsonl and glm2N/notes_w1_tagged.jsonl, plus the console output of steps 3, 6 and 7 as glm2N/teacher-log.txt.
   Report every JSON line verbatim, wall time per step, and the number of "call failed" lines in the step 6 log.
PUSH: artifacts/claude-rd378g-20260926/glm2N
