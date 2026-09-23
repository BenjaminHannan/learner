COMMON RULES (the research thread, Claude, wrote this task on 2026-09-23). You are a helper agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
- Additive only: create new files; never edit or delete an existing file. Never touch the repo-root notebook/. No secrets; never print config files that may hold keys.
- Run Python with: uv run --no-project --python 3.12 --with pypdf python -B <script> (plain python3 under bash may be a broken x86 binary).
- Check `df -g /` first; stop and report if free disk is under 3 GB.
- Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.

YOUR TASK: download research papers and save them as plain text, for reading by the research thread. Ben has allowed web access for this (2026-09-23). Papers only; the text is reading material and must never be used as training data. No GPU, no models, no Qwen.

Folder: artifacts/claude-papers-20260923/ (create it).
For each arXiv ID below:
1. curl -sSL -o artifacts/claude-papers-20260923/<ID>.pdf https://arxiv.org/pdf/<ID>   (use the ID with "/" replaced by "_" in file names).
2. Convert it to text with pypdf (all pages, page breaks marked "=== page N ==="), saved as artifacts/claude-papers-20260923/<ID>.txt.
3. Delete the .pdf after a successful conversion (it is your own new file). Keep each .txt under 4 MB; if one is bigger, keep the first 4 MB and say so.
IDs: 2112.08542 2309.11495 2102.09690 2011.01675 2407.18370 2403.03208 2006.04702 2308.03279 2305.07759 cs/0006023
If a download fails, retry once after 10 s; then record it as failed and go on.
Write artifacts/claude-papers-20260923/INDEX.md: one line per ID with title (first line of the text), page count, text size in KB, and OK or FAILED with the reason.
Final reply: the INDEX table, then PAPERS-DONE. Time limit 20 minutes.
PUSH: artifacts/claude-papers-20260923
