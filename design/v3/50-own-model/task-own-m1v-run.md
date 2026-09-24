COMMON RULES (the director, Claude, wrote this task on 2026-09-24). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
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
INDEPENDENCE: never open or read items of any TEST-ONLY panel, any artifacts/claude-*panel* folder, artifacts/claude-own-bench-20260923, or any convbench-f0 file. New files only. Never check out branches in the worktree; get a copy of the code for the GPU machine with `git archive origin/main`.
GPU: yes

YOUR TASK: builder for own-M1v, the mouth's sample-first decoding run, on BensPC (RTX 5070 Ti). No training. Artifacts go in artifacts/claude-own-m1v-20260924/. The own-model / mouth thread (Opus) wrote and sealed all the code. Run it and never edit it. If something breaks, stop and report the exact error.
READ FIRST: artifacts/claude-own-m1v-20260924/PASSMARKS.md.
1. SEAL. On the Mac worktree, after git fetch, run `shasum -a 256 -c artifacts/claude-own-m1v-20260924/SEAL-code.sha256.txt` against origin/main's files (use `git archive origin/main` into a temp dir if the worktree is behind). Every line must be OK, otherwise stop.
2. WEIGHTS on BensPC. The own-M1n mouth is on the Mac at ~/premonition-models/own-m1n-mouth/merged/. Copy that folder to BensPC (e.g. C:/Users/benja/own-m1n/merged) with scp via `ssh benspc`, unless it is already there. Check that model.safetensors has sha256 de12daf488e462814caa6c9de23603aae22326b26060525b2b534f08c4b1564a on BensPC. Use the lis-301 venv on BensPC (it has torch + transformers), or make a new venv with torch, transformers >= 5.6 and safetensors.
3. CODE on BensPC. `git archive origin/main scripts/claude_own_m1v_speak.py scripts/claude_own_m1_speak.py scripts/claude_own_m1_common.py artifacts/claude-own-m0b-20260923/dev.jsonl` → copy to BensPC and extract, keeping the paths.
4. RUN ONCE on BensPC's GPU. From the extracted root, run:
   python scripts/claude_own_m1v_speak.py --model <merged dir> --data artifacts/claude-own-m0b-20260923/dev.jsonl --out dev_out.jsonl --samples 4 --seed 1
   Save the printed JSON summary as dev_summary.json. One run only: no re-runs and no other seeds. Then free the GPU (the process exits).
5. Copy dev_out.jsonl and dev_summary.json back to artifacts/claude-own-m1v-20260924/ on the Mac. On the Mac, run the fresh recount for Pm1v.2: for every row with a non-null reply, run the sealed slot_check (scripts/claude_own_m1_common.py) on raw[tries-1]; the number of failures must be 0. Report it.
6. RESULTS-run.md: counts only.
   - Pm1v.1 spoke / 1000;
   - Pm1v.2 recount failures;
   - Pm1v.3 distinct slotted replies and the top reply count, with the top 5 quoted;
   - Pm1v.5 crashes;
   - the try histogram;
   - median / p90 ms;
   - device.
   Do NOT grade grammar (Pm1v.4): the mouth thread runs the blind graders on dev_out.jsonl after you push it. Quote 10 random filled replies (dev material, fictional names).
PUSH: artifacts/claude-own-m1v-20260924/dev_out.jsonl artifacts/claude-own-m1v-20260924/dev_summary.json artifacts/claude-own-m1v-20260924/RESULTS-run.md
