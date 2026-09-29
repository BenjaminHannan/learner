STATUS: HELD. Not approved against the $5 vast budget for tonight (coordinator 04:49 UTC 09-29). Only the coordinator/Director release it after a budget decision.
BASH-ONLY: yes
GPU: rent (one vast card, best TFLOPS per $/h, >= 16 GB, at most $0.50/h; cap $2.50 for the whole task)
DISK: 1
Owner: Opus manager session, for Ben (Ben asked for vast use 2026-09-29; this task's own cap is $2.50 of Ben's $5 for this session). Sparse-MoE job mxd-1 on a rented GPU: the strict-fp32 CPU-vs-GPU smoke plus phase 1 (MoE sources seeds 0 and 1, MoE practised dev ladders, same-GPU loop control dev ladders). PHASE 1 DEV ONLY, HOLDOUT NOT RUN, no holdout file is read or made. This is a DUPLICATE of BensPC job mxd-1 in science (same sealed code and marks, artifacts/claude-moe-deep-20260929/PASSMARKS.md and SEAL.sha256.txt; nothing there is edited): whichever runs first, the other should be withdrawn by the Director; neither is chosen by score. The start refuses (DUPLICATE) if main already has SMOKE-gpu.json, runs/ or eq-runs/ of the sealed folder, or results of this kit.
It runs handoff/kit/opmxd/vstart.sh from the pinned commit (PIN=d56fe70f309067a0da2ee18bb7a061f887828cd5, filled in after the kit is committed): refuses if an instance labelled opus-mxd is live, an earlier start ran, or credit is under $2.50; rents the single-GPU offer with the best TFLOPS per $/h (>= 16 GB, compute capability >= 8.0, at most $0.50/h, and only if estimate x price <= $2.00; the estimate is BASE_H 5.25 h on a 5090, an untested guess, scaled up for slower cards); sends the pinned tree by git archive (scripts, the sealed moe folder, the fewex folder, the loop-source sha file, the kit's box/) and the two loop control sources from the Mac if their sha256 match (else LOOP-SOURCE-MISSING and the loop control ladders are skipped); the rental checks the torch 2.14.0+cu126 pin (compute capability 12.x excluded), the seal (6 of 6), the selftest ("selftest": "ok") and runs the smoke (PASS true or false, both go on), then phase 1 part by part in the order MX source s0, MX ladder s0, loop control s0, then seed 1, so a money stop leaves seed 0 whole; the Mac guard stops at $2.50 (or 1.5 x the estimate) and destroys only after a manifest-verified copy of the small files (never a .pt), else it stops the instance, not destroys it. Never reads or prints the vast key. Stage checkpoints (.pt) die with the rental, so a later holdout cannot use this rental's stages: this job gives dev records only. The kit was tested against fakes only (handoff/kit/opmxd/test/fake_run.sh); the rental steps, torch 2.14.0+cu126 wheel and CUDA speed are untested.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=d56fe70f309067a0da2ee18bb7a061f887828cd5
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/opmxd | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/opmxd/vstart.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
