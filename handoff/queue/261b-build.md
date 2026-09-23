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

GETTING YOUR FILES: the director works from GitHub. Run: git fetch -q origin claude/project-thread-p68q5v. Read each file named below with: git show origin/claude/project-thread-p68q5v:<path>. Never check out or merge that branch.
GPU: yes

YOUR TASK: the builder for exp 261b, the one diagnosis-driven follow-up to 261's registered FAIL (261 stays FAIL).
Read these first (via git show): design/v3/30-modes/261b-decision.md (the diagnosis and the ONE change) and handoff/kit/briefs/261-earcheck.txt (261's brief: the ear, checker, BensPC, llama-server and arm setup you reuse). Also read 261's own files in this worktree: artifacts/claude-earcheck261-20260922/PASSMARKS.md and RESULTS.md, and scripts/claude_earcheck261_*.py (read-only; import, never edit).

The one change: 261's sealed arm A (canonicaliser + brake + checker at theta 0.25, prompt B, unchanged) PLUS the mixed-case span guard from the decision note, applied after the checker. The guard only holds back (UNSURE); it never adds or edits a frame. Write the particle list and the value_kind exemptions before the seal, from the relation table v2 and general knowledge only.
Scorer: 261's sealed scorer plus Ruling 1 (a frame whose relation is in the gold relation's table "narrower" list counts as a hit), in a new wrapper file. Nothing else changes.

Before the seal (dev only):
1. Reproduce 261's dev numbers from its sealed files (theta.json sweep at 0.25) to show your pipeline matches.
2. Run the guard on 261's dev (257 dev split + dev_checker.jsonl): report how many kept frames it holds back, by tag, and how many of those were right (false holds). Also write 20+ of your own dev turns with typo words next to names and 20+ all-lowercase turns (own wording) and report the guard on them. Do not tune anything else.
2b. The particle list must include "of" and cover multi-word place names; report false holds on your own dev names with particles (write 15+).
3. Write PASSMARKS.md. It must state that the ONLY model change is the mixed-case hold rule; the narrower-relation rule is a scorer change, sealed with the scorer, and A261 is rescored with the same scorer so the A vs A261 difference is the guard alone. Include a prediction for false holds on R15 particle names (they count toward M3b) with numbered predictions P261b.n, seal (shasum -a 256 > artifacts/claude-earcheck261b-20260923/SEAL.sha256.txt, covering code, PASSMARKS and dev files), append ledger lines (cat >>).
Registered test: the fresh blind panel artifacts/claude-earpanel261b-20260923/ (written in parallel by a blind writer; spec handoff/kit/briefs/earpanel261b-spec.txt). Never open it before your seal. After your seal, poll for its SEAL.sha256.txt every 2 minutes for up to 90 minutes, check it OK from the repo root, run the strict schema check, then run every arm ONCE. Never run earpanel257 or earpanel261 (both are spent or TEST-ONLY).
Arms: A (registered: 261's A + guard), A261 (261's A exactly), A_brake, B (138i + 228 as in 261).
Marks, arm A, same bars as 261: M1 no_save saves <= 1; M2 wrong saves <= 1; M3 exact TEACH recall >= 85% and >= B+30; M3b UNSURE <= 12% of gold TEACH; M4 ASK >= 90%; M5 median ear+checker+guard <= 800 ms; M6 every A frame byte-identical in A261. Also report (no bars): A vs A261 on M1-M4, per family, per tag R1-R15, and each frame the guard held with category only.
Compute: BensPC via ssh benspc, exactly as 261 did. Start llama-server yourself with 261's command and stop it by its exact PID at the end; confirm with nvidia-smi. Never touch pythonw 13036. Waves under 30 min. New files only: scripts/claude_earcheck261b_*.py, artifacts/claude-earcheck261b-20260923/.
Write RESULTS.md laid out like 261's (result first, integer counts, categories only, never quote panel items), then your final reply.
PUSH: artifacts/claude-earcheck261b-20260923 scripts/claude_earcheck261b_*.py artifacts/fable-predictions-ledger.md
