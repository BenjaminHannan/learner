Starting lis-318 rental run — fetching the latest handoff and kit.
Spec is clear — now checking local prerequisites and prior rental patterns.
Credit is tight but rentals auto-refill — building the code tree first.
Tree seals all check out — packaging and securing a GPU.
Cheapest qualifying 5090 found at ~$0.47/hr — renting it now.
Instance is running — setting up SSH and uploading the tree.
Reader upload broke mid-transfer — resuming with rsync --partial.
Instance stopped unexpectedly — attempting restart.
Account credit is depleted (balance -$0.01) — waiting for the auto-refill the kit mentions, then retrying.
No refill after nearly an hour. Wrapping up with a ledger entry and full report.
Verdict: CREDIT-STOP — lis-318 never trained, no marks measured. The vast.ai account ran out of credit mid-task and the auto-refill never fired in ~55 minutes of polling, so no GPU was available for DATA/TRAIN/DEV/PANEL. Nothing was invented or half-run: the sealed panel was never touched (0 runs per arm — safe to requeue).

Marks table (all NOT RUN — integer counts: 0 of 6 measured):

| Mark | Bar | Result |
|---|---|---|
| Q1 reads chat (B R0) | ≥217/255 AND ≥ A+38 | NOT RUN |
| Q2 saves more (B saved_right) | ≥ A+40 | NOT RUN |
| Q3 safe (B wrong_turns) | ≤2/240 | NOT RUN |
| Q4 no invention | ≤1 | NOT RUN |
| G1 no forgetting (B ≥ A−23 on lis-301 dev) | B ≥ A−23 | NOT RUN |
| G2 speed (B median ≤ A+200ms) | ≤ A+200 | NOT RUN |

Every move, in order (UTC 2026-09-25):
1. `git fetch -q origin main builder-outbox` OK. Read PASSMARKS (lis-318), rent-kit 330, lis-302 first 13 lines, lis-301-train, rent-lis-318 task — all via `git show origin/main:<path>`.
2. Local READER check: `~/premonition-models/lis301-merged/model.safetensors` sha256 = b4fd93a2…d21b890 — MATCH.
3. Built code tree (builder-outbox + main on top, 1.9 GB) and verified all seals from where paths resolve: lis300 14/14 OK, lis301 13/13 OK, lis318-data 14/14 OK, readpanel318 4/4 OK.
4. `vastai show instances`: no rent-lis-318 live → no DUPLICATE. Packed tree.tgz (159 MB).
5. Rental 1: offer 44173830 (5090, $0.469) → create returned success False → destroyed it (id 52522859), $0.
6. Rental 2: offer 44188475 (16 CPU, 80 GB disk, net 571/556 Mbps, rel n/a on show, dph $0.5037) → contract 52522884, running in ~4 min (inside the 6-min rule). Image pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime, torch 2.8.0+cu129 CUDA True. Uploaded tree.tgz OK, extracted OK.
7. READER upload via rsync --partial broke mid-transfer (2 GB file, sender errors); retry hit "Connection refused" — instance had died (cur_state stopped). Restart refused ("resources unavailable"). Destroyed 52522884. Alive ~03:13–03:40 UTC ≈ 0.45 h × $0.5037 ≈ $0.23.
8. Rental 3 attempt: create refused `400: account lacks credit`. Balance was $0.20 at start, −$0.04 by 04:12 UTC. Polled 5× over ~55 min (03:52, 04:02, 04:12…) — autobill ($5/threshold $5) never fired. No 4th rental was possible.
9. Stopped per money rules: within the $2.00 task budget (spent ~$0.23), but the account itself is empty — nothing left to rent with. Destroy confirmed: `vastai show instances` = 0 live. Ledger line appended via `cat >>` (only change made; additive-only kept).

Every miss / deviation:
- DATA, TRAIN, THRESHOLD/sweep, T, dev-per-src, G1, SEAL-run, PANEL A/B, e2edev read, model copy-back, RESULTS-rent.md: all NOT DONE — no GPU to run them on.
- No code was ever edited; no error traceback exists (nothing broke — the blocker is billing, not code).
- READER-FAIL does not apply (the copy is doable; the host died, then credit ran out). Correct requeue: needs account credit, then 1 fresh rental; panel still sealed (0 runs used).
- PUSH: only `artifacts/fable-predictions-ledger.md` has a new line. The other 7 PUSH paths were never created — the watcher should push just the ledger.

What this means in plain English: think of it like renting an oven to bake a cake — I gathered and checked every ingredient (all seals passed), rented the oven, but the payment card ran out of money halfway and the oven got taken away before baking started. No cake, but also nothing burned: the recipe (sealed panel) is untouched, the ingredients (tree, reader model) are still in the kitchen, and about $0.23 of the $2.00 budget was spent on the short-lived oven. The chat thread can requeue this exact task as soon as the vast.ai account has credit.
