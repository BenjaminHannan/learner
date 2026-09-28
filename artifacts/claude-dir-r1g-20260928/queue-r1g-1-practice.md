COMMON RULES (helper R1G, Claude, wrote this task on 2026-09-28 for the Director; adapted from the H3 v2 queue files by helper H10). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it (see WAIT). Do not run it while HELD.
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds/uses a private copy of origin/main in $HOME/premonition-r1g (committed files only). Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (two processes x 2 threads). TIME CAP: 330 minutes. LABEL: r1g-practice. The self-test on the cloud CPU took under a minute at 150 smoke steps; timing there (2 threads): practice step on sums 0.46 s against the loop's 0.35 s, on grids 0.81 s against 0.71 s, so about 15 to 30 percent slower than the loop; the full 12,000 steps per seed are untested at scale.
WAIT: start only if origin/main has artifacts/claude-dir-r1g-20260928/PASSMARKS.md, SEAL.sha256.txt and scripts/claude_dir_r1g_net.py, and artifacts/claude-fewex-20260927/EQ-DEV-GATE.json says PASS.
WHY: PASSMARKS.md "Source guard". Source practice, seeds 0 and 1, the ruler's qualified recipe (12,000 batches of 64 sums or Latin grids, no maze), plug-in claude_dir_r1g_net. scripts/claude_dir_r1g_practice.py saves a resumable checkpoint every 1,000 steps in the run folder, so a second run of this job RESUMES.
STOP RULES: (1) if the self-test or the harness selftest fails, report the first traceback verbatim and STOP (do not fix the code, do not practise). (2) After training, read each source.json: if v1_pass is false or gradient_check.nonzero_all is false for either seed, report it and STOP: PASSMARKS.md says no maze run. Do not retrain, do not change anything.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-r1g; A=artifacts/claude-dir-r1g-20260928
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" show origin/main:$A/SEAL.sha256.txt > /dev/null || { echo "WAITING-FOR-SEAL"; exit 5; }
git -C "$G" show origin/main:artifacts/claude-fewex-20260927/EQ-DEV-GATE.json | grep -q '"verdict": "PASS"' || { echo "ABORT: baseline gate not PASS"; exit 5; }
mkdir -p "$W"; git -C "$G" archive origin/main scripts $A artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
(cd "$W" && shasum -a 256 -c $A/SEAL.sha256.txt) || { echo "STOP: sealed files differ from SEAL.sha256.txt"; exit 6; }
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
mkdir -p $A/runs
$PY scripts/claude_dir_r1g_selftest.py --out $A/selftest.json --smoke-steps 200 2>&1 | tee $A/selftest.log
grep -q '"selftest": "ok"' $A/selftest.log || { echo "STOP: selftest failed"; exit 6; }
$PY scripts/claude_fewex_eq_bench.py selftest --plugin claude_dir_r1g_net --threads 2 2>&1 | tee $A/harness-selftest.log
[ ${PIPESTATUS[0]} -eq 0 ] || { echo "STOP: harness selftest failed"; exit 6; }
for S in 0 1; do
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_dir_r1g_practice.py --seed $S --out $A/runs/r1g-s$S --threads 2 > $A/runs/practice-r1g-s$S.log 2>&1 &
  echo "practice seed $S pid $!"
done
wait
for S in 0 1; do
  echo "== seed $S"; tail -2 $A/runs/practice-r1g-s$S.log
  $PY - $A/runs/r1g-s$S/source.json <<'PYEOF2'
import json, sys
r = json.load(open(sys.argv[1]))
print(json.dumps({"seed": r["seed"], "weights": r["weights"], "fixed_depth": r["fixed_depth"], "old": {k: v["right"] for k, v in r["old"].items()},
                  "v1_pass": r["v1_pass"], "nonzero_all": r["gradient_check"]["nonzero_all"], "mix_mean_abs": r["mix_mean_abs"], "gamma": r["gamma"],
                  "train_seconds": round(r["train_seconds"])}))
PYEOF2
done
shasum -a 256 $A/runs/r1g-s0/source.pt $A/runs/r1g-s1/source.pt | tee $A/checkpoints-sha256.txt
for S in 0 1; do mkdir -p "$G/$A/runs/r1g-s$S"; cp $A/runs/r1g-s$S/source.json "$G/$A/runs/r1g-s$S/"; cp $A/runs/practice-r1g-s$S.log "$G/$A/runs/"; done
cp $A/checkpoints-sha256.txt $A/selftest.json $A/selftest.log $A/harness-selftest.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): torch and python versions; every printed self-test line verbatim; wall time per seed; the printed source.json line for both seeds (x of 200 for sums4 and grids5, fixed depth, v1_pass, nonzero_all, mix_mean_abs, gamma). Nothing here is a maze score.
PUSH: artifacts/claude-dir-r1g-20260928/runs (source.json and logs only, NOT .pt or resume.pt) artifacts/claude-dir-r1g-20260928/checkpoints-sha256.txt artifacts/claude-dir-r1g-20260928/selftest.json artifacts/claude-dir-r1g-20260928/selftest.log artifacts/claude-dir-r1g-20260928/harness-selftest.log
