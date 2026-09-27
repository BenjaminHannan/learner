BASH-ONLY: yes
GPU: rent (one vast card: best TFLOPS per $/h among offers with >= 16,000 MB GPU RAM checked in MB, compute capability >= 8.0, CUDA 12.8, at most $1.00/h and a fit check; money stop $2.50 for this whole task, inside Ben's $4 per job; time cap scaled by the card's TFLOPS and 1 wave)
DISK: 1
Owner job (Trustworthy notes thread, Claude, wrote this on 2026-09-27 14:31:04 UTC). HELD: the Director releases it under Ben's standing vast order (14:05:17, 14:05:27 and 14:06:43 UTC: jobs waiting on BensPC go to vast, at most $4 per job, the best TFLOPS per $/h). When releasing, move handoff/held/185-rd378g-benspc-bo-p1..p4.md to handoff/held/superseded/ so BensPC does not also run rd-378g. rd-378g (a note writer trained from the plain 1B on the ungraded GLM and Luna rows, then scored on LoCoMo 5-9 and G5) on ONE vast card, per artifacts/claude-rd378g-20260926/ADDENDUM-N.md (sealed in SEAL-ADD-N). It runs handoff/kit/rd378gv/vstart.sh from the pinned commit 6c373a564e41a57039cf86a5dbf5ede24d65a7d6, tested against a fake vast and rental. Steps:
- It refuses if rd-378g has RESULTS.md, benspc/RESULTS-benspc.md or vast/, or if an instance labelled claude-notes-rd378g is live. It reports the credit only, and stops if the credit is under $2.50.
- It rents the single-GPU offer with the best TFLOPS per $/h. Every rule is checked again on each raw offer: GPU RAM in MB, compute capability, CUDA, price, and the fit check (60 minutes on a 5090, scaled by 5090 TFLOPS over the card's, x $/h, at most 0.8 x $2.50). It tries at most 3 hosts. It logs the card, its TFLOPS, GPU RAM, $/h, TFLOPS per $/h and estimated dollars, and attaches ~/.ssh/id_ed25519.pub.
- It sends the pinned code and starts box/drive.sh detached. drive.sh:
  - checks GPU RAM on the rental;
  - installs torch 2.11.0+cu128, transformers 5.17.0 and peft 0.21.0, fail-closed;
  - downloads the approved base (openbmb/MiniCPM5-1B at 87179e5c) and MiniLM (1110a243);
  - fetches locomo10.json and checks its sha256;
  - checks SEAL-B, SEAL-ADD-K, A and B, SEAL-ADD-N and SEAL (13 OK, only claude_lis300_train.py FAILED), and the 4 selftests;
  - runs the chain: dialogs, train (one --batch 8 retry on out-of-memory), devcheck, write59, score, whenoff, g5G and g5R. G's adapter is sealed right after training.
- It starts rsend.sh, which sends R (~/premonition-models/rd378-notes-merged, sha256 checked on the Mac and on the rental) for g5R. If R does not arrive, g5R is skipped and ADDENDUM-K's 57% fallback applies.
- It leaves the Mac guard running. The guard stops on DONE, a failed setup, $2.50, the time cap, a 30-minute stall with the GPU idle, or a lost host. It copies W and P back and checks them against a sha256 manifest made on the rental, checks every finished step's files, and checks G's adapter against SEAL-run. Only then does it destroy the instance by its exact id and confirm it is gone. Otherwise it stops the instance without destroying it, and the collect prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never destroys an instance this task did not create, never edits sealed code, never pushes LoCoMo text (LoCoMo files stay on the rental in DATA/ and P/, and go to ~/rd378g-private/vast on the Mac) and never pushes weights.
Collect with rent378g-2-collect (release about 1 h 30 min after this job prints STARTED; the chain is estimated at about 1 hour on a 5090, a guess).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=6c373a564e41a57039cf86a5dbf5ede24d65a7d6
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/rd378gv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/rd378gv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
