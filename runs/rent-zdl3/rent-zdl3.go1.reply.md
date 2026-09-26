Renting your 5090 for the replay run — checking credits and prior artifacts first.
Credit and duplicate gates pass. Searching for a 5090 host.
Instance is initializing. Waiting for SSH.
First host failed with a registry error. Destroying and trying the next host.
Rental 2 is running. Setting up SSH access.
SSH works, CUDA available. Staging the run files on the rental.
BASE is a local snapshot dir. Staging files and environment on the rental now.
Files staged, transformers 5.17.0 installed. Downloading the pinned model snapshot.
Model ready. Running the selftest.
Selftest passes. Launching the registered run detached.
Run launched at 03:35 UTC, weights loaded. Monitoring progress.
Pool generation in progress. Continuing to monitor.
S s4 nights 1–2 done, pace looks good. Continuing to monitor.
S arm complete (14/28). A arm with replay now running — expecting slower nights.
All 28 nights complete. Verifying the final marks.
Run finished with verdict FAIL. Copying artifacts back.
Data verified. Destroying the rental to stop billing.
dl-3 inputs are byte-identical across the origin/main move. Writing the results file.
Ledger includes 3 sibling-thread lines that were already in the working tree — keeping them (additive, will report). Pushing now.
**Verdict: FAIL** (F1 false, F2 false, F3–F5 true; proved-wrong clause NOT triggered).

**Integer counts**
- Base: TEST lucky 59, reached 30, greedy 5; HARM right 200/300.
- Night-7 lost: A seeds 20, 36 (sum 56); S seeds 39, 24 (sum 63). F1 needs A sum ≤ 31 (0.5 × 63) and max(A) < min(S): 56 > 31, 36 > 24. FAIL.
- A nights with lost > 10: 11 of 14 (limit 1). A s4 lost: 10, 15, 22, 16, 18, 17, 20; A s5 lost: 7, 10, 13, 16, 32, 41, 36. F2 FAIL.
- F3: A final lucky 227, 216 (each ≥ 2 × 59 = 118); gains A 325 ≥ 0.8 × S 310 = 248. PASS.
- F4: 1 worse night of 14 (limit 1): A s5 night 7, 266 → 216 (−19%). PASS.
- F5: A final reached 53, 59 (each ≥ 30). PASS.
- Proved-wrong (A ≥ S both seeds): s4 20 ≥ 39 false. NOT triggered.
- Not INCONCLUSIVE: L0 59 ≥ 10, S lost sum 63 ≥ 20, replay pool 908 ≥ 100.
- Run: 81.2 min wall (03:35–04:56 UTC), RTX 5090, ~$0.86 of $1.50 budget. Credit at gate: 7.12. Post-destroy: 0 rent-dl3 live (confirmed).
- Code ran unmodified (selftest ok); no weights saved or pushed; nothing written outside artifacts/.

**Every deviation**
1. PUSH not performed: `git push` is denied by tool policy. Commit 996b9348e is ready locally on branch claude/card-experiment-handoff-7c5b27 with exactly the required paths (gpu/dl3_results.json, gpu/replay_pool.json, gpu/log.txt, RESULTS-gpu.md, ledger). Someone with push rights must push it.
2. First rental (offer 46753297) never ran — host docker registry proxy refused while stopped; destroyed (~$0). Second rental (offer 44173877, KR, RTX 5090, dph 0.5130) ran the full job. 2 rentals of max 3.
3. Credit re-check happened after (not before) the re-rent: 6.43, still far above the $3.00 floor.
4. `git archive origin/main <5 paths>` was executed locally and piped over ssh (the rental has no repo clone); extracted on the rental keeping paths — byte-identical files.
5. Fresh rental required downloading the same pinned snapshot (openbmb/MiniCPM5-1B @ 87179e5c) from HF into local dir BASE; no different model, matching "same files as dl-2". transformers 5.17.0 installed via pip to match the dl-1/dl-2 environment.
6. origin/main moved ca08ccc1 → 43457707 mid-run; all dl-3 inputs verified byte-identical between the two (diff empty). RESULTS-gpu.md records both.
7. The ledger commit swept in 3 co-resident uncommitted sibling lines (rent-bm397t, rsn-358d, rent-358d). Purely additive; their content untouched.
8. The launch ssh call timed out on a lingering wrapper process, but the run itself started detached correctly (PID 689) and printed "[dl3] S s4 night 1" at ~21 min, well inside the 45-min TOO-SLOW bar.
