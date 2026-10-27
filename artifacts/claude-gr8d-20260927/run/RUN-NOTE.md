# gr-8 dev run note (practice only; PLAN-gr8d.md)

- Plan, code, chain and practice set sealed in 90f863ac9 (git commit time 2026-09-27T09:36:31Z).
- First STEP line: STEP start 2026-09-27T09:36:38Z (from `date -u` inside chain.sh). Seals, gr-7's adapter sha256 and
  both selftests passed. The replay started at 09:36:39Z.
- Chain PID 30642 (bash artifacts/claude-gr8d-20260927/cpu/chain.sh), launched once, on this container's CPU (4
  threads), $0.
- 2026-09-27T10:40:55Z: the replay finished (200 rows; greedy read a grid on 195; the pick differs from greedy on 11). The squares started at 10:19:24Z. Marks are left to the count and the recount.
- 2026-09-27T11:40:43Z: the squares finished (200 rows; greedy read a grid on 200; the pick differs on 0). The unseen formats started at 10:58:09Z and are almost done; the lookalikes follow.
- 2026-09-27T11:46:18Z: the unseen formats finished (200 rows; the pick differs on 16) and the lookalikes finished at about 11:45Z (150 rows; greedy read a grid on 5; the pick differs on 0). The count ran at 11:45:41Z and the chain ended (STEP done 11:45:42Z), 2 h 9 min after the first STEP. Every task was launched once. Count: run/logs/count.log (outcome DEV-FAIL on D1). A separate agent's recount is next. Known count bug, found when reading count.log: the squares lines are counted twice (400 for 200 squares), because the squares group name equals the task name; D2 compares two doubled numbers, so its result is unaffected.
