# Aha-1 results (prereg `PREREG-aha1.md`)

## Attempt 1 (2026-10-24, Vast box 57463018, A100 SXM4, $0.443/h): no result
- Launched 04:05Z with `AHA1=1` (arms nb sleep, aha sleep, aha c16). By the job's time limit (~1.83 h) the box label
  showed no result file at all, so not even the control arm (Creative-2's sleep, 18 min on its own box) finished.
- Vast's log URLs returned 403 for the whole run, and the box would not reach the stopped state, which `cat` needs,
  so the log could not be read. The box was destroyed at about 2.1 h (~$0.93 of the $1 cap). Cause unknown.
- Fix for next time: `label_report.py` now puts the eval numbers (`acc`/precision) and the last log line in the
  box label, so progress is visible without the log service.
- No marks are judged. The prereg is unchanged; the next attempt runs the same three arms.

## Attempt 2 (2026-10-24 11:31-12:20Z, BensPC RTX 5070 Ti, seed 0, $0): FAIL
Raw JSONs in `results/aha1/` (sha256 prefixes nb e788e4f8, aha be822db8, aha_c16 0bcb1a2a).

| arm | C2 dev C16 acc | answered | precision | answered with a branch (right) | HARD C16 acc / prec | C2 dev F1 |
|---|---|---|---|---|---|---|
| nb (Creative-2 ban), post-sleep | **74.2** | 75.0 | **99.0** | 0 | 16.3 / 74.2 | 43.0 |
| aha, post-sleep | **65.2** | 71.5 | **91.3** | 16 (2) | 17.3 / 77.6 | 44.5 |
| aha, pre-sleep | 21.5 | 24.2 | 88.7 | 7 (1) | 6.3 / 76.0 | - |

By kind, C2 dev post-sleep C16 (nb -> aha): affine 42 -> 63, double_add 67 -> 63, last_digit 88 -> 37, sq_plus 75 -> 63, square 100 -> 100.
Sleep data: aha found fits on 283/1024 pool puzzles (nb 210); 61 of aha's 716 Qwen-found pairs contain a branch.

## Verdicts
- P1 FAIL: 65.2 vs 74.2, -9.0 (mark: no worse than -2).
- P2 FAIL: precision 91.3% (mark: >= 95%).
- Not "wrong": precision is above 80% and the gap is under 10.

## Cause (shown, from the counts)
- 14 of aha's 16 wrong answers on C2 dev are branching programs (2 of 16 branching answers right). Without branches, aha's
  precision is 165/167 = 98.8%. Hiding one example does not stop threshold cheats such as
  `lambda x: x if x < 23 else 4` on a last-digit puzzle (9->9, 24->4, 6->6): the hidden example is still predicted.
- The accuracy loss is mostly last_digit (88 -> 37). There, small inputs map to themselves, so a threshold covers any one
  hidden example. Branch pairs also went into sleep (61 pairs).
- The gain is real but smaller: hiding examples found more fits for sleep (283 vs 210 pool puzzles), and affine went 42 -> 63.

Plain reading: "predict what you weren't shown" is a weak test when the examples are few and easy to cover. The other half of
an aha, preferring the simplest rule, is missing. Next one-change test (Aha-2, to be pre-registered): same as aha, but choose
the shortest fitting program (fewest AST nodes) among the 16, in eval and for sleep data.
Note: nb's rerun (74.2 / 99.0) is higher than Creative-2's A100 run (67.6 / 97.7): run-to-run spread on this test is several points.
