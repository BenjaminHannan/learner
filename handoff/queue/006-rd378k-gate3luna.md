COMMON RULES (the "Trustworthy notes" thread, Claude, wrote this task on 2026-09-27 03:57 UTC). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts.
GPU: no. Mac CPU only; about 12 pilot calls, then about 120 gate calls (at most ~400 with retries) to GPT-6 Luna through Ben's Codex plan via the Director's helper, $0 per run. ONE process, no parallel parts; no opencode, no OpenRouter, no rental. It may run at the same time as 007-rd378g-writeluna.
LOAD-LIGHT: yes (network-bound: each Luna call runs remotely through the Codex CLI; locally only python plus one codex process per call)

YOUR TASK: rd378k-gate3luna. First read origin/main:artifacts/claude-rd378k-20260926/PASSMARKS-F.md, then PASSMARKS-H.md, then PASSMARKS-K.md. It runs a small format pilot on 4 training dialogs, and only if the pilot passes, the label gate on the same 38 dialogs, with every call going to Luna. No training, no GPU. Code: scripts/claude_luna_run.py, scripts/claude_luna_codex.py, scripts/claude_rd378k_teacher3oc.py, scripts/claude_rd378k_teacher3.py and scripts/claude_rd378k_teacher.py (read their docstrings). Run them, never edit them; if something breaks, stop and report the exact error.
LUNA RULES: never read, print or copy anything under ~/.codex or any Codex / ChatGPT config, auth file or key; the helper handles the route.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rd378k-20260926/gate3luna/labels.jsonl or artifacts/claude-rd378k-20260926/pilot-luna/pilot-log.txt.

1. COMMIT=$(git log -1 --format=%H origin/main -- artifacts/claude-rd378k-20260926/SEAL-ADD-K.sha256.txt). Run `git archive $COMMIT scripts artifacts/claude-rd378k-20260926 artifacts/claude-rd378g-20260926 artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl | tar -x -C <tmp>`. Then, with mkdir -p first:
   - `git show origin/builder-outbox:scripts/claude_glm_opencode.py > <tmp>/scripts/claude_glm_opencode.py` (only for the seal check in step 2);
   - `git show origin/builder-outbox:artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl > <tmp>/artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl`.
   Run everything from <tmp> (python via `uv run --offline --no-project --python 3.12 python -B`; standard library only). Report COMMIT.
2. SEAL: `shasum -a 256 -c` on these files in artifacts/claude-rd378k-20260926/:
   - SEAL-ADD-K.sha256.txt (5 OK)
   - SEAL-ADD-H.sha256.txt (1 OK)
   - SEAL-ADD-F.sha256.txt (3 OK)
   - SEAL-ADD-E.sha256.txt (2 OK)
   - SEAL-ADD-D.sha256.txt (2 OK)
   - SEAL-ADD-C.sha256.txt (2 OK)
   - SEAL.sha256.txt (15 OK; the ONLY allowed FAILED line is scripts/claude_lis300_train.py, which PASSMARKS-D.md replaces)
   Also `shasum -a 256 artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl` must start 87a51358fa2bdedaaf0edafeb273074e.
   Anything else: stop with SEAL-MISMATCH and every line.
3. python -B scripts/claude_luna_run.py --check -> "luna bound ok"; python -B scripts/claude_luna_run.py scripts/claude_rd378k_teacher3oc.py selftest -> ends "rd378k teacher3oc selftest 1/1 ok"; else stop.
4. PILOT: python -B scripts/claude_luna_run.py scripts/claude_rd378k_teacher3oc.py label --judge-in artifacts/claude-rd378g-20260926/glm/notes_w1.jsonl --only-hash 12 --hash-rem 0 --out artifacts/claude-rd378k-20260926/pilot-luna
   Save its console output as artifacts/claude-rd378k-20260926/pilot-luna/pilot-log.txt and report its JSON line verbatim.
   - PILOT PASS: "dialogs" is 4, "unparsed" is 0 and "failed_calls" is at most 2. Go on to step 5.
   - Otherwise: stop with PILOT-FAIL, and do not run steps 5-7. Still do step 8 for pilot-log.txt only.
   Never open or copy the pilot's labels files.
5. GATE, under nohup with its own log (one process; poll the log; never start a second copy): python -B scripts/claude_luna_run.py scripts/claude_rd378k_teacher3oc.py label --judge-in artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl --only-hash 3 --hash-rem 1 --out artifacts/claude-rd378k-20260926/gate3luna
6. python -B scripts/claude_rd378k_teacher.py agree --labels artifacts/claude-rd378k-20260926/gate3luna/labels.jsonl --verdicts artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl
7. python -B scripts/claude_rd378k_teacher.py agree --labels artifacts/claude-rd378k-20260926/gate3luna/labels_passA.jsonl --verdicts artifacts/claude-rd371b-20260926/data/judge_train_out.jsonl   (report only)
8. Copy into the worktree:
   - artifacts/claude-rd378k-20260926/pilot-luna/pilot-log.txt;
   - if step 5 ran: artifacts/claude-rd378k-20260926/gate3luna/labels.jsonl, labels_passA.jsonl and failures.jsonl, plus the console output of steps 3 and 5-7 as gate3luna/teacher-log.txt.
   Report every printed JSON line verbatim, wall time per step, and the number of "call failed" lines in each log.
PUSH: artifacts/claude-rd378k-20260926/gate3luna artifacts/claude-rd378k-20260926/pilot-luna/pilot-log.txt
