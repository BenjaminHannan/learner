Sealed scale run with cold-open ladder — verifying seals and passmarks before launch.
Passmarks loaded. Now pulling the build results, baseline, and seals.
Both seals pass. Reading the build results and baseline records.
Baseline data captured. Now studying the sealed runner's interface.
o0b inputs match nb-320's recorded hashes. Checking how compact open handles the JSON compat file (matters for the tamper arm).
The 1M workload gen exceeds the 120s foreground limit — moving it to background.
All small workloads ready; 1M generating in background. Starting 20k baseline write.
Baseline 20k matches nb-320 exactly (22,077 events). Now compact arm.
Both 20k writes clean (22,077 events each). Cold opens x3 per arm.
Compact opens 35x faster at 20k (0.04s vs 1.5s). Probes next.
M3 holds at 20k (identical wrong-rows). M2 export check — calling the sealed `export_events` as ordered.
1M workload still building. Running 100k baseline write meanwhile.
100k compact write clean (110,077 events). Opens x3 per arm — baseline first (~1 min each).
Compact 100k opens in ~0.2s vs ~58s baseline. Probes now.
Baseline 100k reproduces nb-320 exactly (934+66). Compact probe next.
M2 passes at 100k. 1M workload still building — running crash/tamper (section B) meanwhile.
Crash: 30/30 killed mid-write, zeros across the board. Tamper next.
M7 complete (20/20 + 2/2 triggers). Section D ladder — building small dirs for both arms.
Ladder dirs built. Cold opens x5 per dir per arm.
1M workload file landed. Verifying completeness.
1M workload verified (1,000,001 lines). Now the SIGKILL-during-write reopen test, baseline arm first.
5 clean mid-write kills (baseline). Timing fresh opens of the killed dirs.
Baseline post-kill opens all succeed (~0.18s). Same procedure, compact arm.
Genuinely partial now. Timing opens.
Baseline valid: all 5 open, ~0.08–0.10s. Compact arm redo.
Section D complete — all 10 post-kill opens succeed. Launching the 1M compact write in background.
1M write running (cap 00:53). Aggregating numbers from finished steps meanwhile.
All 117 two-hop rows verified as sampler artifacts. Checking 1M progress.
447MB — full size reached, pickle dump in progress. Waiting for completion.
1M opens ~2.1s median — over M4's 1.0s bar. Probing at 1M now.
1M recall verified. Aggregating the D ladder.
All measurements done. Reading the ledger's P321.1 entry before writing outputs.
All evidence in hand. Writing `results-run.json`.
Fixing a transcription typo (20k compact forget count).
Extracting full probe listings for the report.
Writing `RESULTS-run.md`.
Appending the P321.1 outcome to the ledger.
JSON has trailing data — inspecting the tail.
Committed. Now the mandated cleanup.
VERDICT: FAIL on the registered bars — M1, M4, and M5-at-1M fail; M2, M3, M6, M7 pass. The compact store finishes the 1M write the baseline never finished, recalls perfectly at all sizes, and survives crash/tamper — but it is bigger on disk than the baseline and misses the 1M speed bars.

Marks (integer counts): M1 FAIL — dir total 622,519,357 B / 950,000 FACT writes = 655.3 B/FACT vs bar 93.4 (1/5 of 467.1); P321.1 (≤58.4) also fails, ratio 1.40x baseline. M2 PASS — export sha256 byte-equal at 20k (26af3065…) and 100k (4476af21…); 1M clause vacuous. M3 PASS — one-hop 6000/6000 right across sizes; wrong_rows byte-identical to baseline at 20k (51) and 100k (66); 1M 934 + 66/66 verified hop-1-sampler artifacts, 0 store errors. M4 FAIL — 1M open median 2.085 s (bar 1.0) and probe RSS 1,638,334,464 B = 1.64 GB (bar 1.48 GB). M5 FAIL — one-hop p99 0.19 ms / 0.26 ms / 4.78 ms vs 1 ms floor (1M only). M6 PASS — 30/30 killed mid-write, 0 lost / 0 dups / 0 failed opens. M7 PASS — 20/20 tamper caught by open, UPDATE 1/1 + DELETE 1/1 blocked.

Every move: both seals 3/3 + 3/3 OK (files match origin/builder-outbox) before anything else. Workloads regenerated sealed at seed 3200 (o0b sha match, 3,754 templates; event counts match nb-320 exactly). 20k/100k both arms: write → open x3 → probe (seeds 20200/101000), all SAVED, 0 unexpected. 1M compact: write finished in 3,155.5 s (52.6 min, inside 90-min cap; RSS 0.05–1.5 GB, inside 8 GB), 1,100,077 events, then open x3 (4.093/2.045/2.085) and probe (seed 1010000, one-hop 2000/2000). Crash 30x + tamper 20x sealed drivers at 20k compact. M2 via sealed export_events. D ladder: 500/2000/5000 cold-open x5 both arms (compact medians 0.004/0.008/0.014 s vs baseline 0.095/0.143/0.198 s) plus 5 genuine post-SIGKILL opens per arm at 5k (baseline med 0.085 s, compact med 0.002 s, 0 failures). Outputs committed as 063c52c48 (RESULTS-run.md ~40 KB, results-run.json ~11 KB, ledger +1 line); /tmp/nb321run/ deleted.

Deviations (all in the report): probes ran with PYTHONHASHSEED=0 both arms so asks match exactly (my 20k two-hop is 949+51 vs nb-320's 948+52 — sampler noise); 1M probe seed 1010000 derived from nb-320's N+N/100 pattern; first D kill attempt VOID (killed the uv wrapper, orphans finished the writes — redone with process-tree kills, only the redo counts); `git push` is denied by the sandbox tool policy, so the commit is ready locally for the director to push (note: the ledger commit also carries 10 concurrently-appended lines from other agents — additive, untouched).

What it means in plain words: the compact notebook is a faithful copy of the old one that finally works at a million facts — same answers everywhere, crash-proof, opens in ~2 s where the old one needed ~a minute at a tenth the size. What it doesn't mean: it is NOT smaller on disk (its folder is 40% bigger — it keeps a full plain-text history copy beside the compact file), NOT under the 1M speed bars, and NO timing transfers to a quiet machine (loads 8–63 all run).
