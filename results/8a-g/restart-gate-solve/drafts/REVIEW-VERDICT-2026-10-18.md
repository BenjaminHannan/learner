# Built-in /code-review verdict on the restart-gate drafts: fix rounds 1-2 + item 7 (ruling Q95), 2026-10-18

**Reviewed diff:** `acafb1fbce~1..3812a40c8b` on `claude/restart-gate-solve`. That covers the Amendment 1 clarification, review items 1-6 and 9 (425db638f9), zero-risk items 8 and 10 (cb1828b80a), and item 7 per Q95 (3812a40c8b).
**Verdict: NOT PASSED. The package stays DRAFT.** Three blocking items are open. Two are new from this re-review and need a decision; one is carried over and still awaits its ruling. Per the standing condition, I stopped and did not patch.

**Tests at 3812a40c8b (solve session, idle machine):**
- `test_gatefix`: 34 of 34 pass.
- Pack suite on the drafts: ALL OK, 37 `ok` lines.
- `gatefix.patch` applied with `patch -p1` to a fresh copy of the pack reproduces all three changed files byte for byte.
- `t_kill_fails_then_works` is a pre-existing timing flake. It failed 1 time in 10 on the UNMODIFIED pack.
- The reviewer's own environment could not run the installer test (the pack files are absent from the drafts folder). That is a setup issue, not a code finding.

**Unchanged by everything here:** the registered probe rule P2, and the reviewed two-resume reading of `rejudge_probe.py` (equality tests over 1000 and 3000 random traces). Amendment 1 adoption remains Ben's. Nothing here approves spend, a bar or a halt.

## Blocking (decision needed before another fix round)

| # | where | finding (confirmed against the code) | why it blocks | proposed resolution (needs a ruling) |
|---|---|---|---|---|
| B1 (carried) | `rejudge_probe.py` calibration path | Bit-identical resumes (R1 = R2, N̄ = 0) with D̄ > 0 give ratio = ∞ and UNRESOLVED_CALIBRATE ("run 2 more resumes"). Those resumes repeat R1/R2 exactly, so the duplicate refusal (item 2) rejects them. The verdict can never resolve. | This is PREREG falsifier (c), the case that says the noise diagnosis is wrong, and the tool sends the operator into a loop. | Add an explicit outcome: "FRAMING FALSIFIED: restarts identical but differ from the logged run; escalate". It fires only when N̄ = 0 and D̄ > 0. It changes the pre-registered reading text, so it needs a ruling. |
| B2 (new) | `g2fa4_supervisor.py:336` (`trace_a`, opt-in `--trace-a-early`) | `trace_a` judges only the first resume that has redone updates. An unplanned crash 1-2 updates after a checkpoint makes that resume the judged one. Its ≤ 2 redone updates now give a hard "early window cannot be checked" FAIL that stops the run. Any earlier resume also suppresses the planned kill (`not ev.resumed`, line 770), so no later resume can supply the window. | A healthy run is stopped by a running gate. That is the expensive false stop the whole solve argues against. It only affects the opt-in flag, but that flag is what Amendment 1 recommends. | Either (a) "not computable" in the running gate is recorded and defers to the probe (reading gate), not a stop; or (b) `trace_a` judges the first resume with ≥ 3 contiguous redone updates and records the others. A design choice. |
| B3 (new) | `g2fa4_supervisor.py:318-331` (`trace_a`) | The early window is `common[1:3]` of the step intersection. Nothing checks that `common[0] = rstep+1` and `common[1:3] = [rstep+2, rstep+3]`. A missing train line at rstep+1 shifts both the "first redone update" and the early window, and the message still names them as the defined updates. The probe checks contiguity; trace A does not. | It prints a check that was not computed as defined, which ruling Q95 explicitly forbids. | Require contiguity. Otherwise mark the window "not computable", which then falls under the B2 decision. This is mechanical once B2 is decided. |

## Non-blocking (verdict per item)

| # | where | finding | solve-session verdict |
|---|---|---|---|
| N1 | `g2fa4_supervisor.py:361` | A missing listed exact field is a hard fail, and the real aux keys are "unchecked" | **Dismissed with evidence:** real b3g2 train lines carry `lr`, `rounds`, `plan_fallback`, `plan_gapped`, `plan_rows` (`posctrl/raw/a4_e0.01.json`, the real model on CPU). GPU is untested; that goes in a README note. |
| N2 | `rejudge_probe.py:283` | The `--calibration` file is validated before the two-resume verdict is known, so a bad calibration file can hide a clear OUTSIDE/INSIDE behind exit 3. `calibration_source` is recorded even when the calibration is not applied. | Real, introduced by fix round 1. Fix: compute the two-resume verdict first and validate the calibration only when it will be applied. Medium. |
| N3 | `install_g2fa4.py:149-163` | The bar is parsed from the supervisor source at import; a missing file or malformed line kills every installer mode before it logs. `--help` and the docstring still say 0.005. | Real (carried from the last review). Fix: parse lazily, only with `--trace-a-early`; print the loaded value in help. |
| N4 | `g2fa4_supervisor.py:1278` | The JSON and MD asides can get different stamps | Cosmetic. One stamp per pair. |
| N5 | `rejudge_probe.py:348` | `aside()`, the `EARLY_LIMIT` default and `early_of` are duplicated from the supervisor | Cleanup. A small shared stdlib helper would remove the duplication. |
| N6 | `README.md:81,89` | The item-5 row and the "30 tests" count are stale after item 7 | Doc fix. |

## What happens next
B1 and B2 need a coordinator ruling (B1 touches pre-registered reading text, so possibly Ben's). B3 follows mechanically from B2. Once ruled, one fix round would cover B1-B3 plus N2, N3 and N6 with regression tests, followed by a re-test and a re-review. N4 and N5 can wait or go in a separate zero-risk commit.
