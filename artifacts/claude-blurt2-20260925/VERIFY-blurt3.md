# blurt-3 (does sleep raise the guesser's luck?) = registered PASS (one CPU run)

Run: thread CPU, $0, 168 min, main 6a9112b91. DEV rule picked temperature 1.5 (41 vs 40). Practice seed 5; fresh test
seed 780: 66 puzzles after 14 overlaps dropped (the 80 in the passmarks was before drops). 30 blurts per test puzzle
= 1,980 per measurement. Reasoner right 23/400 in practice; wins on 151 of 377 misses.

| | seed 0 | seed 1 | mean |
|---|---|---|---|
| L0 lucky blurts before sleep | 63 | | 63 |
| W: slept on lucky hits + own right | 126 | 136 | 131 |
| C: slept on own right only (same count) | 85 | 87 | 86 |
| Test puzzles with at least one lucky blurt: before / W / C | 27 | 38, 38 | 3, 4 |
| Greedy solves (reasoner alone): before / W / C | 2 | 4, 7 | 3, 3 |

- U1 luck rises: 131 ≥ 1.5 × 63 = 94.5: PASS.
- U2 the wins caused it: 131 ≥ 1.3 × 86 = 111.8, and each W seed (126, 136) beats each C seed (85, 87): PASS.
- Proved wrong / inconclusive clauses: not triggered (151 wins; L0 63).
Verdict: PASS.

Important detail (found while verifying, not a mark): C's lucky blurts sit on only 3-4 puzzles. Practising its own
23 answers over and over made its guesses nearly all the same, so when it is right it is right 30 times, and on
almost every other puzzle it never gets lucky at all (27 puzzles hit before, 3-4 after). W kept its variety and
widened it: 38 puzzles hit, up from 27. So the counted marks, if anything, flatter C.
Shown: sleeping on lucky hits made the guesser right about twice as often on fresh puzzles and reach 11 more puzzles.
Not shown: that it replicates (the greedy-solve result shrank on replication, +11 then +6); transfer to other kinds of
problems; any effect on ideas.
Lesson for sleep: practising only the same few known answers kills the guesser's variety (a creativity collapse).
