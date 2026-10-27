# blurt-2b (practise every lucky hit) = registered FAIL, PROVED WRONG on the CPU run

Run: thread CPU, $0, 169 min, main c7f740b90. DEV rule picked temperature 1.0 (45 vs 35). Practice seed 4, fresh test
seed 779 (119 puzzles after 31 overlaps dropped). Reasoner right 26/400; wins on 167 of 374 misses; 128 extra distinct
hits, so W had 321 examples (C: 26 own answers repeated to 321).

| | seed 0 | seed 1 | mean |
|---|---|---|---|
| S0 before sleep | 5/119 | | 5 |
| W: all lucky hits + own right | 6 | 8 | 7 |
| C: own right only | 7 | 9 | 8 |

- L1: W − S0 = +2 (mark +8): FAIL. L2: W − C = −1 (mark +5): FAIL.
- Proved wrong clause (mean W ≤ mean C): TRIGGERED. On this run, practising lucky hits did not beat plain practice.
Because PASS needed every finished run, the queued GPU repeat cannot change this verdict.

All four loop runs so far (fresh puzzles, reasoner alone, mean of 2 seeds):
| run | S0 | with hits | control | hits − control |
|---|---|---|---|---|
| blurt-2 CPU | 6 | 17 | C 6 | +11 |
| blurt-2 GPU | 6 | 12 | C 5.5 | +6.5 |
| blurt-2p CPU | 8 | 13.5 | P (wrong guesses) 9.5 | +4 |
| blurt-2b CPU (all hits) | 5 | 7 | C 8 | −1 |
Shown: the gain from sleeping on lucky hits is small and unstable. Suggested, not shown: more hits per puzzle (many
near-copies of one answer) may crowd out the rest; this run's control also rose (+3) for the first time.
