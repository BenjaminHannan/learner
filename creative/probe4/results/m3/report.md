# Probe-4 report

96 tasks with all 12 tries (38 traps, 58 non-traps); of 96 in the task file. Replay gate: 100.00% of tries reproduce recorded success.

| picker | all tasks (%) | traps (%) | non-traps (%) | generated tokens / task | prompt tokens / task |
|---|---|---|---|---|---|
| FIRST | 50.0 | 21.1 | 69.0 | 199 | 4705 |
| RAND | 53.3 | 30.0 | 68.5 | 2461 | 56761 |
| VOTE | 47.9 | 21.1 | 65.5 | 2461 | 56761 |
| SELF | 59.4 | 18.4 | 86.2 | 2473 | 60447 |
| TEST-B | 59.4 | 15.8 | 87.9 | 2776 | 65731 |
| TEST-T | 66.7 | 31.6 | 89.7 | 2758 | 65731 |
| ORACLE | 78.1 | 60.5 | 89.7 | 2461 | 56761 |

Verdict: **PASS**
Pass marks (PREREG): E1 TEST-T >= FIRST + 10 points (>= 60.0%); E2 >= SELF + 5 (>= 64.4%); E3 >= TEST-B + 5 (>= 64.4%). Proved wrong: TEST-T <= FIRST + 3 (<= 53.0%). E1=ok, E2=ok, E3=ok

Paired bootstrap 95% intervals (points, over tasks; reported only, the verdict uses the point values):
- TEST-T - FIRST: [8.3, 25.0]
- TEST-T - SELF: [2.1, 13.5]
- TEST-T - TEST-B: [3.1, 12.5]

RAND is the expected success of a random try (mean over the 12). Ties for TEST-B / TEST-T break by SELF, then the lowest try. Tokens: FIRST = one try; RAND / VOTE / ORACLE = the 12 tries; SELF = 12 tries + 12 judge passes; TEST-x = 12 tries + 4 test samples + the 12 judge passes used for tie-breaks.
- TEST-B tests: unparsable replies 1/384, validity 89.6%, samples with no valid check 71, agree with the reference plan 66.4%, tasks where all 12 tries tie on the score 32.3%
- TEST-T tests: unparsable replies 0/384, validity 98.8%, samples with no valid check 0, agree with the reference plan 84.8%, tasks where all 12 tries tie on the score 25.0%
