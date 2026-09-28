COMMON RULES (helper R2g, Claude, wrote this task on 2026-09-28 for the Director; adapted from the H3 v2 queue files by helpers H3 and H10). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it after queue-r2g-1-practice.md has run and its report is committed. Do not run it while HELD.
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree. The job works in $HOME/premonition-r2g built by job 1 (same machine).
LOAD-LIGHT: no (four single-thread processes; two waves of two when `sysctl -n hw.ncpu` is under 10). TIME CAP: 330 minutes with four at once, 660 in two waves. LABEL: r2g-dev. MUST RUN ON THE SAME MACHINE AS queue-r2g-1-practice (it reads $HOME/premonition-r2g/.../runs/r2g-s{0,1}/source.pt).
WAIT: start only if origin/main has artifacts/claude-dir-r2g-tied-20260928/runs/r2g-s{0,1}/source.json with "v1_pass": true in both, AND artifacts/claude-fewex-20260927/EQ-DEV-GATE.json says PASS. Otherwise ABORT with WAITING.
WHY: PASSMARKS.md order step 3. The dev ladders of the equal-practice ruler with the harness UNEDITED: R2g practised and R2g fresh, seeds 0 and 1 (four runs; each k = 1..16,384, 2,048 updates per rung, both sleeps). The baseline's dev jobs took about 169 minutes with eight running together (RESULTS-EQ.md); expect about the same (untested). The harness refuses to overwrite a finished run; an interrupted run has no resume: delete that run's folder under eq-runs/ and start it again, and say so.
NO CHANGE of any kind is allowed after a dev score is seen. This job records dev, then runs the swap and tie credit checks on the DEV panel. The holdout is NOT touched.
STOP RULE: any traceback: report the first one verbatim, run nothing else.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-r2g
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
A=artifacts/claude-dir-r2g-tied-20260928
for S in 0 1; do git -C "$G" show origin/main:$A/runs/r2g-s$S/source.json | grep -q '"v1_pass": true' || { echo "WAITING: no committed passing source.json for seed $S"; exit 5; }; done
git -C "$G" show origin/main:artifacts/claude-fewex-20260927/EQ-DEV-GATE.json | grep -q '"verdict": "PASS"' || { echo "WAITING: baseline gate not PASS"; exit 5; }
for S in 0 1; do [ -f "$W/$A/runs/r2g-s$S/source.pt" ] || { echo "ABORT: r2g-s$S source.pt missing in $W (run on the machine that ran job 1)"; exit 6; }; done
git -C "$G" archive origin/main scripts $A artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
NC=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
mkdir -p $A/eq-runs
ladder() {  # $1 seed, $2 init, $3 out name
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_r2g_net --arm loop --seed $1 --init $2 --source $A/runs/r2g-s$1 --out $A/eq-runs/$3 --threads 1 > $A/eq-runs/$3.log 2>&1 &
  echo "$3 pid $!"
}
if [ "$NC" -ge 10 ]; then
  for S in 0 1; do for I in pre fresh; do ladder $S $I h3-$I-s$S; done; done; wait
else
  for S in 0 1; do ladder $S pre h3-pre-s$S; done; wait
  for S in 0 1; do ladder $S fresh h3-fresh-s$S; done; wait
fi
# NOTE: run folders are named h3-pre-s* and h3-fresh-s* because scripts/claude_dir_h3_report_add1.py hard-codes those names ("h3" = the design under test = R2g).
for N in h3-pre-s0 h3-pre-s1 h3-fresh-s0 h3-fresh-s1; do echo "== $N"; tail -1 $A/eq-runs/$N.log; ls $A/eq-runs/$N/adapt.json; done
python3 scripts/claude_dir_r2g_report.py --split dev --runs $A/eq-runs --loop "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre" --plain "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre" --out $A/dev-table.json
# credit checks on DEV: swap gap of the design; the loop's too if its k1024.pt survives on this machine (search below; never rebuilt)
for S in 0 1; do
  $PY scripts/claude_dir_r2g_swapcheck.py score --plugin claude_dir_r2g_net --run-dir $A/eq-runs/h3-pre-s$S --k 1024 --out $A/eq-runs/swap-design-s$S.json --threads 1
  LR=$(find "$HOME" -maxdepth 6 -path "*eq-runs/loop-s$S-pre/k1024.pt" 2>/dev/null | head -1)
  if [ -n "$LR" ]; then $PY scripts/claude_dir_r2g_swapcheck.py score --plugin claude_fewex_net --run-dir "$(dirname "$LR")" --k 1024 --out $A/eq-runs/swap-loop-s$S.json --threads 1; else echo "no loop k1024.pt found for seed $S: symmetry credit not checked"; fi
  $PY - $A/eq-runs/h3-pre-s$S/k1024.pt <<'PYEOF'
import sys, json, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=True)
print(json.dumps({"ckpt": sys.argv[1], "mean_abs_tie": {k: round(float(v.abs().mean()), 5) for k, v in sd.items() if k.endswith(".tie")}}))
PYEOF
done
shasum -a 256 $A/eq-runs/h3-*-s*/*.pt > $A/eq-runs/checkpoints-dev-sha256.txt
for D in $A/eq-runs/h3-*-s?/; do mkdir -p "$G/$D"; cp $D/adapt.json "$G/$D/"; done
cp $A/eq-runs/*.log $A/eq-runs/swap-*.json $A/eq-runs/checkpoints-dev-sha256.txt "$G/$A/eq-runs/" 2>/dev/null; cp $A/dev-table.json "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): wall time per run; the dev-table lines per seed (F_eq of R2g, fresh R2g, loop, plain, R2g minus loop, F_few of R2g and of the loop) and the 9x9 dev counts per rung (x of 300) for the four runs from dev-table.json; mean rounds and cap hits per rung; the swap-check lines (original, swapped, gap of 300; say when the loop's is missing); the mean |tie| lines. Do NOT judge against PASSMARKS: dev numbers are not a verdict.
PUSH: artifacts/claude-dir-r2g-tied-20260928/dev-table.json artifacts/claude-dir-r2g-tied-20260928/eq-runs   (adapt.json, logs, swap json, sha256 list; NOT the .pt files)
