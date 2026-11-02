# Probe-5 report (LFM3-1.7B, llama.cpp)

96 tasks with all 12 tries (38 traps, 58 non-traps); of 96 in the task file. Replay gate: 100.00% of tries reproduce recorded success.

| picker | all tasks (%) | traps (%) | non-traps (%) | generated tokens / task | prompt tokens / task |
|---|---|---|---|---|---|
| FIRST | 38.5 | 18.4 | 51.7 | 238 | 5717 |
| RAND | 40.7 | 22.6 | 52.6 | 2642 | 70840 |
| VOTE | 43.8 | 23.7 | 56.9 | 2642 | 70840 |
| SELF | 52.1 | 13.2 | 77.6 | 2654 | 74492 |
| TEST-B | 50.0 | 13.2 | 74.1 | 5272 | 80003 |
| TEST-T | 57.3 | 21.1 | 81.0 | 2915 | 80003 |
| ORACLE | 72.9 | 57.9 | 82.8 | 2642 | 70840 |

Verdict: **PASS**
Pass marks (PREREG): E1 TEST-T >= FIRST + 10 points (>= 48.5%); E2 >= SELF + 5 (>= 57.1%); E3 >= TEST-B + 5 (>= 55.0%). Proved wrong: TEST-T <= FIRST + 3 (<= 41.5%). E1=ok, E2=ok, E3=ok

Paired bootstrap 95% intervals (points, over tasks; reported only, the verdict uses the point values):
- TEST-T - FIRST: [9.4, 28.1]
- TEST-T - SELF: [0.0, 10.4]
- TEST-T - TEST-B: [2.1, 13.5]

RAND is the expected success of a random try (mean over the 12). Ties for TEST-B / TEST-T break by SELF, then the lowest try. Tokens: FIRST = one try; RAND / VOTE / ORACLE = the 12 tries; SELF = 12 tries + 12 judge passes; TEST-x = 12 tries + 4 test samples + the 12 judge passes used for tie-breaks.
- TEST-B tests: unparsable replies 311/384, validity 85.4%, samples with no valid check 312, agree with the reference plan 46.2%, tasks where all 12 tries tie on the score 91.7%
- TEST-T tests: unparsable replies 0/384, validity 99.6%, samples with no valid check 0, agree with the reference plan 78.3%, tasks where all 12 tries tie on the score 15.6%
