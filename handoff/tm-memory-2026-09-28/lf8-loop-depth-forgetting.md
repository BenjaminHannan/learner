---
name: lf8-loop-depth-forgetting
description: lf-8 (09-27): does the 8-layer loop forget less than 358e4's 2-block loop? CPU test run by the Making-things-up thread for the TM
metadata:
  type: project
  modified: 2026-09-27T19:41:45.259Z
---
Asked by Ben 19:35:34 UTC 09-27 ("so then do the test", cmsg_01FuvegZXjMmeUzStiEFVnEW2GCUswgRDMfwHGUkGY9TTf) via the Thread manager: forgetting tests (358e line) used a 2-block loop; his reasoner design is an 8-layer loop.
- Sealed 72cb903bc: artifacts/claude-lf8-20260927/PASSMARKS.md, scripts/claude_lf8_run.py (imports 358e4 unchanged; sets X.SIZES["small"]["layers"]). loop2 1,646,750 weights, loop8 6,386,174 (3.9x, a depth test not same-size). Seeds 9, 10.
- Marks: T = grids5+sums4+maze7 after C (of 600). V grids5 after A and sums4 after B >= 120. PASS mean T8 >= T2+40 and higher on both seeds; proved wrong T8 <= T2+10 on both. 358e4 dense-replayall T spread 393-525 over 6 seeds (noise).
- CPU fallback ran 19:41-20:01 UTC, then stopped by exact PID (RUN-NOTE 1cd03d172) when Sleep research started the registered run on vast at 19:55:13 (5090, instance 53022539). Trigger disabled. If the vast run fails, rerun the CPU lanes from scratch (scratchpad lf8_lanes.sh pattern: 2 lanes x 2 threads).
- TM 19:41: Sleep research (session_01LJ2LcTKkk3ipL1CryhUDgB) runs the same sealed plan on vast; my CPU run is the FALLBACK. When Sleep research says its vast run started, stop my CPU runs by exact PID + RUN-NOTE line; if vast fails, mine stands.
**Why:** tells whether the forgetting results carry over to Ben's 8-layer loop.
**How to apply:** after the runs, score, blind recount, RESULTS.md + VERIFY.md, verdict to the TM. Related: [[made-up-facts-line]], [[cloud-container-idle-reclaim]].
