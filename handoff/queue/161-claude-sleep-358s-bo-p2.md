BASH-ONLY: yes
GPU: yes (BensPC RTX 5070 Ti; $0, no rental)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 11:01:17 UTC). rsn-358s without an LLM builder: the free builders of 157 and 158 stalled (Director 10:5x UTC). GPU pass 2 of up to 5, all identical and state-driven: collect finished runs, then (only if BensPC has no python.exe and at most 700 MiB GPU memory used, and GPU-BUSY.txt names this job) launch the next unstarted runs in 156's order detached through WMI (two at once, one more while 5 GB stays free), or, once all eight are trained or dead, the evals of every sealed checkpoint in one detached chain, or copy the finished tests.json back. Runs keep going after the job ends; the watcher's busy gate holds the next pass until they finish. A pass with nothing left prints ALL-TRAINED-AND-EVALUATED.
It runs handoff/kit/sleep358s/pass.sh from the pinned commit 84917d07bb51fdc69e6993559f490a14989ffdbf (tested against a mock BensPC). The kit's BensPC helpers go over as files (tar through cmd.exe), never piped into bash, and their hashes are checked before use. It never edits sealed code, never stops or kills any process on BensPC, never launches a second copy of a run that has W/<R> or W/<R>.log, never relaunches a run that died, evaluates each sealed checkpoint at most once and only after its sha256 is in SEAL-run, never opens a test item, and never pushes weights.
```bash
set -u
JOB=$(basename "$0" .bo.sh); PIN=84917d07bb51fdc69e6993559f490a14989ffdbf
date -u; echo "job $JOB"
git fetch -q origin main || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358s | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358s/pass.sh" "$K" "$PIN" full "$JOB"; rc=$?
rm -rf "$K"
grep -E '15[78]-claude-sleep-358spc' ~/premonition-watch/queue/log.txt | tail -4
exit $rc
```
PUSH: artifacts/claude-rsn358s-20260926/SEAL-run.sha256.txt artifacts/claude-rsn358s-20260926/runs artifacts/claude-rsn358s-20260926/run/RUN-NOTE-bo.md
