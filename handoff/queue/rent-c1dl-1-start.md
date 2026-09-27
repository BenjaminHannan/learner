BASH-ONLY: yes
GPU: rent (one vast card, best TFLOPS per $/h, GPU RAM >= 15,000 MB checked on the Mac; cap $1.50 for this whole task, the guard stops at $1.00 or 1.5 h on a 5090, scaled for slower cards)
DISK: 1
Owner job (Everyday chat thread, Claude, wrote this on 2026-09-27 17:30 UTC). HELD: release only on the Director's placement under Ben's standing vast order (14:05-14:06 UTC 09-27), after the Thread manager's check of the kit. c1-dl (does 0.2d's talker input cost LFM2.5-1.2B anything; report only, DEV chats, no TEST-ONLY panel) on ONE vast card, per artifacts/claude-c1dl-20260927/PLAN.md (sealed in SEAL.sha256.txt). One arm, DL: c1-dev's arm D command with the pinned LFM2.5-1.2B snapshot as the talker model (no code change, no new model), from the sealed tree (commit 62a5944c8, SEAL-2 24/24). It runs handoff/kit/c1dlv/vstart.sh from the pinned commit 19af6d2942ca75cc659d3cf5c2f3e41ce8c34fbb (a copy of c1-dev's kit; tested against a fake vast and rental). Steps:
- It refuses if c1-dl already has RESULTS-vast.md or run-vast/, or if an instance labelled claude-everydaychat-c1dl is live. It reports the credit only (it stops if under $1.50).
- It checks every offer on the Mac (GPU RAM in MB, compute capability >= 8.0, CUDA 12.8 driver) and ranks them by TFLOPS per $/h. It keeps an offer only if the estimate (20 min + 10 min on a 5090, scaled by TFLOPS) x $/h plus the download at the host's $/GB is at most 0.8 x $1.00. Up to 3 hosts. Before each create it re-checks that this job is still released on main. It logs the card, its TFLOPS, $/h and TFLOPS per $/h, and scales the time cap by 5090 TFLOPS / its TFLOPS.
- It sends the sealed tree and box/drive.sh and starts drive.sh detached (launched in braces so ssh returns). drive.sh: torch 2.11.0+cu128 and transformers 5.17.0, fail-closed; the one pinned LFM snapshot (the only download); SEAL-2 24/24; the four selftests; then arm DL, retried once.
- It starts the Mac guard at once. The guard stops at $1.00, at the time cap, on a stall or on a lost host. On a money, time or stall end it first stops the rental's own run by drive.sh's recorded PID. It copies W/, outC1/ and drive.log back and checks every file against a sha256 manifest made on the rental. Only then does it destroy the instance by its exact id and confirm it is gone. Otherwise it stops the instance without destroying it, and the collect job prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never touches an instance this task did not create, never edits sealed code and never pushes weights.
It prints STARTED when arm DL has begun (at most 35 minutes after launch), or how far the rental got. Collect with rent-c1dl-2-collect (release about 20 min after STARTED on a 4090-class card; longer on slower cards: the start's estimate line says how long).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=19af6d2942ca75cc659d3cf5c2f3e41ce8c34fbb
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/c1dlv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/c1dlv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
