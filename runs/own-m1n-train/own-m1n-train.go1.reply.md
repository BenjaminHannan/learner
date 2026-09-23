Starting M1n build — verifying workspace and passmarks.
Passmarks and code understood. Now checking ledger, rental state, and training script.
No rental history on record. Checking local state and GPU offers.
Checking rental creation options and SSH setup.
Data is small and in git. Renting the GPU now.
Instance 52279213 rented at 18:43:40 UTC ($0.5159/hr). Waiting for it to come up.
SSH is up. Setting up the GPU box now.
While the box sets up, verifying seals locally from origin/main.
Seals verify: all 8 hashes match. Checking box setup.
Data built: 5602 train kept, 1000 dev kept, 0 dropped — matches expected. Waiting on venv.
Setup is running (pip downloading torch). Waiting.
Venv ready (torch 2.11 cu128, transformers 5.17). Downloading the model.
Model downloaded (commit 87179e5c…). Launching training.
Training healthy: step 140/702, ~3750 tok/s. Watching to completion.
Training complete with merged model. Collecting training stats.
Seal written. Running the single dev measurement.
~64 rows/min, ETA ~15 min. Polling periodically.
Dev done: 1000/1000 spoke, 1000 first-try, but only 59 distinct replies. Running the Pm1n.3 recount and pulling quotes.
Copying the 2.2GB merged model to the Mac in the background while I write up results.
Copy is slow (~0.8MB/s, ~40 min left). Writing artifact files meanwhile.
Transfer stalled to a crawl. Switching to resumable rsync.
Connection back. Resuming copy with rsync.
Rsync is transferring fast now. Waiting for it to finish.
Transfer is 99.97% there (only ~0.6MB short). Waiting for rsync to finish.
Copy complete. Verifying the model hash.
Hash matches. Destroying the instance to stop the clock.
## Verdict: FAIL (Pm1n.4 variety miss; the other 4 marks PASS)

| Mark | Bar (counts) | Got (counts) | Result |
|---|---|---|---|
| Pm1n.1 spoke within 5 tries | ≥ 990/1000 | 1000/1000 (100.0%) | PASS |
| Pm1n.2 greedy first-try pass | ≥ 950/1000 | 1000/1000 (100.0%) | PASS |
| Pm1n.3 fresh slot_check recount fails | 0 | 0 / 1000 non-null | PASS |
| Pm1n.4a distinct slotted replies | ≥ 300/1000 (30%) | 59/1000 (5.9%) | FAIL |
| Pm1n.4b most common reply | ≤ 30/1000 (3%) | 129/1000 (12.9%), "<S1>'s \<R1> is \<V1>." | FAIL |
| Pm1n.5 crashes | 0 | 0 | PASS |

Fallbacks: 0 in every status (OK 350/350 spoke, SAVED 150/150, UNKNOWN 150/150, ABSTAIN 100/100, CLARIFY 150/150, FORGOT 100/100). Speak timing: median 1221.5 ms/row, p90 1381.7 ms (cuda). Training: 702/702 steps, step-1 loss 2.9962 → step-700 loss 0.262, dev_loss 0.9034, 3.72 min, 3658.9 tok/s, batch 16 with no OOM (no batch-8 fallback). Base: MiniCPM5-1B commit 87179e5c1f455ef22e6223592d2d61351b525bfc. Data: 5602 train / 1000 dev kept, 0 dropped (as expected). Cost ≈ $0.68 (1.32 h × $0.5159/hr, ceiling $4/3h respected). "Proved wrong" clause (first-try < 80%) NOT triggered.

## Every move
- Seals: SEAL-code 5/5 lines OK, SEAL-data 3/3 lines OK (hashes match origin/main; no sealed file touched). Sealed code run unedited.
- Rented 1× RTX 5090 (instance 52279213, label own-m1n, reliability 0.9877, $0.5159/hr) 18:43:40Z→20:02:52Z. Pre-check: 0 live instances, ledger rental total ≈ $0.09 → cap $30 safe. New venv on box (torch 2.11 cu128, transformers 5.17, peft, safetensors, hf_hub).
- SEAL-run.sha256.txt written BEFORE measuring (merged sha de12daf4…, counts sha 986dd779…).
- Dev measured ONCE (1000/1000 rows, default 4 samples), never re-run or tuned on. Recount done independently (0 fails). 20 seed-7 sample rows quoted in dev_out_sample.jsonl.
- Model copied to ~/premonition-models/own-m1n-mouth/merged/; local shasum equals sealed hash. Weights never in git.
- Instance destroyed; only own-m1b (v1 rerun, parallel on purpose) remains — untouched. Ledger appended (Pownm1n.1–.5 + P-vast-m1n).

## Misses / deviations
- MISS: Pm1n.4 variety — top 5 slotted replies cover 457/1000 rows. The mouth learned the format, not variety.
- Host networking flaked twice mid-run (ssh banner timeouts, ~2–5 min each; API still showed running). No re-rent needed: compute was done and the model copy resumed via rsync and verified by hash. Watchdog polls ran throughout; log progress never stalled 10 min.
- The task's OPUS-RULES.txt tmp path doesn't exist on this Mac; I worked from the key points restated in the task (additive-only: 6 new files created, ledger append-only, no sealed/another-agent file touched).
- Added the Mac's ssh pubkey to the vast.ai account (key id 1420036) to reach the rental. No secret printed or stored in the repo.
- PUSH paths ready: artifacts/claude-own-m1n-20260923/{RESULTS.md, SEAL-run.sha256.txt, dev_summary.json, dev_out_sample.jsonl, train_summary.json, train_log.jsonl} + artifacts/fable-predictions-ledger.md.

## What it means (plain English)
Think of the mouth as a student who learned to fill in a form perfectly but writes every answer in the same few sentences. It never breaks the rules (every reply names the right person and value, 100% on the first try), but it sounds like a robot: 59 different phrasings where 300 were required, and 1 in 8 answers is the identical template "\<name>'s \<relation> is \<value>." What it does NOT mean: the training data or format failed — the slot system works flawlessly. The next step is a variety problem (e.g. different training sampling or a diversity rule), not a correctness problem.
