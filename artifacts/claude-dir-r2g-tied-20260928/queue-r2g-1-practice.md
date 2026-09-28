COMMON RULES (helper R2g, Claude, wrote this task on 2026-09-28 for the Director; adapted from the H3 v2 queue files by helpers H3 and H10). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it once PASSMARKS.md, DESIGN.md and the scripts named below are on origin/main. Do not run it while HELD.
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds a private copy of origin/main in $HOME/premonition-r2g (committed files only) and works there; later r2g jobs on the SAME machine find the checkpoints. Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (two processes x 2 threads). TIME CAP: 330 minutes (one practice took about the loop's time: sums step 0.43 s vs 0.41 s and grids step 1.12 s vs 0.89 s at 2 threads in the CPU selftest, one sample each; 12,000 steps; untested at scale). LABEL: r2g-practice.
WHY: PASSMARKS.md "Source guard". Source practice, seeds 0 and 1, the ruler's qualified recipe (ADDENDUM-3: 12,000 batches of 64 sums or Latin grids, no maze) for the R2g tied-directions loop (plug-in claude_dir_r2g_net). scripts/claude_dir_r2g_practice.py saves a resumable checkpoint every 1,000 steps in the run folder, so a second run of this same job RESUMES.
STOP RULES: (1) if any selftest fails, report the first traceback verbatim and STOP (do not fix the code, do not practise). (2) After training, read each source.json: if v1_pass is false or gradient_check.nonzero_all is false for either seed, report it and STOP: PASSMARKS.md says no maze run and reject at this fixed 0.3. Do not retrain, do not change anything.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-r2g
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
A=artifacts/claude-dir-r2g-tied-20260928
git -C "$G" show origin/main:$A/PASSMARKS.md > /dev/null || { echo "WAITING-FOR-PASSMARKS"; exit 5; }
git -C "$G" show origin/main:scripts/claude_dir_r2g_net.py > /dev/null || { echo "WAITING-FOR-SCRIPTS"; exit 5; }
mkdir -p "$W"; git -C "$G" archive origin/main scripts $A artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
grep -q '"verdict": "PASS"' artifacts/claude-fewex-20260927/EQ-DEV-GATE.json || { echo "ABORT: baseline EQ-DEV-GATE is not PASS"; exit 5; }
mkdir -p $A/runs
# 0. SELFTESTS (each must end ok)
$PY scripts/claude_dir_r2g_selftest.py --out $A/selftest-run.json --smoke-steps 200 2>&1 | tee $A/selftest-run.log
grep -q '"selftest": "ok"' $A/selftest-run.log || { echo "STOP: r2g selftest failed"; exit 6; }
$PY scripts/claude_dir_r2g_swapcheck.py selftest 2>&1 | tee -a $A/selftest-run.log
grep -q swapcheck_selftest $A/selftest-run.log || { echo "STOP: swapcheck selftest failed"; exit 6; }
python3 scripts/claude_dir_r2g_report.py selftest 2>&1 | tee -a $A/selftest-run.log
$PY scripts/claude_fewex_eq_bench.py selftest --plugin claude_dir_r2g_net --threads 2 2>&1 | tee $A/harness-selftest.log
[ ${PIPESTATUS[0]} -eq 0 ] || { echo "STOP: harness selftest failed"; exit 6; }
# 1. PRACTICE (two processes, one per seed)
for S in 0 1; do
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_dir_r2g_practice.py --seed $S --plugin claude_dir_r2g_net --out $A/runs/r2g-s$S --threads 2 > $A/runs/practice-r2g-s$S.log 2>&1 &
  echo "practice seed $S pid $!"
done
wait
# 2. SOURCE GUARD
for S in 0 1; do
  echo "== r2g seed $S"; tail -2 $A/runs/practice-r2g-s$S.log
  $PY - $A/runs/r2g-s$S/source.json <<'PYEOF'
import json, sys
r = json.load(open(sys.argv[1]))
print(json.dumps({"seed": r["seed"], "plugin": r.get("plugin"), "weights": r["weights"], "fixed_depth": r["fixed_depth"], "old": {k: v["right"] for k, v in r["old"].items()},
                  "v1_pass": r["v1_pass"], "nonzero_all": r["gradient_check"]["nonzero_all"], "train_seconds": round(r["train_seconds"])}))
PYEOF
done
$PY - $A/runs/r2g-s0/source.pt $A/runs/r2g-s1/source.pt <<'PYEOF'
import sys, json, torch
for p in sys.argv[1:]:
    sd = torch.load(p, map_location="cpu", weights_only=True)
    print(json.dumps({"ckpt": p, "mean_abs_tie": {k: round(float(v.abs().mean()), 5) for k, v in sd.items() if k.endswith(".tie")},
                      "mean_abs_br_bc_x0.3": {k: round(0.3 * float(v.abs().mean()), 5) for k, v in sd.items() if k.endswith((".br", ".bc"))}}))
PYEOF
shasum -a 256 $A/runs/r2g-s0/source.pt $A/runs/r2g-s1/source.pt | tee $A/checkpoints-sha256.txt
for S in 0 1; do mkdir -p "$G/$A/runs/r2g-s$S"; cp $A/runs/r2g-s$S/source.json "$G/$A/runs/r2g-s$S/"; cp $A/runs/practice-r2g-s$S.log "$G/$A/runs/"; done
cp $A/checkpoints-sha256.txt $A/selftest-run.json $A/selftest-run.log $A/harness-selftest.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): torch and python versions; every printed selftest line verbatim and the harness-selftest lines; wall time per seed; the printed source.json lines (x of 200 for sums4 and grids5, fixed depth, v1_pass, nonzero_all); the mean |tie| lines. Nothing here is a maze score.
PUSH: artifacts/claude-dir-r2g-tied-20260928/runs artifacts/claude-dir-r2g-tied-20260928/checkpoints-sha256.txt artifacts/claude-dir-r2g-tied-20260928/selftest-run.json artifacts/claude-dir-r2g-tied-20260928/selftest-run.log artifacts/claude-dir-r2g-tied-20260928/harness-selftest.log   (source.json and logs only; NOT the .pt files or resume.pt)
