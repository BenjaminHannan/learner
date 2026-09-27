BASH-ONLY: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 24 GB, at most $0.60/h; cap $4 for this whole task, guard stops at $3.60 or 6 h on a 5090, scaled for slower cards)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 14:11:28 UTC). HELD: release only on Ben's release words (his 14:05 UTC standing order covers vast; the Director's check needs his words naming the job), after the running rentals and when the Director's ledger has room. When releasing, move handoff/queue/160-164-claude-sleep-358s-bo-p1..p5.md to handoff/held/superseded/ so BensPC does not also run 358s. rsn-358s (does a 3x loop reasoner still beat a 3x plain net) on ONE vast card, per artifacts/claude-rsn358s-20260926/ADDENDUM-vast-1.md: all 8 runs (loop and plain, seeds 9-12) are rerun there, and BensPC's 3 finished runs become report-only. It runs handoff/kit/sleep358sv/vstart.sh from the pinned commit c40168614cfa2c1553d947a535c3fd595fa6f8d5. That is the 358t v3 vast kit (built from the Thread manager-reviewed 358u kit v2), tested against a fake vast and rental. Steps:
- It refuses if 358s has RESULTS.md, runs-vast/, run-vast/ or SEAL-run-vast, if an instance labelled claude-sleep-358s is live, or while any of handoff/queue/160-164 (358s on BensPC) is still on main or running on the watcher. It reports the credit only (it stops if under $4).
- It rents the single-GPU offer with the best TFLOPS per $/h: at least 24 GB GPU RAM, compute capability >= 8.0, at most $0.60/h, reliability >= 0.98, >= 16 CPU cores, inet_down >= 200 (up to 3 hosts). It logs the card, its TFLOPS and its $/h, scales the time cap by 5090 TFLOPS / its TFLOPS, and attaches ~/.ssh/id_ed25519.pub.
- It sends the pinned code and starts box/drive.sh detached. drive.sh: torch 2.11.0+cu128, fail-closed; SEAL-code 19/19; selftest and check-mask; the 8 sealed trains in the sealed order, each started only while 5 GB of GPU memory is free and at most one per 5 minutes; sha256 of each final.pt into SEAL-run before any eval; one eval per checkpoint.
- It leaves the Mac guard running. The guard stops at $3.60 or the time cap, on a stall or on a lost host. It copies everything back and checks it against a sha256 manifest made on the rental, against SEAL-run, and for every run's train log, summary and tests.json. Only then does it destroy the instance by its exact id and confirm it is gone. Otherwise it stops the instance without destroying it, and the collect job prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never destroys an instance this task did not create, never edits sealed code, never opens a test item and never pushes weights.
Collect with rent358s-2-collect (release about 2 h 30 min after this job prints STARTED).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=c40168614cfa2c1553d947a535c3fd595fa6f8d5
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358sv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/sleep358sv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
