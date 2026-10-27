# slp-364c pass marks (registered 2026-09-25 ~05:20 UTC, before its blind bench exists)

Change (one set, inside v2's own new checks): gate v3 (scripts/claude_slp364c_gate.py) = v2 with
(1) the new-people check run in a forked copy of the process, so the real loop's memory is never touched;
(2) one correction per word inside that check, asked back; (3) the restart check also asks words known before the night.
Why: slp-364b registered FAIL. v2 caught 17/20 but broke later teaching on 20/20 honest nights (P364b.5 0/20).
Both arms: slp-360 + slp-368 lock + slp-361 undo. Twin: gate v1 (slp-364) in the same run. v2 is not an arm
(it is known to be harmful). Runner: scripts/claude_slp364c_run.py (the 364b runner with v3 and the new bench).
Bench: scripts/claude_slp364c_bench.py, a third bench written by a separate agent told not to open any gate or
result; its probes include new teaches and a correction after the sleep.

| Mark | Bar |
|---|---|
| P364c.1 faulty nights rejected by v3 | ≥ 18/20 |
| P364c.2 honest nights rejected by v3 | ≤ 1/20 |
| P364c.3 v3 catches minus v1 catches | ≥ +3 |
| P364c.4 every v3 night: main notebook log unchanged and the sandbox restored | 40/40 |
| P364c.5 honest nights: the bench's user-probe replies identical under v3 and v1 | 20/20 |

Proved wrong if: v3 catches fewer than 15/20, rejects more than 2/20 honest nights, or changes any honest night's replies.

## Disclosures written at seal time
- Dev on the opened 364b bench (9 cases): 6 honest nights kept with user replies identical to 364b's v1 arm (0 differences,
  the P364b.5 defect is gone there); the corrections-ignored and restart-only-forgetting misses are now caught; the
  "confidence cut 100x" silent no-op (slp364b-27) is still missed. v3 has no rule aimed at it.
- The likely cause of v2's damage is inferred, not tested; v3 avoids the question by never touching the real loop's memory.
