BASH-ONLY: yes
GPU: rent (one vast RTX 5090, reliability >= 0.98, >= 16 cores; the guard stops at $2.50 (cap $3, under Ben's $4 per job) or 3 h 30 min; estimate about $0.60-1.20)
DISK: 1
Owner job (a stand-in chat acting for the stopped sleep research thread on this one test, Claude, wrote this on 2026-09-28 00:07:15 UTC), under Ben's prompt of 23:45 UTC 09-27 and his standing order for vast. rent358u-4c-recopy printed RECOPY-INCOMPLETE-STOPPED, so by that prompt's rule the 4 loop nets of rsn-358u are retrained: rsn-358u2, plan and acceptance mark in artifacts/claude-rsn358u2-20260928/PLAN.md (on main before this job). Instance 52964920 (358u's originals) is NOT touched: it stays stopped for Ben to decide. It runs handoff/kit/sleep358u2v/vstart.sh from the pinned commit 4752a89a660db1216a738483dd137d8e0fe10093 (a copy of the 358u kit; tested against a fake vast and rental). Steps:
- It refuses if artifacts/claude-rsn358u2-20260928 already has SEAL-run, runs/ or run-vast/ on main or builder-outbox, if PLAN.md is not on main, if ~/premonition-watch/rsn358u2-vast/rentals.txt exists, or if an instance labelled claude-sleep-358u2 is live. It reports the credit only (it stops if under $4).
- It rents the cheapest RTX 5090 offer (up to 3 hosts, 15 min each for ssh), attaches ~/.ssh/id_ed25519.pub, sends the pinned code and starts box/drive.sh detached: torch 2.11.0+cu128 fail-closed; 358u's SEAL-code 20/20, selftest and check-mask; the 4 loop trains (seeds 13-16) at once with 358u's sealed command; sha256 of each final.pt into SEAL-run; V1 poison and eval once each.
- It leaves the Mac guard running. The guard stops at $2.50, 3 h 30 min, a stall or a lost host. At the end it copies the small files back (checked against a sha256 manifest made on the rental) and fetches each final.pt one file at a time through a tmp file into ~/premonition-models/rsn358u2/loop-s<S>/final.pt, kept only if its sha256 matches the manifest and SEAL-run (up to 3 tries per file). Only when all 4 are verified on the Mac does it destroy the instance by its exact id and confirm it is gone; otherwise it stops the instance without destroying it.
- The vast key is never read or printed. It never touches an instance this job did not create, never edits sealed code, never opens a test item and never pushes weights.
Collect with rent358u2-2-collect, released about 2 h after this job prints STARTED.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=4752a89a660db1216a738483dd137d8e0fe10093
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358u2v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358u2v/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
