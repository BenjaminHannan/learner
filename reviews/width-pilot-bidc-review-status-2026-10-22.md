# Bid C calibration drafts: review status (2026-10-22), for the coordinator

PR [BenjaminHannan/learner#95](https://github.com/BenjaminHannan/learner/pull/95), branch `claude/bidc-calibration-drafts` (base `claude/project-thread-2zeaoc`). Folded in, per Ben: the `pilot_bars` fix on `claude/width-pilot-drafts`. All of this is DRAFT. **The 2-round cap is reached, so the code is parked for the coordinator.**

| Round | Target | Blocking | Non-blocking | Fix commits |
|---|---|---|---|---|
| 1 | dcac6910f (drafts) and a2a83f9f0 (pilot_bars) | 3: gate check 3 compared a reload with a reload; c2b opened the test before its checks; Bid C caps fell back to the opened C2 test | 7 | 73dccb70b and e485386fc (bidc; record rows default to C2 dev, per addendum A4); 47ab75da2 (pilot_bars) |
| 2 (final) | dcac6910f..e485386fc and 47ab75da2 | 3: check 1 accepted a C2b `.json` against the wrong rows; a cross-machine bit difference read as FAIL; `--record-eval` inputs were checked only after training | 6 | **c07afac1c** (bidc), **ce5cbef2e** (pilot_bars: relative tolerance 1e-12, no absolute floor) |

- **Blocking findings open: 0 known.** All six blocking findings across the two rounds have fix commits.
- **The round-2 fixes (c07afac1c, ce5cbef2e) are unreviewed**, because the cap was reached. Calibration evidence from this code counts as shipped only once a built-in review passes (coordinator ruling, 10-20).
- **Tests at c07afac1c:** creative 107/107. custom_io 36 passed, 13 failed; the 13 are the same failures as on the unmodified branch (FileNotFoundError, skills data not in the container). **pilot_bars at ce5cbef2e:** 24/24.
- **Non-blocking items left open:**
  - `make_c2c` writes files before checking answer and prompt lengths (zero expected on C2-style rows);
  - `--min-parents 0` is read as falsy (fails safe);
  - caps are stamped twice on derived checkpoints;
  - repeated sha reads in check 3.
- **New gate facts for the run card:**
  - the gate takes `.pt` records only;
  - every record carries its rows-file sha256 and a machine block;
  - a machine mismatch exits **4 (REFUSED)**, distinct from FAIL 1;
  - **P_0 must be trained, or at least its `--record-eval` made, on the gate machine (BensPC)**;
  - a kernel update on BensPC would refuse old records (`platform.platform()` includes the kernel version).
