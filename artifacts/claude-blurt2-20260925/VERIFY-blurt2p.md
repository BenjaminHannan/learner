# blurt-2p placebo check = registered FAIL (not proved wrong)

Run: thread CPU, $0, 192 min, main 8813be47c. DEV rule picked temperature 1.5 (44 vs 40). Practice seed 3, fresh test
seed 778 (120 puzzles after 30 overlaps dropped). Reasoner right 14/400; wins on 171 of 386 misses (316/11,580 blurts).

| | seed 0 | seed 1 | mean |
|---|---|---|---|
| S0 before sleep | 8/120 | | 8 |
| W: sleep on right guesses (+ own right) | 14 | 13 | 13.5 |
| P: sleep on wrong guesses (+ own right), same puzzles, same count | 10 | 9 | 9.5 |

- P1 right answers matter: W − P = +4 (mark +5): FAIL. Each W seed beats each P seed: yes.
- P2 replication: W − S0 = +5.5 (mark +8): FAIL.
- Proved wrong (P ≥ W): no.
Verdict: registered FAIL.

Across all three runs (fresh puzzles, reasoner alone): W − S0 = +11, +6, +5.5; W beats its control every time (C: +11,
+6.5; P: +4). Practising on wrong guesses gave +1.5, so a small part of the gain is just practice.
Shown: sleeping on lucky hits helps a little, reliably (every W seed above every control seed in all runs).
Not shown: a gain as big as the +8 bar; the first CPU run (+11) looks like the lucky high end.
