BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 13:40:41 UTC). HELD: release after rent358t3-1-start has printed STARTED, and only if rent358t3-2-collect printed NOT-YET. rsn-358t v3 vast collect 2 of up to 2, per artifacts/claude-rsn358t-20260926/ADDENDUM-v3-4-vast.md , ADDENDUM-v3-5-vast-checks.md and ADDENDUM-v3-7-card-choice.md. It runs handoff/kit/sleep358tv/vcollect.sh from the pinned commit 78384533de91d501abef0194967e390a8bf62abc. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end. The guard itself copies back and destroys or stops the rental, so nothing costs extra while this waits. It then puts SEAL-run-v3.sha256.txt, runs-v3/<R>/ (train log and summary, tests.json, tests-ema.json, logs) and the rental's records into the worktree for the PUSH. The records go in run-vast-v3/: progress file, torch check, checks, Stage 0 output, file manifest, rental list, the guard's log, and COLLECT.txt with each checkpoint's sha256 checked against ~/premonition-models/rsn358t3. If the guard has not ended, it prints NOT-YET and changes nothing. If the instance was stopped instead of destroyed, it prints FLAG-DIRECTOR. It never pushes weights.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=78384533de91d501abef0194967e390a8bf62abc
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358tv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358tv/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-rsn358t-20260926/SEAL-run-v3.sha256.txt artifacts/claude-rsn358t-20260926/runs-v3 artifacts/claude-rsn358t-20260926/run-vast-v3
