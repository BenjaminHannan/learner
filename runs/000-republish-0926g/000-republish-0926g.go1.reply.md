Republishing skipped jobs — auditing the outbox and clearing stale markers.
The rules file is missing — I'll note that and proceed under the key constraints from your brief.
Watcher fix confirmed. Now auditing which jobs were skipped by the old publish.
Found a format mismatch — most jobs use `PUSH:` but a few use different wording. Checking the full scope.
Initial scan shows many jobs missing from both locations — verifying the worktree state before deciding what to republish.
Confirmed the key candidates. Now doing a complete audit of all 39 flagged jobs.
Audit complete — 4 jobs need republishing. Verifying edge cases before clearing markers.
Cleanup targets locked in. Removing stale markers and monitoring the republish.
First republish round done — checking whether results actually landed.
Republish didn't land — the watcher can't parse these jobs' push paths. Writing the final report.
FAIL — republish did not land. 0 of 4 missing jobs made it to builder-outbox.

Marks table (integer counts):

| # | Check | Count |
|---|---|---|
| 1 | watcher has `git add -f -- "$p"` in publish() + matches origin/main | 1 / 1 pass |
| 2 | .pushed files modified 09-26 audited | 39 / 39 |
| 2 | already on builder-outbox (counts equal worktree), left alone | 31 / 31 |
| 2 | empty .md, nothing to publish (006m) | 1 / 1 skip |
| 2 | OB-missing but worktree-missing too, left alone (006k-run02c, mu404-run, rd378L) | 3 / 3 skip |
| 2 | OB-missing but worktree-has-files, .pushed removed | 4 / 4 |
| 3 | watcher re-pushed after removal (.pushed recreated) | 4 / 4 |
| 3 | jobs with files now on builder-outbox | 0 / 4 |
| 3 | rent-02dr worktree files (logs 6 + run 4 + score 10 + score-machine 4 + RESULTS 1) | 25 files |
| 3 | rent-02dr OB files after wait | 0 files |
| 3 | rent-02dr sha256 OB-vs-manifest compared / matched | 0 / 0 |
| 3 | rent-sf401 worktree / OB after | 16 / 0 |
| 3 | rent-ch403 worktree / OB after | 9 / 0 |
| 3 | rent-bmrivsmoke worktree / OB after | 7 / 0 |
| PUSH | REPORT.md written (artifacts/claude-republish-20260926g/REPORT.md) | 1 file |

Every move:
- Checked uptime + df (53 GB free), fetched origin/main + builder-outbox.
- Confirmed watcher.sh line 36 fix, diff vs origin/main empty.
- Audited all 39 .pushed (PUSH paths via `artifacts/...` tokens; OB via `git ls-tree -r`, worktree via `find`, names/counts only, no result contents opened).
- Removed exactly 4 markers at 16:08:46Z: rent-02dr.pushed, rent-sf401.pushed, rent-ch403.pushed, rent-bmrivsmoke.pushed.
- Waited ~7 min (to 16:15:39Z); observed watcher rounds 12:09:12-12:09:26 re-push all 4 with "no changes added to commit"; OB stayed 0.
- Wrote REPORT.md (89 lines, new dir, additive-only). Rented nothing.

Every miss:
- rent-02dr: 25 files in worktree, 0 on outbox. Miss by 25.
- rent-sf401: 16 files in worktree, 0 on outbox. Miss by 16 (000-republish-0926f already tried once at 12:04, also 0).
- rent-ch403: 9 files in worktree, 0 on outbox. Miss by 9.
- rent-bmrivsmoke: 7 files in worktree, 0 on outbox. Miss by 7.

Deviations (2):
1. OPUS-RULES.txt not found (task path missing; scratchpad/briefs/ absent, scratchpad empty). Followed the key points quoted in the task.
2. Load-bearing PUSH format mismatch: watcher only reads `^PUSH:` lines, but rent-02dr/sf401/ch403 use `PUSH to builder-outbox:` and bmrivsmoke uses `PUSH (builder-outbox):`. So the 4 re-pushes were empty by design. Fix needs watcher to parse these variants (not done here, additive-only).

What it means / doesn't mean (plain high-school English):
- Think of builder-outbox as the school turn-in bin and .pushed as the "already turned in" sticker. I peeled the sticker off 4 assignments that were never actually in the bin, the helper robot walked by and put new stickers on, but it still didn't put the papers in the bin because it can't read those 4 cover sheets.
- It does NOT mean the work is lost: all 57 files (25+16+9+7) are sitting in the Mac worktree untouched. It does NOT mean the other 31 jobs are broken — they are already in the bin with matching counts.
- It does NOT mean rent-02dr failed: its own reply claims 24/24 hashes matched at copy time; right now the bin just has 0 of its files, so there was nothing to hash-compare (0/0).
