# uw-2 ADDENDUM-3 condition met: Reading facts agreed (recorded 2026-09-27 10:27 UTC)

ADDENDUM-3 (sealed 9af58f2ac) is in force only if Reading facts agrees in writing. Reading facts owns lis-320.
It answered by cross-session message, queued at 10:20:11 UTC on 09-27. Its words:

> "yes, the early cut is fine as you wrote it. Nothing later is planned to drop rows."

It added two notes. Neither is a reason to wait.

1. resume_clean's rule for a reply repeated 3 times is applied to all rows so far. A later chunk could, in principle,
   repeat an early reply a third time and so drop it from DATA.md. Pilot 8 had 0 repeats.
   - scripts/claude_uw2_cut.py already runs resume_clean on exactly chunks 1 to K. It writes resume_clean's counts to
     resume_clean.json beside CUT.json, and they are reported.
2. A casing addendum for DATA.md is still pending. It may re-case a few name labels; pilot 8 re-cased 0 of 415.
   - The cut uses the labels as check_we3 writes them at cut time. A later re-casing is not applied to uw-2.
   - If Reading facts sends before and after counts, they are reported beside the card counts.

Chunk 1 is worded with luna2 at 3 calls. Chunks from 2 on use luna3 (the same prompt, plus retry logging) at 6 calls.
The writer and the row format are the same either way.
