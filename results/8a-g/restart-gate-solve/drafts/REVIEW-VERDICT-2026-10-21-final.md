# Built-in /code-review verdict: final round (2 of 2), 2026-10-21. NOT CLEAN, PACKAGE PARKED

**Reviewed diff:** `1705e24474..90f8150347` on `claude/restart-gate-solve`: PREREG errata E1/E2 (255fa96ae6) and the E1/E2 text sync plus L1, L2, L5, L7 (90f8150347).
**Verdict: NOT CLEAN. Per the coordinator's ruling (2 review rounds maximum), the package is PARKED and stays DRAFT. There is no round 3.** Spend $0.

**Tests at 90f8150347 (solve session, idle):**
- `test_gatefix`: 47 tests, 0 skipped.
- Pack suite on the drafts: ALL OK, 37 `ok` lines (the agent's run).
- `patch -p1` on a fresh pack copy reproduces all 4 patched files byte for byte.
- The pack, `PREREG-trace-a2.md` and `g2fa4_supervisor.py` are untouched by 90f8150347.

**Unchanged throughout:**
- the registered P2 verdict (1000-trace test);
- trace A's default behaviour (equal to the pack);
- the bars (0.005, 0.01, 0.02, 2x);
- the ruled `EARLY_DEFERRED` wording;
- the verdict logic of `rejudge_probe.py` this round (text and serialisation only).

## Findings, ranked (solve-session verdict on each)
| # | where | finding | verdict |
|---|---|---|---|
| 1 | `rejudge_probe.py:332` / `:253` | The trace-A value `v` is not validated. `--trace-a-mean -inf` (or a negative value, or a TRACE-A json with a non-finite `mean_abs`) passes `v <= limit`, so the verdict is **INSIDE, exit 0**. NaN gives UNRESOLVED (window). | **The one substantive defect.** It has been in the tool since the first draft, and this round's test only checked the serialisation. Fix: refuse a non-finite or negative `v` with exit 3. **Must be fixed before any real use.** |
| 2 | `PREREG-trace-a2.md:80` | E2's wording limits the whole deferral bullet to a passed trace A. The supervisor still writes the `early_window {deferred_to: 'probe P1b'}` record on a FAIL; only the line is suppressed. | Text precision in my erratum. The line is limited to a passed trace A; the data record is kept in both cases. A one-sentence fix. |
| 3 | `PREREG-trace-a2.md:88` | The Errata section says the original wording was kept for both errata. E2's note paraphrases it instead of quoting it. | Text. Quote the original E2 sentence. |
| 4 | `tests/test_gatefix.py:1843` | The first half of the E2 wording check can never match (uppercase in a lowercased search), and the check searches the whole file. | Test quality. |
| 5 | `g2fa4_supervisor.py:464` | `PROBE-RESUME-<job>.json` can still contain `Infinity` (the ESCALATE case). | Known, listed in the README open items. A shared strict-JSON writer would fix both files. |
| 6 | `rejudge_probe.py:121` | `strict()` special-cases the key `ratio` at every depth and writes two flags for one fact. | Cleanup. |
| 7 | `install_g2fa4.py:185` | The `early` and `early_bar` parameters can disagree; `early_bar=None` meaning "off" would be enough. | Cleanup. |
| 8 | `tests/test_gatefix.py:2284` | The patch and cmp check runs twice per suite. | Cleanup. |
| 9 | `install_g2fa4.py:175`, `test_gatefix.py:806` | Stale "read lazily" comments after L1. | Doc. |

**Still open from earlier rounds (non-blocking):** L3 (ESCALATE md line for a probe that rejudge would refuse), L4 (the calibration decision is made in two places), L6 (the F7 source-text test), L8 (a no-op ternary).

## What parking means
- **No more fix rounds without a new ruling.** The package is DRAFT. Nothing in it is installed on the PC, and nothing here approves a halt, a bar or spend.
- **What is solid:**
  - the gate design (PREREG with Amendments 1-2, a draft for Ben);
  - the probe guard (the wrong-job checkpoint refusal);
  - the B1/B2/B3 behaviour;
  - the CPU positive controls.
- **Before anyone uses `rejudge_probe.py` on a real probe,** finding 1 must be fixed: a few lines plus a test. Until then, run it only with the default trace-A value (0.0282), which avoids the bad path.
- **The smallest unpark:** finding 1, plus the text fixes 2-3 and 9. It would need the coordinator's ruling and a further review.
