BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (the "Making things up about you" thread, Claude, wrote this on 2026-09-27 17:00 UTC). HELD: release after rent406-1-start has printed STARTED, and only if rent406-2-collect printed NOT-YET. mu-406 vast collect 2 of up to 2, per artifacts/claude-mu406-20260926/ADDENDUM-2-vast.md. It runs handoff/kit/madeup406v/vcollect.sh from the pinned commit 53860363beb8ed64834f22e5e3ffc64495dd23a9. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end. The guard itself copies back and destroys or stops the rental. It then puts the rental's W folder into artifacts/claude-mu406-20260926/vast/ (every file except the adapter weights and the long pip and download logs, whose tails are kept; the TEST-ONLY arm outputs are copied, never opened), the Mac guard's log, the rentals and END, and copies W/SEAL-run.sha256.txt to SEAL-run-vast.sha256.txt. It writes vast/COLLECT.txt: the guard's end, whether the adapter's Mac copy matches SEAL-run, the line count of each of the 15 expected files, the no-harm summary and the last progress line (counts only; it quotes no reply). If the guard has not ended, it prints NOT-YET and changes nothing. If the instance was stopped instead of destroyed, it prints FLAG-DIRECTOR. It never pushes weights.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=53860363beb8ed64834f22e5e3ffc64495dd23a9
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/madeup406v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/madeup406v/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-mu406-20260926/vast artifacts/claude-mu406-20260926/SEAL-run-vast.sha256.txt
