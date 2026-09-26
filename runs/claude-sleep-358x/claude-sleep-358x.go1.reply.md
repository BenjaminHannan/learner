Starting your sealed builder run — fetching code and checking gates.
Sealed specs loaded. Now checking duplicate and budget gates.
No duplicates found. Checking remaining gates and source checkpoints.
Source hashes verified locally. Now checking rental gate and live instances.
Credit and rental gates pass. Now hunting for a cheap 5090.
Found cheap offers. Checking prior rental setup before launching.
Rental playbook confirmed. Finalizing offer selection.
Rental created. Waiting for it to come online.
Rental is having image-pull issues. Monitoring briefly before failing over.
Second host showing same image-pull error. Checking what works elsewhere.
Third rental is pulling the image. Waiting for SSH.
Rental is live. Streaming the sealed code tree now.
Seals pass 14/14. Copying the 8 source checkpoints.
All 8 sources verify. Launching all 16 carry runs detached.
All 8 loop workers died, 8 plain workers healthy. Waiting for plains to finish.
All 8 plain nets finished in 4.9 min. Launching loop batch 1 (seeds 1–2).
Loops are fast (~6 min/batch). Waiting for batch 1 to finish.
Batch 1 done. Launching loop batch 2 (seeds 3–4).
All 16 runs complete. Sealing weights and running the 16 evals.
All 16 evals complete. Copying results back to the Mac.
Results are back. Computing the verdict numbers.
All artifacts verified. Destroying the rental to stop spend.
Rental destroyed and confirmed gone. Writing the results file.
VERDICT: FAIL + PROVED-WRONG. Practice on sums/grids/number puzzles carries over to mazes for the plain net (pre 812.5 vs fresh 2000 mean steps-to-bar, pre < fresh 4/4 seeds) but NOT for the loop (pre and fresh both 5000/5000 on all 4 seeds — never reached the bar). Loop-pre mean (5000) is far above plain-pre mean (812.5), so the "loop learns a new kind faster" claim is proved wrong. Full report: artifacts/claude-rsn358x-20260926/RESULTS.md (commit 6ce4bf7b0, local — push blocked, see deviation 7).

Credit gate: balance 0, credit 5.894937036269795. Director rental gate: none (auto-refill). Duplicate gate: clear (no RESULTS.md on origin/main or origin/builder-outbox; 0 live claude-sleep-358x).

Integer counts:
- SEAL-code-v2: 14/14 OK on rental before any run; selftests ok (envs prints "selftest ok: ..." prefix-match, run prints "selftest ok"); code never edited.
- Sources: 8/8 sha256 match on Mac and rental.
- Carry runs finished: 16/16 (4000 steps each); evals run exactly once per final-carry.pt: 16/16, counts only, TEST-ONLY files never opened.
- Steps-to-bar (7x7 ≥150/200; 5000 = never): loop-pre 5000×4 (mean 5000); loop-fresh 5000×4 (mean 5000); plain-pre 750/750/1000/750 (mean 812.5); plain-fresh 2000×4 (mean 2000).
- X0: PASS (plain-fresh bar 4/4 ≥ 3 required; sources 8/8). X1: FAIL (ratio 5000/5000 = 1.00, needs ≤0.75; pre<fresh 0/4). X2: FAIL (ratio 5000/812.5 = 6.15, needs ≤0.75; 0/4). Proved-wrong clause fires (5000 ≥ 812.5).
- Cold (0-step): 0/200 on 7x7 and 9x9 for all 16 nets. 9x9 to-100/to-200: 5000 (never) for all 16. 7x7 to-200: loops 5000×8; plain-pre 1500×4; plain-fresh 3000×4.
- Tests /300 (maze7/maze9/maze11/maze13): plains maze7 300 on all 8; loops maze7: 103,134,90,114,39,92,8,81 (pre-s1..s4, fresh-s1..s4); best loop maze9 59 (pre-s4); all other details in RESULTS.md.
- Spend: rental 3 (52775569, RTX 5090) 16:09:51–16:39:41Z ≈ 0.50h × $0.4898 ≈ $0.24 of $0.60; rentals 1–2 destroyed while loading, $0. Task total ≈ $0.24. Rental destroyed, 0 live labelled claude-sleep-358x confirmed.
- Pushed paths contain 0 .pt files (67 files: RESULTS.md, SEAL-run 16 lines, 64 run files, ledger line).

Every deviation (7): (1) source path has extra nesting `claude-rsn358i-20260926/W/` vs brief; (2) 358i SEAL-run.sha256.txt on neither origin branch — verified 8/8 vs local worktree copy (matches grab358i 8/8 claim); (3) envs selftest prints "selftest ok: ..." with detail; (4) rentals 1–2 died on host docker-proxy pull failure, destroyed in-rule, $0; rental 3 on other host with pinned image worked (3 rentals, max allowed); (5) 16-at-once OOMed (loop ≈4 GB/proc; 8 loop procs died at step 0, nothing kept) — ran 8 plains then loops 2×4, not "seeds 1-2 first"; (6) SEAL-run labels weights `W/<R>/final-carry.pt`, weights never pushed; (7) `git push` denied by sandbox — commit 6ce4bf7b0 is local-only with own paths; watcher must push; others' staged files untouched.
