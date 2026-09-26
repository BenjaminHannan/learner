Complex registered run – fetching sealed instructions and checking for duplicates first.
No duplicate on the builder branch – now mapping the BensPC access path.
BensPC is reachable and GPU is idle – setting up the registered run.
Tree transferred intact – extracting and verifying hashes on BensPC.
Both reader hashes match – running the router check and seal verification.
Inline quoting keeps breaking – switching to script files for all BensPC commands.
All seals OK (347/347, bank 3/3, panels 2/2) – running the five self-tests.
Step 1 complete, all self-tests pass – building the sleep base checkpoint.
Base checkpoint done – launching the DEV GATE (three commands, starting with dev sleep).
The background process died when SSH closed – testing detach methods.
Survives. Cleaning up the probe and launching the DEV GATE properly.
Dev-sleep hit a turnlog error – inspecting the sealed code to understand (not editing).
The seal includes Windows-newline wrappers – reading how they're meant to be used.
Dev-sleep is running properly now (both models loaded, GPU 5.3GB). Improving the poller while it works.
Dev-sleep finished (night 1, tries=310, GPU idle). Verifying completion state.
Gate condition 1 met (1 night, tries=310). Launching dev bank X.
Dev bank X done (276 rows, 10 lives). Launching dev chat panel X.
DEV GATE PASSES. Launching registered sleep (3 nights).
Sleep running (python alive, GPU loaded). Polling periodically.
Night 1 done (tries=4650, adapter saved). Waiting for nights 2–3.
Night 2 done. Waiting for night 3.
Sleep complete (3/3 nights). Running step 4a activation check.
4a passes (10/10 equals saved, 10/10 differ, pass=true). GPU idle. Launching bank D X.
Bank X done (953 rows, 40 lives). Launching bank G.
Bank G done (860 rows, 40 lives). Launching bank T.
Bank T done (658 rows, 40 lives). Running the bank scorer.
Bank scored. Starting step 6 panels – chat X first.
Chat X done (60/60). Launching chat T.
Chat T done (60/60). Launching chat G.
Chat G done (60/60). 28 min to cap – launching creative X immediately.
Creative X done (60/60). 12 min to cap – copying chat files to score/ and launching creative T.
Chat scored. Waiting on creative T (53/60).
Creative T done (60/60). Running creative score + 7a params in one go.
All compute done before cap. Copying results back now (excluding adapter weights).
Tarball verified (hash matches, no weight files). Copying into the worktree.
All data gathered. Writing RESULTS-benspc.md.
Verdict: COMPLETE (not partial). The registered 0.2c run finished on BensPC inside the 10:50 UTC cap — GPU idle 10:47. Step 4b not run (past the 09:30 cutoff → "not measured"). Blind-judge rows pending off-box judging.

## Marks table (integer counts; X = slept 02c agent, G = 0.1+gram360, T = plain twin)

| Row | Count | Reading |
|---|---|---|
| L1 3/3 nights tried+trained+reloaded | tries 4650/4650/4650, examples 66/83/95, weight Δ 2.61/2.08/2.17, reload-exact 3/3 | PASS (mechanical) |
| L2 TEST after night 3 ≥ 1.5× before | greedy 12 vs 5 = 2.4× (reached 61 vs 39, lucky 192 vs 74) | PASS (mechanical) |
| L3 drops >15% vs prior night ≤ 1 | greedy 5→7→11→12, 0 drops | PASS |
| L4 net flips ≤5/night, ≤0 after n3 | −22/−38/−37 (lost 7/10/10) | PASS |
| L5 TEST reached n3 ≥ before | 61 ≥ 39 | PASS |
| L6 items lost after n3 ≤ 20 | 10 | PASS |
| 4a activation | 10/10 equal saved, 10/10 differ at scale 0, pass=true | PASS |
| Q1 think-numeric X−G ≥ +3 | 10−12 = −2 | bar not met |
| Q2 X−T ≥ 0 | 10−11 = −1 | bar not met |
| K2 puzzles X ≥ T | 0 vs 0 | tie |
| ME1 edit-asks right X ≥ G | 3 vs 4 | count |
| Y1 mechanical ALL right X−G | 63−77 = −14 | count |
| Bank rows | X 953 / G 860 / T 658 rows, 40/40/40 lives | done |
| Chat panel | X/T/G 60/60/60 convos; distinct replies 271/294/266 | done, judged off-box |
| Creative | X/T 60/60 items; puzzles solved 0/0 | done, judged off-box |
| H1–H4, C1, C2, K1, S1 | packets in score/ | PENDING blind judges |
| H5/H6 (4b) | not run (step 6 ended 10:44 > 09:30 cutoff) | NOT MEASURED, open |

## Every move
Tree (builder-outbox + main, self122 5ca02173✓) → new folder on BensPC. READER b4fd93a2✓, READER319 e688e1b2✓, MiniLM route check ✓. Seals 347/347 + bank 3/3 + panel 2/2; tests 10/10, 13/13, 9/9, 12/12, 1/1. Base checkpoint + DEV GATE PASS. Sleep 3 nights, 4a, bank X/G/T + score, chat X/T/G + creative X/T + scores, params. Copy-back hash-verified (49c7b054✓). Staged 46 files for PUSH (run02c absent — nothing to push); adapter02c.pt (16,568,145 bytes, a33211dc✓) reported only, never pushed. $0.

## Misses / deviations
1. First dev-sleep attempt (exact rent-02c command, no shim) crashed after model load: `TurnLog323Corrupt: read-back mismatch` — Windows writes `\r\n`, sealed code expects `\n`. Wrote 0 files. Fix: prefixed sealed `claude_winnl2_wrap.py` to every runner command (repo-tested shim, gram-364 precedent); CRLF count in all outputs = 0. Code never edited.
2. git-bash background procs die on SSH close here, so steps launched via Win32_Process Create with PID recorded; ran strictly one at a time; kill-by-PID available, never needed.
3. Chat --score (CPU-only) overlapped creative T to fit the cap; GPU stayed on creative T.
4. EP382 logs absent (0 files) — expected: sealed build has MEM02C=0 (382b memory frozen out), so no ep382_stats exist. sleep_T.jsonl absent — expected.

## What it means (plain English)
The night-training part worked: three nights each practiced, learned (weights moved), and puzzle scores roughly doubled (5→12) without forgetting general items. But on the fresh tests, the slept agent answered fewer checkable questions right than both controls (X 63 vs G 77 on bank; think-numbers 10 vs 12 vs 11), so the "fixes joined together help" claim is not supported by the script counts; the conversation/creative/safety rows await the blind judges. The general-knowledge no-harm lanes (H5/H6) have no reading because the day ran out of clock — that row stays open, not passed.
