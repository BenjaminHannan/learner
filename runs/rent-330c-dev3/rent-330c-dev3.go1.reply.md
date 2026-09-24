Month-end rehearsal queued — fetching the sealed instructions and rental kit.
No duplicate on record — setting up the dress rehearsal run.
Prior runs mapped — inspecting the latest scripts and last rehearsal log.
Code tree sealed — checking the reader payload and rental offers.
Rental secured — waiting for it to come online.
SSH proxy is failing on this host — attempting a reboot before re-renting.
First host's SSH was broken — destroyed it and searching for a fresh host.
Healthy 5090 online — uploading the code tree and reader.
Reader upload was interrupted — re-copying the weights.
Reader verified — installing dependencies and pulling the generator model.
All pre-checks green — launching the P330c arm.
Arm and scorer finished — pulling the full log to verify.
Clean run — copying results back to the Mac.
Results verified — destroying the rental and closing out.
VERDICT: rent-330c-dev3 DONE, all checks passed. The final pre-seal 330c agent (333d + 338b-with-capital-Your-check + vary330c) ran clean on a rented RTX 5090: DEV seal 3/3, all unit tests green, 1 arm (P330c, 248 rows / 10 lives, wall 3m9s), scorer exit 0, 0 tracebacks, ~$0.24 of the $1.00 budget, 0 instances left live.

Marks table (integer counts):

| Check | Count |
|---|---|
| DUPLICATE hits (builder-outbox run/ pre-existed, or live rent-330c-dev3) | 0 |
| DEV bank seal (`sha256sum -c SEAL.sha256.txt`) | 3/3 OK |
| 338b unit tests | 3/3 OK |
| 333d unit tests | 2/2 OK |
| vary330c unit tests | 2/2 OK |
| twinb banner first-line match | 1/1 |
| Arms run (P330c only, per task) | 1 |
| Arm rows / lives | 248 / 10 |
| Scorer exit code | 0 |
| Score files (grammar + judge_asks + judge_saves + mechanical) | 4 |
| Tracebacks (arm + score logs) | 0 |
| Rentals used (of 4 allowed) | 2 |
| rent-330c-dev3 instances live after | 0 |
| Result files copied back and row-checked before destroy | 5/5 |
| Code files edited | 0 |
| Panel items opened/read/quoted | 0 |

Every move: fetched origin/main; confirmed no DUPLICATE (no run/ on builder-outbox, no live rent-330c-dev3); verified disk 20 GB free and $9.02 credit; built tree.tgz from builder-outbox + main archives with self122_head.pt sha match 5ca02173; offer search then rented 52461049 (offer 44173823, $0.469/h) at 18:00:34Z — ssh proxy broken, reboot failed, destroyed ~18:08Z (~$0.06, no work); re-ran offer search, rented 52462150 (offer 45043235, $0.469/h, KR, 16 vCPU) at 18:08:34Z, running ~18:11Z; uploaded tree + READER (first reader scp broke mid-transfer at 519M with wrong sha, re-copied to full 2.1G with sha match b4fd93a2, plus 5 config/tokenizer files); image torch 2.8.0+cu128 CUDA True; downloaded BASE MiniCPM5-1B commit 87179e5c (match) + MiniLM; route122 returned no raise; seal 3/3; all 3 unit-test suites green; launched arm+score under setsid/nohup; arm wrote 248 rows/10 lives in 3m9s; scorer printed its line (in RESULTS-rent.md verbatim); copied run/ + score/ back, verified 248 rows / 10 lives locally; destroyed 52462150 at 18:31:59Z (~0.39h x $0.469 = ~$0.18); whole-task ~$0.24 of $1.00; confirmed 0 rent-330c-dev3 live; wrote RESULTS-rent.md; appended 1 ledger line.

Every miss / deviation: rental 1 was a dead host (ssh proxy failure, same pattern as rent-330c-dev's 52454797) — cost ~$0.06, counted in budget, no data lost since no work had run. Reader upload needed a second pass after a dropped connection. Extra file `rental-run330c.log` sits in the new folder besides the PUSH list (new file in a new folder, not pushed — PUSH paths are exactly RESULTS-rent.md, run, score, ledger). Ledger diff shows 22 added lines because sibling tasks appended 21 lines concurrently; my 1 line is last, append-only preserved. Scorer's `user_rows: 194` vs my local key-guess check is cosmetic — arm log and scorer agree on 248 rows / 10 lives.

What it means in plain English: think of this as the final dress rehearsal before the big sealed test. The robot ran 10 pretend lives (248 conversation turns) on fake practice data, saved about 49 facts out of 131, answered 11 tricky questions right while safely saying "I don't know" on most of the rest, and invented only a handful of wrong answers. Nothing crashed. What it doesn't mean: this says nothing about the real hidden test — practice data is not the real exam, and these counts are just bookkeeping, not a grade.

PUSH (left in worktree for the watcher): artifacts/claude-e2e330c-dev3-20260924/RESULTS-rent.md, artifacts/claude-e2e330c-dev3-20260924/run, artifacts/claude-e2e330c-dev3-20260924/score, artifacts/fable-predictions-ledger.md.
