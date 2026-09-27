BASH-ONLY: yes
GPU: rent (one vast card, best TFLOPS per $/h, GPU RAM >= 15,000 MB checked on the Mac; cap $2 for this whole task, the guard stops at $1.50 or 3 h on a 5090, scaled for slower cards)
DISK: 1
Owner job (Everyday chat thread, Claude, wrote this on 2026-09-27 14:44 UTC). HELD: release only on the Director's placement under Ben's standing vast order (14:05-14:06 UTC), after the Thread manager's check of the kit. c1-dev (can a plain 1B talker meet 0.2d's C1 no-harm bar on the practice chats; report only, DEV chats, no TEST-ONLY panel) on ONE vast card, per artifacts/claude-c1dev-20260927/ADDENDUM-2-vast.md. The four arms D, T, Q, L run there with the BensPC chain's commands from the sealed tree (commit 62a5944c8, SEAL-2 24/24). It runs handoff/kit/c1devv/vstart.sh from the pinned commit d0072550e7756cbfb99a184f3c891faf78049463 (sealed in SEAL-kit-vast.sha256.txt; tested against a fake vast and rental). Steps:
- It refuses if c1-dev has RESULTS-vast.md, run-vast/ or RESULTS-benspc.md, if the BensPC run note shows a launched chain, while any *c1dev-benspc* pass is in handoff/queue/ on main or running on the watcher, or if an instance labelled claude-everydaychat-c1dev is live. It reports the credit only (it stops if under $2).
- It checks every offer on the Mac (GPU RAM in MB, compute capability >= 8.0, CUDA 12.8 driver) and ranks them by TFLOPS per $/h. It keeps an offer only if the estimate (25 min + 60 min on a 5090, scaled by TFLOPS) x $/h plus the download at the host's $/GB is at most 0.8 x $1.50. Up to 3 hosts. Before each create it re-checks that this job is still released on main. It logs the card, its TFLOPS, $/h and TFLOPS per $/h, and scales the time cap by 5090 TFLOPS / its TFLOPS.
- It sends the sealed tree and box/drive.sh and starts drive.sh detached (launched in braces so ssh returns). drive.sh: torch 2.11.0+cu128 and transformers 5.17.0, fail-closed; bm-390's three pinned model snapshots (the only downloads; no new model); SEAL-2 24/24; the four selftests; then arms D, T, Q, L one after another, each retried once.
- It starts the Mac guard at once. The guard stops at $1.50, at the time cap, on a stall or on a lost host. On a money, time or stall end it first stops the rental's own run by drive.sh's recorded PID. It copies W/, outC1/ and drive.log back and checks every file against a sha256 manifest made on the rental. Only then does it destroy the instance by its exact id and confirm it is gone. Otherwise it stops the instance without destroying it, and the collect job prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never touches an instance this task did not create, never edits sealed code and never pushes weights.
It prints STARTED when arm D has begun (at most 35 minutes after launch), or how far the rental got. Collect with rent-c1dev-2-collect (release about 1 h after STARTED on a 5090; longer on slower cards: the reply's estimate says how long).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=d0072550e7756cbfb99a184f3c891faf78049463
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/c1devv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/c1devv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
