# REPORT: republish rent-sf401 (task 000-republish-0926f)

Date: 2026-09-26. Agent: build/verification agent in worktree card-experiment-handoff-7c5b27.
Mission: remove the watcher marker `rent-sf401.pushed` so the fixed watcher republishes
rent-sf401's results to origin/builder-outbox, then verify.

## Verdict: REPUBLISH DID NOT RESTORE THE ARTIFACTS (FAIL)

The watcher did run and did re-mark rent-sf401 as pushed, but
origin/builder-outbox still contains zero files under
artifacts/claude-sf401-20260926/. The republish was a no-op for the missing
files. Root cause found (see section 4). No files were rented, no files edited,
1 marker file deleted as ordered, 1 report file created (this one).

## 1. Watcher self-update check (PASS)

- `~/premonition-watch/watcher.sh` line 36 contains `git add -f -- "$p"`: YES (1 match).
- `~/premonition-watch/watcher.new` line 36 contains `git add -f -- "$p"`: YES (1 match).
- Both files identical size, dated Sep 26 12:01 local. Watcher restarted itself at
  12:01:58 local (log: "self-update, restarting", pid 16015). Fix confirmed live.

## 2. Marker removal (DONE, exactly as ordered)

- Before: `~/premonition-watch/queue/rent-sf401.pushed` existed (0 bytes, dated 11:59).
- At 16:02:48 UTC removed exactly that 1 file. No other file touched.
- After removal the queue still held rent-sf401.exit, rent-sf401.go1.done,
  rent-sf401.go1.err.txt, rent-sf401.go1.reply.md, rent-sf401.md (5 files kept).

## 3. Republish watch + outbox check (FAIL: 0 of 16 files present)

- Watcher log shows `2026-09-26 12:04:41 pushed rent-sf401` (= 16:04:41 UTC,
  113 seconds after marker removal) and the marker file was re-created.
- Fresh `git fetch origin builder-outbox` at 16:06:29 UTC and again 16:07:11 UTC:
  files matching `claude-sf401-20260926` on origin/builder-outbox: 0.
- Files matching `sf401` on origin/builder-outbox: 5, all under runs/ only:
  runs/rent-sf401/rent-sf401.exit, rent-sf401.go1.done, rent-sf401.go1.err.txt,
  rent-sf401.go1.reply.md, rent-sf401.md.
- Expected but missing: artifacts/claude-sf401-20260926/RESULTS-rent.md (0/1),
  run/ files (0/8), score/ files (0/7).

## 4. Root cause (why the fixed watcher still published nothing)

- `grep -c '^PUSH:' ~/premonition-watch/queue/rent-sf401.md` = 0. The queue file
  has NO line starting with `PUSH:`.
- Its line 27 reads `PUSH to builder-outbox: artifacts/claude-sf401-20260926/
  RESULTS-rent.md artifacts/claude-sf401-20260926/run
  artifacts/claude-sf401-20260926/score artifacts/fable-predictions-ledger.md`
  (starts with "PUSH to", not "PUSH:"). The watcher's publish() only matches
  `^PUSH:`, so it staged 0 artifact paths and committed nothing (log shows
  "no changes added to commit" right before "pushed rent-sf401").
- The 16 source files DO exist in this worktree ($W), the folder the watcher
  copies from: 1 RESULTS-rent.md, 8 run/*.jsonl (arm_A, arm_B, sf401_events_B,
  gram360_parts_B, sleep_A, gram360_parts_A, sf401_counts_B, sleep_B), 7
  score/* (judge_asks_A, judge_asks_B, grammar_B, mechanical.json,
  judge_saves_A, grammar_A, judge_saves_B). Total 16 files present locally,
  0 on the outbox branch.
- So the `git add -f` fix is live but can never fire for this job: there are no
  parsed PUSH paths to force-add. Fixing it needs a `PUSH:` line in the queue
  file, which this agent is forbidden to edit (additive-only rules). Director
  action required.

## 5. Pre-checks and deviations

- `uptime` load high but irrelevant (no compute run); `df -g /`: 53 GB free
  (limit was 3 GB). Disk check: PASS, 0 disk used by this task.
- Deviation 1: OPUS-RULES.txt not found at the tasked path; the whole
  scratchpad/76c622f5.../scratchpad tree is empty. Proceeded under the key
  rules restated in the task itself (additive-only, append-only ledger,
  fictional names, no secrets, names-only listing). Files edited: 0.
- Deviation 2: none other. No TEST-ONLY panel was opened, tuned, or quoted;
  only file NAMES were listed, never contents. No config files printed.

## Marks (integer counts)

- Watcher files with `git add -f` fix: 2/2 (watcher.sh, watcher.new).
- Marker files removed: 1 (rent-sf401.pushed). Other files removed: 0.
- Republish rounds observed: 1 (16:04:41 UTC). Marker re-created: 1.
- Outbox files under artifacts/claude-sf401-20260926/: 0/16.
- Outbox files under runs/rent-sf401/: 5/5.
- Local worktree files under artifacts/claude-sf401-20260926/: 16/16.
- Report files created: 1. Existing files edited: 0.

## What this means (plain English)

Think of the watcher as a mail carrier with a fixed rule: it only mails boxes
whose address label starts exactly with "PUSH:". The rent-sf401 package has a
label that says "PUSH to builder-outbox:" instead, so the carrier walks past it
every round, scans zero boxes, and reports "delivered" anyway. Upgrading the
carrier's truck (the `git add -f` fix) changed nothing because the problem is
the label, not the truck. The 16 result files are sitting safely in the local
worktree; they just need a correctly formatted label (a `PUSH:` line), which
only the director can authorize. This does NOT mean the rent-sf401 experiment
failed or its data is lost; it means the results are unpublished, not missing.
