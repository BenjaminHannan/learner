COMMON RULES (helper Huginn ideas, Claude, wrote this 2026-09-29 for the Director; adapted from the H3 v2 jobs). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss.
STATUS: QUEUED (no real dependency; Mac CPU, $0).
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds a private copy of origin/main in $HOME/premonition-hist (committed files only); checkpoints stay there and are never pushed.
LOAD-LIGHT: no (four processes x 2 threads when `sysctl -n hw.ncpu` is at least 10, otherwise two waves of two). TIME CAP: 330 minutes when four run at once, 660 when two waves (H3 estimate about 1 to 3 hours per seed; untested for this net). LABEL: hist-practice.
WHY: artifacts/claude-dir-hist-20260929/PASSMARKS.md validity V1. Source practice (ADDENDUM-3 recipe: 12,000 batches of 64 sums or Latin grids, no maze) of the history-read loop (window 8) and its window-1 control, seeds 0 and 1.
STOP RULES: (1) if the selftests fail, print the first traceback verbatim and STOP. (2) after training, if v1_pass is false or gradient_check.nonzero_all is false for any of the four sources, report it and STOP (no maze run).

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-hist
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
for i in 1 2 3 4; do git -C "$G" fetch -q origin main && break || sleep $((i*5)); done
git -C "$G" show origin/main:scripts/claude_dir_hist_net.py > /dev/null || { echo "ABORT: fetch or files missing"; exit 4; }
mkdir -p "$W"; git -C "$G" archive origin/main scripts artifacts/claude-dir-hist-20260929 artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
A=artifacts/claude-dir-hist-20260929; mkdir -p $A/runs
$PY scripts/claude_dir_hist_marks.py selftest 2>&1 | tee $A/selftest-marks.log
$PY scripts/claude_dir_hist_selftest.py 2>&1 | tee $A/selftest.log
grep -q "SELFTEST ok" $A/selftest.log || { echo "STOP: selftest failed"; exit 6; }
for PL in claude_dir_hist_net claude_dir_hist_net_w1; do
  $PY scripts/claude_fewex_eq_bench.py selftest --plugin $PL --threads 2 2>&1 | tee -a $A/harness-selftest.log
  [ ${PIPESTATUS[0]} -eq 0 ] || { echo "STOP: harness selftest failed for $PL"; exit 6; }
done
NC=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
prac() {  # $1 seed, $2 plugin, $3 run name
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_dir_hist_practice.py --seed $1 --plugin $2 --out $A/runs/$3-s$1 --threads 2 > $A/runs/practice-$3-s$1.log 2>&1 &
  echo "practice $3 seed $1 pid $!"
}
for S in 0 1; do prac $S claude_dir_hist_net hist; done
if [ "$NC" -ge 10 ]; then for S in 0 1; do prac $S claude_dir_hist_net_w1 histw1; done; wait
else wait; for S in 0 1; do prac $S claude_dir_hist_net_w1 histw1; done; wait; fi
for R in hist histw1; do for S in 0 1; do
  echo "== $R seed $S"; tail -2 $A/runs/practice-$R-s$S.log
  $PY - $A/runs/$R-s$S/source.json <<'PYEOF'
import json, sys
r = json.load(open(sys.argv[1]))
print(json.dumps({"seed": r["seed"], "plugin": r.get("plugin"), "weights": r["weights"], "fixed_depth": r["fixed_depth"], "old": {k: v["right"] for k, v in r["old"].items()}, "v1_pass": r["v1_pass"], "nonzero_all": r["gradient_check"]["nonzero_all"], "train_seconds": round(r["train_seconds"])}))
PYEOF
done; done
shasum -a 256 $A/runs/hist-s0/source.pt $A/runs/hist-s1/source.pt $A/runs/histw1-s0/source.pt $A/runs/histw1-s1/source.pt | tee $A/checkpoints-sha256.txt
mkdir -p "$G/$A/runs"
for R in hist histw1; do for S in 0 1; do mkdir -p "$G/$A/runs/$R-s$S"; cp $A/runs/$R-s$S/source.json "$G/$A/runs/$R-s$S/"; cp $A/runs/practice-$R-s$S.log "$G/$A/runs/"; done; done
cp $A/checkpoints-sha256.txt $A/selftest.log $A/selftest-marks.log $A/harness-selftest.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): torch and python versions; every printed selftest line verbatim; wall time per run; the four printed source.json lines (x of 200 for sums4 and grids5, weights, v1_pass, nonzero_all).
PUSH: artifacts/claude-dir-hist-20260929/runs artifacts/claude-dir-hist-20260929/checkpoints-sha256.txt artifacts/claude-dir-hist-20260929/selftest.log artifacts/claude-dir-hist-20260929/selftest-marks.log artifacts/claude-dir-hist-20260929/harness-selftest.log   (source.json, logs only; NOT the .pt files)
