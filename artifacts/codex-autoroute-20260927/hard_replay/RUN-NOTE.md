# AR2 registered preparation

Fresh panel-seed search (`date -u`): Sun Sep 27 14:23:55 UTC 2026. No matches.

Panel preparation start (`date -u`): 2026-09-27 14:52:23 UTC

Machine: MacBook-Pro; preparation PID 65318.

Registration, already pushed before this run: 542f61b8c63e505ed02b881eb2216d57001ed1c7.

Command: `python -B artifacts/codex-autoroute-20260927/hard_replay/prepare_panels.py`.

No model construction or optimizer updates in panel preparation. The later preflight and driver record their own UTC times, machine and PIDs.

Corrected MPS preflight start (`date -u`): 2026-09-27 14:56:20 UTC; end 14:56:23 UTC. Machine MacBook-Pro; PID 67716. All checks passed, zero optimizer updates. See preflight-final.json and preflight-2.log.

The earlier sampler-check failure is retained in preflight.log (executor session 97890). Its OS PID was not captured because the preflight wrote process metadata only on success; this is a preparation provenance gap, not an unknown training trajectory. It failed before model construction, with no optimizer updates. See IMPLEMENTATION-NOTE.md for the test-only assertion correction.
