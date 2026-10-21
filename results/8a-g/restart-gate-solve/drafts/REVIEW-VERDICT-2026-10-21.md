# Built-in /code-review verdict: B1 code + fix round, 2026-10-21 (the single review allowed by the coordinator's Oct 20 ruling; now PARKED)

**Reviewed diff:** `6af9705d31..206361aff3` on `claude/restart-gate-solve`. It covers PREREG Amendment 2 plus the B2/B3 clarification (667bddaf22), the B1 ESCALATE code (7c9dc9a1ef), and the fix round F1-F3, F5-F7, N2, N3 (206361aff3).
**Verdict: NOT CLEAN. No defect in the gate logic was found. The package stays DRAFT and is PARKED** (one review round under the ruling; cap of 2 in total).

**What does not need fixing:**
- **Gate logic:** the registered P2, the default `trace_a`, the bars and the ruled `EARLY_DEFERRED` wording are unchanged.
- **B1 ESCALATE:** behaves as specified. 6000 random traces against the pre-B1 logic all match, except the 929 that meet the trigger.
- **B1 / B2 / B3:** all resolved in code.

**Tests at 206361aff3 (solve session, idle):**
- `test_gatefix`: 44 of 44 pass.
- Pack suite on the drafts: ALL OK, 37 `ok` lines (the agent's run).
- `patch -p1` on a fresh copy of the pack reproduces `g2fa4_supervisor.py`, `install_g2fa4.py`, `tests/test_probe.py` and `tests/fake_runner.py` byte for byte.
- The pack and `PREREG-trace-a2.md` are untouched by the code commits.

## Must fix before a clean pass: pre-registered text errors (written by the solve session; no bar moves)
| # | where | finding | fix |
|---|---|---|---|
| E1 | `PREREG-trace-a2.md` Amendment 2, "Order" (copied into `rejudge_probe.py` AMEND2 and every output) | "the N̄ = 0, D̄ = 0 case … stays INSIDE by the existing rules" is wrong. With the default trace-A value 0.0282 > max(0.02, 0), the existing rules give **UNRESOLVED (window)**. The code and the test are correct; the sentence is not. | Erratum: "stays judged by the existing rules (INSIDE, or UNRESOLVED (window) when the trace-A value is above the 0.02 floor)". Re-copy into AMEND2. |
| E2 | `PREREG-trace-a2.md`, B2/B3 clarification | It says the deferral is always recorded with the line. Since F1, the line is printed and stored only when trace A **passed**. | Erratum: "…on a trace A that passed; a failed trace A carries no deferral line". |

## Fix later (non-blocking)
| # | where | finding |
|---|---|---|
| L1 | `install_g2fa4.py:187` | The bar is read twice. The value checked in the `[ok]` row is not the one written to the plan, and the second read is outside the error handler. Fix: pass `early_bar` through. |
| L2 | `rejudge_probe.py:328` | Every ESCALATE has ratio = ∞, so REJUDGE json contains the non-standard `Infinity` token. Fix: write `null` plus a flag. |
| L3 | `g2fa4_supervisor.py:1021` | The "reads as ESCALATE" md line can appear for a probe that `rejudge_probe.py` would refuse (< 3 updates). This is unreachable via `probe-resume` since item 7, but possible from a direct call. |
| L4 | `rejudge_probe.py:320` | The "apply the calibration?" decision is made in two places (`main` and `rejudge`). Cleanup. |
| L5 | `tests/test_gatefix.py:2128` | The patch test counts as passed when `patch` is missing (Windows). It should report SKIPPED, not ok. |
| L6 | `tests/test_gatefix.py:1920` | The F7 single-decision check counts source text, which is brittle. |
| L7 | `README.md:34` | The test-count breakdown doesn't add up (lists 5, says 6; the parts sum to 45 vs 44). |
| L8 | `tests/test_gatefix.py:2095` | A no-op ternary. |

## Next
The package is parked under the review cap. The smallest path to a clean pass:
1. E1 and E2 as PREREG errata. They are text only and move no bar. The AMEND2 copy in `rejudge_probe.py` is re-synced and the text test re-run.
2. Optionally L1, L2, L5 and L7 in a separate commit.
3. A second (final) review round.

That is the coordinator's call.
