BASH-ONLY: yes
GPU: yes (BensPC RTX 5070 Ti; $0, no rental)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 12:32:17 UTC). rsn-358u (sealed 01715d892: 358i3's recipe with the puzzle-kind input fixed to one value; loop vs plain, seeds 13-16) without an LLM builder. Run AFTER rsn-358s (160-164) has finished. GPU pass 1 of up to 6, all identical and state-driven: set up C:\Users\benja\rsn358u once from the pin (scripts, the sealed 358u folder, 358i's tests; only if the sealed folder is absent), check the seal (20/20), run the selftest and check-mask once, collect finished runs (sha256 into SEAL-run before anything reads them), then, only if BensPC has no python.exe, at most 700 MiB GPU memory used, and GPU-BUSY.txt names this job: launch the next unstarted runs in the sealed order detached through WMI (two at once, one more while 5 GB stays free), or, once all eight are trained or dead, one detached chain that runs V1 poison and then the test eval once per sealed checkpoint, or copy the outputs back. A pass with nothing left prints ALL-TRAINED-AND-EVALUATED.
It runs handoff/kit/sleep358u/pass.sh from the pinned commit 1135df76988c01d652c79a0b008c02cb8c6baa9c (tested against a mock BensPC). The helpers go over as files (tar through cmd.exe) and their hashes are checked before use. It never edits sealed code, never stops or kills any process, never launches a second copy of a run that has W/<R> or W/<R>.log, never relaunches a run that died, evaluates each checkpoint at most once, never opens a test item, and never pushes weights.
```bash
set -u
JOB=$(basename "$0" .bo.sh); PIN=1135df76988c01d652c79a0b008c02cb8c6baa9c
date -u; echo "job $JOB"
git fetch -q origin main || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358u | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358u/pass.sh" "$K" "$PIN" full "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt artifacts/claude-rsn358u-20260927/runs artifacts/claude-rsn358u-20260927/run/RUN-NOTE-bo.md
