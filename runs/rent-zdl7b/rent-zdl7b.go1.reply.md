GPU run dl-7b queued — checking credit, duplicates, and passmarks before renting.
Credit and duplicate gates pass — hunting for a 5090/4090 rental.
Approval confirmed on origin/main — now tracing how prior runs provisioned the model.
Still piecing together the rental setup — checking model provisioning details.
Found the model snapshot pattern — pulling the exact rental configuration.
Cheapest reliable 5090 found ($0.40/hr, Korea) — creating the rental now.
Rental running — setting up torch, transformers, and the model snapshot.
Selftest passes — launching the 85-minute registered run detached.
Run is live (PID 517, pool step in progress) — polling for the first night line.
First night line printed in 7 minutes — TOO-SLOW gate cleared. Monitoring the full run.
S s12 complete (7/7). Continuing through S s13, F s12, F s13.
S arm done (14/14). F arm with anchor now running — slightly slower per night.
Final seed in progress (F s13 night 2/7) — waiting for completion.
Run finished in 73 minutes — verdict FAIL in the marks preview. Copying artifacts back.
Files verified intact (hash tools were misbehaving; Python confirms). Reading full results for the report.
Premise supported (84.6%). Destroying the rental, then writing the report.
Rental destroyed and confirmed gone. Writing RESULTS-gpu.md.
Ledger has 2 staged lines from other jobs — my commit will include them (additive; will report). Checking push state.
Push is policy-blocked — the watcher will push the committed paths. Final verification.
**Verdict: FAIL** (F1 pass, F2 pass, **F3 fail**, F4 pass, F5 pass; not proved wrong; not inconclusive).

Integer counts (from gpu/dl7_results.json marks block + per-night rows):
- Base: TEST lucky L0 = 66, reached 35, greedy 2; HARM right 200/300. Pool: asked 3000, questions 1479, answered 1282, fragile 427 (bar 100).
- Night-7 lost: F = 3 (s12), 4 (s13), sum 7; S = 11 (s12), 15 (s13), sum 26.
- F1: 7 <= 13.0 (0.5×26) and 4 < 11 each-seed → PASS.
- F2: 0 of 14 F nights lost > 10 (limit 1) → PASS.
- F3: 179, 216 >= 132 (2×66) yes, but gains 263 < 276.0 (0.8×345, short by 13) → FAIL.
- F4: 0 of 14 F nights >15% below prior night (worst dip 200→179 = −10.5%) → PASS.
- F5: reached 52, 53 >= 35 → PASS.
- Proved-wrong (F lost >= S both seeds): 3 >= 11 false → not proved wrong.
- Inconclusive bars all clear: L0 66 ≥ 10; S lost sum 26 ≥ 20; pool 427 ≥ 100.
- Report-only: night-7 KL F 0.0175/0.0128 vs S 0.1529/0.1764; gained F 14/20 vs S 47/50; premise check 22/26 = 84.6% of S lost items in base's lowest-confidence third (≥60%) → premise SUPPORTED.
- Run: RTX 5090 (KR), run wall 72.4 min (18:48–20:01Z), rental ~1.45 h × $0.4167 ≈ $0.60 of $1.00; contract 52799251, 1 rental; credit at gate 4.09; commit f35b1b09; model rev 87179e5c; selftest ok; first night line at 7 min.

Deviations (5):
1. Task text said budget HELD for Ben's yes; origin/main handoff/queue/rent-zdl7b.md shows Ben approved +$1.00 at 18:39:42 UTC, so I proceeded under the approved $1.00 (kill line $0.95 never hit).
2. `shasum`/`sha256sum` on this Mac returned the empty-file hash for all 4 copied files; verified instead via Python (sizes 98893/59682/121/12941 bytes, JSON parses, marks match).
3. Ledger commit includes 2 previously-staged lines from other jobs (k1f HOST-FAIL, rsn-358i2) plus my 1 line — additive, same file.
4. `git push` is blocked by tool policy; commit 9c11efc5b (6 paths: 4 gpu files + RESULTS-gpu.md + ledger) is ready for the watcher to push. No weights pushed (run saves none).
5. First launch SSH call timed out at 60 s while the remote wrapper lingered, but the setsid-detached run (PID 517) was unaffected and completed; the stuck wrapper held no resources the run needed.
