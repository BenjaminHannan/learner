STATUS: HELD. Real dependency: release about 30 min after dir-s3-vast-1-start-r2 reports STARTED (Director, 2026-09-29); collect must not run before the rental exists.
BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 24 GB, at most $0.65/h; cap $2.50 for the whole task)
DISK: 1
Owner job (helper S3, Claude). dir-s3 numbers "nearest valid answer", marks sealed in artifacts/claude-dir-s3-numbers-20260929/PASSMARKS.md (seal SEAL-s3.sha256.txt). It runs handoff/kit/s3v/vcollect.sh from the pinned commit fc64d12fc2d22dd3b699889dfff32d67017c7055 and collects: restarts the Mac guard if it died, waits up to 70 min for it to end, then puts runs-vast/<mode>/<net>/ and the rental's records into run-vast/ for the PUSH. NOT-YET if the guard has not ended; FLAG-DIRECTOR if the instance was stopped, not destroyed. Release about 30 min after dir-s3-vast-1-start prints STARTED, and repeat until COLLECTED. Never reads or prints the vast key. The kit is a copy of handoff/kit/lfszv (torch 2.11.0 pinned) and was not run yet (untested: rental steps).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=fc64d12fc2d22dd3b699889dfff32d67017c7055
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/s3v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/s3v/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-dir-s3-numbers-20260929/runs-vast artifacts/claude-dir-s3-numbers-20260929/run-vast
