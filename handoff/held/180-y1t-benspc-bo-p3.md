BASH-ONLY: yes
GPU: yes (BensPC RTX 5070 Ti; one job at a time; $0, no rental). NO RENTALS, whatever fails. The watcher writes C:\Users\benja\GPU-BUSY.txt as "queue job 180-y1t-benspc-bo-p3" while this task runs: that is this job, so go on and leave the file to the watcher. If the file names any other job, stop with BUSY and run nothing.
DISK: 1
Owner job (Answering-from-memory thread, Claude, wrote this on 2026-09-27 11:42:05 UTC). y1t on BensPC without an LLM builder (Director 11:12 UTC): replaces handoff/held/benspc-y1t.md, which is never released (artifacts/claude-y1t-20260926/ADDENDUM-6-bash-only.md, sealed). Pass 3 of 4; all four are identical and state-driven. A pass makes the tree C:\Users\benja\y1t\tree once from the pinned commit, checks the seals, the items sha256 and the four selftests once, and then does one of three things. (1) If the chain has not started, and BensPC has no python.exe, at most 700 MiB of GPU memory in use, at least 10 GB free on C: and GPU-BUSY.txt naming this job, it starts remote/chain.cmd once, detached through WMI (drafts, train, eval, eval_plain, h1_A, h1_B), and records the GPU 5 minutes later. (2) If the chain is running, it writes a note (STALLED when the step's log is 30 minutes old). (3) If the chain is done, it copies the results back and writes artifacts/claude-y1t-20260926/run/RESULTS-benspc.md. The chain keeps going after a pass ends; the watcher's busy check holds the next pass until no python.exe runs. A pass after RESULTS-benspc.md exists prints DONE or DUPLICATE and does nothing.
It runs handoff/kit/y1tpc/pass.sh from the pinned commit 15a952c79a89053861bb99bae400f463f853328c (tested against a mock BensPC). The helpers go to BensPC as files (tar through cmd.exe), never piped into bash, and their sha256 is checked before use. It never edits sealed code, never stops or kills any process, never starts a second chain, never relaunches a chain that died, never opens the TEST-ONLY panel or the H1 rows, and never pushes weights (the adapter goes to ~/y1t-adapter on the Mac and stays on BensPC in premonition-models/y1t).
```bash
set -u
JOB=$(basename "$0" .bo.sh); PIN=15a952c79a89053861bb99bae400f463f853328c
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/y1tpc | tar -x -C "$K"
[ -f "$K/handoff/kit/y1tpc/pass.sh" ] || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/y1tpc/pass.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-y1t-20260926/run artifacts/claude-y1tH1-20260926/run
