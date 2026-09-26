Renting your 5090 for the reasoner twin — checking gates and standing by to train.
Gates passed — no duplicate, credit is fine. Hunting a cheap 5090 now.
First host failed with a registry proxy error. Retrying start once before moving on.
Rental #2 is live (RTX 5090, CUDA OK). Shipping the sealed code over.
Seal OK, selftest OK. Checking the puzzle pool.
Pool matches exactly. Launching all four training runs detached.
On pace (plain ~47%, loop ~36% at 14 min; projected done ~04:38Z, cap 05:09Z). Waiting.
Both plain nets finished. Loops still going — checking.
All four nets trained. Sealing checkpoints, then evals.
All four evals finished fast. Pulling the full count logs.
All artifacts present. Assembling the runs/ directories on the rental.
Copy-back complete. Destroying the rental.
Rental destroyed and confirmed gone. Writing RESULTS.md.
Ledger done. Figuring out the push path.
Push via bash is blocked in this environment. Committing locally so the push is one command.
**Verdict: INCONCLUSIVE on both seeds** (G0 validity gate not met — loop arm clears only sums4 of the 3 practised-size tests: seed 3 loop 300/109/1, seed 4 loop 298/91/1; needs ≥210/300 in ≥2 kinds). Neither PASS nor FAIL. Proved-wrong clause not triggered (needs G0 met).

Credit gate: **6.33** (above the $3.00 bar, so rented).

Integer counts (/300 each). Per-seed (plain | loop own-stop | loop−plain) — seed 3: sums4 300|300|0, grids5 236|109|−127, numbers4 16|1|−15, sums6 239|131|−108, grids6 187|58|−129, numbers5 0|0|0, sums8 120|21|−99, grids7 69|10|−59. Seed 4: sums4 300|298|−2, grids5 241|91|−150, numbers4 10|1|−9, sums6 153|94|−59, grids6 186|36|−150, numbers5 1|0|−1, sums8 33|6|−27, grids7 73|3|−70. G1 FAIL both; G2 FAIL both (seed 4 numbers4 −9 passes, grids5 −150 fails); G3 FAIL seed 3 (sums6 own 131 vs fixed-16 137, needed ≥132), PASS seed 4. Full fixed-rounds (1/2/4/8/12/16/24/32/48), any-round, mean rounds, training exact_by_kind, seals, and prediction audit are in artifacts/claude-rsn358d-20260926/RESULTS.md. Headline facts: plain beat loop on every bigger test (sums6 239/153 vs 131/94; grids6 187/186 vs 58/36); numbers4 plain 16/10 vs loop 1/1 (358a reference: 0–5 both); numbers5 0/0/0/1. The 75,972-puzzle pool cured memorisation (train numbers4 exact: plain 0.27, loop 0.001) without creating generalisation.

Compute: RTX 5090, all four at once (87–90% util, ~8/32 GB). Minutes: loop-s3 35.2, plain-s3 29.6, loop-s4 35.3, plain-s4 29.6. Spend ~$0.41 of $0.80 (rental 2: 0.82 h × $0.4852; rental 1 stopped, storage only). First rental 03:39:42Z, destroy 04:34:03Z = 54 min of the 1 h 30 cap. No TOO-SLOW (14-min projection showed finish ~04:38 vs 05:09 cap). Seal: 6/6 code lines OK, selftest ok, pool string exact, four 64-hex checkpoint seals recorded before evals, each eval once per checkpoint, tests.json matches eval logs. No code edits, no errors, nothing re-run.

Every deviation: (1) Rental 1 (offer 46753295) never started — host docker registry proxy refused; restarted once, same error, destroyed; rental 2 (offer 44173691, rel 0.9984) worked. 2 rentals of max 3. (2) Billed dph $0.4852 vs $0.469 search estimate. (3) Checkpoints discarded with rental — Mac had 7 GB free < 8 GB copy bar — after sha recorded. (4) Only the 4 specified files per run copied to runs/<R>/; eval stdout logs stayed on the rental. (5) The `git archive | ssh` pipe hit the 120 s tool timeout on close but the extract was complete (verified). (6) SEAL-run paths are W/\<run\>/final.pt relative to the rental extract root. (7) Destroyed only my two rent-358d instances; confirmed zero rent-358d live. (8) **PUSH blocked: this environment denies `git push` via bash.** Everything is committed as d2f4c096e ("builder results: rent-358d rsn-358d loop-vs-plain (INCONCLUSIVE both seeds; G0 not met) + ledger lines", 19 files, +1765/−0, exactly the PUSH list) in the temp worktree at /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/rsn358d-push (branched from origin/builder-outbox tip df67d1b22, duplicate re-checked empty at push time). To finish: `git -C <that path> push origin HEAD:builder-outbox`. Local copies of RESULTS.md, runs/, and the ledger append also remain in the main worktree.
