# rd-378g addendum N (2026-09-27 14:22:44 UTC): the run may be on one vast card instead of BensPC

Written after ADDENDUM-M (430e61a03) and before any step of the rd-378g run has started anywhere. The experiment does not
change. Only the machine and how the files reach it change. This file adds to PASSMARKS.md and addenda A-M and is sealed in
SEAL-ADD-N.sha256.txt.

## Why
- Ben's standing vast order:
  - 14:05:17 UTC: "just use vast until I tell you not to";
  - 14:05:27 UTC: "use cheap gpus, whatever gives most tflops/$/hr";
  - 14:06:43 UTC: "yes", to the Thread manager's reading. That reading: jobs waiting on BensPC go to vast, at most $4
    per job, from the $30 pool, the card with the best TFLOPS per $/h, and the time cap scaled to the card.
- The Director asked for a held vast kit for rd-378g at 14:15 UTC.
- The BensPC passes (185-rd378g-benspc-bo-p1..p4) cannot launch now. BensPC C: had 3.7 GB free at 12:11 UTC, and the
  kit needs 6 GB. BensPC ssh has also failed since 12:30 UTC (the Director's ledger).

## Which machine runs it
- Whichever route the Director releases first runs, once:
  - the vast kit, handoff/kit/rd378gv, through handoff/held/rent378g-1-start.md and two collect jobs;
  - or the BensPC passes.
- The vast start refuses to run if benspc/RESULTS-benspc.md, vast/ or RESULTS.md already exists.
- Once the vast start has run, the 185 passes are superseded and never released. The Director moves them to
  handoff/held/superseded/ when releasing the vast start.

## The same run
Everything the experiment measures is unchanged:
- the rows (SEAL-B), the trainer and every setting, including the one --batch 8 retry on out-of-memory;
- the dev format check, the LoCoMo 5-9 write and store v4 score, the when-off score, and the two G5 writes;
- G1-G5 with their bars, the 57% fallback, the wording, and R = 585 of 772.

The rental runs the BensPC chain's steps in the same order, with the same stop rules (box/drive.sh mirrors
handoff/kit/rd378gpc/remote/chain.cmd).

## What differs on the rental (procedure only)
- **Base model:** openbmb/MiniCPM5-1B at revision 87179e5c1f455ef22e6223592d2d61351b525bfc, downloaded on the rental.
  - This is the approved base, the same revision as BensPC's lis300 copy. It is not a new model.
  - rd-378u downloaded it the same way on a rental and rebuilt R's merged sha256 bit for bit.
  - Its sha256 is reported beside BensPC's (7ab8fd86...660d).
- **MiniLM:** snapshot 1110a243, downloaded the same way; the path check is the same as BensPC's.
- **Libraries:** torch 2.11.0+cu128, transformers 5.17.0 and peft 0.21.0, rd-378u's rental versions. Fail-closed: any
  other version stops the run before training.
- **LoCoMo:** locomo10.json is fetched from bm390's pinned source (snap-research/locomo at 3eb6f2c). Its sha256 must be
  79fa87e9...8ff4, or the run stops.
- **R:** it goes from the Mac's copy (~/premonition-models/rd378-notes-merged), sha256-checked on the Mac and again on the
  rental (rsend.sh). If R has not arrived intact within 60 minutes after G's G5 write, R's G5 write is skipped (R-SKIPPED).
  G5 then uses ADDENDUM-K's fallback: R's share is taken as 52%, so the bar is G at most 57%.
- **Weights:** G's merged model stays on the rental and goes when the rental is destroyed. Its sha256 is sealed in
  SEAL-run. It can be rebuilt from the base and G's adapter. G's adapter comes back to the Mac
  (~/premonition-models/rd378g-vast-adapter), sha256-checked. Weights are never pushed.
- **Where results land:** artifacts/claude-rd378g-20260926/vast/, with the file names benspc/ would have had.
  - LoCoMo-derived files (dialogs59, G's notes on it, per_question) go to ~/rd378g-private/vast on the Mac only.
  - The rental keeps LoCoMo files out of W/, the only folder whose files may be pushed.
- **Disk:** the disk floor of ADDENDUM-L is a BensPC rule and does not apply to a rental. The rental has 40 GB.

## The card (Director, 14:15 UTC)
- **Filters.** One GPU, with every filter checked again client-side on each raw offer:
  - GPU RAM at least 16,000 MB, checked in MB, and again on the rental with nvidia-smi. The rd-378 writer trained with this
    trainer, batch 16 and max-len 512 on BensPC's 16 GB card without running out of memory.
  - compute capability 8.0 or higher (bf16);
  - a CUDA 12.8 driver;
  - reliability 0.98, 8 cores, 40 GB disk, a direct port, and at most $1.00/h (a sanity bound).
- **Ranking:** offers are ranked by TFLOPS per $/h, and at most 3 hosts are tried.
- **Fit check.** The estimate must fit: estimate x $/h <= 0.8 x the money stop.
  - The estimate is 60 minutes on an RTX 5090 (a guess), times max(1, 5090 TFLOPS / the card's TFLOPS), times 1 wave.
  - It is one wave because every step runs after the one before.
- **Time cap:** 3 x the scaled estimate, plus 60 minutes for R, plus 20 minutes of setup, counted from the first rental.
- **Money stop:** $2.50 for all rentals of this task together, inside Ben's $4 per job.
- **Card log:** the start logs the card, its TFLOPS, its GPU RAM in MB, its $/h, its TFLOPS per $/h and the estimated
  dollars. The collect copies that line into vast/COLLECT.txt.

## End of the rental
- The Mac guard checks every 5 minutes. It ends on the first of these:
  - DONE;
  - a FAILED setup;
  - the money stop;
  - the time cap;
  - a stall: no log or output growth for 30 minutes with the GPU idle;
  - a lost host.
- It copies back W and P, checks every file against a sha256 manifest made on the rental, checks that every step that
  ended rc=0 brought its files, and checks that the Mac copy of G's adapter matches SEAL-run.
- Only then does it destroy the instance by its exact id and confirm it is gone. Otherwise it stops the instance, and
  the collect prints FLAG-DIRECTOR.
- It never touches an instance this task did not create. The label is claude-notes-rd378g.
- For the vast route, the guard is the stall watch; ADDENDUM-M's peeks are for BensPC. A hung step that keeps the GPU
  busy is ended by the time cap.
