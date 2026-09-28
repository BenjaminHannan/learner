STATUS: HELD. Released by the Director deleting this line (lf-sz helper, 2026-09-28 21:56:22 UTC): the price is under $0.50 (RUN-PLAN.md: about $0.15 to $0.18, money stop $0.45), so the standing rule of 09-28 21:34 UTC needs no OK from Ben.
BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (lf-sz helper, Claude). lf-sz vast collect: runs handoff/kit/lfszv/vcollect.sh from the pinned commit 4e000f02bf15e92913dbb2799f6ae881de04ff79. Restarts the Mac guard if it died, waits up to 70 min for it to end, then puts runs-vast/<R>/ and the rental's records into run-vast/ for the PUSH. NOT-YET if the guard has not ended; FLAG-DIRECTOR if the instance was stopped, not destroyed. Release about 30 min after lfsz-1-start prints STARTED.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=4e000f02bf15e92913dbb2799f6ae881de04ff79
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/lfszv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/lfszv/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-lfsz-20260928/runs-vast artifacts/claude-lfsz-20260928/run-vast
