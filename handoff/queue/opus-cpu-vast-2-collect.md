STATUS: HELD. Real dependency: the guard's END of opus-cpu-vast-1-start (its rental must have started and the guard ended, up to about 7 h after STARTED). Release about 30 min after opus-cpu-vast-1-start prints STARTED and repeat until COLLECTED; the Opus manager session removes this line at its turn.
BASH-ONLY: yes
GPU: rent (collect only; touches no rental; cap $2.50 for the whole task is the start job's)
DISK: 1
Owner: Opus manager session, for Ben (this task's own cap $2.50 of Ben's $5 for this session). Collect for opus-cpu-vast-1-start (sealed CPU tests run unchanged on a rented CPU box; the Mac copies of those jobs stay queued and the Director decides which to withdraw; neither run is chosen by its score). It runs handoff/kit/opcpu/vcollect.sh from the pinned commit (PIN=18deff81bf423c5285cf4ff4c890817d70457a6e, same as the start job): restarts the Mac guard if it died, waits up to 70 min for it to end, then puts each test's small files (json and logs, never a .pt) into artifacts/opus-manager-20260929/cpu-vast/<test>/ (ks-1-lead0, s2think, trn-decode, pond-a-dev, pond-b-dev, pond-c-dev, pond-z-dev, pond-doubt, s1-loop, s1-plain) and the rental's records (drive-state, torch check, input hashes, manifest, each job's printed report, the Mac log, DEVIATIONS.md, COLLECT.txt) into cpu-vast/_rental/, and NEVER into any sealed folder. NOT-YET if the guard has not ended; FLAG-DIRECTOR if the instance was stopped, not destroyed. Never reads or prints the vast key. Tested against fakes only.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=18deff81bf423c5285cf4ff4c890817d70457a6e
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/opcpu | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/opcpu/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/opus-manager-20260929/cpu-vast
