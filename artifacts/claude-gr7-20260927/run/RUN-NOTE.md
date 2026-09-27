# gr-7 run note (PASSMARKS-gr7 "Where it runs"; ADDENDUM-gr5-3's rules)

- Marks sealed in c8b971c76; code and chain sealed in f6ec1b62f. Rows and panel are gr-6's sealed ones (eea8d6e10).
- Before sealing, the code was smoke-tested on made-up files only: `train` on 2 gr-6 training rows, and `dev` on 3
  gr-6 training rows relabelled as dev. No held-out dev row and no panel row was read. The dry run of the chain's
  checks at 04:25:35Z made an empty run/ folder, which was removed before launch.
- First STEP line: STEP start 2026-09-27T04:25:50Z (from `date -u` inside chain.sh).
- Chain PID 17595 (bash artifacts/claude-gr7-20260927/cpu/chain.sh), launched once.
- Container: this Claude Code cloud session's container, 4 CPUs, torch 2.14.0+cpu, 4 threads.
- Cap end: 2026-09-27T10:25:50Z, 6 hours after the first STEP line. At the cap the chain is stopped by exact PID and
  whatever finished is reported as PARTIAL.
- Restarts: none so far.
- 2026-09-27T04:26:21Z: seals and selftests passed; training (epochs 4 to 6) started at 04:25:53Z.
- 2026-09-27T05:26:44Z: training (epochs 4 to 6) is still running (STEP train at 04:25:53Z; about 2 hours expected).
