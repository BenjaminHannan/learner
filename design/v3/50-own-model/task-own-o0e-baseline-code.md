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

GETTING YOUR FILES: run git fetch -q origin main and read the plan with git show origin/main:design/v3/50-own-model/01-own-ear-mouth-plan.md. Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
INDEPENDENCE: other own-model builders run in parallel. Never open artifacts/claude-own-* folders other than your own, and never open any TEST-ONLY panel or artifacts/claude-*panel* folder. New files only; scripts are named scripts/claude_own_<yourtask>_*.py. Time limit 30 minutes unless stated. Fictional names only.

YOUR TASK: builder for own-O0e, the PLAIN-TRANSFORMER BASELINE CODE (plan §7, §7.1). CPU only; plain torch. Artifacts: artifacts/claude-own-o0e-20260923/.
Build scripts/claude_own_o0e_model.py: decoder-only, 12 blocks, width 640, SwiGLU MLP width 1,600, RMSNorm, rotary, 8,192 tied embeddings, context 1,024. PARAMETER AUDIT: it must print 61,783,680 (report the exact number; if the code gives a different count explain every difference).
Build scripts/claude_own_o0e_serialize.py: turns a teach/ask/correct dialogue (list of turns with gold facts, the format is up to you but documented) into training text for three arms: B-plain (the conversation only), B-RAG (conversation + top-k taught sentences found by plain word-overlap search, no learned parts, inserted before each question), B-notebook (conversation + the current notebook rows as text before each question). Also a greedy answer extractor used identically for every arm.
Build scripts/claude_own_o0e_train.py: resume-safe trainer (atomic checkpoints every 10 min, restart loop, deterministic data order), bf16 on CUDA.
Tests on the Mac CPU: the audit; a kill test at a tiny width (params identical after resume); a <= 10-minute smoke on 200 toy dialogues you generate inside this task showing the loss falls and all three serializations round-trip; a throughput estimate from a 2-minute CPU run (report only).
Marks (sealed before tests): Pown0e.1 audited count = 61,783,680 +/- 0.2%; Pown0e.2 kill test identical; Pown0e.3 serializations include no gold answer text in any question prompt (checked on all 200 toy dialogues).
PUSH: artifacts/claude-own-o0e-20260923 scripts/claude_own_o0e_model.py scripts/claude_own_o0e_serialize.py scripts/claude_own_o0e_train.py artifacts/fable-predictions-ledger.md
