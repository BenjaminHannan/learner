# slp-367 results: PASS (5/5 marks, both seeds; blind recount agrees, VERIFY.md)

Run 2026-09-25 ~02:05-02:38 UTC, CPU, $0, sealed code (SEAL.sha256.txt checks OK from the tree root).

| Mark | Bar (each seed) | Seed 1 | Seed 2 |
|---|---|---|---|
| P367.1 sleeps started inside a user turn | 0 | 0 | 0 |
| P367.2 word installs; new-people probes right | installed, ≥ 4/5 | yes, 5/5 | yes, 5/5 |
| P367.3 teach + filler replies identical to FORCED | 55/55 | 55/55 | 55/55 |
| P367.4 3 new turns, 60 s idle → no sleep | not SLEEP | THINKING | THINKING |
| P367.5 then 30 min → sleep | SLEEP | SLEEP | SLEEP |

Report only: IDLE slept 7 times a day (plus 1 in the quiet check). Because it can learn in the middle of the day, it
answered 10 of the 20 grandmother questions (K11-K20) that FORCED could only answer after the day was over: 10 right,
0 wrong, 0 "I don't know" in each seed (blind recount checked each against the taught world).

## Limits (from the blind recount, all shown)
- P367.1 passes by construction: the rule itself refuses to sleep during a turn. It was needed (a sleep would
  otherwise have started inside turns 10, 20, ... 70), but that counter is not saved in results.json.
- P367.4/P367.5 test the rule's arithmetic on a fake clock. "30 min idle" really means "30 min since the last sleep".
- P367.2 does not separate the arms: FORCED also scores 5/5. The "broken-chain" 6th probe is really an unknown-name probe.
- The last 5 turns of the day were not slept on in the evening steps (fewer than 10 new turns, under 30 min);
  in real use the 30-minute rule would pick them up.
- A message that arrives during a running sleep still waits for it to end (~1.5 min on CPU). Not fixed here.
- Suggested: the seal covers the 367 files and marks, not the world driver or loop code.

## What it means
Sleep no longer has to be forced once a day: the assistant now sleeps by itself when it is idle and has enough new
material, never in the middle of a reply, and it can learn during the day. It does not yet let a new message cut
a sleep short.
