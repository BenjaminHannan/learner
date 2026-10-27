COMMON RULES (the Benchmarks thread, Claude, wrote this task on 2026-09-27 06:13 UTC). Follow the first 14 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, at most 4 parallel processes, report in your final reply). Get files with `git fetch -q origin main builder-outbox` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths).
GPU: no (Mac CPU; GPT-6 Luna calls through Ben's Codex plan via scripts/claude_luna_codex.py, $0 extra; about 1,580 calls plus retries: 1,382 sessions and one question call per kept chat). No opencode, no GLM, no OpenRouter, no reader, no rental, no BensPC. Label: bm398w-luna. TIME CAP: 7 hours in total; at it, stop every command still running by exact PID, go to step 10 and report PARTIAL with the steps finished. DISK: 1.
LOAD-LIGHT: yes
KEY RULES: never read, print, copy or commit anything under ~/.codex, any config or auth file, or any key. The helper never touches them.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox already has artifacts/claude-bm398w-20260927/data/RESULTS-data.md.
WHY: artifacts/claude-bm398w-20260927/PLAN.md (on origin/main, sealed in SEAL.sha256.txt). Ben 03:47 UTC: Luna may write training data. Code plans every chat; Luna words the sessions and the questions with short answers; code checks every reply. Nothing is trained or judged here.
SHELL LIMIT: each word/ask command below starts no new call after 45 minutes and caps each call at 12 minutes, so it ends inside your 80-minute command limit; rerun it as written (it resumes and gives failed sessions one more try).
THE PANEL IS TEST-ONLY: never open, print, count by content, summarise or quote anything under $O/panel. Only the counts printed by the commands below may be reported.

1. TREE: D=$(mktemp -d); git archive origin/main scripts artifacts/claude-bm398w-20260927 artifacts/claude-lis320-20260926/avoid_names_dev.txt artifacts/claude-lis320-20260926/avoid_test.sha256 | tar -x -C $D; cd $D; O=artifacts/claude-bm398w-20260927/data; mkdir -p $O/train $O/panel.
   PY means `uv run --offline --no-project --python 3.12 python -B` (standard library only; no torch); under zsh write it out in full. export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1.
   AV="--avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256"
2. SEAL: `shasum -a 256 -c artifacts/claude-bm398w-20260927/SEAL.sha256.txt` (every line OK, else stop with SEAL-MISMATCH and run nothing).
3. CHECKS: `$PY scripts/claude_bm398w_data.py selftest` must end "BM398W-DATA-SELFTEST PASS 35/35". Record `uptime` and `df -g /`.
4. PLANS (code only):
   $PY scripts/claude_bm398w_data.py plan --seed 3993 --n 170 $AV --out $O/train/plans.jsonl
   $PY scripts/claude_bm398w_data.py plan --seed 3994 --n 26 $AV --avoid-plans $O/train/plans.jsonl --out $O/panel/plans.jsonl
   `shasum -a 256` must give 16341e5447f600f353f20102669701c371f697881aa4f749a3d46b73a74bbc2a (train) and 0cccc54a3664099d8bfd18c37330a09062ec44fede90b008d34e6fb6ca14b8bf (panel). Any mismatch: stop with PLAN-MISMATCH.
5. PILOT (W=3 unless the Director's current Luna share says otherwise; record W and why):
   $PY scripts/claude_bm398w_data.py word --plans $O/train/plans.jsonl --out $O/train/sess.jsonl --workers $W --max-minutes 45 --max-failed 20 --limit 5
   Rerun it until a run prints "skipped" equal to "jobs", at most 3 runs in all. Then
   $PY scripts/claude_bm398w_data.py count --plans $O/train/plans.jsonl --sess $O/train/sess.jsonl --limit 5
   GATE: "kept_chats" must be at least 3. Else stop with PILOT-FAIL: copy back (step 10) and report every printed line.
6. PANEL SESSIONS: the same word command with --plans $O/panel/plans.jsonl --out $O/panel/sess.jsonl and no --limit; rerun until "skipped" equals "jobs", at most 4 runs. Then count (no --limit).
7. TRAINING SESSIONS: the word command of step 5 without --limit (it skips the pilot's kept sessions). Rerun until a run prints "skipped" equal to "jobs" or 8 runs in all, whichever comes first. Then count (no --limit).
8. QUESTIONS: for train and then panel:
   $PY scripts/claude_bm398w_data.py ask --plans $O/X/plans.jsonl --sess $O/X/sess.jsonl --out $O/X/qa.jsonl --workers $W --max-minutes 45 --max-failed 20
   (X = train, then panel); rerun each until "skipped" equals "jobs", at most 3 runs each. Then count with --qa.
9. BUILD (code only):
   $PY scripts/claude_bm398w_data.py build --plans $O/train/plans.jsonl --sess $O/train/sess.jsonl --qa $O/train/qa.jsonl --out $O/train/build
   $PY scripts/claude_bm398w_data.py build --panel --plans $O/panel/plans.jsonl --sess $O/panel/sess.jsonl --qa $O/panel/qa.jsonl --out $O/panel/build
   FLOOR: each build prints "floor": "OK" (exit 0) or "DATA-SHORT" (exit 3). On DATA-SHORT, report DATA-SHORT (still copy back).
10. COPY BACK: copy $O (train/ and panel/, every file) into artifacts/claude-bm398w-20260927/data/ of your worktree (force-add; artifacts/ is git-ignored) and write RESULTS-data.md there: every printed JSON line verbatim, in order, with its command and start/end time (UTC); W and why; the GATE and FLOOR results; `shasum -a 256` of every file under data/ (counts and hashes only; never Luna's text). Then rm -rf "$D" (exact path) and confirm it is gone.
PUSH: artifacts/claude-bm398w-20260927/data
