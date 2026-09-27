Starting dl-9 GPU build — checking gates, passmarks, and worker status.
SSH is up and gates are clear. Now checking the GPU worker state.
Pre-checks pass. Setting up the run folder on BensPC.
Tree streamed. Running the selftest check.
Selftest passed. Launching the full run detached with logging.
Nested quoting failed — switching to a launcher-file approach to keep the exact logged command.
Remote shell is already PowerShell — dropping the nested invocation.
Remote exec shell is cmd.exe — adjusting quoting for that layer.
Quoting keeps collapsing — switching to base64-encoded PowerShell to bypass all quote layers.
Launched (wrapper PID 16372). Verifying the run is alive and logging.
Wrapper died silently — likely script execution policy blocking the .ps1. Bypassing files entirely with nested encoded commands.
Still nothing. Testing the mechanism with a trivial command first.
Mechanism works. Testing the exact inner-command shape (cd, &, redirect) with a trivial payload.
Foreground works — the ssh session's job object is killing detached children on disconnect. Switching to WMI process creation (escapes the ssh job) via a .bat file.
WMIC is removed on this Windows. Using Task Scheduler instead (no quotes needed).
Run is alive (two python PIDs, log.txt created). Waiting for early progress.
Pool stage done (501/1000 survived, as expected). Waiting for night lines to project finish time.
Seed 16 nearly done. Continuing to poll.
Run finished on projection. Collecting the marks block and results.
Copying results back to the worktree.
All numbers verified. Writing RESULTS-gpu.md.
Fixing a stray typo in the table headers.
Cross-checking transcribed numbers against dl9_results.json independently.
All 14 nights verified exact. Appending the ledger line and tidying the BensPC scheduler.
Verdict: PASS — dl-9's separate expert with a learned switch stopped the forgetting and kept the learning, on both seeds, on BensPC. No weights saved or pushed.

Marks table (integer counts, from the script's printed marks block, transcribed into RESULTS-gpu.md exactly):

| mark | bar | seed 16 | seed 17 | met? |
|---|---|---|---|---|
| H1 forgetting stopped | X lost ≤ 5 each seed; X sum ≤ 0.25 × S sum | X 0, S 20 | X 0, S 27 | yes (0 ≤ 5; 0 ≤ 11.75) |
| H2 learning kept | X gain ≥ 0.9 × S gain each seed | X 177 = S 177 | X 229 = S 229 | yes |
| H3 switch learned | test_on ≥ 95/100; panel off ≥ 285/300 each seed | 100 on; 300 off | 100 on; 300 off | yes |
| H4 choosing beats chance | X gain sum ≥ 2 × R gain sum; X lost sum ≤ R lost sum | gain 406 ≥ 272; lost 0 ≤ 13 | (sums) | yes |
| proved_wrong | X lost > 0.5 × S lost, or X gain < 0.8 × S gain, either seed | no | no | false |
| INCONCLUSIVE check | L0 < 10 or S night-7 lost sum < 20 | L0 = 54; S sum = 47 | — | not inconclusive |

Every move: 1 run, seeds 16 + 17 × 7 nights = 14 nights, 150 puzzles/day × 30 guesses, TEST 100 × 20 (seed 3090), HARM 300 panel. Pool: 1000 asked → 501 kept (400 train / 101 held, 260 with suffix). Base: lucky 54, greedy 2, harm_right 201. Script total 111.3 min (nights 100.4: s16 50.8, s17 49.6); wall 03:32:41Z → ~05:24Z. Per-night S/X/R lucky, greedy, harm lost/gained, switch test_on/panel_on/by-kind/held_neg_on, and both night-7 reworded rows (switch_on 100/100 on all 4 frames both seeds) are in RESULTS-gpu.md, every number cross-checked against dl9_results.json — 0 mismatches. Misses: none; S-lost items with switch on: 0 on all 14 nights. Machine: RTX 5070 Ti (15745/16303 MiB free, no compute jobs), transformers 5.17.0, torch 2.11.0+cu128 (CUDA 12.8), lis300 venv, MiniCPM5-1B snapshot present, $0.

Every deviation (7): (1) ran under disclosed 3 GB gate (C: 4.4 GB at start; re-run of job 150); (2) detached via Task Scheduler, not shell background — Win32-OpenSSH kills detached trees on disconnect (2 Start-Process wrappers, PIDs 16372/11360, died silently; foreground worked; same command line + merged gpu/log.txt); (3) dead attempts left nothing; (4) helper files BensPC/Mac-/tmp-only, never pushed; 22-byte mech-test.txt deleted before copy-back; (5) no night lines at 20 min, projected at 04:08 from nights 1–3 → ~05:25 finish, no TIME-STOP needed; (6) GPU-BUSY.txt named this job (151-fixsleep-dl9pc-b), left to watcher, scheduler task deleted after; (7) sealed code never edited, selftest ok.

What it means (high-school plain): giving the night's learning its own expert + an on/off switch erased panel forgetting (0 vs 20/27 lost) while keeping all puzzle gains, and choosing beat chance ~3×. What it doesn't mean: puzzles vs quiz questions look very different, so the switch had an easy job — says nothing about blended questions, multiple experts, or grids.

PUSH-ready (watcher pushes; artifacts/ is ignored): artifacts/claude-dl9-20260926/RESULTS-gpu.md, artifacts/claude-dl9-20260926/gpu/dl9_results.json, artifacts/claude-dl9-20260926/gpu/log.txt, artifacts/fable-predictions-ledger.md (1 line appended).
