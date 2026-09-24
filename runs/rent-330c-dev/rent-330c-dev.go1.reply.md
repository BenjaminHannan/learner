Renting a GPU twin for the 330c rehearsal — pulling the sealed kit and checking budget.
No duplicate on record — checking the kit details and rental options.
Reader and seal hashes check out — verifying rental credit and availability.
Found a cheap 5090 that fits the budget — building the code tree for upload.
Tree packaged — renting the GPU now.
First host stalled on startup — destroying it and trying the next offer.
Second host is running — uploading the code tree and reader model.
SSH is refusing connections — rebooting to fix the tunnel.
Fourth host is up — testing SSH access.
SSH works — checking the GPU environment.
Reader hash matches — extracting the tree and installing dependencies on the rental.
Models cached with matching hashes — running seal verification and unit tests.
Arm 1 launch looks off — inspecting what happened on the box.
Arm 1 actually finished in the background — verifying its output.
Both arms finished clean — running the scorer.
All artifacts verified — destroying the rental.
Appending the ledger line and doing a final check.
Verdict: PASS (rehearsal). rent-330c-dev ran end to end on rented Linux GPU 52455952: seal 3/3 OK, 338b 3/3 OK, both arms finished (P330c 248 rows, twinb 194 rows, 10/10 lives each), scorer exit 0, twinb `<think` rows 0, tracebacks 0. Spend ~$0.27 of $1.50. All PUSH paths staged locally; watcher to push.

Marks table (integer counts):

| check | count |
|---|---|
| duplicate run/ on origin/builder-outbox | 0 (absent, proceeded) |
| DEV seal files OK on rental | 3/3 |
| 338b unit tests OK on rental | 3/3 |
| arms with twinb banner as first line | 2/2 |
| P330c rows / lives / user / confirm_answer | 248 / 10 / 194 / 54 |
| twinb rows / lives / user / confirm_answer | 194 / 10 / 194 / 0 |
| scorer exit code | 0 |
| score files copied back, sizes match box | 7/7 |
| run files copied back, sizes match box | 2/2 |
| twinb rows with `<think` in reply | 0 (expected 0) |
| P330c rows with `<think` in reply | 0 |
| traceback lines in either arm log | 0 |
| TEST-ONLY panel items opened / quoted | 0 / 0 |
| judge/grammar packets opened | 0 |
| month-end code files edited | 0 |
| P330c facts_saved / facts_total | 49 / 131 |
| twinb facts_saved / facts_total | 0 / 131 |
| P330c confirm_rows / twinb confirm_rows | 54 / 0 |

Every move: fetched origin main + builder-outbox; confirmed no duplicate; credit $6.13 ≥ budget; built tree (builder-outbox + main, self122_head.pt sha 5ca02173 match, 156 MB); offer search → rented 52453726 ($0.4676/h, loading >6 min, destroyed $0); fresh search → rented 52454797 ($0.469/h, running but ssh refused 6+ min, 1 reboot failed, destroyed ~$0.05); fresh search → create 52455934 success:false, destroyed stub $0; fresh search → rented 52455952 ($0.469/h, RTX 5090 32607 MiB, torch 2.8.0+cu128 CUDA True); uploaded tree + READER (sha b4fd93a2 match); pip install transformers 5.17.0; cached BASE (commit 87179e5c match) + MiniLM; route122 OK; seal 3/3; 338b 3/3; arm P330c (184 s) then arm twinb (69 s), sequential separate processes; scorer OK; copied run/+score/ back with byte-size match; destroyed 17:46:25Z, 0 rent-330c-dev live (sibling rent-330c-dev2 left alone); ledger appended; RESULTS-rent.md written.

Misses/deviations: 3 dead rentals of 4 allowed (detail above); one transient race where a backgrounded arm's log wasn't visible in the same ssh call but the arm completed detached — no data lost, walls taken from container clock + file mtimes. No code edits, no panel contact.

What it means in plain English: the 330c dress rehearsal works on Linux — the full agent and the plain twin both ran all 10 practice lives and the scorer counted everything. The full agent remembers 49 of 131 facts and asks 54 follow-up questions; the plain twin remembers nothing and never asks. What it doesn't mean: nothing about the real registered test — this was practice data only, and the blind judges haven't run.

PUSH: artifacts/claude-e2e330c-dev-20260924/RESULTS-rent.md artifacts/claude-e2e330c-dev-20260924/run artifacts/claude-e2e330c-dev-20260924/score artifacts/fable-predictions-ledger.md
