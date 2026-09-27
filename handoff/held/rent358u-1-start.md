BASH-ONLY: yes
GPU: rent (one vast RTX 5090; cap $4 for this whole task, guard stops at $3.60 or 4 h 30 min)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 13:05:40 UTC). HELD: release only after Ben says yes to this rental (relayed by the Thread manager) and the Director's ledger has room; when releasing, move handoff/held/165-170 (358u on BensPC) to handoff/held/superseded/ so only one machine runs 358u. rsn-358u on ONE vast rental, per artifacts/claude-rsn358u-20260927/ADDENDUM-1-vast.md. It runs handoff/kit/sleep358uv/vstart.sh from the pinned commit 474ed5a3244d4f160363c1b95dd18b8b6cc96409 (tested against a fake vast and rental): refuses if 358u already has runs or a live instance labelled claude-sleep-358u; reports the credit only (stops if under $4); rents the cheapest RTX 5090 with reliability >= 0.98 and >= 16 CPU cores (up to 3 hosts); sends the pinned code; starts box/drive.sh detached on the rental (torch 2.11.0+cu128 pin and check, SEAL 20/20, selftest and check-mask, all 8 sealed trains at once, sha256 of each final.pt into SEAL-run before any eval, then V1 poison and the test eval once each); waits until all 8 have launched; then leaves a guard on the Mac (~/premonition-watch/rsn358u-vast/vguard.sh under caffeinate) that stops at $3.60 or 4 h 30 min, on a stall (30 min, GPU idle) or a lost host (20 min), and at the end copies everything back, puts each final.pt in ~/premonition-models/rsn358u with sha256 checks, destroys the instance by its exact id and confirms it is gone. The vast key is never read or printed (the vastai CLI uses its own config). It never destroys an instance this task did not create, never edits sealed code, never opens a test item and never pushes weights. Collect with rent358u-2-collect (release about 1 h 30 min after this one ends).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=474ed5a3244d4f160363c1b95dd18b8b6cc96409
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358uv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358uv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
