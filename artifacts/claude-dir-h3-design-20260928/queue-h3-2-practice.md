COMMON RULES (helper H3, Claude, wrote this task on 2026-09-28 19:20 UTC for the Director). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. Use at most 4 parallel processes. macOS has no `timeout` command (use perl alarm).
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds a private copy of origin/main in $HOME/premonition-h3 (committed files only) and works there, so a later job on the SAME machine finds the checkpoints. Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (two processes x 2 threads = 4 cores). TIME CAP: 330 minutes. LABEL: h3-practice. WAIT: start only if the Director has committed queue job 1's selftest.log to origin/main with `"selftest": "ok"` in it (check with git archive; otherwise ABORT with WAITING-FOR-SELFTEST).
WHY: PASSMARKS.md "Source guard". Source practice of the settle-gate loop, seeds 0 and 1, the ruler's qualified recipe (ADDENDUM-3: 12,000 batches of 64 sums or Latin grids, no maze). scripts/claude_dir_h3_practice.py is claude_sparse_practice.py with this design's net; it saves a resumable checkpoint every 1,000 steps in the run folder, so a second run of this same job RESUMES. Expected about 2.8 hours per seed (untested; scaled from the sparse test).
STOP RULES: after training, read each source.json. If v1_pass is false or gradient_check.nonzero_all is false in EITHER seed, report it and STOP: PASSMARKS.md says no maze run. Do not retrain, do not change anything.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-h3
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" show origin/main:artifacts/claude-dir-h3-design-20260928/selftest.log | grep -q '"selftest": "ok"' || { echo "WAITING-FOR-SELFTEST"; exit 5; }
mkdir -p "$W"; git -C "$G" archive origin/main scripts artifacts/claude-dir-h3-design-20260928 artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
A=artifacts/claude-dir-h3-design-20260928; mkdir -p $A/runs
for S in 0 1; do
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_dir_h3_practice.py --seed $S --out $A/runs/h3-s$S --threads 2 > $A/runs/practice-s$S.log 2>&1 &
  echo "seed $S pid $!"
done
wait
for S in 0 1; do
  echo "== seed $S"; tail -2 $A/runs/practice-s$S.log
  $PY - $A/runs/h3-s$S/source.json <<'PYEOF'
import json, sys
r = json.load(open(sys.argv[1]))
print(json.dumps({"seed": r["seed"], "weights": r["weights"], "fixed_depth": r["fixed_depth"], "old": {k: v["right"] for k, v in r["old"].items()},
                  "v1_pass": r["v1_pass"], "nonzero_all": r["gradient_check"]["nonzero_all"], "train_seconds": round(r["train_seconds"])}))
PYEOF
  $PY scripts/claude_dir_h3_gate_report.py --ckpt $A/runs/h3-s$S/source.pt --out $A/runs/gate-source-s$S.json --threads 2
done
shasum -a 256 $A/runs/h3-s0/source.pt $A/runs/h3-s1/source.pt | tee $A/checkpoints-sha256.txt
mkdir -p "$G/$A/runs"
for S in 0 1; do mkdir -p "$G/$A/runs/h3-s$S"; cp $A/runs/h3-s$S/source.json "$G/$A/runs/h3-s$S/"; cp $A/runs/practice-s$S.log $A/runs/gate-source-s$S.json "$G/$A/runs/"; done
cp $A/checkpoints-sha256.txt "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): wall time per seed, the printed source.json lines (x of 200 for sums4 and grids5, fixed depth, v1_pass, nonzero_all), the gate_report lines for both seeds (mean gate at rounds 1, 8, 16, 32, 48 for sums4, grids5, dev_mazes9). State plainly if either mean gate is above 0.98 in every round (dead gate) or below 0.05.
PUSH: artifacts/claude-dir-h3-design-20260928/runs artifacts/claude-dir-h3-design-20260928/checkpoints-sha256.txt   (source.json, logs and gate reports only; NOT the .pt files or resume.pt)
