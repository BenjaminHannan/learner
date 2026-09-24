Fail-closed SLEEP mark — sealing the mutant runner and proving it trips.
The brief's rules file is missing — I'll work from the embedded rules and reconstruct the originals.
Originals mapped — now pinning down the baseline results for comparison.
Baselines captured — checking the agents and configs before building the mutant.
273's baseline is panel-based — checking whether the standard scorers work for it.
Design settled — now building the fail-closed wrapper and sealed run scripts.
Runner done — now the three run-all copies with the SLEEP legs added.
All five sealed files written — sealing before any execution.
Seal verified 5/5. Load is very high so the heavy run-alls will gate on `waitload`; the tiny M1 unit check can run now.
M1 holds on both sides. Launching the first heavy run-all (292t); the script's own `waitload` will gate on system load.
The suite step failed — inspecting the log before deciding anything.
The environment is missing the MiniLM snapshot the agent stack needs. Searching more broadly before concluding it's truly gone.
No snapshot on the machine. Checking exactly what killed the smoke daemon at t071 — statements shouldn't need the router.
The daemon dies on the first filler question needing the learned router. Checking if network exists at all (to even consider restoring the snapshot).
Network works. The sealed pipeline needs its frozen encoder snapshot — I'll restore exactly the three files the loader reads, recording the revision for provenance.
Router restored. Preserving the failed-run evidence, cleaning up its orphaned daemon, then re-running 292t fresh.
292t is clean across the board. Running the 273 arm now.
273 matches 292t exactly as predicted. Running the F1 arm.
All three arms complete. Now the field-by-field M3 comparison and smoke numbers.
All marks green. Verifying repo integrity (additive-only) and the verdict files before writing results.
Everything verified. Writing the results files now.
`artifacts/` is gitignored (prior exps force-added theirs) — force-adding exactly the four listed files.
Push is blocked by environment policy — committing locally so nothing is lost, and reporting the block.
Verdict: **mut-0 HOLDS** — M1, M2, M3 all hold. Committed locally as 7692680e4 (8 files); `git push` was denied by this environment's tool policy, so the director must push `claude/card-experiment-handoff-7c5b27` (1 commit ahead).

Marks table (integer counts):

| mark | bar | result |
|---|---|---|
| M1 mut0 suite_sleep, 292t agent | pass False + NOT-RUN | pass=False, NOT-RUN, skipped=True, exit 2 |
| M1 original suite_sleep, 292t (report) | report (expect pass True) | pass=True, skipped=True, exit 0 |
| M2 smoke 292t | RAN + recorded | RAN, 83.9 s, PASS |
| M2 smoke 273 | RAN + recorded | RAN, 89.0 s, PASS |
| M2 smoke F1 | RAN + recorded | RAN, 86.4 s, PASS |
| M2 combined verdicts | 3/3 NOT-RUN, never PASS | 3/3 NOT-RUN (exit 2) |
| M3 292t non-SLEEP vs recorded | identical | identical, 0 moves |
| M3 273 non-SLEEP vs 292t recorded | identical | identical, 0 moves |
| M3 F1 non-SLEEP vs recorded | identical | identical, 0 moves |
| Measure: sleep wall s/sleep, 273 | report | 89.0 s |

Every move, every miss, deviations:
- Moves: 0. Same skip reason both M1 sides. Smokes: 1 sleep each, installed (ep 20), probes 5/5 right 0 wrong 0 abstain, taught 50/50 0 dupes, 0 overwrites, broken-chain abstains, all 3. M3: 292t sessions 3 identical ids / bench 0 / rt136 145 rows 0 diffs identical gate / rt143 124 rows 0 diffs / vp [N06,E04] vs [] / PASS==PASS; 273 identical on all 10 fields; F1 sessions 57 identical ids / bench 648 identical ids / rt136 52 reply-only + 0 other / rt143 34 + 106 teach-text identical + 0 other / vp 98 + vs 12 identical / PASS==PASS problems []. Misses: 0.
- Deviations (3, environmental, all reported): D1 OPUS-RULES.txt absent at stated path (F1-D8 class; followed task-message rules). D2 first 292t run failed — machine lacked the MiniLM snapshot (route122 FileNotFoundError; smoke daemon died t071; evidence in local `run292t-envfail/`); restored the frozen encoder from HF main rev 1110a24 (2026-06-01, predates builder runs; 3 files to ~/.cache only, repo untouched), verified, reran once cleanly — reported, not silent. D3 load-gated waits (F1 VP waited load1 113→47); totals 479/582/1130 s; disk ≥14 GB. Seal re-verified 5/5 OK after all runs; 0 existing files edited (the one tracked mod, `fable-predictions-ledger.md`, predates this task).

What it means / doesn't mean (high-school English): the SLEEP test used to report PASS without ever running — like an A on an exam never taken. Now it reports NOT-RUN and blocks PASS. Nothing else changed: all three agents match their recorded scores exactly (0 changed answers), and each now also finishes a live sleep run. It does NOT prove sleep works generally (1 sleep per arm), grade answer quality, or test reader/ear stages.

Mut-1 plan (in RESULTS.md, not run): (1) swap tick order back → caught by M1; (2) drop inbox check → M1 + M3 panel; (3) sleep never due → M2 + smoke (0 sleeps → FAIL); (4) listening tick replaced by thinking tick → M3 panel while M1 still passes (proves both suites needed).

Push debt: exactly the 8 tasked files are committed (4 scripts + PASSMARKS + SEAL + RESULTS + results.json); run dirs (`run292t/`, `run273/`, `runf1/`, `run292t-envfail/`, `m1unit/`) stay local as evidence, same pattern as 273's run273.
