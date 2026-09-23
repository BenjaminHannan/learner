Building 268b on the 138nb base — re-running dialogs and adding the guard.
Files check out — now mapping the base agent and dev dialogs.
Dev drivers mapped — now inspecting the runner pattern and base behavior.
Load is high (65) — holding heavy suites until it drops. Reading remaining build pieces.
Push question deferred to the end. Now writing the 268b agent.
Now the 46 new dev dialogs for table-reader shapes.
Smoke-testing the new agent build.
MRO correct. Quick single-dialog smoke on both arms.
Base didn't take the bait on that shape — debugging the composer directly.
Bug reproduces on spouse/founder. The author-with-work-subject case needs a look at the answer path.
Gate passes — the difference is downstream table/ears behavior. The pilot data will characterize it; launching the full 138nb dev run.
Dev run on 138nb done despite load 85. Analyzing base behavior.
Writing dialog definitions, runall driver, and scorer.
Generating predictions from pilot rows.
Predictions sealed in draft. Piloting M3 suites + latency before writing PASSMARKS.
All probes equal. Latency pilot next.
All pilots pass. Writing PASSMARKS.md.
Sealing now.
Seal verified 23/23. Appending ledger predictions.
Ledger done. Launching registered DEV + M2–M4 run.
Panel not out yet. Starting the 150-minute poll.
Panel published. Copying it unchanged and verifying the seal.
Both arms run once. Scoring with the sealed scorer.
All checks done. Writing stripped M1 scores and RESULTS.md.
RESULTS written. Checking push conventions before committing.
Appending the outcome ledger line, then committing only my files.
Artifacts is gitignored — need `-f` like prior builders.
Pilot scratch bulk must not be pushed. Trimming.
Precedent matches (268 pushed 11,902 files). Verifying staged == worktree, then committing.
Commit clean (7737 files, mine only). Pushing.
Push is blocked by environment policy. Verifying final state for the report.
**Verdict: FAIL** — on M1's bug clauses only (bug 11/16 right vs bar ≥14, 1 wrong vs bar 0). Everything else passes.

Marks table (integer counts, 138nb beside every figure):

| mark | 138nb | 268b | bar | verdict |
|---|---|---|---|---|
| M1 bug right /16 | 0 | 11 | ≥14 | FAIL |
| M1 bug wrong /16 | 16 | 1 | 0 | FAIL |
| M1 bug honest non-answer /16 | 0 | 4 | rest abstains | info |
| M1 reverse_nochain /10 | 10 | 10 | identical | pass |
| M1 forward_chain /12 | 12 | 12 | identical | pass |
| M1 forward_1hop /10 | 10 | 10 | identical | pass |
| M1 uncued_reverse /6 | 6 | 6 | identical | pass |
| M1 abstain /6 | 6 | 6 | identical | pass |
| M1 non-bug rows byte-identical /44 | — | 44 | identical | pass |
| M1 question writes /60 | 0 | 0 | 0 | pass |
| DEV moves | — | 46/46 exact | predicted | pass |
| DEV teach/triple changes | — | 0 | 0 | pass |
| M2 invpanel moves /70 | — | 0 | [] | pass |
| M2 new wrong / lost right | — | 0 / 0 (69/69 kept) | 0 | pass |
| M3 suites moves | — | 0/0/0, GATE clean | 0 | pass |
| M3 rt136 labels | — | 16 inherited, direct [] | exactly | pass |
| M3 rt143 moves (124) | — | 0 | 0 | pass |
| M3 probes equal | — | 7/7 | 7/7 | pass |
| M3 ghosts / write changes | — | 0 / 0 | 0 | pass |
| M4 median delta | — | −0.005 ms | ≤+5 ms | pass |

Every move (ids only): bug right (11): n268b-001, 003, 005, 006, 008, 009, 011, 012, 013, 015, 016. Miss (4, bench73 honest non-answer): n268b-002, 004, 007, 014. Wrong (1): n268b-010, stage loop138-nhop, forward-pattern reply. Dev 46/46 exact (8 to 190 gold+label, 3 to ask, 4 to decline, 13 to abstain, 8 to table-inverse gold+label, 10 to table-label153); 315/361 other turns identical.

Every miss/deviation: (1) M1 bug bar missed both clauses — diagnosis: guard's R1–R4 list has no "Who <verb>" employer/work shape, so n268b-010's (employer-valued start, [employer]) frame survived as a forward-walk reply (falsifier P268b.6 clause 1 tripped); the 4 misses are the predicted married-to → bench73 class, never wrong. (2) M2 extra-prediction miss: predicted question_wrote [] but both arms write on the same 4 teach_control items (legitimate teaches, right on both; design M2 has no writes bar → M2 passes). (3) Post-seal driver-only files (sealed scorer untouched): scripts/claude_268b_score_fix1.py fixes 2 sealed-scorer bugs (KeyError on dev keys; invpanel score is {"per_item":...}), scripts/claude_268b_m1run.py adds the schema-required question_stage. (4) Panel dir was already committed in this worktree; I extracted identical sealed content over it, seal 5/5 OK, never edited/read items/tuned. (5) PUSH not done: `git push` is denied by environment tool policy. All files are committed locally as 0df95a40 (7737 files, mine only) on branch claude/card-experiment-handoff-7c5b27 — needs a human push. Raw panel rows (run/m1/rows-*.jsonl, work-score-*.json, score-*.log, run/work/) were left uncommitted per the no-publish rule.

What it means: moving the unchanged guard onto the table-reader base fixed 15 of 16 real bug cases (11 right with label, 4 honest non-answers), with zero changes anywhere else — suites, probes, speed all identical. What it doesn't mean: backwards questions are not fixed — one shape still answers wrong and four shapes shrug; the 14-of-16 goal failed, and nothing outside backwards questions improved.
