# HANDS toy report

## Milestone (a), 2026-11-06

Design frozen before toy outcomes: SHA-256 59087e05d7536d2ae5cf9bb44015e564ab1745a229c73adfcf01f655000b49ac. Approved disk amendment is in that hash. T1–T10 are not relaxed.

Built a bounded lease, sandbox-only input receiver, actual RGB playground with the four GUI tasks and the existing Sparks engine, a manual playground window, and a native Mac stop-guard source. No production OS input backend exists in this toy.

- New Node tests: 3/3 pass. Structured rule reference finishes all four GUI tasks on seeds 101, 202, 303. These short contract checks are not the frozen 120-episode T1 evaluation.
- Synthetic sandbox takeovers: 300, zero later accepted packets, zero stuck holds. Callback→release p95 0.009875 ms, max 0.031208 ms.
- Compiled Swift guard, same locked revoke path as its physical tap: 300 synthetic callbacks, 0 failures, p95 0.000125 ms, max 0.000792 ms. This excludes physical input/tap delivery and IPC.
- **T8 is PARTIAL, not passed:** physical-device delivery and native OS held-input release remain unproven. The helper deliberately cannot post real input. Neither measurement proves a 10 ms physical-device response.
- Full baseline desk suite: 1,092 tests; 1,083 pass, 8 fail, 1 skip. All eight failures are in the supplied known list: agentbench (2), fake-sleepmode, login1-electron, realpath (3), and 8192-token prompt. Baseline log is beside this report.

No Ben recording, real-brain use, BensPC use, app install, or desktop input. Next: pixel worker and sleep/export, then fake recorder tests.

The big brain picks the job.  
The little playground is ready for safe tests.  
Its stop switch drops old moves when touched.  
We have not proved the real mouse stop yet.  
Nothing is watching Ben.
