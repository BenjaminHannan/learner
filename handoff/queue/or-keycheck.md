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
GPU: no (Mac CPU only; network calls only, about 2 minutes).

YOUR TASK: check that Ben's new OpenRouter key file works, without ever exposing the key. Written by the sleep research thread, 2026-09-24.
KEY RULES: the key lives ONLY in ~/.config/openrouter/key. Never print it, echo it, log it, copy it, commit it, or put it on a command line (process lists are visible). Pass it to curl only through a config read from stdin, e.g.
  printf 'header = "Authorization: Bearer %s"\n' "$(cat ~/.config/openrouter/key)" | curl -sS -K - <url>
Never print full HTTP headers or request dumps. If any output you are about to write contains the characters "sk-or", stop and write KEY-LEAK-RISK instead.

1. File: report whether ~/.config/openrouter/key exists, its byte count (wc -c <), whether it starts with the 6 characters "sk-or-" (yes/no only), and its permissions (stat -f %Lp). If missing or empty, report NO-KEY-FILE and stop.
2. Key status: GET https://openrouter.ai/api/v1/key with the key. Report the HTTP status and only these fields: limit, limit_remaining, usage, is_free_tier. A 401 means the key is wrong or revoked: report BAD-KEY and stop.
3. Prices (no key needed): GET https://openrouter.ai/api/v1/models. Report (a) every model id containing "glm" with its prompt and completion price per million tokens and context length; (b) the 12 cheapest paid text models with context >= 32000, by prompt+completion price, same fields. Do not call any model in this step.
4. One tiny call: POST https://openrouter.ai/api/v1/chat/completions with the key, model = the id from 3a whose name contains both "glm" and "flash" with the highest version number (if none, the cheapest paid model from 3b), max_tokens 5, messages [{"role":"user","content":"Reply with the single word ok."}]. Report the model id, HTTP status, the reply text, and usage/cost fields if present. Make exactly one call.
5. Write artifacts/or-keycheck-20260924/REPORT.md: verdict first (WORKS / NO-KEY-FILE / BAD-KEY / CALL-FAILED), then the numbers above. No key material anywhere.
PUSH: artifacts/or-keycheck-20260924/REPORT.md
