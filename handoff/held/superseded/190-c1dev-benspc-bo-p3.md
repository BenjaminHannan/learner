BASH-ONLY: yes
GPU: yes (BensPC RTX 5070 Ti; one job at a time; $0, no rental). NO RENTALS, whatever fails. The watcher writes C:\Users\benja\GPU-BUSY.txt as "queue job 190-c1dev-benspc-bo-p3" while this task runs: that is this job, so go on and leave the file to the watcher. If the file names any other job, stop with BUSY and run nothing.
DISK: 1
Owner job (Everyday chat thread, Claude, wrote this on 2026-09-27 12:28 UTC). c1-dev on BensPC without an LLM builder: replaces k2-c1dev-benspc (held, superseded; artifacts/claude-c1dev-20260927/ADDENDUM-1-bash-only.md, sealed in SEAL-kit.sha256.txt). Pass 3 of 3; all three are identical and state-driven. A pass makes the tree C:\Users\benja\lis301\work\c1dev\tree once from the pinned commit, checks SEAL-2 (24 lines), the three model folders and four selftests once, and then does one of three things. (1) If the chain has not started, and BensPC has no python.exe, at most 700 MiB of GPU memory in use, at least 4 GB free on C: and GPU-BUSY.txt naming this job, it starts remote/chain.cmd once, detached through WMI (arms D, T, Q, L over the 60 DEV practice chats; eval only, no weights), and records the GPU a few minutes later. (2) If the chain is running, it writes a note (STALLED when the arm's log is 30 minutes old). (3) If the chain is done, it copies the chats and logs back and writes artifacts/claude-c1dev-20260927/RESULTS-benspc.md (counts only). The chain keeps going after a pass ends. A pass after RESULTS-benspc.md exists prints DONE or DUPLICATE and does nothing.
It runs handoff/kit/c1devpc/pass.sh from the pinned commit 62a5944c8a17abd75322781763d2928326edeeda (tested against a mock BensPC). The helpers go to BensPC as files (tar through cmd.exe), never piped into bash, and their sha256 is checked before use. It never edits sealed code, never stops or kills any process, never deletes anything on BensPC, never starts a second chain, never relaunches a chain that died, never opens a TEST-ONLY panel, and writes no weights.
```bash
set -u
JOB=$(basename "$0" .bo.sh); PIN=62a5944c8a17abd75322781763d2928326edeeda
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/c1devpc | tar -x -C "$K"
[ -f "$K/handoff/kit/c1devpc/pass.sh" ] || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/c1devpc/pass.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-c1dev-20260927/run artifacts/claude-c1dev-20260927/RESULTS-benspc.md
