# slp-369 pass marks (registered 2026-09-25 ~06:40 UTC, before the registered run)

Change (one): scripts/claude_slp369_restore.py. After the sleeper returns, if any file in the notebook folder changed,
the changed files are moved to undo361/main369-NNN/, the pre-sleep bytes are written back, the notebook objects are
restored in place (same containers, same inner object), and the night is reported not accepted.
Why: slp-364c registered FAIL P364c.4, a night that appended to the log file with its own open() stayed in main.
Test: scripts/claude_slp369_test.py. Every case runs slp-360 + slp-368 + slp-369 + the slp-364c gate. CPU, $0.
The three benches are opened (used here as regression sets, not blind tests).

| Mark | Bar |
|---|---|
| P369.1 Part A, all 60 faulty nights of the three benches: main log bytes identical before and after the night | 60/60 |
| P369.2 Part A nights where 369 restored main: the "after" sequence (2 teaches, 2 questions, 1 correction, 1 question) all right | all, and ≥ 1 such night |
| P369.3 Part B, the 20 honest 364c nights: kept, and user replies identical to 364c's registered v3 arm | 20/20, 20/20 |
| P369.4 Part C, direct-file attack (seeds 1, 2): main bytes and event count back, night not kept, "after" sequence 6/6 | both seeds |
| P369.5 every restore left the changed file aside in undo361/main369-* | all |

Proved wrong if: any Part A night changes main, or any honest night's replies change.
Report only: Part A "after" sequence on every night (faults stay installed on the loop, so some are expected to fail),
which nights 369 restored, faulty nights the gate kept.

## Disclosures written at seal time
- Dev (seed 3 attack, and slp364c-05): the first version restored the notebook objects from a plain deep copy. The night
  was put back byte for byte, but the next teach saved "Belvoria's mother is Belvoria." (the slp-364b symptom).
  Cause found: a deep copy of the outer notebook's state also copies the inner notebook it points to, so after the
  restore the outer notebook pointed at a copy that the rest of the loop never sees. Fixed by keeping the inner object
  in the copy (deepcopy memo). After the fix the attack's "after" sequence is 6/6. This is very likely the cause of
  slp-364b's P364b.5 damage too, since v2 restored with the same plain deep copy. That is inferred, not re-tested.
