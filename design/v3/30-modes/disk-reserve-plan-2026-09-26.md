# Watcher disk reserve (director, 2026-09-26 02:20 UTC) — queued for after tonight's runs

Evidence (artifacts/claude-diskcheck-20260926/REPORT.md on builder-outbox): Mac 20 GB free at 01:56 UTC.
Recent growers: rental copy-backs of merged models (2 GB each: rd378-notes, rd371-verifier, lis318, lis319),
~/.codex thread_history (1.2 GB, outside this project), the 15 GB card-experiment worktree.

Change (one, after 11:00 UTC 09-26, not mid-run):
1. Job files may carry `DISK: <GB>` = expected peak local disk (copy-backs included). Default 3 if absent.
2. watcher.sh launch gate: require free >= 5 + sum(DISK of running jobs) + DISK(new job); else log and hold.
3. Rental kits copy back adapters + per-item results, not merged 2 GB models, unless the task names the model as a deliverable.
Candidate cleanup needing Ben's yes: rd371-verifier-merged, lis318-merged (nothing current loads them; move to Trash, never rm).
