Starting dl-5 GPU run — checking credit, duplicates, and passmarks.
Credit gate passes (credit $8.60) and duplicate gate passes (no gpu artifacts, no live dl5 instance). Searching for rental offers.
Setup pattern confirmed from dl-2/dl-3 (local BASE snapshot, pytorch 2.8.0 runtime image). Creating the rental now.
Rental 1 starting (contract 52770457, $0.4361/hr). Waiting for it to come up.
Host can't pull images — destroying rental 1 and trying another host.
Rental 2 is provisioning (image building — Docker works here). Waiting for running state.
dl5 selftest ok, model downloaded. Running gridday selftest.
Both selftests pass. Launching the registered run detached.
Run is live (PID 598, base measured 372/762). Waiting for first-night progress.
Fast pace (~3.3 min/night, nights 1–2 done). Checking back in ~30 min.
Halfway (13/26 lines) at 40 min. Waiting for completion.
Nearly done (K arm running, adapters saved). Waiting for finish.
Run finished — verdict FAIL, not proved wrong. Copying artifacts back.
Hashes match. Analyzing results for the blind recount.
Recount matches exactly. Destroying the rental, then writing the report.
Writing RESULTS-gpu.md.
**Verdict: FAIL** (G1, G2, G2b pass; G3 fails). Not INCONCLUSIVE, not proved wrong.

**Integer counts (blind recount of dl5_results.json — all match the stored marks block exactly):**
- Night 0: 372/762 (forced 314/619, open 58/143) = 48.8 pts; harm-right 200/300
- S final: s8 715/762 = 93.8 (forced 618/619, open 97/143); s9 712/762 = 93.4 (forced 619/619, open 93/143)
- P final: s8 50/762 = 6.6 (forced 0/619, open 50/143); s9 55/762 = 7.2 (forced 0/619, open 55/143)
- G1: 93.8, 93.4 ≥ 63.8 — PASS. G2: gaps 87.2, 86.2 pts — PASS. G2b open gaps 32.8, 26.5 pts — PASS. G3: S lost 98 (s8), 61 (s9), both > 20 — FAIL.
- Not INCONCLUSIVE: S night-1 rows 1144, 925 (≥100). Proved-wrong false: open S 97>50 and 93>55.
- S days solved/150: s8 101,103,105,107,113; s9 85,101,92,101,104. P legal-wrong per night: s8 224,247,260,269,269; s9 182,236,242,250,272. K s8 per-night right: 705,715,705,715,706. Test-grids-in-day: 0.

**Run facts:** RTX 5090 (South Korea), 87.7 min wall, ~$0.81 of $1.60 (rental1 ~$0.04 + rental2 1.60h×$0.4806 ~$0.77). Code commit 76d9d98f. Adapters local-only, 16575557 B each, sha c74b1783 (s8) / 5352be44 (s9). All 6 copy-back hashes match both ends. Rental destroyed; 0 claude-fixsleep-dl5 live. Credit at gate 8.60 (balance 0).

**Every deviation:**
1. Rental 1 (52770457) died on host docker-proxy pull refusal — destroyed un-run, re-rented (2 of max 3).
2. Pip-installed transformers==5.17.0 plus huggingface_hub (a transformers dependency) on the rental so the image-missing transformers and the pinned-revision snapshot download (same files as dl-2, rev 87179e5c) could run.
3. One ssh foreground command ran in /root instead of dl5 (harmless; reran correctly). Both selftests passed unmodified: "selftest ok", "selftest OK".
4. **PUSH blocked:** commit 9cf1f3f59 holds exactly the 6 required files (RESULTS-gpu.md, gpu/dl5_results.json, gpu/log.txt, 2 sidecars, ledger line; no .pt weights), but this environment denies `git push` via bash — the Fix-sleep thread or Director must push commit 9cf1f3f59 from this worktree.
5. Shared-account credit fell 8.60→5.36, but sibling jobs rent concurrently; my dollars above are dph×hours only (~$0.81), well under the $1.50 kill line (never crossed).
