# Aha-1 results (prereg `PREREG-aha1.md`)

## Attempt 1 (2026-10-24, Vast box 57463018, A100 SXM4, $0.443/h): no result
- Launched 04:05Z with `AHA1=1` (arms nb sleep, aha sleep, aha c16). By the job's time limit (~1.83 h) the box label
  showed no result file at all, so not even the control arm (Creative-2's sleep, 18 min on its own box) finished.
- Vast's log URLs returned 403 for the whole run, and the box would not reach the stopped state, which `cat` needs,
  so the log could not be read. The box was destroyed at about 2.1 h (~$0.93 of the $1 cap). Cause unknown.
- Fix for next time: `label_report.py` now puts the eval numbers (`acc`/precision) and the last log line in the
  box label, so progress is visible without the log service.
- No marks are judged. The prereg is unchanged; the next attempt runs the same three arms.
