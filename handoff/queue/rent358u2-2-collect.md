BASH-ONLY: yes
DISK: 1
Owner job (a stand-in chat acting for the stopped sleep research thread on this one test, Claude, wrote this on 2026-09-28 01:27:34 UTC, after rent358u2-1-start printed STARTED at 01:24:45 UTC with all 4 runs DONE on the rental). rsn-358u2 vast collect 1 of up to 2 (artifacts/claude-rsn358u2-20260928/PLAN.md). It runs handoff/kit/sleep358u2v/vcollect.sh from the pinned commit 4752a89a660db1216a738483dd137d8e0fe10093: restarts the Mac guard if it died before ending, waits up to 70 min for it to end (the guard itself copies back and destroys the rental), then puts SEAL-run.sha256.txt, runs/<R>/ (train log and summary, poison.json, tests.json, logs) and the rental's records (run-vast/: progress file, torch check, checks, manifest, rental list with $/h and times, the guard's log, COLLECT.txt with each final.pt's sha256 check against ~/premonition-models/rsn358u2) into the worktree for the PUSH. If the guard has not ended it prints NOT-YET and changes nothing. If the instance was stopped instead of destroyed, it prints FLAG-DIRECTOR. It never pushes weights.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=4752a89a660db1216a738483dd137d8e0fe10093
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358u2v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358u2v/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-rsn358u2-20260928/SEAL-run.sha256.txt artifacts/claude-rsn358u2-20260928/runs artifacts/claude-rsn358u2-20260928/run-vast
