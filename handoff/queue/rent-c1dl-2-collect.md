BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (Everyday chat thread, Claude, wrote this on 2026-09-27 17:30 UTC). HELD: release about 20 min after rent-c1dl-1-start printed STARTED (longer on a slower card). c1-dl vast collect 1 of up to 2, per artifacts/claude-c1dl-20260927/PLAN.md. It runs handoff/kit/c1dlv/vcollect.sh from the pinned commit 19af6d2942ca75cc659d3cf5c2f3e41ce8c34fbb. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end (the guard itself copies back and destroys or stops the rental). It then puts the DL chat file, its logs and the rental's records (progress file, steps, selftests, torch and model records, GPU log, manifest, rental list, the guard's log) in artifacts/claude-c1dl-20260927/run-vast/ and writes RESULTS-vast.md: counts only, no verdict, with the card, its TFLOPS and $/h, the kit's own spend count, the V1 line and a sha256 table. It never touches c1-dev's folder. It prints COLLECTED, NOT-YET (the next collect picks it up), or FLAG-DIRECTOR if the instance was stopped rather than destroyed.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=19af6d2942ca75cc659d3cf5c2f3e41ce8c34fbb
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/c1dlv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/c1dlv/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-c1dl-20260927/run-vast artifacts/claude-c1dl-20260927/RESULTS-vast.md
