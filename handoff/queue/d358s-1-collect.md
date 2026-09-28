STATUS: HELD. DO NOT RUN (helper D, 2026-09-28 21:19 UTC from date -u). The Director releases it (deleting this line) only after d358s-0-inspect shows the guard's END line and sealed runs.
BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (helper D, Claude). Collect for the FIRST rsn-358s vast rental (rent358s-1-start, STARTED 2026-09-27 14:59 UTC), which was never collected. It runs handoff/kit/sleep358sv/vcollect.sh from the same pinned commit as the start (04a388f2d5d0a0bc4a00efb99418cb1840d53b4b). It restarts the Mac guard only if the guard died before ending, waits up to 70 min for it to end, then puts SEAL-run-vast.sha256.txt, runs-vast/<R>/ and the rental's records into the worktree beside (never over) BensPC's runs/. It prints NOT-YET, NOT-STARTED, DUPLICATE or FLAG-DIRECTOR when those apply, and never pushes weights and never prints a score. After it, per PASSMARKS.md, a blind recount from raw files comes before any RESULTS.md, and no gap is read until all 8 runs are in.
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
