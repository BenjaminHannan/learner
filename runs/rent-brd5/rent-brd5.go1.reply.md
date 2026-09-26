Starting brd5 GPU run — checking gates and credit first.
Credit and duplicate gates pass — searching for a 5090 rental.
Tree built and md5 matches — waiting for the rental to boot.
Files on rental with md5 verified — installing packages and fetching the model.
Selftest passes — launching the registered run detached.
Good progress at ~10 min (base 123, W seed 0 at 144) — continuing to monitor.
Run finished — copying results back.
Checksums match — destroying the rental and confirming.
Verdict: INCONCLUSIVE (registered run finished clean; the W-vs-base replication bar missed, so the marks force inconclusive even though every PASS sub-condition on the W–N gap is numerically TRUE).

Counts (integers):
- Credit gate: 8.94 (credit; balance 0) — above 3.00, proceeded. 1 rental, 0 re-rents.
- Duplicate gate: 0 gpu dirs on origin/main or origin/builder-outbox; 0 live rent-brd5 instances — proceeded.
- Test panel: 240 puzzles (160 3-num + 80 4-num); md5 968b9f2fb798f0c30b58e99a11185050 verified on rental. Selftest: "selftest ok" (1 line).
- Practice: 400 puzzles; own 20, wins 167, examples 187; W distinct puzzles 187; N distinct wins 20, N distinct puzzles 40.
- cov@30: base 123; W 144/145/136; N 91/83/97; C 22/22/18. Per-seed W−N gaps +53/+62/+39 (D=24). CI W−N [16.52, 26.15]pp; CI W−base [2.17, 13.5]pp; CI N−base [−20.18, −6.81]pp.
- PASS sub-conditions: 4/4 TRUE. Proved-wrong clause: FALSE (upper 26.15 ≥ +5). Inconclusive third condition: TRUE (no W seed ≥ base+24=147; max W=145).
- Spend: ~0.46 h × $0.5037/h ≈ $0.23 of $1.00 budget. GPU: RTX 5090, instance 52678258, destroyed and confirmed gone (0 rent-brd5 live). Wall 20.0 min script-measured. Model commit 87179e5c1f455ef22e6223592d2d61351b525bfc.
- Copied back 4 files (brd5_summary.json, streams.json with 240+3+3+3 streams, narrow_picks.jsonl with 20 lines, log.txt), md5-verified rental-vs-local. Staged (force-add): 5 new brd5 files + 1 ledger line. No commit/push of branches (watcher pushes).

Deviations (every one):
1. Kit §A builds the rental tree from full origin/builder-outbox + origin/main plus self122_head.pt; per this task's step 1 I shipped only the 9 listed files (6 scripts + 2 puzzle panels + PASSMARKS) — instructed override, additive-only.
2. Kit §C fetches two models (MiniCPM5-1B + all-MiniLM-L6-v2); per this task I fetched only plain MiniCPM5-1B ("never download any other model").
3. Kit §B says no LOW-CREDIT stop (auto-refill); this task imposed a $3.00 CREDIT-STOP gate — applied the task's gate (credit 8.94, passed).
4. Rental limits used the task's values (budget $1.00, max 3 rentals, label rent-brd5) not the kit's ($4/job, 4 rentals).
5. First multi-file scp command failed (wrong scp multi-source syntax, local "No such file" — no data lost); retried as 4 single-file scps, all arrived and checksummed.
6. `vastai destroy` needed a piped `y` confirmation on first attempt (aborted once, $0 effect); destroyed on retry.
7. First detached-launch SSH call exceeded my 120 s tool timeout because it slept 60 s after launching; the launch itself had succeeded (verified process + log on next call).
