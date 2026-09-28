# k1h-glm2 REPORT (counts only; no chat and no answer quoted)

Task: k1h-glm2 (Creative answers in chat thread, 2026-09-26 20:13 UTC). GLM 5.3 Flash
through the opencode route, helper v1.1, at most 2 calls at once. Mac CPU only.
Verdict: PARTIAL — 240/240 k1e answers done; 593 new chats written (below the
about-650 target); 0 of the 593 new chats answered (time cap blown by a machine
sleep; step-6 formula gave M=-1213 so answer2 skipped everything). A resume job
can answer O/chats.jsonl (the answer step resumes and skips answered chats).

## Inputs
- Files from origin/main via `git archive origin/main scripts
  artifacts/claude-k1e-20260926/train/items.jsonl artifacts/claude-k1h-20260926
  artifacts/claude-k1f-20260926 artifacts/claude-k1fpanel-20260926/SEAL.sha256.txt`
  into a temp dir; everything run from there with
  `uv run --offline --no-project --python 3.12 python -B` (stdlib only, nothing
  installed). O = temp dir O. Code run, never edited.
- k1e items input: 240 chats.

## Seal and selftest (from temp dir)
- `shasum -a 256 -c artifacts/claude-k1h-20260926/SEAL-k1h.sha256.txt`: 25 OK, 0 failed.
- `shasum -a 256 -c artifacts/claude-k1h-20260926/SEAL-addendum1.sha256.txt`: 2 OK, 0 failed.
- `shasum -a 256 -c artifacts/claude-k1h-20260926/SEAL-addendum2.sha256.txt`: 4 OK, 0 failed.
- selftest printed:
  {"items": 5, "already": 0, "answered": 4, "failed": 1, "not_started": 0, "minutes": 0.0, "stopped_early": false}
  {"items": 5, "already": 4, "answered": 1, "failed": 0, "not_started": 0, "minutes": 0.0, "stopped_early": false}
  [k1h-glm] chats call 0 done (1/2)
  [k1h-glm] chats call 1 done (2/2)
  {"chats": 1, "mix": {"idea0": 1}, "rejected": {"repeat": 2, "bad: kind/turn count": 1}, "calls": 2, "failed_calls": 0}
  k1h glm selftest 3/3 ok

## Sessions (`opencode session list -n 1000 | wc -l`, count only)
- before: 8 (2026-09-26 20:23:06 UTC)
- after: 12 (2026-09-28 ~00:12 UTC)

## Step times (UTC, `date -u`) and outputs
- step 1 begin: 2026-09-26 20:22:52.
- seals + selftest: between 20:22:52 and 20:23:06 on 2026-09-26 (all pass, see above).
- answer1 start: 2026-09-26 20:23:13; end: 2026-09-26 21:01:09; exit 0.
  answer1-log.txt (13 lines):
  [k1h-glm] answer 20/240 answered 20 failed 0 2 min
  [k1h-glm] answer 40/240 answered 40 failed 0 4 min
  [k1h-glm] answer 60/240 answered 60 failed 0 7 min
  [k1h-glm] answer 80/240 answered 80 failed 0 9 min
  [k1h-glm] answer 100/240 answered 100 failed 0 11 min
  [k1h-glm] answer 120/240 answered 120 failed 0 13 min
  [k1h-glm] answer 140/240 answered 140 failed 0 17 min
  [k1h-glm] answer 160/240 answered 160 failed 0 20 min
  [k1h-glm] answer 180/240 answered 180 failed 0 23 min
  [k1h-glm] answer 200/240 answered 200 failed 0 28 min
  [k1h-glm] answer 220/240 answered 220 failed 0 34 min
  [k1h-glm] answer 240/240 answered 240 failed 0 38 min
  {"items": 240, "already": 0, "answered": 240, "failed": 0, "not_started": 0, "minutes": 37.9, "stopped_early": false}
- chats attempt 1 start: 2026-09-26 21:01:13; killed ~2026-09-26 22:46:13 by the
  tool harness 105-minute timeout at 25/36 calls (script healthy, not a script
  error). No chats.jsonl written (the script writes it only at the end), no JSON
  line printed. Partial log kept as logs/chats-log-attempt1.txt (25 progress lines).
- chats retry start: 2026-09-26 22:47:24; end: between 2026-09-27 00:58 UTC (poll
  showed 32/36) and 2026-09-27 04:58:32 UTC (a salvage commit already contained
  the complete 37-line log); exit 0.
  chats-log.txt (37 lines):
  [k1h-glm] chats call 0 done (1/36)
  [k1h-glm] chats call 1 done (2/36)
  [k1h-glm] chats call 2 done (3/36)
  [k1h-glm] chats call 4 done (4/36)
  [k1h-glm] chats call 5 done (5/36)
  [k1h-glm] chats call 3 done (6/36)
  [k1h-glm] chats call 6 done (7/36)
  [k1h-glm] chats call 8 done (8/36)
  [k1h-glm] chats call 7 done (9/36)
  [k1h-glm] chats call 9 done (10/36)
  [k1h-glm] chats call 11 done (11/36)
  [k1h-glm] chats call 10 done (12/36)
  [k1h-glm] chats call 13 done (13/36)
  [k1h-glm] chats call 12 done (14/36)
  [k1h-glm] chats call 14 done (15/36)
  [k1h-glm] chats call 16 done (16/36)
  [k1h-glm] chats call 17 done (17/36)
  [k1h-glm] chats call 18 done (18/36)
  [k1h-glm] chats call 15 done (19/36)
  [k1h-glm] chats call 20 done (20/36)
  [k1h-glm] chats call 21 done (21/36)
  [k1h-glm] chats call 22 done (22/36)
  [k1h-glm] chats call 23 done (23/36)
  [k1h-glm] chats call 19 done (24/36)
  [k1h-glm] chats call 25 done (25/36)
  [k1h-glm] chats call 26 done (26/36)
  [k1h-glm] chats call 27 done (27/36)
  [k1h-glm] chats call 24 done (28/36)
  [k1h-glm] chats call 28 done (29/36)
  [k1h-glm] chats call 30 done (30/36)
  [k1h-glm] chats call 31 done (31/36)
  [k1h-glm] chats call 29 done (32/36)
  [k1h-glm] chats call 32 done (33/36)
  [k1h-glm] chats call 33 done (34/36)
  [k1h-glm] chats call 34 done (35/36)
  [k1h-glm] chats call 35 done (36/36)
  {"chats": 593, "mix": {"idea1": 213, "idea0": 216, "uf1": 59, "uf2": 55, "uf3": 50}, "rejected": {"bad: fact value not in teach turns": 21, "bad: keys": 2, "bad: kind/turn count": 1, "repeat": 1, "bad: relation": 1, "bad: fact owner not in teach turns": 2}, "calls": 36, "failed_calls": 5}
- answer2 start/end: 2026-09-28 00:11:46; M = 480 - 1668 - 25 = -1213; exit 0.
  answer2-log.txt (1 line):
  {"items": 833, "already": 240, "answered": 0, "failed": 0, "not_started": 593, "minutes": 0.0, "stopped_early": true}

## File counts
- `wc -l`: O/answers.jsonl 240, O/chats.jsonl 593 (total 833).
- CR (`\r\n` byte count): O/answers.jsonl 0, O/chats.jsonl 0.
- sha256 (temp dir and worktree copies identical, all 6 files):
  chats.jsonl 49c74254ea797454d98967b4b3123f23f51498ae8e70089ff978191db76ee8a2
  answers.jsonl 348b645b1e87be405b31d7684bbb0d7e57976a716e79b57414374dd32aac944c
  answer1-log.txt 4fd8416f3cba077690027f54f3a9b54ca42749256080a921bf03d9c6a2d7d789
  chats-log.txt e71e9ce0eb98495a2d59303699f72091defe12947d9c257c09e6dc2f349e7545
  chats-log-attempt1.txt b4057e81bf0d04494335686e0669c96603492117725bbfc8bdb1890790556c88
  answer2-log.txt b2965350a7a1aa76f0bcafc808dabcae85679218c5fd3780df6c2176488eea27
- origin/main and origin/builder-outbox glm/chats.jsonl and glm/answers.jsonl are
  byte-identical to these (same shas); origin logs hold the 3 logs above.

## Every deviation
1. Duplicate-guard process check: the only command matching claude_k1h_glm was
   this job's own opencode wrapper (the task text is embedded in its command
   line); no worker process was running. Treated as clear.
2. All script runs used the step-1 prefix
   `uv run --offline --no-project --python 3.12 python -B` (steps 4-6 show bare
   `python -B`).
3. Chats attempt 1 killed at 25/36 by the tool harness timeout (105 min), not by
   the script; its 25 finished calls were lost (script writes chats.jsonl only at
   the end). Partial log preserved as the extra file logs/chats-log-attempt1.txt.
4. Chats re-run from scratch (the code has no chats resume): 36/36 calls,
   chats 593, failed_calls 5 — below the about-650 target.
5. The Mac slept roughly 2026-09-27 00:58 UTC to 2026-09-28 ~00:00 UTC, blowing
   the 8-hour wall-clock cap. Step-6 M computed literally as 480-1668-25=-1213;
   answer2 ran with it and skipped all 593 new chats (0 answered, 0 failed).
6. While this job slept, a separate salvage commit (86599f56d) copied this run's
   temp outputs into the worktree glm/ and they reached origin/main and
   origin/builder-outbox (verified byte-identical). The guard now trips on origin,
   but it is this run's own data, not a competing run. This job added only the 2
   files the salvage lacked (logs/answer2-log.txt, REPORT.md) plus this REPORT.md.
   The salvage's REPORT-salvage.md is left untouched.
7. Branch push withheld: the shared worktree branch is ahead 50 commits with many
   agents' work; pushing it would push unrelated commits. Only this job's 2 files
   are committed; PUSH path declared for the watcher:
   PUSH: artifacts/claude-k1h-20260926/glm
8. Sessions after (12) minus before (8) = +4; other jobs share this machine and
   route; helper v1.1 deletes its own session per call (counts only, per task).
9. Seal/selftest window and chats-retry end reported as ranges (sleep gap); local
   file mtimes disagreed across the sleep, so UTC poll times are authoritative.
10. No chat or answer opened, printed or quoted (counts only). No opencode config,
    auth or key file read. No repo-root notebook writes. No rentals, no GPU, $0.
