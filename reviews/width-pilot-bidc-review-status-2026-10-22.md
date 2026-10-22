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

## Extra final round (allowed by the coordinator 10-22), on c07afac1c and ce5cbef2e only

- **Gate commit c07afac1c: 0 blocking.**
  - A record from another machine can never pass; it is REFUSED with exit 4.
  - The ids and rows-file sha256 checks run before any comparison.
  - `.json` records are refused.
  - The guard before training covers a missing `--caps`, a missing rows file, too few rows, and a MANIFEST mismatch.
- **pilot_bars ce5cbef2e: 1 blocking.** With a bar at 0, such as the card's worst-seed rule "d_i > 0 on every seed-index", float noise from the inputs could flip the verdict (reproduced: a mean of 4.6e-17 fired `mean > 0`). **Fixed once in 6b1cf5d6f:** the tolerance is now 1e-12 × max(|statistic|, |bar|, largest |arm mean|). There is a regression test, and 25/25 pilot_bars tests pass.
- **Also fixed, non-blocking:** the post-training `--record-eval` wrapper now also catches SystemExit, so RESULT.json survives a short rows file. bidc commit after c07afac1c; 19/19 targeted gate tests pass.
- **Non-blocking items left open, for the coordinator:**
  - `platform.platform()` includes the kernel or Windows build, so an OS update between P_0's training and the gate makes check 3 REFUSED for good. Relaxing this to CPU, torch and thread fields only is a one-line change if ruled.
  - MKL/oneDNN environment variables (e.g. `MKL_CBWR`) and `torch.get_float32_matmul_precision()` are not in the machine block, so an environment mismatch would read as FAIL rather than REFUSED. Mitigation: run `record` and the gate from the same shell script.
  - The guard does not check that the `--record-eval` directory exists or that `--record-n` equals the gate's `--n`.
  - The MANIFEST check in `rules_real.load_split` is an `assert`, which `python -O` strips.
  - Report display: a strict comparison can hold where the report shows the statistic equal to the bar at 9 digits.
- **Status:** the review rounds are exhausted. The fixes after this round (6b1cf5d6f; train.py SystemExit) are unreviewed. **The code is PARKED** for the coordinator.

## Final blocking-only review (coordinator 10-22; fresh reviewer) on 6b1cf5d6f and e0d65adb6

**Blocking findings: 0.** Under the coordinator's ruling the code now **counts as shipped**: `claude/bidc-calibration-drafts` at e0d65adb6, and `pilot_bars` at 6b1cf5d6f. Open non-blocking items stay as they are, with no code change (coordinator). Instead the run card requires that the P_0 record and the gate run on BensPC from the same script, with no OS update in between and the MKL environment set identically: `reviews/width-pilot-bidc/PC-JOB-bidc-gate-record.md`.
