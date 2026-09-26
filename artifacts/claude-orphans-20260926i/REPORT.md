# Orphan check — 2026-09-26i (director task 17:15 UTC)

Agent: build/verification, worktree `claude/card-experiment-handoff-7c5b27`. Rented nothing.
`date -u` at task start: Sat Sep 26 17:15:08 UTC 2026 (Mac local 13:15 EDT = UTC-4).
Pre-checks: `uptime` load ~86, `df -g /` 53 GB free (> 3 GB). No heavy steps taken. Max parallel processes used: 2.

## 1. Instances (`vastai show instances`, raw JSON, 17:15-17:16 UTC)

6 instances total, all `actual_status`/`cur_state` = running/running. Start times converted with `date -u -r <epoch>`.

| id | label | status | dph_total | start (UTC 2026-09-26) |
|---|---|---|---|---|
| 52755827 | claude-director-depot | running | 0.11361111111111112 | 13:45:29 |
| 52775111 | rent-brd9 | running | 0.4944444444444444 | 16:06:30 |
| 52775913 | claude-madeup-mu404b | running | 0.5037037037037037 | 16:12:28 |
| 52778152 | claude-fixsleep-dl6b | running | 0.48518518518518516 | 16:25:32 |
| 52779987 | claude-notes-rd378u | running | 0.5037037037037037 | 16:38:31 |
| 52780943 | claude-thought-rv390 | running | 0.4782407407407407 | 16:45:33 |

5 labels match `claude-<x>`. No `.running` file is named exactly `<instance-label>.running` for any of them; matching below is by job suffix (see Deviations).

`ls ~/premonition-watch/queue/*.running` (8 files): 000-orphans-0926i (this job), rd378g-teacher, rd378k-teacher, rent-brd9, rent-mu404b, rent-rd378u, rent-rv390, rent-zdl6b.

Per `claude-<x>` label:

- claude-director-depot (52755827): NO matching `.running` file (queue has only done/pushed `rent-depot.*`, no `rent-depot.running`). No builder process. Reported only (see 3).
- claude-madeup-mu404b (52775913): job `rent-mu404b.running` EXISTS. Builder alive, PIDs 9893, 9924.
- claude-fixsleep-dl6b (52778152): job `rent-zdl6b.running` EXISTS. Builder alive, PIDs 18627, 18660.
- claude-notes-rd378u (52779987): job `rent-rd378u.running` EXISTS. Builder alive, PIDs 25474, 25506.
- claude-thought-rv390 (52780943): job `rent-rv390.running` EXISTS. Builder alive, PIDs 23177, 23209.

Other running jobs (all builders alive, PIDs only):

- rent-brd9 (instance 52775111, non-`claude-*` label): PIDs 282, 315.
- rd378g-teacher (Mac CPU job, no instance): PIDs 39327, 39358, 39779, 39783.
- rd378k-teacher (Mac CPU job, no instance): PIDs 34733, 34767.
- 000-orphans-0926i (this job): PID 45600.

Count: 7 of 7 non-mine running jobs have at least one alive builder process. 0 running jobs without a live builder.

## 2. claude-sleep-358t

Wait condition met at FIRST check (~17:16 UTC), no polling needed:

- `git fetch -q origin main builder-outbox` (rc=0); `git show origin/builder-outbox:artifacts/claude-rsn358t-20260926/AUTOCAST-CHECK.md` EXISTS (rc=0).
- `ps -axo pid,etime,command | grep 358t / check-358t`: NO process alive (grep rc=1).
- Worktree copy `artifacts/claude-rsn358t-20260926/AUTOCAST-CHECK.md` present (mtime 13:09 Mac).

Instance labelled exactly `claude-sleep-358t`: DOES NOT EXIST among the 6 instances above. Therefore: no files copied back, no `vastai destroy`, no ledger line from this job.

Recorded values (from AUTOCAST-CHECK.md as pushed by the 000-check-358t job, not re-measured by me): id 52780312, duration 1614.55 s = 0.4485 h, dph_total 0.4875, cost 0.4485 x 0.4875 = $0.2186 (~$0.22). That job's commit 7c0294524 (13:10 Mac) states: PIDs killed, instance 52780312 destroyed, 20 run files copied back (10 `train_log.jsonl` + 10 `*.log` under `artifacts/claude-rsn358t-20260926/runs/`), ledger line appended. `runs/orphan/` NOT created by me (nothing left to copy; check job already copied the logs).

## 3. Destroys

Destroyed 0 instances. No other `claude-*` instance lacks an alive builder except claude-director-depot (no `.running`, no builder process) — reported only, not touched (Director's depot; only its owner thread or the Director may stop it).

## Deviations (4)

1. OPUS-RULES.txt path from the brief (`/private/tmp/claude-502/.../scratchpad/briefs/OPUS-RULES.txt`) does NOT exist; `scratchpad/briefs/` is absent from this worktree. Followed the rules as restated in `~/premonition-watch/queue/000-orphans-0926i.md` (additive only, fictional names, no secrets, key via `$(cat ...)` never printed, counts exact).
2. No exact `<instance-label>.running` file exists for any `claude-<x>` label; matches in section 1 are by job suffix (rent-mu404b, rent-zdl6b, rent-rd378u, rent-rv390).
3. Brief says the 358t builder exited rc=2 at 13:10 Mac; queue file mtimes: `claude-sleep-358t.exit` = rc=2 at 13:08 Mac, `000-check-358t.exit` = rc=0 at 13:10 Mac (pushed 13:12 Mac).
4. PUSH list names `runs/orphan` and the ledger; neither was created/appended by this job (358t already gone; nothing destroyed) — pushing REPORT.md only.

Counts: 6 instances, 5 `claude-*` labels, 8 `.running` files, 7/7 non-mine running jobs with live builders, 0 files copied, 0 destroys, 0 ledger lines, 1 new file (this report).
