BASH-ONLY: yes
GPU: yes (BensPC RTX 5070 Ti; one job at a time; $0, no rental). NO RENTALS, whatever fails. The watcher writes C:\Users\benja\GPU-BUSY.txt as "queue job <this job's name>" while this task runs: that is this job, so go on and leave the file to the watcher. If the file names any other job, stop with BUSY and run nothing.
DISK: 1
Owner job (Trustworthy notes thread, Claude, wrote this on 2026-09-27 12:13:36 UTC). rd-378g on BensPC without an LLM builder (Thread manager 12:0x UTC; the Director's y1t call 11:12 UTC): replaces handoff/held/rd378g-pc2-q.md, which is never released (artifacts/claude-rd378g-20260926/ADDENDUM-L.md, sealed in SEAL-ADD-L). Pass 2 of 4; all four are identical and state-driven, and the Director picks their names and queue place. A pass makes the tree C:\Users\benja\rd378g2\tree once from the pinned commit, checks the seals, the four selftests, the MiniLM snapshot and the LoCoMo file hash once, and then does one of three things. (1) If the chain has not started, and BensPC has no python.exe, at most 700 MiB of GPU memory in use and GPU-BUSY.txt naming this job (or no file), it finds the rd-378 writer R on BensPC (copying it from the Mac only with at least 9 GB free on C:), then starts remote/chain.cmd once, detached through WMI, only with at least 6 GB free on C: (dialogs, train, devcheck, write59, score, whenoff, g5G, g5R), and records the GPU 5 minutes later. (2) If the chain is running, it writes a note (STALLED when the step's log is 30 minutes old). (3) If the chain is done, or died, it copies the results back and writes artifacts/claude-rd378g-20260926/benspc/RESULTS-benspc.md (a run record; the thread scores it). The chain keeps going after a pass ends; the watcher's busy check holds the next pass until no python.exe runs. A pass after RESULTS-benspc.md exists prints DONE or DUPLICATE and does nothing.
It runs handoff/kit/rd378gpc/pass.sh from the pinned commit b6833c2b74dc8209885ef967d2b93092f899bbb9 (tested against a mock BensPC). The helpers go to BensPC as files (tar through cmd.exe), never piped into bash, and their sha256 is checked before use. It never edits sealed code, never stops or kills any process, never deletes anything on BensPC, never starts a second chain, never relaunches a chain that died, never opens a TEST-ONLY panel, never pushes LoCoMo text (dialogs59, g59 and per_question go to ~/rd378g-private on the Mac only) and never pushes weights (G's adapter goes to ~/premonition-models/rd378g-adapter on the Mac and to premonition-models\rd378g on BensPC).
```bash
set -u
JOB=$(basename "$0" .bo.sh); PIN=b6833c2b74dc8209885ef967d2b93092f899bbb9
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/rd378gpc | tar -x -C "$K"
[ -f "$K/handoff/kit/rd378gpc/pass.sh" ] || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/rd378gpc/pass.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-rd378g-20260926/benspc artifacts/claude-rd378g-20260926/g5
