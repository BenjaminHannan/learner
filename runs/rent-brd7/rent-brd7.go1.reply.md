Starting brd7 — fetching branches and checking gates.
Cheapest 5090 at $0.469/hr — within budget. Checking specs and renting.
Prior runs used `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel`. Renting now.
Instance running. Building the code tree and shipping it.
md5 matches, torch CUDA OK. Installing packages and fetching the model.
Selftest OK. Launching the run detached.
Run is live and progressing (temp eval done). Monitoring.
Run finished. Copying results back.
All files verified. Destroying the rental now.
Instance destroyed and confirmed gone. Writing up results.
Verdict: NOT SHOWN (registered brd-7 run completed; no PASS, not proved wrong, not inconclusive).

Credit at gate: 7.48 (balance 0.00; credit is the usable number, above the $3.00 gate so renting proceeded). Duplicate gate: clear (origin/main had only PASSMARKS + test panel, builder-outbox had nothing, no live rent-brd7 instance).

Integer counts: base cov@30 135 of 240; W cov@30 158, 158, 146 (deltas +23, +23, +11 vs required +24 = 159 every seed); C cov@30 28, 33, 27 (W−C 130, 125, 119); N cov@30 99, 89, 96; W−base CI [2.65, 13.31] (above 0, upper bound above +5 so no proved-wrong); practice 400 puzzles, 20 own + 183 wins (203 W examples, 20 narrow picks); run wall 20 min; 1 rental, 0 re-rents; spend ~$0.24 of $1.00 (0.494 h × $0.49444 dph); 4 files copied back + RESULTS-gpu.md + 1 ledger line, all staged (force-added, watcher pushes).

Every deviation:
1. Log saved as gpu/log.txt (renamed from run.log) to match sibling result-dir convention.
2. Code tree built via `git archive origin/main <paths>` on the Mac and scp'd to the rental (rental has no repo; content byte-identical to origin/main, paths preserved) instead of running git archive on the rental.
3. Billed dph $0.49444 (incl. disk) vs search-listed $0.469; spend computed on the billed rate.
4. First `setsid nohup ... &` ssh invocation held the session (no output, timed out) but the run had launched; all further polling used fresh connections and the run completed normally (exit implied by PROCS=0 plus all output files written).
5. Destroy needed `echo y |` piped confirmation; instance confirmed gone (empty instance list).
