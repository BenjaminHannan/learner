# Leap-1 results (closed 2026-10-27, superseded by the puzzle-practice and looping threads)

Only one arm finished: LEAPU seed 0 (Vast A100, 2026-10-24). Shown, one seed, Qwen3.5-0.8B, 600 held-out EVAL puzzles.
| round | first-try mean | d1 | d2 | d3 | d4 | d5 | d6 | ARC-Easy | pool puzzles verified | pairs from repair |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 12.5 | 48 | 6 | 12 | 3 | 2 | 4 | 84.4 | - | - |
| 1 | 20.8 | 67 | 10 | 21 | 5 | 8 | 14 | 85.2 | 127/1000 | 20 |
| 2 | 21.7 | 70 | 12 | 21 | 6 | 11 | 10 | 85.8 | 178 | 16 |
| 3 | 21.8 | 71 | 12 | 23 | 5 | 9 | 11 | 85.6 | 198 | 10 |
| 4 | 22.0 | 72 | 13 | 22 | 4 | 11 | 10 | 85.0 | 200 | 10 |
| 5 | 22.7 | 72 | 13 | 21 | 7 | 11 | 12 | 85.4 | 214 | 5 |
16-sample checked search on EVAL: 11.8% (precision 92%) at round 0, 18.2% (precision 89%) at round 5.

Reading (suggested): sleep on verified wins gives a real one-time jump (+8.3) with no forgetting, then flattens
(+1.9 over rounds 2-5). The explorer is the same 0.8B with more samples; it verified only 5-19 of ~167 depth>=3 pool
puzzles per round, so it cannot push past the worker. That motivated LEAPS (addendum 2: exact enumerative search,
finds a fit for 96% of depth-2/3 puzzles in a CPU check), which was built but never run.
Untested: SELF, LEAP, LEAPS, the 4B/9B/35B-A3B references and the check-then-escalate cascade. The PC runs never
reported (the Mac Remote Control session went offline 2026-10-24 04:05Z); the 35B-A3B vLLM box failed at engine start.
