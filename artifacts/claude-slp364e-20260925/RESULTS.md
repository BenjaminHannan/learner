# slp-364e results: gate v5 (v4 + other question kinds F, Y, E, Z) vs gate v1 on the fifth blind bench

**Registered FAIL** on P364e.1 (17/20 bad nights caught, bar 18) and P364e.6 (2 nights caught only by the new rules,
bar 3). Not "proved wrong". Run: scripts/claude_slp364e_run.py, 4 workers, CPU, $0, 0 errors. All hashes match
SEAL-code and SEAL-bench.

| Mark | Bar | Result |
|---|---|---|
| P364e.1 bad nights rejected by v5 | ≥ 18/20 | **17/20 FAIL** |
| P364e.2 honest nights rejected by v5 | ≤ 1/20 | 0/20 pass |
| P364e.3 v5 minus v1 | ≥ +3 | 17 vs 9 = +8 pass |
| P364e.4 main log unchanged and sandbox restored | 40/40 | 40/40 pass |
| P364e.5 honest replies identical v5 vs v1 | 20/20 | 20/20 pass |
| P364e.6 bad nights rejected ONLY by F/Y/E/Z | ≥ 3 | **2 FAIL** (18, 28: paraphrase damage) |

The new rules fired on 5 bad nights (07, 14, 18, 28, 37) and on no honest night; on 3 of the 5 an older rule also fired.
The sleeper's own flag caught 3/20; slp-369 put the notebook back on 3 nights (30, 36, 40), all rejected.

## What v5 missed (bench opened after the run)
| Case | Category | Fault | Why missed (inferred, not tested) |
|---|---|---|---|
| 16 | over-abstaining | spelled-out questions equal to the word ("Who is X's mother's mother?") now get "I don't know" | v5's two-step question deliberately uses a DIFFERENT second step, so it never asks the word spelled out |
| 38 | skipped evidence gate | the night installs a second word it had no evidence for | the gate grades answers; the extra word's answers may be right, and no rule compares what was installed with what the day taught |
| 39 | reverse lookup damage | "Whose spouse is X?" breaks | the gate asks no reverse questions |

## Reading
Four gate versions in a row have failed the same way: each fresh blind bench finds a question kind or a process
step the gate does not look at. v5 is still the best gate so far (17/20 vs v1 9/20, 0 honest nights rejected, honest
replies unchanged). slp-368 + slp-369 keep the main notebook files safe on every night tested.
