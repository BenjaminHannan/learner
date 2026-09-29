STATUS: HELD. Released by the Director deleting this line (helper S3, 2026-09-29). Up to $2.50 of vast, inside Ben's $5 for tonight; the Director chooses the spend. Do not release together with dir-s3-min / dir-s3-random (BensPC copies) unless the Director wants both.
BASH-ONLY: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 24 GB, at most $0.65/h; cap $2.50 for the whole task)
DISK: 1
Owner job (helper S3, Claude). dir-s3 numbers "nearest valid answer", marks sealed in artifacts/claude-dir-s3-numbers-20260929/PASSMARKS.md (seal SEAL-s3.sha256.txt). It runs handoff/kit/s3v/vcollect.sh from the pinned commit 2e7458d32f0c1ee5d7a164dcd3cf1c1a556e521c and collects: restarts the Mac guard if it died, waits up to 70 min for it to end, then puts runs-vast/<mode>/<net>/ and the rental's records into run-vast/ for the PUSH. NOT-YET if the guard has not ended; FLAG-DIRECTOR if the instance was stopped, not destroyed. Release about 30 min after dir-s3-vast-1-start prints STARTED, and repeat until COLLECTED. Never reads or prints the vast key. The kit is a copy of handoff/kit/lfszv (torch 2.11.0 pinned) and was not run yet (untested: rental steps).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=2e7458d32f0c1ee5d7a164dcd3cf1c1a556e521c
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/s3v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/s3v/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-dir-s3-numbers-20260929/runs-vast artifacts/claude-dir-s3-numbers-20260929/run-vast
