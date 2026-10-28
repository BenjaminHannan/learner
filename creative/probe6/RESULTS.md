# Probe-6 TEST results (run once, as sealed in PREREG.md; arm and t from DEV.md, committed before)

Test pools: the frozen Probe-5 LFM3 pools (96 tasks, 38 traps, 12 tries each), Probe-5's TEST-T and SELF scores, no new tries. Chosen: J-D1 (d1-3B Q8_0 GGUF, llama.cpp `/v1/systemone`, same prompt as dev), t = 0.7. Command: `test_stage.py` (raw output `out/test_report.json`).
Rows in `tries/results.jsonl.gz` do carry `final_reply` (used as is; 159 of 1152 are empty, and none of those has a `?` in the last assistant message either). The repo copy is gzipped, so it was decompressed to a scratch file and passed with `--tries` (a small option added to test_stage.py).

Sanity check passed: plain TEST-T reproduces Probe-5: 57.3 all / 21.1 traps / 81.0 non-traps (replay gate 100%).

## Verdict: PROVED WRONG
A1 (all >= 62.3): FAIL (57.3). A2 (non-trap >= 77.5): ok (81.0). PROVED WRONG mark (all <= 58.3): met, 57.3.

| picker | all | traps | non-traps |
|---|---|---|---|
| TEST-T (Probe-5) | 57.3 | 21.1 | 81.0 |
| ASK-GATE, J-D1, t=0.7 | 57.3 | 21.1 | 81.0 |
| ORACLE-GATE (true labels) | 65.6 | 42.1 | 81.0 |
| J-HAIKU gate, t=0.7 (reference) | 60.4 | 36.8 | 75.9 |

Judge test AUROC (trap vs non-trap, 96 tasks): J-D1 0.751 (dev 0.744); J-HAIKU 0.915 (reference).

## Why ASK-GATE equals TEST-T (shown)
d1's P(ask) is low on most tasks (test median 0.28, max 0.83); only 3 of 96 tasks reach 0.7 (all three are traps), and gating those changed no winner. At t=0.7 the gate was effectively off. Dev showed the same: 3 of 248 tasks reached 0.7. t was fixed before the test and was not re-tuned; no other t was scored on test.

## Diagnostic: asking tries in trap pools (shown, 38 trap pools x 12 tries = 456 tries)
| | pass | fail |
|---|---|---|
| tries whose reply contains `?` | 82 | 101 |
| tries with no `?` | 21 | 252 |

Asking tries pass 45% of the time in trap pools vs 8% for non-asking tries. 28 of 38 trap pools contain an asking try; in 19 of them an asking try passes. In non-trap pools asking tries pass 2 of 178 (1%); 2 non-trap pools contain a passing asking try.

## Reading (suggested)
- The rule's ceiling on test (ORACLE-GATE) is +8.3 points, and a gate with a good judge (Haiku, AUROC 0.915) gains +3.1 overall while losing 5 points on non-traps (false asks), so A1 and A2 together are hard even with a strong judge at t=0.7.
- J-D1 ranks traps above non-traps reasonably (AUROC 0.75) but its probabilities are too compressed for a fixed t of 0.7; a lower t might behave differently. That is untested on purpose (post-hoc tuning on the test pools would not be a test).
