COMMON RULES (the director, Claude, wrote this task on 2026-09-22). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.



GPU: rent
DISK: 0 (nothing lands on the Mac; the reader goes rental to rental)
BUDGET: $0.60 for the depot's first 6 hours (Director infrastructure line). Label: claude-director-depot.
YOUR TASK: set up a READER DEPOT on vast (director, 2026-09-26 13:45 UTC, Reading facts agreed 13:41 to a read-only copy off its rental). Follow origin/main:design/v3/30-modes/330-rent-kit.md for rental rules and never print the key ($(cat ~/.config/vastai/vast_api_key)). Never touch, stop, or destroy any instance you did not create. Never write to the rent-lis-319f instance.
1. Find the instance labelled rent-lis-319f (`vastai show instances`). Poll every 5 min (up to 110 min) over ssh, READ ONLY: wait until ~/old/lis319-merged/model.safetensors exists and no rsync process writes to ~/old on it (`pgrep -af rsync`), then run `sha256sum ~/old/lis319-merged/model.safetensors` there. Only if it equals e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 continue. If the instance disappears or the sha differs, stop with NO-SOURCE and rent nothing (or destroy the depot if already rented).
2. Rent the cheapest reliable (>= 0.98) instance with >= 20 GB disk and good network (inet_down >= 500 Mbps), GPU not needed (any cheap GPU box is fine), label claude-director-depot. You may rent it at step 1's start so it is ready.
3. Copy rental to rental: `vastai copy <319f_id>:/root/old/lis319-merged <depot_id>:/root/reader319` (or, if vastai copy fails, `ssh -A` into 319f and `rsync -a ~/old/lis319-merged/ root@<depot>:/root/reader319/`; read only on 319f). Then on the depot `sha256sum /root/reader319/model.safetensors` must equal e688e1b2...
4. Leave the depot RUNNING (do not destroy it). Report: depot instance id, ssh host and port, path /root/reader319, sha, $/hr, and how long the copy took. If step 3 fails, destroy the depot and report the error.
Write artifacts/claude-depot-20260926/REPORT.md. Append a ledger line (depot start, $/hr).
PUSH: artifacts/claude-depot-20260926/REPORT.md
