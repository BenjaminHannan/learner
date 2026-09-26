Your RSN-358a build is queued — reading the sealed rules and run plan.
The brief path didn't match — checking the worktree layout to locate the rules.
That rules file is missing from scratchpad — I'll proceed under the additive-only rules from your task and verify against the sealed plan.
Local tree lacks the RSN-358a artifacts — I'll pull the sealed files and find the BensPC route.
GPU is free (15.5 GB available) and Mac disk is OK — now verifying the sealed code hashes.
Rules confirmed — now tracing how prior runs reached BensPC.
BensPC has torch CUDA and 28 GB free — setting up the sealed code over there.
Selftest passed — verifying the seal hashes now.
Seal verified locally, all lines OK — confirming the remote copy matches.
The pilot failed to start (missing output dir) — creating it and relaunching.
Loop pilot finished in ~0.5 min with no OOM — launching the plain pilot.
Training is on track (~1750 steps/min, matching the pilot estimate) — polling periodically.
Loop seed 1 finished (32.2 min, no OOM) — sealing its checkpoint and running its one eval.
Loop-s1 files secured — launching plain seed 1.
Plain seed 1 done (25.9 min) — sealing and evaluating it.
Loop seed 2 done (32.9 min) — sealing and evaluating.
Plain seed 2 done (25.8 min) — sealing and running its eval.
All four runs are done — assembling the results files from the fetched logs.
All counts in hand — checking the ledger format before writing results.
Now writing the results report.
All Mac copies match the seals — correcting the checkpoint line in my report to stay truthful.
The ledger is append-only, so adding a correction line for the checkpoint location.
Verdict: FAIL (G0 met on both seeds, G1 passes seed 1 but fails seed 2; proved-wrong clause NOT triggered).

Sharing report (S1): BensPC RTX 5070 Ti, total 16303 MiB, used 404 MiB, free ~15570 MiB at start, processes all graphics/desktop (dwm, explorer, Discord, Lunar Client, etc.), no compute job, GPU-Util 0%. Free memory never dropped below 10342 MiB during the whole run; own 4 GB cap (RSN358A_GPU_GB=4) never hit, no OOM anywhere, no SHARE-STOP, no OOM-CAP, no TOO-SLOW. Never touched another process. GPU $0.

Marks table (all n=300, integer counts):

| mark | seed 1 | seed 2 |
|---|---|---|
| G0 validity (both arms ≥210 practised-size in ≥2/3 kinds) | MET (sums 300/300, grids 240/243, numbers 1/3) | MET (sums 300/300, grids 244/248, numbers 2/4) |
| G1 bigger loop−plain (need +30 on 2/3, ≥−10 on third) | PASS (+59 sums6, +67 grids6, 0 numbers5) | FAIL (−11 sums6, +76 grids6, +2 numbers5) |
| G2 practised loop−plain (each ≥−10) | PASS (0, +3, +2) | PASS (0, +4, +2) |
| G3 stop rule (own-stop ≥ fixed-16 −5; mean sums6 > sums4) | PASS (256≥251, 270≥266, 1≥−4; 8.82>7.14) | PASS (244≥239, 265≥262, 2≥−4; 8.01>6.52) |

Every move (plain → loop, seed 1 / seed 2): sums4 300→300 / 300→300; sums6 197→256 (+59) / 255→244 (−11); sums8 78→88 (+10) / 142→94 (−48, report); grids5 240→243 (+3) / 244→248 (+4); grids6 203→270 (+67) / 189→265 (+76); grids7 92→192 (+100) / 88→173 (+85, report); numbers4 1→3 / 2→4; numbers5 1→1 / 0→2.

Every miss: numbers puzzles unsolved by all 4 runs (1–4/300 even at practised size), so G0 rests on sums+grids. Seed 2 sums6 loop lost by 11 (the G1 killer, also breaks the −10 floor). Plain-arm seed swing on sums6: 197 (s1) vs 255 (s2). Each of the 8 sealed tests ran exactly once per final checkpoint; items never opened.

Deviations (7): D1 pilots used W/pilot-* not /tmp/* (no /tmp on Windows, timing only). D2 one-at-a-time training (sharing rule overrode "two at a time"). D3 design file also copied to BensPC for complete seal; full 14/14+1/1 seal check run locally from git archive, remote spot hashes match, selftest ok. D4 brief's OPUS-RULES.txt path was empty; followed /tmp copy + task text (same rules). D5 unrelated Python PID 764 briefly held ~2.5 GB GPU; never touched, free VRAM stayed ≥10 GB. D6 Mac checkpoint copy deferred at 6 GB free, then done at 11 GB free (all 4 hashes match). D7 first pilot launch died instantly (missing W/ dir); relaunched cleanly, no test contact.

Timings: pilots loop/plain 0.5 min each (14 s data-ready → ~32 min full-run estimate, 4-run total ~117 min actual: 32.2/25.9/32.9/25.8, under the 480 cap). Loop 6,438,302 weights, plain 6,385,149. Checkpoints sealed before each eval, kept at C:/Users/benja/premonition-models/rsn358a/<run>/final.pt and ~/premonition-models/rsn358a/<run>/final.pt (hashes match), never in git.

What it means: the round-thinking net beat its plain twin big on grids6 twice (+67, +76) and sums6 once (+59) without slipping on practised sizes — extra thinking time did turn into bigger solved puzzles there. But it failed the bar because on seed 2 the plain twin won sums6 by 11; one win + one loss doesn't hold up. The number puzzles say nothing about round-thinking — neither net could do them at all.

What it doesn't mean: round-thinking isn't useless (seed 1 swept every mark); the plain net isn't better (lost grids6 twice, never won numbers); the idea isn't proved wrong (gaps were large, clause needs tiny gaps everywhere); and this says nothing about sums8/grids7 (report-only) or about giving the plain net extra compute another way (never tested).

PUSH: artifacts/claude-rsn358a-20260925/RESULTS.md, artifacts/claude-rsn358a-20260925/SEAL-run.sha256.txt, artifacts/claude-rsn358a-20260925/runs/ (12 files), artifacts/fable-predictions-ledger.md (5 lines appended, ledger otherwise untouched; only my own new RESULTS.md lines edited, no existing/sealed/another-agent file modified).
