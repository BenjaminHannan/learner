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
GPU: yes (BensPC RTX 5070 Ti; one job at a time). SHORT: about 10 GPU minutes (arm V runs the calculator arm 5 times). TIME WINDOW: start only between 08:00 and 18:00 ET (BensPC nights are reserved); if you are outside it, do nothing and reply WAIT. Hard cap 60 minutes, and never past 20:00 ET.

YOUR TASK: rsn-299b-panel, the REGISTERED run of rsn-299b (think five times, then vote). Run once. Never edit code. The reasoning thread wrote and sealed everything.
INDEPENDENCE: never open, print or quote any item of artifacts/claude-thinkpanel299b-20260924/ (TEST-ONLY). Report only the numbers the score command prints, plus counts computed from the run files (no question or answer text).
GETTING THE CODE: a fresh `git archive origin/main` copied to BensPC; run from its root. `sha256sum -c artifacts/claude-rsn299b-20260924/SEAL-code.sha256.txt` and `sha256sum -c artifacts/claude-thinkpanel299b-20260924/SEAL.sha256.txt`: every line OK, else stop. `python -B scripts/claude_rsn299_tool.py` prints "selftest ok". `python -B scripts/claude_rsn299b_run.py mock` runs without error.
MODEL: BASE = openbmb/MiniCPM5-1B via huggingface_hub.snapshot_download("openbmb/MiniCPM5-1B", local_files_only=True) in the lis-301 venv (as in rsn-299-panel). Record the commit hash; it must be the same as in rsn-299-panel.
RUN (once each, one after the other):
   python -B scripts/claude_rsn299b_run.py run --arm P --model BASE --items artifacts/claude-thinkpanel299b-20260924/items.jsonl --out OUT/panel-P.jsonl
   python -B scripts/claude_rsn299b_run.py run --arm V --model BASE --items artifacts/claude-thinkpanel299b-20260924/items.jsonl --out OUT/panel-V.jsonl
   python -B scripts/claude_rsn299b_run.py score --items artifacts/claude-thinkpanel299b-20260924/items.jsonl --p OUT/panel-P.jsonl --t OUT/panel-V.jsonl --out OUT/panel-score.json
   OUT = artifacts/claude-rsn299b-20260924/run. Copy OUT back to the Mac worktree and check the files arrived.
RESULTS.md in artifacts/claude-rsn299b-20260924/: verdict first; P299b.1-P299b.3 with integer counts and PASS/FAIL, from panel-score.json; right/unsure/wrong for both arms, total and per category; how many V rows had fewer than 3 of 5 votes (count rows where vote.votes < 3); median seconds per item per arm; model commit hash; GPU name; every deviation.
PUSH: artifacts/claude-rsn299b-20260924/run artifacts/claude-rsn299b-20260924/RESULTS.md
