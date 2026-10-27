BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 15:10:26 UTC). HELD: release only if rent358n3-2-collect printed NOT-YET. slp-358n3 vast collect 2 of up to 2. It runs handoff/kit/sleep358nv/vcollect.sh from the pinned commit e9e4ba46ae86268361f8fd60e249d9c8cc89a8af. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end. The guard itself copies back and destroys or stops the rental. It then puts SEAL-run.sha256.txt, runs/<R>/ (each seed's result json and logs) and the rental's records into the worktree for the PUSH: progress file, torch check, checks, day sizes, RESUME result, GPU memory log, file manifest, rental list, the guard's log, and COLLECT.txt with each S-final.pt's sha256 checked against ~/premonition-models/slp358n3. If the guard has not ended, it prints NOT-YET and changes nothing. If the instance was stopped instead of destroyed, it prints FLAG-DIRECTOR. It never pushes weights.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=e9e4ba46ae86268361f8fd60e249d9c8cc89a8af
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358nv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358nv/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-slp358n3-20260927/SEAL-run.sha256.txt artifacts/claude-slp358n3-20260927/runs artifacts/claude-slp358n3-20260927/run-vast
