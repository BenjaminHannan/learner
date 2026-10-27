BASH-ONLY: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 24 GB, at most $0.60/h and only if its estimate x $/h <= 0.8 x $2.00; cap $2.40 for this whole task, guard stops at $2.00 or 1.5 x the card's estimate (2 h on a 5090, scaled by TFLOPS and by waves from its RAM))
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 15:10:26 UTC). HELD: release after 358u is collected (its SEAL-run.sha256.txt on main), under Ben's 14:05 UTC standing order for vast, when the Director's ledger has room. slp-358n3, the build's sleep gate H-B on the reasoner (sealed: artifacts/claude-slp358n3-20260927/PASSMARKS.md, SEAL-code 18 lines), on ONE vast card. It runs handoff/kit/sleep358nv/vstart.sh from the pinned commit e9e4ba46ae86268361f8fd60e249d9c8cc89a8af (tested against a fake vast and rental). Steps:
- It refuses if slp-358n3 has RESULTS.md, runs/, run-vast/ or SEAL-run, or if an instance labelled claude-sleep-358n3 is live. It prints WAITING and rents nothing until 358u's SEAL-run is on main and the Mac copies of ~/premonition-models/rsn358u/loop-s13..16/final.pt match it. It reports the credit only (it stops if under $4).
- It rents the best TFLOPS per $/h offer that fits the money, attaches ~/.ssh/id_ed25519.pub, sends the pinned code, uploads the 4 checkpoints and checks them 4/4 on the rental, and starts box/drive.sh detached. drive.sh: torch 2.11.0+cu128, fail-closed; SEAL-code 18/18; 358u selftest; the sealed day-size rule; RESUME on the rental's CPU; the 4 seed runs (s13 and s14 with the report-only L arm); sha256 of each slept S-final.pt into SEAL-run.
- It leaves the Mac guard running. The guard stops at $2.00 or the time cap, on a stall or on a lost host. It copies everything back and checks it against a sha256 manifest made on the rental and against SEAL-run, with each seed's result, sizes.json and resume.json present. Only then does it destroy the instance by its exact id and confirm it is gone. Otherwise it stops the instance without destroying it, and the collect job prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never destroys an instance this task did not create, never edits sealed code, never opens a test item and never pushes weights.
Collect with rent358n3-2-collect: release it X h + 30 min after this job prints STARTED, where X is the "estimate X h" in its log.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=e9e4ba46ae86268361f8fd60e249d9c8cc89a8af
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358nv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358nv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
