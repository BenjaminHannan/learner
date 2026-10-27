COMMON RULES (helper R2g, Claude, wrote this task on 2026-09-28 for the Director; adapted from the H3 v2 queue files by helpers H3 and H10). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it after queue-r2g-2-dev.md's dev records are committed and, one of: artifacts/claude-dir-r2g-tied-20260928/sleep-draws/sleep-draws-s0.json and -s1.json on origin/main, OR the Director's artifacts/claude-dir-r2g-tied-20260928/SLEEPS-SKIPPED.txt on origin/main. Do not run it while HELD.
GPU: no (CPU only, fp32). DISK: 2.
WORKDIR: run from the git worktree; works in $HOME/premonition-r2g (same machine as jobs 1 and 2).
LOAD-LIGHT: no (four single-thread processes; two waves of two under 10 cores). TIME CAP: 120 minutes with four at once, 240 in two waves. LABEL: r2g-holdout. MUST RUN ON THE SAME MACHINE AS JOBS 1 AND 2.
WAIT: start only if origin/main has artifacts/claude-dir-r2g-tied-20260928/dev-table.json and the four eq-runs/{h3-pre,h3-fresh}-s{0,1}/adapt.json, AND the sleep-draws or SLEEPS-SKIPPED.txt condition above. Otherwise ABORT with WAITING. ABORT if any eq-runs/*/holdout.started exists locally: a holdout is never re-opened after a partial run.
WHY: PASSMARKS.md order step 5. The one holdout pass per run (four runs), harness UNEDITED (`holdout` refuses unless the baseline's EQ-DEV-GATE.json says PASS, and refuses a second pass). Then the verdict arithmetic by scripts/claude_dir_r2g_report.py. Nothing is changed, tuned or re-run after these scores.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-r2g
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
A=artifacts/claude-dir-r2g-tied-20260928
git -C "$G" show origin/main:$A/dev-table.json > /dev/null || { echo "WAITING: dev-table.json not on main"; exit 5; }
for N in h3-pre-s0 h3-pre-s1 h3-fresh-s0 h3-fresh-s1; do git -C "$G" show origin/main:$A/eq-runs/$N/adapt.json > /dev/null || { echo "WAITING: adapt.json $N not on main"; exit 5; }; done
DRAWS=""
if git -C "$G" show origin/main:$A/sleep-draws/sleep-draws-s0.json > /dev/null 2>&1 && git -C "$G" show origin/main:$A/sleep-draws/sleep-draws-s1.json > /dev/null 2>&1; then
  DRAWS="--sleep-draws $A/sleep-draws"; echo "sleep draws found on main: row 5 judged on the three-draw means"
elif git -C "$G" show origin/main:$A/SLEEPS-SKIPPED.txt > /dev/null 2>&1; then
  echo "SLEEPS-SKIPPED.txt found on main: row 5 is report-only"
else
  echo "WAITING: neither the sleep-draws files nor SLEEPS-SKIPPED.txt is on main"; exit 5
fi
cd "$W" || exit 4
ls $A/eq-runs/*/holdout.started 2>/dev/null && { echo "ABORT: a holdout was already started"; exit 7; }
[ -n "$DRAWS" ] && { git -C "$G" archive origin/main $A/sleep-draws | tar -x -C "$W" || exit 4; }
git -C "$G" archive origin/main scripts artifacts/claude-fewex-20260927/EQ-DEV-GATE.json | tar -x -C "$W" || exit 4
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
NC=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
hold() {  # $1 seed, $2 init, $3 run name
  nohup perl -e 'alarm shift; exec @ARGV' 6600 $PY scripts/claude_fewex_eq_bench.py holdout --plugin claude_dir_r2g_net --arm loop --seed $1 --init $2 --out $A/eq-runs/$3 --threads 1 > $A/eq-runs/$3.holdout.log 2>&1 &
  echo "holdout $3 pid $!"
}
if [ "$NC" -ge 10 ]; then
  for S in 0 1; do for I in pre fresh; do hold $S $I h3-$I-s$S; done; done; wait
else
  for S in 0 1; do hold $S pre h3-pre-s$S; done; wait
  for S in 0 1; do hold $S fresh h3-fresh-s$S; done; wait
fi
for N in h3-pre-s0 h3-pre-s1 h3-fresh-s0 h3-fresh-s1; do echo "== $N"; tail -1 $A/eq-runs/$N.holdout.log; ls $A/eq-runs/$N/holdout.json; done
SW=""; [ -f $A/eq-runs/swap-design-s0.json ] && SW="--swap-design $A/eq-runs/swap-design-s{seed}.json"; [ -f $A/eq-runs/swap-loop-s0.json ] && SW="$SW --swap-loop $A/eq-runs/swap-loop-s{seed}.json"
python3 scripts/claude_dir_r2g_report.py --split holdout --runs $A/eq-runs --loop "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre" --plain "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre" $DRAWS $SW --out $A/holdout-table.json
for D in $A/eq-runs/h3-*-s?/; do cp $D/holdout.json "$G/$D/" 2>/dev/null; done
cp $A/eq-runs/*.holdout.log "$G/$A/eq-runs/"; cp $A/holdout-table.json "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
NOTE for the Director (not a step): the swap-check files come from job 2 (dev panel), so they exist whether or not the holdout has run; the tie files are in job 2's report.
REPORT (final reply): the printed lines and the verdict and symmetry lines verbatim; the 9x9 holdout counts per rung (x of 300) for R2g, fresh R2g and the loop, per seed; the failing rows per seed; F_few per arm. Labels: shown for what the files say, suggested for causes, untested for the rest. Do not soften a REJECTED or NOT PROMOTED.
PUSH: artifacts/claude-dir-r2g-tied-20260928/holdout-table.json artifacts/claude-dir-r2g-tied-20260928/eq-runs   (holdout.json and logs only)
