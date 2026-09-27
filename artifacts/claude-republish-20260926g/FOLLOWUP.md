# Republish 2026-09-26g — FOLLOWUP (resume agent, go2)

Task: republish every job whose results were skipped by the old publish (director, 16:18 UTC 09-26).
Resume context: go1 already audited 39 jobs, removed 4 markers at 16:08:46Z, waited, and wrote
REPORT.md in this folder (89 lines, left untouched here). This file only adds what changed after
REPORT.md's final check (16:15:39Z). Run from the same worktree. Rent: 0. Disk free 53 GB throughout.
No result file contents opened (names and counts only; sha256 compared as hashes, match counts only).

## 1. Watcher fix confirmed (with one new fact)

- Running script ~/premonition-watch/watcher.sh publish() contains `git add -f -- "$p"` (line 36).
- New since REPORT.md: the watcher SELF-UPDATED at 12:14:04 local (watch.log "self-update, restarting").
  The new publish() parses `grep -h '^PUSH[^:]*:'`, which matches `PUSH:`, `PUSH to builder-outbox:`
  and `PUSH (builder-outbox):` forms. REPORT.md's load-bearing deviation (old watcher only matching
  `^PUSH:`) is fixed by this self-update.

## 2. Re-audit: 41 <job>.pushed modified 2026-09-26 (16:18Z, after `git fetch origin builder-outbox`)

Method: same as REPORT.md — PUSH paths from `^PUSH[^:]*:` lines, `git ls-tree -r origin/builder-outbox`
count (OB) vs worktree file count (W). Ledger path counted but not decisive.

- 35 jobs: every PUSH path on OB with counts equal to worktree. Left alone. This now INCLUDES
  rent-ch403 (RESULTS 1, run 2, dev 6 — landed by the 12:16:57 republish under the NEW watcher;
  `git log origin/builder-outbox` shows `85e72249d builder results: rent-ch403`).
- rent-sf401: no .pushed file present (removed by concurrent job 000-republish-0926h, which owns
  ch403+sf401). Left alone.
- 2 jobs with PUSH paths missing on OB but present in worktree: REMOVED their .pushed (2 files):
  rent-02dr (OB 0/0/0/0/0 vs W 1+4+10+4+6 = 25), rent-bmrivsmoke (OB 0/0 vs W 1+6 = 7).
- Left alone, nothing publishable from this Mac (OB 0 and W 0): rent-q404, rent-rd378L, rent-mu404
  (run path only), 006k-02c-benspc (run02c path only), 006m-rsn-358f-flow (empty .md), rent-358i
  (no PUSH lines in .md). 006h/006i .md files contain prose PUSH lines that split into words
  (OB 0/W 0 fragments); their one real path (006h full/) is OB 8 = W 8. 006k's real paths are
  OB = W (5, 1, 26, 14).

Removed at 16:18:18Z (2): rent-02dr.pushed, rent-bmrivsmoke.pushed. Nothing else created, edited or
deleted. No TEST-ONLY panels read, tuned or quoted. At most 1 process used.

## 3. After wait: files now on builder-outbox (final 16:20:53Z, ~3 min wait)

Watcher rounds 12:19:22-12:19:29 local republished all three pending jobs. Counts via ls-tree:

| job | PUSH path | W files | OB before | OB after |
|---|---|---|---|---|
| rent-02dr | artifacts/claude-e2e02dr-20260926/RESULTS-rent.md | 1 | 0 | 1 |
| rent-02dr | artifacts/claude-e2e02dr-20260926/run | 4 | 0 | 4 |
| rent-02dr | artifacts/claude-e2e02dr-20260926/score | 10 | 0 | 10 |
| rent-02dr | artifacts/claude-e2e02dr-20260926/score-machine | 4 | 0 | 4 |
| rent-02dr | artifacts/claude-e2e02dr-20260926/logs | 6 | 0 | 6 |
| rent-02dr total | (5 paths) | 25 (24 data + 1 RESULTS) | 0 | 25 |
| rent-bmrivsmoke | artifacts/claude-bmriv-smoke-20260926/RESULTS-rent.md | 1 | 0 | 1 |
| rent-bmrivsmoke | artifacts/claude-bmriv-smoke-20260926/run | 6 | 0 | 6 |
| rent-bmrivsmoke total | (2 paths) | 7 | 0 | 7 |
| rent-sf401 (h-agent) | artifacts/claude-sf401-20260926/RESULTS-rent.md | 1 | 0 | 1 |
| rent-sf401 (h-agent) | artifacts/claude-sf401-20260926/run | 8 | 0 | 8 |
| rent-sf401 (h-agent) | artifacts/claude-sf401-20260926/score | 7 | 0 | 7 |
| rent-sf401 total | (3 paths) | 16 | 0 | 16 |
| rent-ch403 (h-agent) | artifacts/claude-ch403-20260926/RESULTS-rent.md + run + dev | 9 | 0 | 9 |

## 4. rent-02dr sha256 comparison (match counts only, no contents)

- Worktree files under its 5 PUSH paths: 25 total (names listed via find; no contents opened).
- OB blobs under the same paths: 25 files. sha256(worktree file) vs sha256(OB blob): 25 matched / 25.
- Copy-back manifest: no separate manifest file by name under artifacts/claude-e2e02dr-20260926/
  (names-only search; the folder holds exactly logs 6, run 4, score 10, score-machine 4,
  RESULTS-rent.md 1). Manifest-equivalent: the job's queue reply file (not a result file) claims
  "24 files back" and "24 / 24" sha match at copy time. Current worktree-to-outbox match is 25 / 25
  (24 data files + RESULTS-rent.md, which was written after copy-back). Consistent with the task's
  "expect 24 files".

## 5. Deviations and misses

- REPORT.md already existed from go1; per additive-only rule it was not edited — this FOLLOWUP.md
  is a NEW file. The task's "Write .../REPORT.md" step was already satisfied by go1. (1 deviation,
  file placement only)
- OPUS-RULES.txt not found at the tasked scratchpad path (same as go1). Followed the key points
  quoted in the task. (1 deviation, inherited)
- 0 misses: every job skipped by the old publish is now on builder-outbox (02dr 25, bmrivsmoke 7,
  ch403 9, sf401 16).

## 6. What was pushed

Nothing new by this agent: FOLLOWUP.md (this file, 1 file) is NOT in the job's PUSH list
(`PUSH: artifacts/claude-republish-20260926g/REPORT.md`), so the watcher will publish REPORT.md
(go1's, already on OB per audit: OB 1 = W 1) but not this file. The director reads it here instead.
