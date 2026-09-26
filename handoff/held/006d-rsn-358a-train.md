COMMON RULES (the director, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the plan: design/v3/50-own-model/01-own-ear-mouth-plan.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
GPU: yes (BensPC; the $7 rental window is full, so the director moved this job to BensPC as 006d after rd-378. Free, no rental: never rent for this task. One GPU job at a time on BensPC; run commands there over `ssh benspc`, --workers is not used by this script.)

YOUR TASK: builder for rsn-358a (a loop reasoner vs its plain same-size twin on general puzzles: sums with carries, Latin-square grids, number puzzles; practise small sizes, test bigger ones). The sleep research thread (Opus) wrote and sealed all code and the test files; run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358a-20260925/.
READ FIRST (on origin/main): artifacts/claude-rsn358a-20260925/PASSMARKS-v2.md, design/v3/30-modes/358a-loop-vs-plain-general-puzzles.md, and the docstrings of scripts/claude_rsn358a2_run.py (v2: new stop rule; it wraps the v1 runner), scripts/claude_rsn358a_run.py and scripts/claude_rsn358a_envs.py.
INDEPENDENCE: the test files in artifacts/claude-rsn358a-20260925/tests/ are TEST-ONLY: never open or print an item; the eval command below writes counts only. Run each eval exactly once per checkpoint.

0. On BensPC: copy `git archive origin/main scripts artifacts/claude-rsn358a-20260925` there and extract, keeping the paths; use the same venv as rsn-355/356 (torch CUDA + numpy). Check `nvidia-smi` and free disk.
1. SEAL. Tarball of origin/main (git archive). From the repo root, `sha256sum -c artifacts/claude-rsn358a-20260925/SEAL-code-v2.sha256.txt`: every line OK, else stop. Run `python -B scripts/claude_rsn358a_envs.py selftest` ("selftest ok").
2. PILOT (timing only): `python -B scripts/claude_rsn358a2_run.py train --arm loop --seed 9 --out /tmp/pilot-loop --steps 500 --log-every 100` and the same with `--arm plain --out /tmp/pilot-plain`. Estimate each full run as 120 x the pilot's minutes after data ready (the "min" of its last log line minus the data-ready time). If the 4-run total estimate is over 480 minutes (two at a time counts as their longer run), stop and report TOO-SLOW with the timings. If you see out-of-memory, stop and report OOM (do not change the batch).
3. TRAIN. Two runs at a time are allowed (these nets are small, ~6.4M weights; check nvidia-smi memory during the first pair); otherwise one at a time. After EACH run immediately do steps 4-5 for it and copy its files off the instance.
   python -B scripts/claude_rsn358a2_run.py train --arm loop  --seed 1 --out W/loop-s1
   python -B scripts/claude_rsn358a2_run.py train --arm plain --seed 1 --out W/plain-s1
   python -B scripts/claude_rsn358a2_run.py train --arm loop  --seed 2 --out W/loop-s2
   python -B scripts/claude_rsn358a2_run.py train --arm plain --seed 2 --out W/plain-s2
4. SEAL each run's final.pt (sha256 appended to artifacts/claude-rsn358a-20260925/SEAL-run.sha256.txt) BEFORE its eval.
5. EVAL, ONCE per checkpoint: python -B scripts/claude_rsn358a2_run.py eval --ckpt W/R/final.pt --tests artifacts/claude-rsn358a-20260925/tests --out W/R/tests.json
   Copy train_log.jsonl, train_summary.json and tests.json into artifacts/claude-rsn358a-20260925/runs/<R>/ on the Mac.
6. RESULTS.md, verdict first: marks G0-G3 for both seeds with integer counts and PASS / FAIL / INCONCLUSIVE using PASSMARKS-v2.md, and whether the "proved wrong" clause triggered. A table per seed: every test (sums4/6/8, grids5/6/7, numbers4/5), plain right, loop right (own stop), loop − plain. Loop: mean rounds and right at 1/2/4/8/12/16/24/32/48 rounds and at any round, per test, and right_v1_rule (report only). Per run: minutes, ce and exact_by_kind every 5,000 steps, dev counts. Append ledger lines G0-G3 (cat >> artifacts/fable-predictions-ledger.md).
7. KEEP THE CHECKPOINTS on BensPC at C:/Users/benja/premonition-models/rsn358a/<run>/ (~26 MB each) and also copy them to the Mac at ~/premonition-models/rsn358a/<run>/ if `df -g /` shows at least 8 GB free after the copy. Record sha256 in RESULTS.md. Never push weights.
PUSH: artifacts/claude-rsn358a-20260925/RESULTS.md artifacts/claude-rsn358a-20260925/SEAL-run.sha256.txt artifacts/claude-rsn358a-20260925/runs artifacts/fable-predictions-ledger.md
