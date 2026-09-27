BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 13:05:40 UTC). HELD: release after rent358u-1-start has printed STARTED, and only if rent358u-2-collect printed NOT-YET. rsn-358u vast collect 2 of up to 2, per artifacts/claude-rsn358u-20260927/ADDENDUM-1-vast.md. It runs handoff/kit/sleep358uv/vcollect.sh from the pinned commit 474ed5a3244d4f160363c1b95dd18b8b6cc96409: waits up to 70 min for the Mac guard to end (the guard itself copies back and destroys the rental, so nothing costs money while this waits), then puts SEAL-run.sha256.txt, runs/<R>/ (train log and summary, poison.json, tests.json, logs) and the rental's records (run-vast/: progress file, torch check, checks, rental list with $/h and times, the guard's log, COLLECT.txt with each final.pt's sha256 check against ~/premonition-models/rsn358u) into the worktree for the PUSH. If the guard has not ended it prints NOT-YET and changes nothing. It never pushes weights.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=474ed5a3244d4f160363c1b95dd18b8b6cc96409
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358uv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358uv/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt artifacts/claude-rsn358u-20260927/runs artifacts/claude-rsn358u-20260927/run-vast
