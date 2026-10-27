BASH-ONLY: yes
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 19:44:42 UTC). HELD: release after rent-lf8-1-start has printed STARTED, and only if rent-lf8-2-collect printed NOT-YET. lf-8 vast collect 2 of up to 2. It runs handoff/kit/lf8v/vcollect.sh from the pinned commit afb1432065d2c21a177a1bd0d4c19b917a3ae0ec. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end. The guard itself copies back and destroys or stops the rental, so nothing costs extra while this waits. It then puts runs-vast/<R>/ (result.json, log.jsonl, lf8.json, the run's stdout and stderr) and the rental's records into the worktree for the PUSH. The records go in run-vast/: progress file, torch check, selftest, Stage 0 output, GPU memory log, file manifest, rental list, the guard's log, and COLLECT.txt. If the guard has not ended, it prints NOT-YET and changes nothing. If the instance was stopped instead of destroyed, it prints FLAG-DIRECTOR.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=afb1432065d2c21a177a1bd0d4c19b917a3ae0ec
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/lf8v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/lf8v/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-lf8-20260927/runs-vast artifacts/claude-lf8-20260927/run-vast
