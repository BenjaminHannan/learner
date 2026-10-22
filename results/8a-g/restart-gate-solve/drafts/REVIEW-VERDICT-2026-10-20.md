# Built-in /code-review verdict on B2 + B3 (coordinator ruling), 2026-10-20

**Reviewed diff:** `2d1d3ae14b..7a76fcdab0` on `claude/restart-gate-solve`: B2 (0c15144595) and B3 (7a76fcdab0).
**Verdict: NOT PASSED. The package stays DRAFT.**
- **B1 is still open and blocking.** It is ruled by the coordinator session, but that ruling has not yet been confirmed in this session. Its amendment and code are not written.
- **One new item needs a wording ruling (R1 below).** The rest are fixable defects or documentation gaps.
- Per the standing condition, I did not patch.

**Tests at 7a76fcdab0 (solve session, idle):**
- `test_gatefix`: 38 of 38 pass.
- Pack suite on the drafts: ALL OK, 37 `ok` lines.
- `patch -p1` on a fresh copy of the pack reproduces `g2fa4_supervisor.py`, `install_g2fa4.py` and `tests/test_probe.py` byte for byte.
- `git diff 2d1d3ae14b..7a76fcdab0 -- drafts/rejudge_probe.py` is empty, and the pack is untouched.

**B2 pass marks (coordinator):** all four are met by tests (`t_b2_running_gate`, `t_b2_deferral_unit`, `t_b3_*`). Run against the old supervisor, `t_b2_running_gate` fails, so the test does detect the old behaviour.

## Needs a ruling
| # | where | finding | proposed |
|---|---|---|---|
| R1 | `g2fa4_supervisor.py:277` (`EARLY_DEFERRED`, the ruling's verbatim line) | "do not read this result until the probe's P1b passes" names P1b alone as the read condition. The reading gate is the probe as a whole: P1, P1b and its verdict under PREREG §4 / Amendment 1. With B1 open, P1b can pass while the probe never reaches a verdict (identical restarts), so the line would make an unreadable run look readable. | Change the wording to "do not read this result until the probe-resume reading passes (P1, P1b and its verdict)". This edits the coordinator's verbatim text, so it needs a ruling. |

## Fix in the next round (non-blocking)
| # | where | finding | verdict |
|---|---|---|---|
| F1 | `g2fa4_supervisor.py:707`, md ~975 | The deferral line is also printed on a trace-A **FAIL**, so a stopped run tells the operator to wait for P1b. | Real. Print it only when trace A passed, and add a test that it is absent on FAIL. |
| F2 | `drafts/gatefix.patch` | `tests/fake_runner.py` now has two new flags but is not in the patch, and README says the patch covers three files. A patched pack cannot run the B2/B3 tests. | Real. Add fake_runner to the patch and the cmp check. |
| F3 | `g2fa4_supervisor.py:360` | When rstep+1 is missing, `early_window.reason` blames updates 2-3 and does not name the missing first update. The docstring disagrees with when `reason` appears. | Real, misleading record. Fix the text. |
| F4 | `PREREG-trace-a2.md` (Amendment 1 "early-window item (hard)") | The pre-registered text does not record the B2 deferral or the B3 contiguity/fail-closed rule. Only the README does. | Add a dated clarification line citing the coordinator ruling, as was done for item 3. Documentation of a ruling; no bar moves. |
| F5 | `install_g2fa4.py:24,314` | `--trace-a-early` help and the docstring do not describe the deferral or the new hard item for a missing rstep+1 (and N3 from the last verdict is still open). | Doc fix (with N3). |
| F6 | `drafts/README.md` | No open-items list. B1, N2 and N3 are not recorded as open, and the DRAFT status is not restated. | Doc fix. |
| F7 | `g2fa4_supervisor.py:829` | The deferral is detected two different ways (`early_deferred()` vs the truthiness of `early_window`). | Cleanup. Use `early_deferred()` everywhere. |

**Still open from 2026-10-18:** B1 (blocking), N2 (calibration validated before the two-resume verdict), N3 (installer reads the bar at import), N4/N5 (cosmetic or duplicate code).

## Next
1. A ruling on R1, and confirmation of B1 in this session.
2. Then one round: the B1 amendment as its own commit, the B1 code, R1 if ruled, F1-F7, N2 and N3, with regression tests.
3. Then re-test and re-review.
