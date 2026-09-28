STATUS: HELD. DO NOT RUN (helper H7, 2026-09-28 20:35 UTC from date -u). The Director releases it (deleting this line) about X h + 30 min after h7-dirh6-1-start prints STARTED.
BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (helper H7, Claude, wrote this on 2026-09-28 20:35 UTC for the Director). dir-h6 vast collect 1 of up to 2. It runs handoff/kit/sleeph6r/vcollect.sh from the pinned commit. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end. The guard itself halts the runs if it stopped them, copies back and destroys or stops the rental. It then puts runs/<R>/ (dirh6-seed<S>.json, <R>.log, <R>.err) and the rental's records (progress file, torch record, pip freeze, seal and check outputs, smoke output, day sizes, GPU memory log, file manifest, rental list, the guard's log) into the worktree, and writes COLLECT.txt. COLLECT.txt prints NO test score: only which seeds have a result file, how many nights each arm finished, and the integrity fields (torch, GPU, minutes, learning rates, plan flags). If the guard has not ended it prints NOT-YET and changes nothing. If smoke failed it prints the first traceback verbatim. If the instance was stopped instead of destroyed it prints FLAG-DIRECTOR. If the final copy-back did not happen it uses the 30-minute snapshot and says so. It never pushes weights (there are none).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=b0d1d74bc1b0b3b4537d2c6f9ffdfe6ba5ed4a92
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleeph6r | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleeph6r/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-dir-h6-sleeplen-20260928/runs artifacts/claude-dir-h6-sleeplen-20260928/run-vast
