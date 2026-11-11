# E0-READY at commit a1adcb196 (branch claude/forgetting-round-g), Oct 20

Per the coordinator's stop rule (Oct 20): the built-in /code-review (level high), scoped to results/forgetting/e0/ (script, tests,
run sheet Part 1) and to the G1 train path (domain/far/learn_probe.py, --guard kfsoft --kl-replay-rows 32 --kl-weight 30,
--replay-priority off), found **nothing blocking** at a1adcb196:
- E0 should run on a correctly prepared PC. It picks the final checkpoint, checks both DEVs and computes harm_measure(5.0, 1.5)
  the same way domain/analyze.py does. Its import chain compiles under Python 3.11 (3.10 itself not available to test).
- G1 trains and scores exactly as at 62cf9ac36. Old-vs-new final-checkpoint identity, flag off: G1 exact 3e5c13359bd13e00, replay KL
  07f65e5bc7e1bddd, A1F e0d004bb487ecc04, replay CE 8de74c6a4c3152ee (round 3). The trainer has not changed since.
- Tests: 18/18 E0 tests pass with torch blocked; 58/58 across domain/far + e0 at c537fe8cc (trainer unchanged since).

Scoped reviews in this round, each blocker fixed before the next:
- c537fe8cc: 1 blocker (the run sheet's --repo pointed at a checkout without custom_io/domain).
- 5397914c5: 2 (a Python-3.12-only import; one --parent across mixed-seed runs).
- ab0634c99: 1 conditional (relative parent paths).
- a1adcb196: none.

Open, non-blocking (recorded, not fixed; no more rounds unless Ben asks):
- E0: a same-named relative parent could resolve from cwd or the run folder without --base (noted, parent_sha256 recorded); one --base
  for all runs; a relative final path gets a "not on disk" note though night_N is correct; repo_dirty can misread across line-ending
  configs; main()'s scoring loop untested; checkpoints loaded twice; DEV pin read by regex; sha helpers duplicated; summary.json read
  without explicit utf-8.
- Run sheet: the commands are bash (run under WSL or Linux, not PowerShell).
- --replay-priority (H1 path): marked NOT FOR USE; review findings 4, 5, 9 and 10 of CODE-REVIEW-950a7d2e2.md stay open.

E0 itself and the Main brain DM1/DM3 gate stay with Ben (run sheet: PC-PACKET-E0-AND-GATE.md, run under WSL/Linux).
