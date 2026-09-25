# slp-364c results: REGISTERED FAIL (P364c.4 only; the catch-rate marks pass)

Run 2026-09-25 ~05:45-06:10 UTC, CPU, $0, sealed gate and sealed blind bench (seal files check OK), 80 nights, 0 errors.

| Mark | Bar | Result | |
|---|---|---|---|
| P364c.1 faulty nights rejected by v3 | ≥ 18/20 | 18/20 | pass |
| P364c.2 honest nights rejected by v3 | ≤ 1/20 | 0/20 | pass |
| P364c.3 v3 minus v1 catches | ≥ +3 | 18 − 11 = +7 | pass |
| P364c.4 every v3 night: main notebook unchanged and sandbox restored | 40/40 | 39/40 | FAIL |
| P364c.5 honest nights: user replies identical under v3 and v1 | 20/20 | 20/20 | pass |

Proved-wrong clause: not triggered. The sleeper's own flag caught 3/20.
Per category (v3, v1): file-live-mismatch 2/2 (0), post-sleep-teaching 2/2 (0), silent-noop 2/2 (1), over-abstain 1/1 (0),
wrong-route 1/1 (0), forgetting 2/2 (2), minority-wrong 2/2 (2), notebook-write 2/2 (2), unasked-word-answered 1/1 (1),
scrap-answers 1/1 (1), taught-overridden 1/1 (1), earlier-word-corrupted 1/1 (1), made-up-answer 0/2 (0).

## What failed (bench opened after the run)
- **P364c.4, slp364c-05:** the fault appends a RETRACT line straight to the notebook FILE with its own open(), bypassing
  Notebook._append, so the slp-368 lock cannot stop it (a limit 368 stated). v3 caught it (M: main changed, plus R) and
  the night was rejected, but nothing puts main back, so the file keeps the line. This is the undo stack's gap, not a
  missed catch.
- **made-up-answer 0/2:**
  - slp364c-07 answers a broken chain with the last person it reached. The gate allows names met along the chain in a
    reply (so "I don't know G01's mother." is fine), and a changed lure reply graded "other" is not flagged.
  - slp364c-34 snaps an unknown relation phrase to the nearest learned word. The gate never asks near-miss phrases.

## Next
- 369 (one change): when a night is rejected, or the lock sees main change, put main's log back to its pre-sleep bytes
  (the added tail moved aside to undo361/, never deleted) and reload the notebook objects.
- 364d (gate v4, a 4th blind bench): flag changed lure replies graded "other" that do not abstain; add near-miss
  relation lures (e.g. "brother" for "mother") for learned words.
