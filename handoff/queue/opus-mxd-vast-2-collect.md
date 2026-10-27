STATUS: HELD. Real dependency: the guard's END of opus-mxd-vast-1-start (its rental must have started and the guard ended). Release about 30 min after opus-mxd-vast-1-start prints STARTED and repeat until COLLECTED; the Opus manager session removes this line at its turn.
BASH-ONLY: yes
GPU: rent (collect only; touches no rental; cap $2.50 for the whole task is the start job's)
DISK: 1
Owner: Opus manager session, for Ben (this task's own cap $2.50 of Ben's $5 for this session). Collect for opus-mxd-vast-1-start (phase 1 dev only, holdout NOT run; a duplicate in science of BensPC job mxd-1). It runs handoff/kit/opmxd/vcollect.sh from the pinned commit (PIN=d56fe70f309067a0da2ee18bb7a061f887828cd5, same as the start job): restarts the Mac guard if it died, waits up to 70 min for it to end, then puts runs/, eq-runs/, SMOKE-gpu.json, TIMING-gpu.json, logs/ and run-vast/ (the rental's records, COLLECT.txt with the sha256 of every source.json, qualified.json and adapt.json) into artifacts/opus-manager-20260929/mxd-vast/ and NEVER into the sealed artifacts/claude-moe-deep-20260929. NOT-YET if the guard has not ended; FLAG-DIRECTOR if the instance was stopped, not destroyed. Never reads or prints the vast key. Tested against fakes only.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=d56fe70f309067a0da2ee18bb7a061f887828cd5
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/opmxd | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/opmxd/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/opus-manager-20260929/mxd-vast
