# mu-406 ADDENDUM 2: the GPU steps run on one vast card

"Making things up about you" thread. Written 2026-09-27 17:04 UTC (date -u), after the teacher gate passed (5d592c0f4) and
before any training row is sealed or any GPU step has run. Marks, data rules, prompts and the five scripts are unchanged
(SEAL.sha256.txt).

## Why
- Ben's standing vast order (14:05-14:06 UTC 09-27, the Director's ledger ae27bb2b6): jobs waiting on BensPC go to vast,
  on the card with the best TFLOPS per $/h, with GPU RAM checked, a time cap scaled to the card, and at most $4 per job.
- The Director asked for this kit at 14:15 UTC 09-27.

## What changes (where the steps run, not what they do)
- Step 6's rows are built in the cloud copy of the repo with `claude_mu406_train.py rows`. This step is code only and
  needs no model. The rows are sealed in SEAL-data.sha256.txt with teach/teach.jsonl before any rental. The rental
  checks every SEAL-data line and will not train on anything else.
- Step 6 and the GPU half of step 7 run in ONE vast rental, using handoff/kit/madeup406v. The rental does the
  training, the merge, the smoke run, the 5 arms, and the 4 no-harm runs (GSM8K and MMLU-Redux for P and T), all on the
  same card.
  - PASSMARKS' "a second job runs the no-harm check" becomes this same rental.
  - M5's "both run in the same job" still holds.
- The software matches BensPC: torch 2.11.0+cu128, transformers 5.17.0 and peft 0.21.0. The rental stops on any other
  version.
- The model is openbmb/MiniCPM5-1B at revision 87179e5c, the approved base.
- The card may differ from BensPC's 5070 Ti, and bf16 numbers can differ slightly between cards. P and T run on the
  same card, so the comparison between them is not affected.
- Card rules, each checked on every offer:
  - at least 23000 MB of GPU RAM, checked in MB;
  - compute capability 8.0 or higher;
  - at least 32 GB of CPU RAM and a CUDA 12.8 driver;
  - at most $1.00/h;
  - the fit check: 100 minutes on a 5090, scaled by the 5090's TFLOPS over the card's (never below 1x), times 1.3,
    times $/h, must be at most 0.8 x $3.00;
  - the best TFLOPS per $/h wins, with one offer per host and up to 3 hosts.
- The rental stops on the first of these:
  - $3.00 spent by this task (inside Ben's $4 cap per job);
  - the time cap: 3.5 h on a 5090, scaled up for slower cards;
  - a stall: no log grows for 30 minutes while the GPU is idle;
  - a lost host.
  On a money, time or stall stop, the guard first stops the driver and its jobs on the rental by their exact PIDs.
- The instance is destroyed only after three checks pass:
  - the copy back matches a sha256 manifest made on the rental;
  - the adapter's Mac copy matches W/SEAL-run.sha256.txt;
  - after DONE, all 15 expected files are there.
  Otherwise the instance is stopped, not destroyed, and the collect job flags the Director.
- Outputs land in vast/ (the rental's W folder, without the adapter weights) and SEAL-run-vast.sha256.txt. The adapter
  stays on the Mac in ~/premonition-models/mu406-vast. Step 7 reads the arms from vast/run/ and the no-harm runs from
  vast/gen/.
- Every start job that rents a card counts as one launch of step 6. PASSMARKS' limit of 3 launches stands.

## Tested against a fake vast and rental
The kit at 53860363b was tested with a fake vastai CLI, a fake ssh that runs each command locally, and a fake rental
where pip, nvidia-smi and the model work (download, training, merge, arms, benchmarks) are stubs. The seals, the three
selftests and the kit's own scripts ran for real. The data was a test-only seal of 700 rows from the 140 training chats
written so far (a throwaway copy, never pushed). All of these passed:
- Card choice from 8 fake offers: 3 kept, ranked by TFLOPS per $/h. Five were dropped, one for each rule: over
  $1.00/h, under 23000 MB, compute capability under 8.0, the fit check, and a second offer on the same host.
- The normal path: SEAL 30/30, SEAL-panel 4/4, SEAL-data 2/2, selftests ok, 9 of 9 jobs exited 0, then DONE. 43 of 43
  files matched the manifest, the adapter's Mac copy matched SEAL-run, and all 15 expected files were there. The
  instance was destroyed (confirmed gone) and collected. A second start was refused (DUPLICATE).
- A failed start (model download): logs copied back, destroyed, START-FAIL.
- A failed training run: FAILED, copied back, destroyed.
- The first offer's create fails, so it rents the next one. Then ssh is lost: HOST-FAIL, stopped, not destroyed,
  FLAG-DIRECTOR.
- The copy back fails twice after DONE: stopped, not destroyed, FLAG-DIRECTOR.
- A stall, a time stop (cap set to 20 s) and a money stop (spend set to $3.25): each stopped the driver and any job still
  running by PID, copied back with every file matching, then destroyed.
- drive.sh on the rental not matching the pinned commit (a test set-up slip): each of the 3 rentals destroyed, then
  HOST-FAIL with nothing launched.
Not tested: the real vast CLI, a real card, and the real model steps. Those run for the first time on the rental.

## Review
- SEAL-data.sha256.txt will also list this addendum, so it is sealed before any rental.
- Sent to the Thread manager, then the Director, before release. The kit jobs stay in handoff/held/ until the Director
  releases them under Ben's standing order.
