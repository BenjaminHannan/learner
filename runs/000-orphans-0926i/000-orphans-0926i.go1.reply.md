Orphan sweep starting — checking worktree for stray builders.
No `claude-sleep-358t` instance in the list — verifying the rest before writing the report.
All checks done — writing the report.
Push is blocked by environment policy — committing locally instead.
The commit swept in other staged files — fixing that now.
Orphan check complete. Report for the director:

**1. Instances (17:15–17:16 UTC, `vastai show instances --raw`, 6 total, all running):**
- 52755827 | claude-director-depot | dph 0.1136 | start 13:45:29 UTC — NO matching `.running`, no builder process (reported only)
- 52775111 | rent-brd9 | dph 0.4944 | start 16:06:30 UTC — builder alive, PIDs 282, 315
- 52775913 | claude-madeup-mu404b | dph 0.5037 | start 16:12:28 UTC — `rent-mu404b.running` exists, PIDs 9893, 9924
- 52778152 | claude-fixsleep-dl6b | dph 0.4852 | start 16:25:32 UTC — `rent-zdl6b.running` exists, PIDs 18627, 18660
- 52779987 | claude-notes-rd378u | dph 0.5037 | start 16:38:31 UTC — `rent-rd378u.running` exists, PIDs 25474, 25506
- 52780943 | claude-thought-rv390 | dph 0.4782 | start 16:45:33 UTC — `rent-rv390.running` exists, PIDs 23177, 23209
- Mac-CPU jobs, no instance, builders alive: rd378g-teacher (39327, 39358, 39779, 39783), rd378k-teacher (34733, 34767). This job: PID 45600. 7/7 non-mine running jobs have live builders.

**2. claude-sleep-358t:** Wait condition met at first check — AUTOCAST-CHECK.md already on origin/builder-outbox AND no 000-check-358t process alive, so no polling. No instance labelled exactly claude-sleep-358t exists. No copy-back, no destroy, no ledger line from me. Recorded from the check job's AUTOCAST-CHECK.md: id 52780312, 0.4485 h, dph 0.4875, $0.22; destroyed by 000-check-358t (commit 7c0294524, 13:10 Mac), 20 run files already back under `runs/`. `runs/orphan/` not created.

**3. Destroys:** 0. Nothing else touched. Only claude-* instance without a builder is claude-director-depot — reported only.

**Deviations (5):** (a) OPUS-RULES.txt path doesn't exist (`scratchpad/briefs/` absent); followed rules as restated in my queue file. (b) No exact `<label>.running` files; matches by job suffix. (c) rc=2 exit file stamped 13:08 Mac, not 13:10 (`000-check-358t.exit` rc=0 at 13:10). (d) PUSH list's `runs/orphan` + ledger N/A — pushing REPORT.md only. (e) `git push` is denied by this environment's tool policy — REPORT.md is committed locally as 796f0cdbd (1 file, own path only) but NOT pushed; needs a push from outside. Also: my first commit attempt swept in 53 siblings' staged files; I soft-reset it immediately and recommitted own-path-only — siblings' staged entries verified intact (53 `A` rows still staged).

Full detail: `artifacts/claude-orphans-20260926i/REPORT.md` (committed, unpushed).
