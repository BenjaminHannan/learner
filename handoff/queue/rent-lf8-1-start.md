BASH-ONLY: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 12 GB, at most $0.65/h and only if its estimate x $/h <= 0.8 x $1.70; cap $2.00 for this whole task, guard stops at $1.70 or 1.5 x the card's estimate (2 h on a 5090, scaled by TFLOPS))
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 19:44:42 UTC). HELD: release only on Ben's own words (Ben 19:37 UTC "run it on vast right now", relayed by the Thread manager, who checks this job first). lf-8, sealed by the Making things up thread at 72cb903bc (artifacts/claude-lf8-20260927/PASSMARKS.md): does the 8-layer loop forget less than the 2-block loop? 358e4's dense-replayall with loop layers 2 -> 8, seeds 9 and 10, 4 runs. It runs handoff/kit/lf8v/vstart.sh from the pinned commit afb1432065d2c21a177a1bd0d4c19b917a3ae0ec (a copy of the sleep358tv kit at 7a1e0b85e, tested against a fake vast and rental). Steps:
- It refuses if lf-8 already has RESULTS.md, runs-vast/ or run-vast/ on main or builder-outbox, or if an instance labelled claude-sleep-lf8 is live. It reports the credit only.
- It rents the single-GPU offer with the best TFLOPS per $/h: at least 12 GB GPU RAM, compute capability >= 8.0, at most $0.65/h, reliability >= 0.98, >= 16 CPU cores, inet_down >= 200 (up to 3 hosts; host 406325 skipped). It logs the card, its TFLOPS and its $/h, and attaches ~/.ssh/id_ed25519.pub.
- It sends the pinned code and starts box/drive.sh detached on the rental: torch 2.11.0+cu128 pin, fail-closed; SEAL.sha256.txt 16/16; the lf8 selftest; Stage 0 with the cache-off line at 0/12, else FIX-FAILS; then all 4 runs at once (scripts/claude_lf8_run.py run --arm loop2|loop8 --seed 9|10; on CUDA the base code runs bf16 autocast with the weight cache off).
- It leaves the Mac guard running. The guard stops at $1.70 or 1.5 x the estimate, on a stall or on a lost host. It copies everything back and checks it against a sha256 manifest made on the rental, and checks that each run brought back result.json, log.jsonl and lf8.json (or is recorded as DIED). It destroys the instance by its exact id and confirms it is gone only if that passes. Otherwise it stops the instance without destroying it, and the collect job prints FLAG-DIRECTOR.
- The vast key is never read or printed. It never destroys an instance this task did not create, never edits sealed code, and there are no weights to copy.
Collect with rent-lf8-2-collect (release about 1 h 30 min after this job prints STARTED).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=afb1432065d2c21a177a1bd0d4c19b917a3ae0ec
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/lf8v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/lf8v/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
