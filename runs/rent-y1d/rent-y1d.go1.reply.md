Starting y1d GPU run — fetching latest instructions and checking for duplicates.
Duplicate check looks clear so far — confirming instance details and account balance.
No duplicates found and budget checks out — renting the GPU now.
First host failed to start — trying a different host.
Rental is running — streaming code and setting up the environment.
Models downloaded with matching commit — running verification checks.
Run launch looked odd — checking whether the process actually started.
Run finished fast — verifying completeness before copying back.
Files verified — destroying the rental.
Rental destroyed — writing the results file and ledger entry.
DONE — y1d GPU diagnosis complete, all artifacts copied back, rental destroyed.

Verdict: complete run, no stop condition triggered. The plain 1B reading raw turns answers 13 of 56 answerable DEV asks whole-chat (vs notebook 5), 3 of 56 from gold-only turns, 9 of 56 via k20 recall.

Integer counts:
- Duplicate gate: 0 gpu artifacts on origin/main, 0 on origin/builder-outbox, 0 live claude-memory-y1d — proceeded.
- Credit at gate: 5.499236376269863 (number only, auto-refills, no stop).
- Rentals used: 2 of max 4. Rental 1 (52756144, dph $0.406): ~6 min in loading, host docker-registry proxy error, destroyed. Rental 2 (52757085, RTX 5090, dph $0.469): 13:55:31Z–14:08:33Z, ran the job.
- Dollars: ~$0.04 + ~$0.10 = ~$0.14 of $0.40 budget.
- SEAL: 8/8 OK. Selftest: printed "selftest ok" (1/1).
- Run: 71 [y1d] lines for 71 asks, 203 rows (= 3×71 − 10 never_told gold-skips), asks=71, conds=3, n=4, seed=4021. Wall ~2 min (14:05:42Z–14:07Z), no 10-min stall, process exited alone.
- Results: answerable_right gold|p382 3, gold|greedy 0, all|p382 13, all|greedy 5, k20|p382 9, k20|greedy 5; never_told idk all|p382 5/10, all|greedy 9/10, k20|p382 8/10, k20|greedy 10/10.
- Decision rules: D1 A_gold 3 < 20 → reading is the bottleneck. D2 F = −10 → finding costs nothing. D3 A_k20 9 < A_all−3 = 10 → ranking costs 4. D4 guard cost gold 1, all 1, k20 0. Routing not met (13 < 25; never_told-under-all 5/10 < 8/10). Proved-wrong clause NOT triggered (13 > 10).
- Copy-back: 3 files sha256-verified identical, then destroyed; 0 claude-memory-y1d live after. No other label touched.
- MiniCPM commit 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected); MiniLM 1110a243f; torch 2.8.0+cu129 CUDA True.
- Staged for watcher PUSH: gpu/y1d_rows.jsonl (203), gpu/y1d_summary.json, gpu/log.txt (74), RESULTS-gpu.md, ledger line — 5 files, 612 insertions, 0 deletions.

Deviations (2, both in RESULTS-gpu.md): rent-kit's fable_self122 smoke check raises FileNotFoundError (no reader weights per task — SEAL/selftest gates passed, not a stop); first ssh launch's trailing tail/ps printed nothing due to shell `&` precedence (follow-up showed a healthy run, completed alone).
