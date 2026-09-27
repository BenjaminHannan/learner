BASH-ONLY: yes
GPU: rent (one vast RTX 5090 at most $0.65/h; cap $1.60 for this whole task, guard stops at $1.45 or 3 h 30 min)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 13:40:41 UTC). HELD: release only after Ben says yes to running 358t v3 on vast (relayed by the Thread manager), after rsn-358u's rental has ended, and when the Director's ledger has room. When releasing, move handoff/queue/260-claude-sleep-358t3pc.md to handoff/held/superseded/ so BensPC does not also run v3. rsn-358t v3 (Ben's looped 8-layer net, and the looped 2-layer net with TRM-style training) on ONE vast rental, per artifacts/claude-rsn358t-20260926/ADDENDUM-v3-4-vast.md and ADDENDUM-v3-5-vast-checks.md. It runs handoff/kit/sleep358tv/vstart.sh from the pinned commit 763ee984b4f91b14a3efe193b62c25488ee1c5cd. That is a copy of the Thread manager-reviewed 358u kit v2, tested against a fake vast and rental. Steps:
- It refuses if v3 already has results or runs, or if an instance labelled claude-sleep-358t3 is live. It reports the credit only.
- It rents the cheapest RTX 5090 at most $0.65/h with reliability >= 0.98, >= 16 CPU cores and inet_down >= 200 (up to 3 hosts), and attaches ~/.ssh/id_ed25519.pub.
- It sends the pinned code and starts box/drive.sh detached on the rental. drive.sh: torch 2.11.0+cu128 pin, fail-closed; SEAL-code-v3 22/22; the four checks; Stage 0 with the cache-off line at 0/12, else FIX-FAILS; the 8 graded trains in the sealed order, each started only while 5 GB of GPU memory is free; sha256 of final.pt and final-ema.pt into SEAL-run before any eval; one eval per checkpoint; before any destroy, every run that did not die must have its train log, summary, tests.json and tests-ema.json. The report-only loop8-trm runs are not run.
- It leaves the Mac guard running. The guard stops at $1.45 or 3 h 30 min, on a stall or on a lost host. It copies everything back and checks it against a sha256 manifest made on the rental and against SEAL-run. It destroys the instance by its exact id and confirms it is gone only if that passes. Otherwise it stops the instance without destroying it, and the collect job prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never destroys an instance this task did not create, never edits sealed code, never opens a test item and never pushes weights.
Collect with rent358t3-2-collect (release about 1 h 30 min after this job prints STARTED).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=763ee984b4f91b14a3efe193b62c25488ee1c5cd
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358tv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358tv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
