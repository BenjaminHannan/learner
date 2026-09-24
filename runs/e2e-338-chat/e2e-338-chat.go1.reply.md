Starting the registered exp 338 run — reading the rules and marks first.
The referenced panels and scripts aren't in this worktree — checking the main checkout next.
STOPPED — did not run. Missing inputs, no code touched, no panel opened.

Task requested: e2e-338-chat registered run (exp 338, open conversation).

What I checked (worktree `/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`, `date` Thu Sep 24 07:45 ET):
- `handoff/queue/lis-302-gpu.md` (COMMON RULES source): NOT FOUND — `handoff/` here contains only `HANDOFF.md`, `kit/`, `memory/`, `replies/`; no `queue/` subfolder.
- `handoff/queue/e2e-330-dev.md` (code/model setup source): NOT FOUND, same reason.
- `artifacts/claude-chat338-20260924/PASSMARKS.md`: NOT FOUND — `artifacts/` has only `claude-chatdemo-20260923` and `claude-chatweak-20260923` matching `*chat*`; nothing matching `*338*` or `*panel338*`.
- `artifacts/claude-chatpanel338-20260924` (TEST-ONLY panel): NOT FOUND — never opened/printed/quoted anything.
- Runner code `scripts/claude_chat338_agent.py`, `scripts/claude_chat338_run.py`, `scripts/claude_cre333_agent.py`, `scripts/claude_e2e330_arms.py`, `scripts/claude_lis_stackb.py`, `scripts/claude_lis_e2e_armsb.py`, `scripts/claude_e2e336_run.py`, `scripts/claude_e2e336_twin.py`, `scripts/claude_e2e336_score.py`, `scripts/claude_age334_agent.py`: NOT FOUND — `scripts/` has only `claude_chatdemo_*`; nothing matching `chat338|cre333|e2e330|e2e336|age334|lis_stack|lis_e2e`.
- Same absence confirmed in main checkout `/Users/ben-hannan/Desktop/projects/beautiful-model` (no `handoff/`, no `*338*` in `artifacts/` or `scripts/`).
- Also checked via `git log --oneline -5` (HEAD `063c52c48`) and `git status`: no 338 files staged or untracked.

Exact error: required task files do not exist in this environment, so steps 1–4 (SEAL check, `SEAL-code.sha256.txt`, the four `claude_chat338_run.py` processes, the 336 DEV safety check, `RESULTS-run.md`) cannot be started. This machine is darwin (Mac, no RTX 5070 Ti); GPU steps target BensPC anyway.

Per instructions I did not edit any code, did not create `SEAL-code.sha256.txt` or `RESULTS-run.md`, did not open any TEST-ONLY panel, and did not push anything.

To proceed I need the month-end thread to provide (or point to the repo/worktree containing): `handoff/queue/lis-302-gpu.md`, `handoff/queue/e2e-330-dev.md`, `artifacts/claude-chat338-20260924/PASSMARKS.md`, the sealed `artifacts/claude-chatpanel338-20260924/SEAL.sha256.txt`, and the ten listed `scripts/claude_*.py` files. No arms finished; nothing was started.
