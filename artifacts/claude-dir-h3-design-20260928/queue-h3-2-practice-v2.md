COMMON RULES (helper H10, Claude, wrote this task on 2026-09-28 20:58 UTC for the Director; adapted from queue-h3-2-practice.md by helper H3). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it once ADDENDUM-1 (artifacts/claude-dir-h3-design-20260928/ADDENDUM-1.md) and the v2 scripts named below are on origin/main. Do not run it while HELD. It replaces queue-h3-2-practice.md (v1 job 2 never ran; do not run both).
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds a private copy of origin/main in $HOME/premonition-h3v2 (committed files only) and works there, so the later v2 jobs on the SAME machine find the checkpoints. Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (four processes x 2 threads = 8 threads when `sysctl -n hw.ncpu` is at least 10, otherwise two waves of two processes x 2 threads). TIME CAP: 330 minutes when four run at once, 660 when two waves (the v1 estimate was about 2.8 hours per seed; the v1 selftest's own timing, 0.19 s per sums batch and 0.37 s per grids batch at 2 threads, suggests about 1 hour per seed for 12,000 steps; both untested at scale). LABEL: h3-practice-v2.
WHY: PASSMARKS.md "Source guard" with ADDENDUM-1. Source practice, seeds 0 and 1, the ruler's qualified recipe (ADDENDUM-3: 12,000 batches of 64 sums or Latin grids, no maze), for TWO arms: the settle-gate loop v2 (plug-in claude_dir_h3_net_v2: the three gate tensors are exempt from weight decay) and the constant-g = 0.9 damping control (plug-in claude_dir_h3_net_v2_const: no gate tensors). scripts/claude_dir_h3_practice_v2.py is claude_dir_h3_practice.py with --plugin. It saves a resumable checkpoint every 1,000 steps in the run folder, so a second run of this same job RESUMES.
STOP RULES: (1) if the v2 selftest or a harness selftest fails, report the first traceback verbatim and STOP (do not fix the code, do not practise). (2) After training, read each source.json: if v1_pass is false or gradient_check.nonzero_all is false for ANY of the four sources, report it and STOP: PASSMARKS.md says no maze run. Do not retrain, do not change anything.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-h3v2
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" show origin/main:artifacts/claude-dir-h3-design-20260928/ADDENDUM-1.md > /dev/null || { echo "WAITING-FOR-ADDENDUM-1"; exit 5; }
git -C "$G" show origin/main:scripts/claude_dir_h3_net_v2.py > /dev/null || { echo "WAITING-FOR-V2-SCRIPTS"; exit 5; }
mkdir -p "$W"; git -C "$G" archive origin/main scripts artifacts/claude-dir-h3-design-20260928 artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
grep -q '"verdict": "PASS"' artifacts/claude-fewex-20260927/EQ-DEV-GATE.json || { echo "ABORT: baseline EQ-DEV-GATE is not PASS"; exit 5; }
A=artifacts/claude-dir-h3-design-20260928; mkdir -p $A/runs
# 0. SELFTESTS (each must end ok; about 20 minutes)
$PY scripts/claude_dir_h3_selftest_v2.py --out $A/selftest-v2.json --smoke-steps 200 2>&1 | tee $A/selftest-v2.log
grep -q '"selftest": "ok"' $A/selftest-v2.log || { echo "STOP: v2 selftest failed"; exit 6; }
for PL in claude_dir_h3_net_v2 claude_dir_h3_net_v2_const; do
  $PY scripts/claude_fewex_eq_bench.py selftest --plugin $PL --threads 2 2>&1 | tee -a $A/harness-selftest-v2.log
  [ ${PIPESTATUS[0]} -eq 0 ] || { echo "STOP: harness selftest failed for $PL"; exit 6; }
done
# 1. PRACTICE
NC=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
prac() {  # $1 seed, $2 plugin, $3 run name
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_dir_h3_practice_v2.py --seed $1 --plugin $2 --out $A/runs/$3-s$1 --threads 2 > $A/runs/practice-$3-s$1.log 2>&1 &
  echo "practice $3 seed $1 pid $!"
}
for S in 0 1; do prac $S claude_dir_h3_net_v2 h3; done
if [ "$NC" -ge 10 ]; then
  for S in 0 1; do prac $S claude_dir_h3_net_v2_const h3c; done; wait
else
  wait; for S in 0 1; do prac $S claude_dir_h3_net_v2_const h3c; done; wait
fi
# 2. SOURCE GUARD AND GATE REPORT
for R in h3 h3c; do for S in 0 1; do
  echo "== $R seed $S"; tail -2 $A/runs/practice-$R-s$S.log
  $PY - $A/runs/$R-s$S/source.json <<'PYEOF'
import json, sys
r = json.load(open(sys.argv[1]))
print(json.dumps({"seed": r["seed"], "plugin": r.get("plugin"), "weights": r["weights"], "fixed_depth": r["fixed_depth"], "old": {k: v["right"] for k, v in r["old"].items()},
                  "v1_pass": r["v1_pass"], "nonzero_all": r["gradient_check"]["nonzero_all"], "train_seconds": round(r["train_seconds"])}))
PYEOF
done; done
for S in 0 1; do
  $PY scripts/claude_dir_h3_gate_report_v2.py --ckpt $A/runs/h3-s$S/source.pt --out $A/runs/gate-source-s$S.json --threads 2
done
shasum -a 256 $A/runs/h3-s0/source.pt $A/runs/h3-s1/source.pt $A/runs/h3c-s0/source.pt $A/runs/h3c-s1/source.pt | tee $A/checkpoints-sha256.txt
mkdir -p "$G/$A/runs"
for R in h3 h3c; do for S in 0 1; do mkdir -p "$G/$A/runs/$R-s$S"; cp $A/runs/$R-s$S/source.json "$G/$A/runs/$R-s$S/"; cp $A/runs/practice-$R-s$S.log "$G/$A/runs/"; done; done
cp $A/runs/gate-source-s0.json $A/runs/gate-source-s1.json "$G/$A/runs/"
cp $A/checkpoints-sha256.txt $A/selftest-v2.json $A/selftest-v2.log $A/harness-selftest-v2.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): torch and python versions; every printed selftest line verbatim (budget, same_loop, shapes, gate_init, gate_open_equals_loop, gate_range, surprise_detached, gradients_fresh_init, groups, decay_effect, learner_v2, gate_std, const_g, practice_smoke, timing_cpu) and the harness-selftest lines; wall time per seed and arm; the printed source.json lines for all four sources (x of 200 for sums4 and grids5, fixed depth, v1_pass, nonzero_all); the gate_report lines for both H3 seeds (mean gate at rounds 1, 8, 16, 32, 48, std_all, and the dead_gate line: dead means std of g below 0.02 on all three sets). Nothing here is a maze score.
PUSH: artifacts/claude-dir-h3-design-20260928/runs artifacts/claude-dir-h3-design-20260928/checkpoints-sha256.txt artifacts/claude-dir-h3-design-20260928/selftest-v2.json artifacts/claude-dir-h3-design-20260928/selftest-v2.log artifacts/claude-dir-h3-design-20260928/harness-selftest-v2.log   (source.json, logs and gate reports only; NOT the .pt files or resume.pt)
