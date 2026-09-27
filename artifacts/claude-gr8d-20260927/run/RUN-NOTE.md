# gr-8 dev run note (practice only; PLAN-gr8d.md)

- Plan, code, chain and practice set sealed in 90f863ac9 (git commit time 2026-09-27T09:36:31Z).
- First STEP line: STEP start 2026-09-27T09:36:38Z (from `date -u` inside chain.sh). Seals, gr-7's adapter sha256 and
  both selftests passed. The replay started at 09:36:39Z.
- Chain PID 30642 (bash artifacts/claude-gr8d-20260927/cpu/chain.sh), launched once, on this container's CPU (4
  threads), $0.
- 2026-09-27T10:40:55Z: the replay finished (200 rows; greedy read a grid on 195; the pick differs from greedy on 11). The squares started at 10:19:24Z. Marks are left to the count and the recount.
- 2026-09-27T11:40:43Z: the squares finished (200 rows; greedy read a grid on 200; the pick differs on 0). The unseen formats started at 10:58:09Z and are almost done; the lookalikes follow.
