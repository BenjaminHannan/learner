BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 14:11:28 UTC). HELD: release after rent358s-1-start has printed STARTED. rsn-358s vast collect 1 of up to 2, per artifacts/claude-rsn358s-20260926/ADDENDUM-vast-1.md. It runs handoff/kit/sleep358sv/vcollect.sh from the pinned commit 04a388f2d5d0a0bc4a00efb99418cb1840d53b4b. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end. The guard itself copies back and destroys or stops the rental. It then puts SEAL-run-vast.sha256.txt, runs-vast/<R>/ (train log and summary, tests.json, logs) and the rental's records into the worktree for the PUSH. None of this touches BensPC's runs/ or SEAL-run.sha256.txt. The records go in run-vast/: progress file, torch check, checks, file manifest, rental list, the guard's log, and COLLECT.txt with each final.pt's sha256 checked against ~/premonition-models/rsn358s-vast. If the guard has not ended, it prints NOT-YET and changes nothing. If the instance was stopped instead of destroyed, it prints FLAG-DIRECTOR. It never pushes weights.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=04a388f2d5d0a0bc4a00efb99418cb1840d53b4b
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358sv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358sv/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-rsn358s-20260926/SEAL-run-vast.sha256.txt artifacts/claude-rsn358s-20260926/runs-vast artifacts/claude-rsn358s-20260926/run-vast
