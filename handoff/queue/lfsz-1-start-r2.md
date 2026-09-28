BASH-ONLY: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 16 GB, at most $0.65/h; cap $0.45 for the whole task, the guard stops there)
DISK: 1
Owner job (lf-sz helper, Claude). lf-sz, sealed in artifacts/claude-lfsz-20260928/PASSMARKS.md: is it depth or just size that keeps old skills? 6 runs at once on one vast card (loop8, a 2-layer loop widened to d512 and a 4-layer loop at d360, all near 6.4M weights, seeds 9 and 10). It runs handoff/kit/lfszv/vstart.sh from the pinned commit 31dd45b60ce23c0a4d66d2f1e08bcb34c6b8ae34: refuses if lf-sz already has RESULTS.md, runs-vast/ or run-vast/ on main or builder-outbox or an instance labelled claude-lfsz is live; rents the single-GPU offer with the best TFLOPS per $/h (>= 16 GB, at most $0.65/h, and only if estimate x price <= $0.36); the rental checks the torch 2.11.0 pin, the 16-line seal and the selftest (three weight counts) and Stage 0, then launches the 6 runs; the Mac guard stops at $0.45, destroys only after a manifest-verified copy. Never reads or prints the vast key. Collect with lfsz-2-collect about 30 min after STARTED.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=31dd45b60ce23c0a4d66d2f1e08bcb34c6b8ae34
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/lfszv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/lfszv/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
