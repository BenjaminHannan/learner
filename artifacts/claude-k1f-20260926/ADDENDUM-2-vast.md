# k1f ADDENDUM 2: run on one vast card instead of BensPC (Creative answers in chat thread, written 2026-09-27 14:58 UTC)

Written before any k1f command has run anywhere. Registered FAILs stay FAILs; nothing in the marks changes.

Label for every k1f and k1h result: K, F and H run on 0.2c's build, whose talker carries the puzzle-trained 0.2c sleep
adapter. H minus F is still one change, because both share that talker.

## Why
- k1f-benspc2 (ADDENDUM-1) has waited in BensPC's queue since 2026-09-26 19:47 UTC and has not started. BensPC was not
  answering ssh when this was written (the watcher's status on 09-27: "BensPC unreachable (ssh rc=255), holding
  k1f-benspc2").
- Ben, 14:05 to 14:06 UTC 09-27, standing until he says stop: every GPU job waiting on BensPC goes to vast; use the
  card with the most TFLOPS per $/h that has enough memory; at most $4 per job, from the $30 pool. The Director asked
  for this kit at 14:15 UTC.

## What changes (the machine only)
- Machine: one vast card, the offer with the best TFLOPS per $/h among those with at least 24000 MB of GPU memory
  (checked in MB on the Mac), compute capability 8.0 or more, a CUDA 12.8 driver, at most $0.60/h, and a fit check:
  0.75 h on a 5090, scaled by 5090 TFLOPS / the card's TFLOPS (never below 1), times $/h, must be at most 0.8 x $1.50.
- Money stop $1.50 for all rentals of this task together (the per-job cap is $4). Time cap 2 h on a 5090, scaled by
  TFLOPS the same way. Destroy only after a copy-back checked against a sha256 manifest made on the rental; otherwise
  stop the instance without destroying it. The kit is handoff/kit/creativechatk1fv (built from the reviewed 358 kits).
- Software: the image's torch 2.8.0+cu128 (eval only, as the 330-rent-kit TORCH VERSION rule allows; k1c ran this way
  on a 5090 with transformers 5.17.0), kit section C's pip line, versions recorded.
- Models: downloaded on the rental at the same pins (MiniCPM5-1B 87179e5c..., Qwen3.5-2B 15852e8c..., LFM2.5-1.2B
  0f604ada..., and all-MiniLM-L6-v2), as PASSMARKS-k1f.md itself says. ADDENDUM-1's line about BensPC's cache no
  longer applies.
- Linux, so no Windows line-ending wrapper; the "\r\n" count is still taken (expected 0).
- Arms: all five at once on a card with 30000 MiB or more; otherwise K, F, T first and Q, L after they exit (rent-k1f's
  4090 rule; per-turn seeds make the order irrelevant). One detached driver (box/drive.sh) runs the steps in order.
- Results: artifacts/claude-k1f-20260926/run/ as registered step 6 lays them out, the rental's records in run/vast/,
  and RESULTS-vast.md in place of RESULTS-benspc.md.

## What still needs BensPC, and why
0.2c's sleep adapter (adapter02c.pt, sha256 a33211dc...36f5) exists only on BensPC; arms K and F (and later k1h's H)
load it. The kit copies that one 16.5 MB file from BensPC over ssh before it rents anything (a file read; BensPC's GPU
is not used) and checks its sha256. If BensPC cannot be reached, the start stops with NO-ADAPTER and spends $0.

## What does not change
The code, the seals (SEAL.sha256.txt), the panel and its seal, the arms and their env settings (K1F_WRITER_MODEL for F
only, K1F_DRAFTS for K and F, SLEEP02C_ADAPTER for K and F), the DEV gate, the V1 lines, the three scorers, the marks
K1f.1-3, the K1 line, the rival readings, the draft report, the judging and the recount.
