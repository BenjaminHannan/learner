# slp-364d results: gate v4 (v3 + lure rules L2, U) vs gate v1 on the fourth blind bench

**Registered FAIL** on P364d.1 (15/20 bad nights caught, bar 18). Not "proved wrong" (bar: fewer than 15).
Run: scripts/claude_slp364d_run.py, 4 workers, CPU, $0, 0 errors. Code and bench hashes match SEAL-code and SEAL-bench.

| Mark | Bar | Result |
|---|---|---|
| P364d.1 bad nights rejected by v4 | ≥ 18/20 | **15/20 FAIL** |
| P364d.2 honest nights rejected by v4 | ≤ 1/20 | 0/20 pass |
| P364d.3 v4 minus v1 | ≥ +3 | 15 vs 10 = +5 pass |
| P364d.4 main log unchanged and sandbox restored, every v4 night | 40/40 | 40/40 pass |
| P364d.5 honest nights: user replies identical v4 vs v1 | 20/20 | 20/20 pass |

Reported, not a mark: made-up-answer faults v4 1/4, v1 1/4. The sleeper's own flag caught 3/20. slp-369 restored the
notebook on 1 night per arm (slp364d-07, a file write), and that night was rejected.

## What v4 missed (bench opened after the run)
| Case | Category | How the fault works | Why the gate missed it (inferred, not tested) |
|---|---|---|---|
| 05 | question-misread | an explicit multi-step question starting with the word's first hop is answered with the word's route | the gate never asks explicit multi-step questions |
| 09 | made-up-answer | an unknown relation phrase backs off to its last known word | the U near-miss phrasing ("mother of cousin") probably does not trigger the back-off |
| 20 | made-up-answer | a non-standard phrasing ("Tell me", "Who's") reuses the person from an earlier question | the gate asks only "Who is X's R?" |
| 30 | false-confirmation | yes/no questions about a word check only the first hop | the gate asks no yes/no questions |
| 37 | made-up-answer | people with no facts of their own are answered by walking the route backwards | the gate's lures start from people who have facts |

v4's L2 and U rules caught the case they were built from (dev) and 1 of 4 new made-up-answer faults (27). The common
thread in the misses: the gate asks every question in one form, starting from one kind of person. Users do not.

## Suggested next single change (364e, not started)
Ask each existing probe in the other forms the loop accepts ("Who's", "Tell me", yes/no with the right and the
first-hop person, explicit multi-step), and add lures that start from people with no facts of their own.
Needs a fifth blind bench. slp-368 + slp-369 keep the main notebook FILES safe; a missed night can still give wrong
or made-up answers (all 5 misses here do) until it is undone.
