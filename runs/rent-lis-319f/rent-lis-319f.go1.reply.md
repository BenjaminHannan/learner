Renting your GPU box — credit and duplicate checks first.
Credit OK. Checking duplicates.
Cheapest reliable 5090 found at $0.41/hr. Renting now.
No image string found in prior tasks — using standard PyTorch image.
Instance 52750756 up ($0.496/hr). Waiting for it to run.
Host can't pull the image — destroying and retrying on another host.
Rental 2 running. Testing SSH and streaming the tree.
Tree done (46M). Starting OLD reader upload in background.
OLD upload running in background. Starting rental setup (pip + BASE download) and seals.
My last check cd'd wrongly for two seals — redoing cleanly from tree root.
All seals OK (14+13+14+16+5+8, zero failures). Checking background jobs.
Base data done (50044/1311 as expected). Building 319f data.
Lengths OK (0 over). Checking OLD upload, then training.
Training needs `peft` (env dep, not a code edit). Checking imports and installing.
Training running (step 180/6406, ~6800 tok/s, ETA ~35 min). Waiting.
OLD still uploading (1.1/2.2 GB). Waiting for both.
OLD upload finished. Verifying its hash and awaiting train end.
OLD hash matches. Waiting for training to finish.
Training done. Reading summary.
New reader sealed. Running panel prep + both reads.
Reads running (rows: 240, 210 with history). Waiting.
Both reads done. Scoring (counts only).
Pairs captured. Running DEV reads.
DEV reads running. Waiting.
All DEV steps done. Collecting remaining counts.
All compute done. Copying back to Mac.
Artifacts verified. Writing RESULTS-rent.md while the reader downloads.
Reader arrived. Verifying hash before destroy.
Hashes match. Destroying the rental.
rent-lis-319f complete. M1-M3 pending judges — no verdict computed here.

**Gates.** Credit: 6.749200177269863 (balance 0), above the $3.00 floor. Duplicate: no RESULTS.md/RESULTS-rent.md on origin/main or builder-outbox, no 007f file, no live rent-lis-319f instance.

**What ran (UTC 2026-09-26, all times UTC).** Rental 1 (52750756, $0.4963/hr, host 410852) never left loading (host docker-proxy refused the image pull) past the 6-min rule → destroyed by exact id (~$0.05). Rental 2 (52751954, RTX 5090, $0.5037/hr, host 406325 KR, pytorch 2.8.0-cuda12.8 image, torch 2.8.0+cu128 CUDA True) running 90 s after create, destroyed 15:04:43 after verified copy-back; confirmed gone via show instances. Total ≈ $0.95 of $2.00 (never near $1.80 stop). Tree streamed (46 MB), OLD reader rsync'd Mac→rental in background 13:22–14:06 with sha e688e1b2… verified on the rental (BensPC fallback unused). All 6 seals 0 failures (14+13+14+16+5+8 OK). Base data 50044/1311 as expected; BUILD train 51244/dev 1461, parsed-JSON-equal to dryrun (BUILD_MATCH); LENGTHS 0 over (exit 0). Train: 6406/6406 steps, 33.96 min, 6753.9 tok/s, batch 16, no OOM, seed 300. New reader sealed 970ef0ac… before any read. Panel (rows 240, 210 with history) read once per reader on CUDA (OLD→14:15, NEW→14:19). DEV chain exit 0.

**Counts.** former_old: as-current 6 (64 items, 49 rows); former_new: 0. Panel valid (49≥30 rows, 6≥2 old saves). pairs OLD: saved 125, exact 72, needs_judge 46, nomatch 7, pairs 47; pairs NEW: saved 119, exact 76, needs_judge 42, nomatch 1, pairs 43 (gold 355, rows 240). Dev report: NEW dev_score turns 1461, pred_writes 659, wrong_turns 2, ms_median 748.2; dev_former NEW 3 vs OLD 27 over 117 scored rows (saved_right 17 vs 1). BASE commit 87179e5c1f455ef22e6223592d2d61351b525bfc. Reader copied to ~/premonition-models/lis319f-merged/, Mac sha matched SEAL-run before destroy. Weights never pushed; no panel text quoted or opened (counts only).

**Deviations (code untouched):** (1) one re-rent after host-side start failure; (2) streamed 4 tiny design text files to the rental so the five SEALs could pass — the TREE list omits files the SEALs hash; (3) streamed lis319 dev_pred.jsonl from builder-outbox — step 8 needs it, TREE list omits it; (4) pip-installed peft 0.21.0 (train script imports it, kit line omits it); (5) re-ran pairs scorer CPU-only to capture full stdout, byte-identical outputs. Ledger typo of mine: "disk 60...80" should read disk 80 (append-only, left as is). Mac peak use ≈ 2 GB (new reader only).

**PUSH (watcher, in worktree):** artifacts/claude-lis319f-20260926/RESULTS-rent.md, BUILD.json, LENGTHS.json, train_summary.json, SEAL-run.sha256.txt, reads_panel_old.jsonl, reads_panel_new.jsonl, former_old.json, former_new.json, pairs_panel_old.jsonl, pairs_panel_new.jsonl, dev_pred_new.jsonl, dev_pred_old_tpl.jsonl, dev_former_new.json, dev_former_old.json, dev_score_new.txt, artifacts/fable-predictions-ledger.md.
