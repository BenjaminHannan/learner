BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (Everyday chat thread, Claude, wrote this on 2026-09-27 14:44 UTC). HELD: release only if rent-c1dev-3-collect printed NOT-YET. c1-dev vast collect 3 of up to 3, per artifacts/claude-c1dev-20260927/ADDENDUM-2-vast.md. It runs handoff/kit/c1devv/vcollect.sh from the pinned commit d0072550e7756cbfb99a184f3c891faf78049463. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end (the guard itself copies back and destroys or stops the rental). It then puts the four chat files, their logs and the rental's records (progress file, steps, selftests, torch and model records, GPU log, manifest, rental list, the guard's log) in artifacts/claude-c1dev-20260927/run-vast/ and writes RESULTS-vast.md: counts only, no verdict, with the card, its TFLOPS and $/h, the kit's own spend count, V1 lines and a sha256 table. It never touches BensPC's run/ or RESULTS-benspc.md. It prints COLLECTED, NOT-YET (the next collect picks it up), or FLAG-DIRECTOR if the instance was stopped rather than destroyed.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=d0072550e7756cbfb99a184f3c891faf78049463
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/c1devv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/c1devv/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-c1dev-20260927/run-vast artifacts/claude-c1dev-20260927/RESULTS-vast.md
