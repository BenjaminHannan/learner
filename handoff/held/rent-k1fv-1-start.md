BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 24000 MB checked in MB, at most $0.60/h, fit check; money stop $1.50 for this whole task, cap $4; time cap 2 h on a 5090, scaled for slower cards)
DISK: 1
Owner job (the "Creative answers in chat" thread, Claude, wrote this on 2026-09-27 14:58 UTC). HELD: release only on Ben's release words (his 14:05 UTC standing order covers vast; the Director's check decides whether it needs his words naming the job) and when the Director's ledger has room. When releasing, move handoff/queue/k1f-benspc2.md to handoff/held/superseded/ (this start refuses while it is still in queue/ or running). k1f, the registered run (does the creative writer answer more usefully when LFM2.5-1.2B writes its drafts instead of MiniCPM5-1B, and how does that compare with plain same-size models?), on ONE vast card per artifacts/claude-k1f-20260926/ADDENDUM-2-vast.md. Eval only, no training, no weights. It runs handoff/kit/creativechatk1fv/vstart.sh from the pinned commit 4d090c75fc9fbd0b11370443c125e10252a1c824, tested against a fake vast and a fake rental. Steps:
- It refuses if k1f already has run/ or RESULTS-benspc.md on builder-outbox (or run/vast, RESULTS-vast.md on main), while handoff/queue/k1f-benspc2.md is on main or running on the watcher, or if an instance labelled claude-creativechat-k1fv is live.
- Before any rental ($0 if it stops here): it finds self122_head.pt on the Mac (sha256 5ca02173...) and copies 0.2c's adapter02c.pt (16.5 MB) from BensPC with scp (a file read; BensPC's GPU is not used), sha256 a33211dc...36f5. If BensPC cannot be reached it prints NO-ADAPTER and rents nothing. It reports the credit only (it stops if under $4).
- It rents the single-GPU offer with the best TFLOPS per $/h among offers with at least 24000 MB of GPU RAM (checked in MB), compute capability >= 8.0, a CUDA 12.8 driver, at most $0.60/h, and the fit check (0.75 h on a 5090, scaled by 5090 TFLOPS / its TFLOPS, times $/h <= 0.8 x $1.50); up to 3 hosts. Before each rental it re-checks that this file is still released in handoff/queue/ on main. It logs the card, its TFLOPS and its $/h, scales the time cap by 5090 TFLOPS / its TFLOPS, and attaches ~/.ssh/id_ed25519.pub.
- It sends the pinned tree, self122_head.pt and the adapter (sha256 checked on the rental), starts box/drive.sh detached, starts the Mac guard, and removes the Mac copy of the adapter. drive.sh: the image's torch (recorded), kit section C's pip line, the four models at their pins, seals (k1f 21, addendum1 2, addendum2 3, panel 1, e2e02c present files), the five tests, the DEV gate, the five arms each launched once (all at once on >= 30000 MiB, else K F T then Q L), V1 on each log, the three scorers, CRLF counts.
- The guard stops at $1.50 or the time cap, on a stall or on a lost host. On a money, time or stall stop it first stops the rental's driver and arms by their exact PIDs. It copies everything back and checks it against a sha256 manifest made on the rental (and, after DONE, that all 26 expected files are there). Only then does it destroy the instance by its exact id and confirm it is gone. Otherwise it stops the instance without destroying it, and the collect job prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never destroys an instance this task did not create, never edits code, never opens a test item and never pushes weights.
Collect with rent-k1fv-2-collect (release about 1 h 15 min after this job prints STARTED; a slower card takes longer, up to the scaled time cap).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=4d090c75fc9fbd0b11370443c125e10252a1c824
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/creativechatk1fv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/creativechatk1fv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
