BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 23000 MB GPU RAM checked in MB, compute capability >= 8.0, at most $1.00/h, fit check; money stop $3.00 for this whole task, cap $4; time cap 3.5 h on a 5090, scaled for slower cards)
DISK: 1
Owner job (the "Making things up about you" thread, Claude, wrote this on 2026-09-27 17:00 UTC). HELD: release only under Ben's standing vast order (14:05-14:06 UTC 09-27) when the Director's ledger has room. mu-406 steps 6 and the GPU half of 7 (the registered run: does a LoRA on Luna's teaching replies make the 1B make up fewer facts about the user than the plain 1B?) on ONE vast card, per artifacts/claude-mu406-20260926/ADDENDUM-2-vast.md. It runs handoff/kit/madeup406v/vstart.sh from the pinned commit 53860363beb8ed64834f22e5e3ffc64495dd23a9, tested against a fake vast and a fake rental. Steps:
- It refuses if mu-406 already has vast/, SEAL-run-vast.sha256.txt or VERIFY.md on main or builder-outbox, if a start already ran on this Mac, or if an instance labelled claude-madeup-mu406 is live. It rents nothing unless SEAL-data.sha256.txt is on main (the teacher gate passed and the training rows are sealed), and nothing if the credit is under $4.
- It rents the single-GPU offer with the best TFLOPS per $/h among offers with at least 23000 MB of GPU RAM (checked in MB), compute capability >= 8.0, >= 32 GB CPU RAM, a CUDA 12.8 driver, at most $1.00/h, and the fit check (100 min on a 5090, scaled by 5090 TFLOPS / its TFLOPS, x 1.3 x $/h <= 0.8 x $3.00); one offer per host, up to 3 hosts. It logs the card, its TFLOPS, $/h and TFLOPS per $/h, scales the time cap, and attaches ~/.ssh/id_ed25519.pub.
- It sends the sealed code and data from the SEAL-data commit and box/drive.sh from the pinned commit (both sha256-checked on the rental), starts drive.sh detached, waits up to 25 min for training to start, then starts the Mac guard. drive.sh: torch 2.11.0+cu128, transformers 5.17.0, peft 0.21.0 (fails closed on other versions); openbmb/MiniCPM5-1B at revision 87179e5c; SEAL 30/30, SEAL-panel 4/4, every SEAL-data line; the three selftests; bm-390's pinned GSM8K and MMLU-Redux files; the LoRA (k1h's recipe, sealed in W/SEAL-run.sha256.txt), the merge, the smoke run, the 5 arms and the 4 no-harm runs, each started only while 6 GB of GPU memory is free; the no-harm score.
- The guard stops at $3.00, the time cap, a stall or a lost host. On a money, time or stall stop it first stops the rental's driver and jobs by their exact PIDs. It copies everything back and checks it against a sha256 manifest made on the rental, the adapter's Mac copy against SEAL-run, and (after DONE) all 15 expected files. Only then does it destroy the instance by its exact id and confirm it is gone. Otherwise it stops the instance without destroying it, and the collect job prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never destroys an instance this task did not create, never edits code, never opens a test item and never pushes weights (the adapter stays in ~/premonition-models/mu406-vast).
Collect with rent406-2-collect (release about 45 min after this job prints STARTED; it waits up to 70 min, and a slower card takes longer, up to the scaled time cap).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=53860363beb8ed64834f22e5e3ffc64495dd23a9
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/madeup406v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/madeup406v/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
