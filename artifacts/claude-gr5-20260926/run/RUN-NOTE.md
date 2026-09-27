# gr-5 run note (ADDENDUM-gr5-3)

- First STEP line: STEP start 2026-09-26T22:43:40Z (from `date -u` inside chain.sh; logs/chain.log).
- Chain PID 1343 (bash artifacts/claude-gr5-20260926/cpu/chain.sh). The training process was PID 1363 at 2026-09-26T23:20:02Z.
- Container: this Claude Code cloud session's container (hostname vm), booted at 2026-09-26 22:36:30 local time, 4 CPUs, 4 threads.
- Cap end: 2026-09-27T04:43:40Z, 6 hours after the first STEP line.
- Restarts: none so far.
- 2026-09-26T23:20:02Z: training is still running. The STEP train line is at 22:43:43Z.
- 2026-09-26T23:57:56Z: training finished (73.9 minutes; adapter sha256 9f19edb7..., 16568343 bytes, kept off git). The dev gate started at 23:57:47Z.
- 2026-09-27T00:09:00Z: dev gate PASS (held-out squares 71 of 72 exact, 0 wrong; held-out no-square rows 107 of 107 none; format dev 30 of 30). The dev split line started at 00:08:50Z.
- 2026-09-27T00:16:39Z: dev split (ADDENDUM-gr5-1, report only): clean held-out squares 52 of 53 exact, 0 wrong, 1 read as none; shared 19 of 19 exact. The first registered task (L on the squares) started at 00:16:29Z.
