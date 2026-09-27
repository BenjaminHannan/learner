BASH-ONLY: yes
GPU: rent (one vast RTX 5090; cap $4 for this whole task, guard stops at $3.60 or 4 h 30 min)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 13:05:40 UTC). HELD: release only after Ben says yes to this rental (relayed by the Thread manager) and the Director's ledger has room; when releasing, move exactly these six files to handoff/held/superseded/ so only one machine runs 358u: 165-claude-sleep-358u-bo-p1.md, 166-claude-sleep-358u-bo-p2.md, 167-claude-sleep-358u-bo-p3.md, 168-claude-sleep-358u-bo-p4.md, 169-claude-sleep-358u-bo-p5.md, 170-claude-sleep-358u-bo-p6.md (not 170-rv390-358i2-pc.md, which is Thought-memory's). rsn-358u on ONE vast rental, per artifacts/claude-rsn358u-20260927/ADDENDUM-1-vast.md and ADDENDUM-2-vast-review.md. It runs handoff/kit/sleep358uv/vstart.sh from the pinned commit d6b7b4672ae117e87494920223b6222cd17b4175 (tested against a fake vast and rental): refuses if 358u already has runs or a live instance labelled claude-sleep-358u; reports the credit only (stops if under $4); rents the cheapest RTX 5090 with reliability >= 0.98 and >= 16 CPU cores (up to 3 hosts); sends the pinned code; starts box/drive.sh detached on the rental (torch 2.11.0+cu128 pin and check, SEAL 20/20, selftest and check-mask, all 8 sealed trains at once, sha256 of each final.pt into SEAL-run before any eval, then V1 poison and the test eval once each); waits until all 8 have launched; then leaves a guard on the Mac (~/premonition-watch/rsn358u-vast/vguard.sh under caffeinate) that stops at $3.60 or 4 h 30 min, on a stall (30 min, GPU idle) or a lost host (20 min), and at the end copies everything back and checks every file against a sha256 manifest made on the rental, and each final.pt against SEAL-run on the Mac (~/premonition-models/rsn358u); only if that passes does it destroy the instance by its exact id and confirm it is gone, otherwise (and on a lost host) it STOPS the instance without destroying it and the collect job prints FLAG-DIRECTOR. It attaches ~/.ssh/id_ed25519.pub to the instance. The vast key is never read or printed (the vastai CLI uses its own config). It never destroys an instance this task did not create, never edits sealed code, never opens a test item and never pushes weights. Collect with rent358u-2-collect (release about 1 h 30 min after this one ends).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=d6b7b4672ae117e87494920223b6222cd17b4175
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358uv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358uv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
