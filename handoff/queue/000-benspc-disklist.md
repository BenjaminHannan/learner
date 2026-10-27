COMMON RULES: READ-ONLY. Delete, move, or edit nothing on BensPC or the Mac. Never open Ben's personal files; list names and sizes only. No GPU use. NEVER WebFetch.
YOUR TASK (Director, 2026-09-27): make a disk inventory of BensPC C: so the Director can propose a clean-up rule for folders our own pipeline made.
WHERE: you run on the Mac. Reach BensPC with `ssh benspc` (PowerShell).
1. `ssh benspc "Get-PSDrive C | Select Used,Free"` and report free GB.
2. For each of C:\ (top level), C:\Users\benja (top level) and C:\tmp* list every folder or file over 50 MB: its full path, size in MB (Get-ChildItem -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum), and LastWriteTime. Also list anything whose name matches rsn*, dl*, k1*, lis*, rv*, qwen*, llama*, *.tar, *-results*, *-logs*, tmp-*, premonition-models, or GPU-BUSY*. Skip AppData, Windows, Program Files*, and ProgramData except for their total size.
3. For each matching item, give its top-level contents (names only, first 15) so it can be matched to a queue job.
Write it all to handoff/replies/000-benspc-disklist.md, laid out as a table.
PUSH: handoff/replies/000-benspc-disklist.md
