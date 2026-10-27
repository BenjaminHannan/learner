# rsn-358b2 recount (sleep research thread, 2026-09-26 15:20 UTC)

Recounted from run/transcripts-{5,6,7}.jsonl on origin/builder-outbox with the sealed parser and checker (parse_grid / is_solution). The true puzzle was read back from each request. Every count matches the builder's RESULTS.md:

| size | alone right | bridge right | bridge "couldn't" | bridge wrong | copy exact | copy unreadable |
|---|---|---|---|---|---|---|
| 5 | 0 | 19 | 73 | 8 | 25 | 63 |
| 6 | 0 | 30 | 63 | 7 | 39 | 57 |
| 7 | 0 | 13 | 78 | 9 | 28 | 66 |

**Verdict stands: INCONCLUSIVE.** B0 (copy exact >= 80/100) is missed at every size. This was plumbing only (NOTE-gate.md); the 0.2d gate is 358b3.

What it shows (report only):
- The 1B alone solved 0 of 300.
- When the square reached the loop net intact, the net solved it: ceiling C was 100/95/71 with 358a's loop-s1.
- The bridge turned 100 wrong answers per size into mostly honest "couldn't"s.

The failure is the 1B's copying. It drops blanks inside runs of "_" (seen in the transcripts: "_ _ _ _ 2 4" copied as "_ _ _ 2 4"). The 8/7/9 bridge wrong answers are copies that were wrong but still solvable, which the checker (seeing only the copy) could not catch.

**For 358b3:** the grid is read by code (the shared puzzle reader), never copied by the 1B. The talker only phrases the reply.
