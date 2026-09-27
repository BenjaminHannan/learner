# 358t v3 addendum 4: the machine may be one vast rental instead of BensPC (sleep research thread, written 2026-09-27 13:39:31 UTC, before any v3 run)

Additive. PASSMARKS-v3.md, PASSMARKS-v2.md and SEAL-code-v3.sha256.txt are unchanged. No v3 training run has happened anywhere. The BensPC task (handoff/queue/260-claude-sleep-358t3pc.md) has not started, because BensPC has not answered ssh since 12:30 UTC 09-27.

**Why:** the Thread manager (13:36 UTC) asked for a held vast version, like 358u's, while it asks Ben whether 358t v3 should run on vast after 358u, within his $5 (12:49:44 UTC). **Nothing rents without Ben's yes to this job.**

**What changes, only if released:**
1. Machine: one vast.ai RTX 5090 (reliability >= 0.98, >= 16 CPU cores, inet_down >= 200), not BensPC. 358i's plain results, which v3 grades against, came from a vast 5090 too.
2. torch 2.11.0+cu128 is installed on the rental and checked before anything runs; any other version stops the job (fail-closed). Stage 0 runs there, and the "loop  free=3 grad=2 cache=False" line must end in 0/12, otherwise FIX-FAILS.
3. Runs: the 8 graded runs (loop-trm and loop8, seeds 1-4) in the sealed order, with the sealed command. Each run starts only while at least 5 GB of GPU memory is free, at most one start per 90 s. The report-only loop8-trm runs (s1, s2) are not run on the rental, to keep the cost down. Addendum 2 already made them the first thing dropped. G4-G5 lines that need them will read "not run (vast)".
4. Seals and evals as in the BensPC task: sha256 of final.pt and final-ema.pt go into SEAL-run-v3 before any eval. Then there is one eval per checkpoint, tests.json (raw, graded) and tests-ema.json (report only), in runs-v3/<R>/. The rental's records (progress file, torch check, checks, Stage 0 output, file manifest, rental list, guard log) go in run-vast-v3/.
5. Safety: this is the reviewed 358u kit v2, copied as handoff/kit/sleep358tv/.
   - The copy back is checked against a sha256 manifest made on the rental, and each run's two checkpoints are checked against SEAL-run on the Mac. The instance is destroyed (exact id, confirmed gone) only when that passes. Otherwise, and on a lost host, it is stopped, not destroyed, and flagged to the Director.
   - The Mac's ssh key is attached. The guard is restarted by each collect job if it died.
6. Only one machine runs v3. The vast start refuses if RESULTS-v3.md, SEAL-run-v3, runs-v3/ or run-vast-v3/ already exists on main or builder-outbox. When releasing, the Director moves handoff/queue/260-claude-sleep-358t3pc.md to handoff/held/superseded/, so BensPC does not also run it.

**What this can and cannot move:**
- The marks compare the new loop arms with 358i's plain nets. Those plain nets were trained on a vast 5090 (torch 2.8; plain has no loop blocks, so the cache bug does not touch it; PASSMARKS-v3). On vast, loop and plain share a GPU type. On BensPC they would not have.
- The torch versions differ (2.11 vs 2.8 for plain), as they would on BensPC too.
- Report only, for RESULTS-v3.md: all 8 runs trained on one 5090 at close to the same time, while BensPC would have run 2-4 at once.

**Money:** cap $1.60 for this whole task, re-rents included (PASSMARKS-v3 "about $1.60 cap"). The Mac guard stops everything at $1.45 or at 3 h 30 min from the first rental.
- Estimate: 358i trained 8 runs at once on a 5090 in 75 min (loop) at $0.49/h. The v3 loop arms cost about the same per step, and the staggered starts add up to 12 min. With 16 evals, that is about 1.7-2 h: about $0.85-1.40 at $0.45-0.70/h, plus up to about $0.20 if a host fails to start.
- If the rate is high, the $1.45 stop can land before the evals finish. The guard then stops the instance (not destroys it) and flags it, and a verdict needs the Director's follow-up. The start rents only offers it can afford, cheapest first.

**Kit test:** fake vast and fake rental. Normal path: 87 of 87 files verified, 16 checkpoints sealed and copied, then destroyed. Stage 0 not 0/12: FIX-FAILS, nothing trained. A run that dies: recorded, then destroyed.
