# Republish 2026-09-26g — REPORT

Task: republish every job whose results were skipped by the old publish (director, 16:18 UTC 09-26).
Run from: /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
Times (UTC): audit 16:00-16:08, removed 4 markers at 16:08:46Z, watcher rounds observed 16:09-16:15, final check 16:15:39Z (about 7 min wait).
Rent: 0. Deleted only *.pushed marker files (4). No result file contents opened (names and counts only; sha256 compared as hashes, match counts only).

## 1. Watcher fix confirmed

Running watcher script has the fix in publish():
- File: ~/premonition-watch/watcher.sh, line 36 contains `git add -f -- "$p"`.
- It matches origin/main:handoff/kit/mimo/watcher.sh exactly (diff empty, fetched 16:0x UTC).
- Running watcher PIDs observed (multiple subshells); main watcher active throughout.

## 2. Audit: 39 <job>.pushed modified 2026-09-26

Method: for each .pushed, extracted artifact paths from any PUSH line in <job>.md
(`grep PUSH | grep -o 'artifacts/[^ )(",;]*'`), then
`git ls-tree -r origin/builder-outbox -- <path>` (OB count) vs worktree file count
(`find $W/<path> -type f | wc -l`). Ledger path checked but not decisive alone.

Result:
- 34 jobs: every PUSH path already on builder-outbox with counts equal to worktree. Left alone (0 removed).
  000-adapters-0926d (1), 000-credit-0926b (1+1), 000-instances-0926c (1),
  000-probe-007b (1+1), 000-push-rd371b (7 files), 000-zdl4-0926e (1),
  005u-rsn-358c1-stop (1+4), 006h-lis-319c-full (8), 006i-rd-371b-train (10),
  007b-382b-benspc (1+24+38+23), claude-sleep-358b2 (1+5),
  lis319k-devbank-mac-r2 (4), lis319k-devbank-mac (4), lis319k-panel-mac (3),
  lis319t2-panel-mac (2), rent-0y1f (3+1), rent-358d (1+16+1), rent-358i (1+32+1),
  rent-bm391 (1+5), rent-bm397t (1+4), rent-brd7 (4+1), rent-brd8 (4+1),
  rent-depot (1), rent-grab358i (1), rent-k1a (1+21), rent-lis-319f (16 files + ledger),
  rent-mu402 (1+9), rent-y1d (3+1), rent-zdl3 (3+1), rent-zdl4 (3+1), rent-zdl4b (3+1).
- 1 job with empty .md (no PUSH lines, nothing to publish): 006m-rsn-358f-flow. Left alone.
- 3 jobs with PUSH paths missing on OB but also missing in worktree (nothing to republish from this Mac, likely still running elsewhere or failed): 006k-02c-benspc (run02c only), rent-mu404 (run only), rent-rd378L (all 3 paths). Left alone (0 removed).
- 4 jobs with PUSH paths missing on OB but present in worktree: REMOVED their .pushed (4 files):
  rent-02dr, rent-sf401, rent-ch403, rent-bmrivsmoke.

Removed at 16:08:46Z (4):
- rent-02dr.pushed (was 11:35)
- rent-sf401.pushed (was 12:04; second touch after 000-republish-0926f's 12:02 removal + 12:04 re-push)
- rent-ch403.pushed (was 12:02)
- rent-bmrivsmoke.pushed (was 11:40)

## 3. After wait: files now on builder-outbox (final 16:15:39Z)

All counts via `git ls-tree -r origin/builder-outbox -- <path> | wc -l`. Worktree counts via find.

| job | PUSH path | worktree files | OB files before | OB files after (16:15Z) |
|---|---|---|---|---|
| rent-02dr | artifacts/claude-e2e02dr-20260926/RESULTS-rent.md | 1 | 0 | 0 |
| rent-02dr | artifacts/claude-e2e02dr-20260926/run | 4 | 0 | 0 |
| rent-02dr | artifacts/claude-e2e02dr-20260926/score | 10 | 0 | 0 |
| rent-02dr | artifacts/claude-e2e02dr-20260926/score-machine | 4 | 0 | 0 |
| rent-02dr | artifacts/claude-e2e02dr-20260926/logs | 6 | 0 | 0 |
| rent-02dr total | (5 paths) | 25 (24 data + 1 RESULTS) | 0 | 0 |
| rent-sf401 | artifacts/claude-sf401-20260926/RESULTS-rent.md | 1 | 0 | 0 |
| rent-sf401 | artifacts/claude-sf401-20260926/run | 8 | 0 | 0 |
| rent-sf401 | artifacts/claude-sf401-20260926/score | 7 | 0 | 0 |
| rent-sf401 total | (3 paths) | 16 | 0 | 0 |
| rent-ch403 | artifacts/claude-ch403-20260926/RESULTS-rent.md | 1 | 0 | 0 |
| rent-ch403 | artifacts/claude-ch403-20260926/run | 2 | 0 | 0 |
| rent-ch403 | artifacts/claude-ch403-20260926/dev | 6 | 0 | 0 |
| rent-ch403 total | (3 paths) | 9 | 0 | 0 |
| rent-bmrivsmoke | artifacts/claude-bmriv-smoke-20260926/RESULTS-rent.md | 1 | 0 | 0 |
| rent-bmrivsmoke | artifacts/claude-bmriv-smoke-20260926/run | 6 | 0 | 0 |
| rent-bmrivsmoke total | (2 paths) | 7 | 0 | 0 |

Watcher did run: watch.log shows pushed rent-02dr 12:09:12, rent-bmrivsmoke 12:09:16, rent-ch403 12:09:19, rent-sf401 12:09:26 (local = UTC-4), and all 4 .pushed files recreated at 12:09. But each publish logged "no changes added to commit" above it, and OB counts stayed 0. So the republish did not land results.

## 4. rent-02dr sha256 comparison (match counts only, no contents)

- Worktree files: 25 total (logs 6, run 4, score 10, score-machine 4, RESULTS-rent.md 1). The 24 data files (excluding RESULTS-rent.md, which was written after copy-back) match the task's "expect 24 files" and the job reply's "24 files back" claim.
- Builder-outbox files under its PUSH paths: 0. Compared 0 files, matched 0.
- Copy-back manifest: no separate manifest file found by name under artifacts/claude-e2e02dr-20260926/ (names-only search). The job's queue reply (not a result file) claims "24 / 24" sha match both ends at copy time (marks table line `copy | files back, sha match both ends | 24 / 24`). Current worktree-to-outbox match is 0 / 25 because outbox is empty. No result contents opened or quoted.
- Worktree RESULTS-rent.md exists (1 file); outbox has 0 copies of it.

## 5. Deviations and misses

- OPUS-RULES.txt not found at the tasked scratchpad path (scratchpad/briefs/ missing; /private/tmp/.../scratchpad/ empty). Followed the key points quoted in the task itself (additive only, fictional names, no notebook writes, no secrets, disk check, counts only). (1 deviation)
- PUSH format mismatch (load-bearing): the running watcher (and origin/main) only publishes `^PUSH:` lines, but rent-02dr, rent-sf401 and rent-ch403 use `PUSH to builder-outbox:` and rent-bmrivsmoke uses `PUSH (builder-outbox):` / rent-358i uses `7. PUSH ...:`. So removing .pushed cannot republish their results with the current watcher; all 4 re-pushes came back empty (OB still 0). This also explains why 000-republish-0926f's sf401 retry at 12:04 left OB at 0. Director fix needed: teach watcher to parse these variants (or rewrite those 4 .md PUSH lines to `PUSH:` form — not done here, additive-only). (1 deviation, 4 misses)
- rent-02dr file count: task said "expect 24 files"; worktree has 25 total (24 data + RESULTS-rent.md). Consistent with reply's 24-back claim (RESULTS written after). Reported as 25/24, not a miss. (0 miss)
- rent-sf401 "may already be handled by 000-republish-0926f": it was touched once (12:02 removal → 12:04 re-push) but OB stayed 0; handled again here (12:09 re-push), still 0. (0 miss, noted)
- rent-rd378L, rent-mu404 (run), 006k (run02c) skipped because worktree has no files to publish (W:MISS); 006m skipped (empty .md). (0 miss, per rule)
- No TEST-ONLY panels read, tuned or quoted. No rentals. Disk free 53 GB throughout (df -g /). At most 1 process used for checks. (0 deviation)

## 6. What was pushed

This job's PUSH path (written here, not yet published by watcher):
- artifacts/claude-republish-20260926g/REPORT.md (this file, 1 file)
