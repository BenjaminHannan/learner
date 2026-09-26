# Republish report: rent-ch403 + rent-sf401 (2026-09-26, task 000-republish-0926h)

Job: republish rent-ch403's results after its publish skipped every path
(both jobs' queue files use the `PUSH to builder-outbox:` line form).
Rent nothing; deleted only the two `.pushed` marker files named below.
No result file content was opened at any point (names and counts only).

## 1. Watcher version check: PASS

`grep -n PUSH ~/premonition-watch/watcher.sh` shows `publish()` using the
new form on two lines:

- `grep -h '^PUSH[^:]*:' "$Q/$n.md" | sed 's/^PUSH[^:]*:// ...` (path extraction)
- `{ echo "runs/$n"; grep -h '^PUSH[^:]*:' ... } | while read -r p; do git add -f -- "$p" ...` (staging)

So the running watcher has self-updated to the version matching
`^PUSH[^:]*:` in `publish()`. Watch log confirms
`2026-09-26 12:14:04 self-update, restarting` (Mac local time = 16:14 UTC)
just before this task started. Count of `^PUSH[^:]*:` occurrences in
`publish()`: 2.

Queue-file PUSH lines (both use the previously-skipped form):

- rent-ch403: `PUSH to builder-outbox: artifacts/claude-ch403-20260926/RESULTS-rent.md artifacts/claude-ch403-20260926/run artifacts/claude-ch403-20260926/dev artifacts/fable-predictions-ledger.md`
- rent-sf401: `PUSH to builder-outbox: artifacts/claude-sf401-20260926/RESULTS-rent.md artifacts/claude-sf401-20260926/run artifacts/claude-sf401-20260926/score artifacts/fable-predictions-ledger.md`

## 2. rent-ch403: REPUBLISHED, 9 files

- Baseline 16:15:27 UTC: 0 files under `artifacts/claude-ch403-20260926/` on `origin/builder-outbox`.
- Removed exactly `~/premonition-watch/queue/rent-ch403.pushed` at 16:15:29 UTC (only that file; nothing else touched).
- Watch log: `2026-09-26 12:16:57 pushed rent-ch403` (~88 s later); marker file recreated.
- After: 9 files on `origin/builder-outbox` under `artifacts/claude-ch403-20260926/`:
  - `artifacts/claude-ch403-20260926/RESULTS-rent.md` (1)
  - `artifacts/claude-ch403-20260926/dev/chat_X.jsonl` (2)
  - `artifacts/claude-ch403-20260926/dev/chat_X403.jsonl` (3)
  - `artifacts/claude-ch403-20260926/dev/judge/pair_a1.jsonl` (4)
  - `artifacts/claude-ch403-20260926/dev/judge/pair_a2.jsonl` (5)
  - `artifacts/claude-ch403-20260926/dev/key_a.json` (6)
  - `artifacts/claude-ch403-20260926/dev/summary.json` (7)
  - `artifacts/claude-ch403-20260926/run/logs/devX.log` (8)
  - `artifacts/claude-ch403-20260926/run/logs/devX403.log` (9)
- All three required categories present: RESULTS-rent.md (1 file), dev/ (6 files), run/ (2 files).

## 3. rent-sf401: REPUBLISHED, 16 files

- Baseline 16:15:27 UTC: 0 files under `artifacts/claude-sf401-20260926/` on `origin/builder-outbox` (RESULTS-rent.md missing), so per task step 4:
- Removed exactly `~/premonition-watch/queue/rent-sf401.pushed` at 16:17:22 UTC (only that file).
- Watch log: `2026-09-26 12:19:29 pushed rent-sf401` (~127 s later); marker file recreated. (Intermediate log lines show sibling jobs `rent-02dr` and `rent-bmrivsmoke` pushed at 12:19:22/12:19:25 by other republish tasks; not mine.)
- After: 16 files on `origin/builder-outbox` under `artifacts/claude-sf401-20260926/`:
  - `artifacts/claude-sf401-20260926/RESULTS-rent.md` (1)
  - `artifacts/claude-sf401-20260926/run/arm_A.jsonl` (2)
  - `artifacts/claude-sf401-20260926/run/arm_B.jsonl` (3)
  - `artifacts/claude-sf401-20260926/run/gram360_parts_A.jsonl` (4)
  - `artifacts/claude-sf401-20260926/run/gram360_parts_B.jsonl` (5)
  - `artifacts/claude-sf401-20260926/run/sf401_counts_B.jsonl` (6)
  - `artifacts/claude-sf401-20260926/run/sf401_events_B.jsonl` (7)
  - `artifacts/claude-sf401-20260926/run/sleep_A.jsonl` (8)
  - `artifacts/claude-sf401-20260926/run/sleep_B.jsonl` (9)
  - `artifacts/claude-sf401-20260926/score/grammar_A.jsonl` (10)
  - `artifacts/claude-sf401-20260926/score/grammar_B.jsonl` (11)
  - `artifacts/claude-sf401-20260926/score/judge_asks_A.jsonl` (12)
  - `artifacts/claude-sf401-20260926/score/judge_asks_B.jsonl` (13)
  - `artifacts/claude-sf401-20260926/score/judge_saves_A.jsonl` (14)
  - `artifacts/claude-sf401-20260926/score/judge_saves_B.jsonl` (15)
  - `artifacts/claude-sf401-20260926/score/mechanical.json` (16)
- All three required categories present: RESULTS-rent.md (1 file), run/ (8 files), score/ (7 files).

## 4. Machine state

- `uptime` at start: load averages ~83/74/81; at end ~78/92/89. High but the watcher kept publishing; no action taken.
- `df -g /`: 53 GB free (20% used), well above the 3 GB stop line.
- Ledger file `artifacts/fable-predictions-ledger.md` is a PUSH path of both jobs; the watcher stages it per job. Not opened or edited here.

## 5. Deviations (2)

1. The brief file `/private/tmp/claude-502/.../scratchpad/briefs/OPUS-RULES.txt` does not exist, and this worktree has no `scratchpad/briefs/` directory at all. Followed the key points as inlined in the task text instead (additive only, fictional names, no notebook writes, names/counts only, report in final reply).
2. None on the publish path: exactly 2 files deleted (`rent-ch403.pushed`, `rent-sf401.pushed`), 1 file created (this REPORT.md), 0 files edited. No rentals, no other deletions.
