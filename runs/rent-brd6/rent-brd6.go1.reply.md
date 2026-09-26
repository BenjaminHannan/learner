Running brd6 on rental GPU — starting credit and setup checks.
Credit gate passed (7.48). Checking for duplicate live instances.
Cheapest suitable 5090: offer 45669284 at $0.469/hr (8 cores, 532GB, 481/474 Mbps, rel 0.997). Checking create syntax.
Instance still loading. Polling again.
Instance running. Setting up SSH access.
SSH works, RTX 5090, torch CUDA-ready. Copying code tree over.
md5 confirmed on rental. Installing packages and fetching the model (detached, logged).
Selftest passed. Launching the main run detached.
Good progress: DEV rule done, base tested. Waiting on practice + training phases.
W4 seed 1 tested (cov@30=159). Training continuing. Polling again.
Almost done — only W8 seed 2 and summary remain.
All files copied back. Reading the summary for the results file.
Instance destroyed and confirmed gone. Writing RESULTS-gpu.md.
Verdict: PROVED WRONG (registered brd-6 run complete, no stop conditions hit).

CREDIT GATE: credit 7.48 (balance 0) — over $3.00, rented. DUPLICATE GATE: clear (origin/main and origin/builder-outbox had no `artifacts/claude-brd6-20260926/gpu`, no live rent-brd6 instance).

Integer counts:
- Test panel: 240 puzzles (160 3-number, 80 4-number); practice: 800 puzzles (first 400 = brd-5 set); DEV missed: 58; temp chosen 1.5 (47 vs 41 lucky).
- cov@30: base 108; W4 162/159/160; W8 161/160/147. Per-seed W8−W4: −1/+1/−13 (needed ≥ +12 every seed: 0 of 3).
- 95% CIs (pp): W8−W4 [−5.72, 2.09]; W4−base [15.79, 27.87]; W8−base [13.77, 26.61].
- PASS: not met. Proved-wrong: met (upper 2.09 < 2.5). Inconclusive: no (W8 398 examples ≥ 300; W4−base lower 15.79 > 0).
- Arm match: 597 passes each, 75 optimizer steps each, mean len 7.74 both, 3-num share 0.859 both.
- Money: 1 rental, 0 re-rents; instance 52683960 (RTX 5090, offer 45669284, rel 0.9975, $0.469/h), created 03:00:40Z, destroyed 03:35:25Z ≈ 0.58 h ≈ $0.27 of $1.00 budget. Running total $0.27.
- Time: run launched 03:08:20Z detached (PID 531), summary ~03:29Z; script minutes 20.8. Running within 4 min; log progressed throughout (no watchdog trigger).
- Model: BASE `/root/.cache/.../snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc`, commit hash 87179e5c1f455ef22e6223592d2d61351b525bfc; no other model downloaded. Selftest: "selftest ok". Test-panel md5 verified on rental: 018f09ff751477d0b9b001ec78ad2ab2.
- Copied back (verified before destroy): brd6_summary.json (31 keys), streams.json (dict), practice.jsonl (800 lines), log.txt. Instance confirmed gone (0 rent-brd6 live). Staged for push: `artifacts/claude-brd6-20260926/gpu` (4 files), `RESULTS-gpu.md`, ledger line appended. No weights saved/pushed; code never edited.

Deviations (2, both minor):
1. Log saved as `gpu/log.txt` (not `gpu/gpu_run.log`) — matches the brd-5 naming convention; same content.
2. CREDIT GATE reported credit 7.48 rather than balance 0 (balance alone is 0; usable credit funds the rental, and sibling rentals were live).
