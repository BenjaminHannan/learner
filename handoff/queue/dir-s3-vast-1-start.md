BASH-ONLY: yes
LOAD-LIGHT: yes (it only starts a vast rental and polls; the Mac load hold kept dir-s3-vast-1-start waiting from 00:25 EDT; Director 2026-09-29)
GPU: rent (one vast card, best TFLOPS per $/h, >= 24 GB, at most $0.65/h; cap $2.50 for the whole task)
DISK: 1
Owner job (helper S3, Claude). dir-s3 numbers "nearest valid answer", marks sealed in artifacts/claude-dir-s3-numbers-20260929/PASSMARKS.md (seal SEAL-s3.sha256.txt). It runs handoff/kit/s3v/vstart.sh from the pinned commit 2e7458d32f0c1ee5d7a164dcd3cf1c1a556e521c and starts the rental: refuses if dir-s3 already has runs-vast/ or run-vast/ on main or builder-outbox or an instance labelled claude-dirs3 is live or credit is under $2.50; rents the single-GPU offer with the best TFLOPS per $/h (>= 24 GB, at most $0.65/h, and only if estimate x price <= $2.00); the rental checks the torch 2.11.0 pin, the seals (20, 3, 3), the selftests and Stage 0, then trains all 8 nets at once (min and random arms, loop and plain, seeds 13 and 14) and runs poison, eval and extra on each; the Mac guard stops at $2.50 and destroys only after a manifest-verified copy. Never reads or prints the vast key. The kit is a copy of handoff/kit/lfszv (torch 2.11.0 pinned) and was not run yet (untested: rental steps).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=2e7458d32f0c1ee5d7a164dcd3cf1c1a556e521c
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/s3v | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/s3v/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
