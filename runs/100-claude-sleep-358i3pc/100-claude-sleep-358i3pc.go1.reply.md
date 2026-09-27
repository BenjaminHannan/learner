GPU build locked to BensPC — checking seals and duplicate gate before touching anything.
Not a duplicate — now figuring out how to reach BensPC from here.
GPU-BUSY names this job so I'm proceeding; GPU is idle with ~16GB free.
Code extracted — verifying the 19-line seal next.
Seal passes 19/19 — running torch check and selftests.
All checks pass. Launching the first two training runs detached.
Launch failed (W dir missing) — creating it and relaunching properly.
Both processes died immediately — reading the error logs.
Mechanics work (print test passes). Relaunching loop-s5 and watching its first 90s live.
Training is running (step 1500 in 1.2 min). Checking it survives ssh disconnect, then launching plain-s5.
Found it: BensPC kills GPU procs when SSH drops. Switching to WMI-detached launch and testing survival.
WMI launch survives disconnect. Killing the test, launching the real runs.
Both runs training, GPU at 4.4/16.3GB. Waiting 5 min per spec before adding a third.
Starting run 3 (loop-s6) — 11.4GB free, 7 min elapsed.
8.1GB free — starting run 4 (plain-s6).
Four runs at max parallelism. Polling progress.
plain-s5 finished (60000 steps). Starting loop-s7 in the freed slot.
loop-s5 done. Starting plain-s7.
loop-s6 and plain-s6 done. Starting loop-s8 and plain-s8.
loop-s7 done. Starting plain-s1 (report-only).
All 8 graded runs complete. Starting plain-s2.
Both s8 runs done. Starting the final two (plain-s3, plain-s4).
All 12 runs launched. While the last wave trains, fetching reference counts for the report-only comparison.
Reference schema confirmed. Waiting for the final wave.
All 12 runs finished training. Sealing and evaluating each checkpoint.
loop-s5 eval ok. Batching the rest (seal-then-eval per checkpoint).
All 12 sealed and evaluated once each. Verifying, archiving weights on BensPC, copying results back.
All weights verified. Now computing the graded marks from the local result files.
Verdict is PASS on all marks. Pulling the middle dev-grid values cut off in the output.
All numbers in hand. Writing RESULTS.md now.
Verdict: PASS. rsn-358i3 on BensPC, fixed 358i loop vs same-machine plain twin, fresh seeds 5-8: V0 pass, G0 8/8 arms, G1 pass (means sums6 +124.00, grids6 +52.00, numbers5 +0.00; gaps>0 on 4/4 seeds for sums6 and grids6), G2 pass (+0.00/+1.50/+0.75), G3 pass (4/4 seeds right>=fixed16-5 on all bigger tests; mean rounds sums6 7.56 > sums4 6.71). Proved-wrong not triggered.

Integer counts: SEAL-code 19/19 OK; selftests 3/3 ok lines; 12/12 runs reached 60000 steps; steps_block_nograd 0/12; evals 12, exactly once per checkpoint; SEAL-run 12 lines, all 64 hex, Mac weight copies match 12/12; 50 files staged (RESULTS.md + SEAL-run + 12x4 run files), 0 weights in repo; 12/12 final.pt kept on BensPC (C:/Users/benja/premonition-models/rsn358i3/) and Mac (~/premonition-models/rsn358i3/); duplicate gate clear (no RESULTS.md on main/outbox); time ~4.5 h training inside 10 h cap, nothing dropped, conclusive.

Graded gaps (loop-minus-plain, 4-seed means, n=300): sums6 +124.00 (81/+171/+110/+134), grids6 +52.00 (48/53/50/57), numbers5 +0.00, sums4 +0.00, grids5 +1.50, numbers4 +0.75. Report-only: BensPC plain s1-4 vs rental plain s1-4 mixed signs (sums6 -25..+17, grids6 -16..+10); 358i2 loop s1-4 minus BensPC plain s1-4: sums6 +63..+146, grids6 +51..+62. Machine: RTX 5070 Ti, torch 2.11.0+cu128, CUDA 12.8. Minutes: loop s5-8 78.5/82.1/75.0/78.0, plain s5-8 75.2/79.1/71.2/76.1, plain s1-4 61.2/58.6/50.8/50.4.

Every deviation (also in RESULTS.md): (1) GPU-BUSY.txt pre-existed naming this job, watcher-owned per kit header, left untouched. (2) Start-Process children die on ssh disconnect (verified empirically); all 12 runs launched via WMI Win32_Process.Create with the exact specified command line, wrapper PIDs recorded, nothing stopped. (3) stderr to sibling W/<R>.err on BensPC only. (4) Parallelism per rule, max 4. (5) 30-min projection held; nothing dropped, no TOO-SLOW. (6) C: free 6.3 GB, above 5 GB line. (7) Seal checked with Git's sha256sum.exe. (8) Selftest ok lines carry suffixes. (9) 358i2 loop s1-4 ref from builder-outbox. (10) Code never edited; TEST-ONLY items never opened, counts only. PUSH paths staged (add -f) for the watcher; I did not commit or push.
