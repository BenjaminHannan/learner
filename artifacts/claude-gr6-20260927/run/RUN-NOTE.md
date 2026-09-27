# gr-6 run note (PASSMARKS-gr6 "Where it runs"; ADDENDUM-gr5-3's rules)

- First STEP line: STEP start 2026-09-27T01:30:06Z (from `date -u` inside chain.sh).
- Chain PID 12014 (bash artifacts/claude-gr6-20260927/cpu/chain.sh), launched once.
- Container: this Claude Code cloud session's container, 4 CPUs, torch 2.14.0+cpu, 4 threads.
- Cap end: 2026-09-27T07:30:06Z, 6 hours after the first STEP line. At the cap the chain is stopped by exact PID and
  whatever finished is reported as PARTIAL.
- Restarts: none so far. A reclaim means a restart from the start under the same seals, noted here.
- 2026-09-27T01:30:43Z: seals and selftests passed; training started.
